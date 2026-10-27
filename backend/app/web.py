"""Serve the built SPA beside the API when running as a single hosted service."""
from pathlib import Path
import re

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        path = path.replace("\\", "/")
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            # Missing APIs and assets must stay 404s, not receive index.html.
            if exc.status_code != 404 or path.split("/", 1)[0] in {"api", "mock", "assets"} or Path(path).suffix:
                raise
            response = await super().get_response("index.html", scope)
        # Only content-fingerprinted build assets can safely use immutable caching.
        # HTML must revalidate so deployments pick up the new asset manifest.
        suffix = Path(path).suffix.lower()
        if not suffix or suffix == ".html" or response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache"
        elif path.startswith("assets/") and re.search(r"-[A-Za-z0-9_-]{8,}\.[a-z0-9.]+$", Path(path).name):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response


def mount_frontend(app: FastAPI, directory: str):
    root = Path(directory)
    if not (root / "index.html").is_file():
        raise RuntimeError(f"Frontend build missing from {root}")
    # Compress only public static files, never authenticated JSON/documents.
    app.mount("/", GZipMiddleware(SPAStaticFiles(directory=root, html=True), minimum_size=1000, compresslevel=6), name="frontend")
