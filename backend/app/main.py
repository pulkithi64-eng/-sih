"""AICTE VeriSense API — FastAPI app, CORS, routers, startup seeding."""
from __future__ import annotations

import importlib
import logging
import os
import shutil
import time
import re
import uuid
import tempfile
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import VERSION, get_settings
from .db import get_engine, init_db
from .security import require_admin
from .tracing import request_id
from .routers import (
    alerts,
    applications,
    audit_log,
    auth,
    dashboard,
    documents,
    findings,
    institutions,
    meta,
    rules,
    sources,
)

log = logging.getLogger("verisense")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_START_TIME = time.time()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    s = get_settings()
    if s.autoseed:
        try:
            from seed.seed import seed_if_empty

            seed_if_empty()
        except Exception:  # noqa: BLE001 - never block startup on demo data
            log.exception("auto-seed failed")
    yield


app = FastAPI(
    title="AICTE VeriSense API",
    version=VERSION,
    description="AI-assisted application validation, document authentication and compliance verification "
                "(SIH 2026 prototype, PS 26261). All outputs are advisory decision support.",
    lifespan=lifespan,
)


@app.middleware("http")
async def correlate_request(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID", "")
    rid = supplied if re.fullmatch(r"[A-Za-z0-9_-]{8,64}", supplied) else uuid.uuid4().hex
    request.state.request_id = rid
    token = request_id.set(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response
    finally:
        request_id.reset(token)

# Security Response Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
    # CSP: Allow self and fonts from Google
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "connect-src 'self' *; "
        "frame-src 'self' blob:; "
        "frame-ancestors 'none';"
    )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
)


# Standardized Exception Handlers for API Reliability
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_req: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field_path = ".".join(str(loc) for loc in err.get("loc", []) if loc != "body")
        errors.append({"field": field_path, "message": err.get("msg")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Input validation failed. Please check the submitted fields.",
            "code": "VALIDATION_ERROR",
            "requestId": getattr(_req.state, "request_id", None),
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_req: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": f"HTTP_{exc.status_code}",
            "requestId": getattr(_req.state, "request_id", None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled(_req: Request, exc: Exception):  # pragma: no cover - safety net
    log.error("unhandled error request_id=%s type=%s", getattr(_req.state, "request_id", None), type(exc).__name__)
    return JSONResponse(
        status_code=500,
        headers={"X-Request-ID": getattr(_req.state, "request_id", "unknown"), "Cache-Control": "no-store"},
        content={
            "detail": "An internal service error occurred. Please contact the system administrator.",
            "code": "INTERNAL_SERVER_ERROR",
            "requestId": getattr(_req.state, "request_id", None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


api = APIRouter(prefix="/api")


# --- Deployment Reliability Probes ---
@api.get("/health", tags=["meta"])
def health():
    from .engine.pipeline_bridge import available

    return {
        "status": "ok",
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline": available(),
    }


@api.get("/health/live", tags=["meta"])
def health_live():
    """Kubernetes / Container Liveness probe."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@api.get("/health/ready", tags=["meta"])
def health_ready():
    """Kubernetes / Container Readiness probe."""
    checks = {}
    is_ready = True

    # 1. Database check
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = "unhealthy"
        is_ready = False

    # 2. Storage write check
    try:
        storage_p = get_settings().storage_path
        with tempfile.TemporaryFile(dir=storage_p) as test_file:
            test_file.write(b"ok")
            test_file.flush()
        checks["storage"] = "healthy"
    except Exception as e:
        checks["storage"] = "unhealthy"
        is_ready = False

    # 3. Rules load check
    try:
        from .engine.rules_loader import load_rules
        rules_list = load_rules()
        checks["rules"] = f"loaded_{len(rules_list)}_rules"
    except Exception as e:
        checks["rules"] = "unhealthy"
        is_ready = False

    status_code = 200 if is_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": is_ready,
            "version": VERSION,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@api.get("/health/system", tags=["meta"], dependencies=[Depends(require_admin)])
def health_system():
    """Detailed system diagnostic for administration & monitoring."""
    uptime_seconds = int(time.time() - _START_TIME)
    storage_p = get_settings().storage_path

    storage_usage = {}
    try:
        total, used, free = shutil.disk_usage(str(storage_p))
        storage_usage = {
            "totalBytes": total,
            "usedBytes": used,
            "freeBytes": free,
            "freePercent": round((free / total) * 100, 1) if total else 0,
        }
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": VERSION,
        "uptimeSeconds": uptime_seconds,
        "storage": storage_usage,
        "environment": {
            "referenceDate": get_settings().reference_date,
            "autoseed": get_settings().autoseed,
            "ocrThreads": get_settings().ocr_threads,
            "jwtExpiryHours": get_settings().jwt_expiry_hours,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


for r in (auth, meta, dashboard, applications, documents, findings, alerts, audit_log, rules, sources, institutions):
    api.include_router(r.router)
app.include_router(api)

# simulated issuing-authority services (AI module); optional until it lands
try:
    _mock = importlib.import_module("app.mock_authorities")
    if get_settings().demo_mode:
        app.include_router(getattr(_mock, "router"), prefix="/mock")
except Exception as _e:  # noqa: BLE001
    log.info("mock authorities not mounted: %s", _e)

# Mount after API/mock routes so /portal/* deep links share the same origin.
if get_settings().frontend_dir:
    from .web import mount_frontend

    mount_frontend(app, get_settings().frontend_dir)
