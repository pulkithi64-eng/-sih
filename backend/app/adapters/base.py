"""Issuing-authority adapter base class + field comparison helpers.

An adapter looks a document up at its issuing authority by reference number and compares authority-held fields
with the fields extracted from the submitted document. In this prototype the authorities are SIMULATED services
(app/mock_authorities, mounted at /mock); a production adapter would call the authorised API (DigiLocker
Issuer/Requester APIs, NBA/NAAC registries, state land-record and fire-NOC portals, ICAI UDIN, AICTE TER gateway).

Transport: HTTP via httpx to VERISENSE_MOCK_BASE (default http://localhost:8001/mock). VERISENSE_MOCK_MODE:
  auto      (default) HTTP; if the server is not reachable (connection refused) fall back to an in-process call
  http      HTTP only (connection failure -> SOURCE_UNAVAILABLE)
  inprocess direct function call into app.mock_authorities.service (tests / seed)
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from difflib import SequenceMatcher
from urllib.parse import quote

from . import state

DEFAULT_BASE = "http://localhost:8001/mock"


@dataclass
class SourceResponse:
    status_code: int          # 200 found, 202 pending, 404 not found, 503 unavailable, 0 transport failure, -1 timeout
    body: dict
    latency_ms: float
    transport: str            # "http" | "inprocess"
    error: str | None = None


# ----------------------------------------------------------------------------- comparison helpers
def _norm_text(s) -> str:
    s = str(s).casefold().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _as_number(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(re.sub(r"(?i)rs\.?|inr|₹|/-|,|\s", "", str(v)))
    except ValueError:
        return None


def _as_date(v):
    if v is None:
        return None
    s = str(v)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s[:10]):
        return s[:10]
    from app.pipeline.extract import parse_date

    return parse_date(s)


DATE_FIELDS = {"issueDate", "expiryDate", "validFrom", "notarisedOn", "paymentDate"}
NUMERIC_FIELDS = {"landAreaAcres", "builtUpAreaSqm", "totalIntake", "amount", "cgpa", "facultyCount", "interestRate"}


def compare_values(name: str, submitted, source) -> bool:
    if submitted is None or source is None:
        return False
    if name in DATE_FIELDS:
        return _as_date(submitted) == _as_date(source)
    if name in NUMERIC_FIELDS:
        a, b = _as_number(submitted), _as_number(source)
        if a is None or b is None:
            return _norm_text(submitted) == _norm_text(source)
        return abs(a - b) <= max(0.005 * abs(b), 0.01)
    if isinstance(submitted, (list, tuple)) or isinstance(source, (list, tuple)):
        sa = {_norm_text(x) for x in (submitted if isinstance(submitted, (list, tuple)) else [submitted])}
        sb = {_norm_text(x) for x in (source if isinstance(source, (list, tuple)) else [source])}
        return sa == sb
    a, b = _norm_text(submitted), _norm_text(source)
    if a == b:
        return True
    if name in ("surveyNo", "referenceNo", "permanentId", "membershipNo", "grade", "academicYear", "financialYear"):
        return a.replace(" ", "") == b.replace(" ", "")
    if len(a) >= 10 and len(b) >= 10 and (a in b or b in a):
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.9


def build_comparisons(fields: list[str], submitted: dict, source: dict) -> list[dict]:
    out = []
    for f in fields:
        sv = submitted.get(f)
        if isinstance(sv, dict) and "value" in sv:
            sv = sv["value"]
        src = source.get(f)
        if sv in (None, "") or src in (None, ""):
            continue
        out.append({"field": f, "submitted": sv, "source": src, "match": compare_values(f, sv, src)})
    return out


def is_past(iso: str | None, today: date) -> bool:
    d = _as_date(iso)
    if not d:
        return False
    try:
        return datetime.fromisoformat(d).date() < today
    except ValueError:
        return False


# ----------------------------------------------------------------------------- adapter
@dataclass
class Adapter:
    id: str
    name: str
    issuer: str
    doc_types: list[str]
    method: str                                  # API | DIGILOCKER | PORTAL
    paths: dict[str, str]                        # docType -> path template under the mock base ("{ref}")
    compare: dict[str, list[str]] = field(default_factory=dict)  # docType -> fields compared with source
    ref_field: str = "referenceNo"
    description: str = ""

    # -- reference used for the lookup
    def reference_for(self, doc_type: str, reference_no: str | None, extracted: dict) -> tuple[str | None, float]:
        ef = extracted.get(self.ref_field) if self.ref_field != "referenceNo" else None
        if isinstance(ef, dict) and ef.get("value"):
            return str(ef["value"]), float(ef.get("confidence", 0.8))
        if reference_no:
            rf = extracted.get("referenceNo")
            conf = float(rf.get("confidence", 0.85)) if isinstance(rf, dict) else 0.85
            return str(reference_no), conf
        rf = extracted.get("referenceNo")
        if isinstance(rf, dict) and rf.get("value"):
            return str(rf["value"]), float(rf.get("confidence", 0.8))
        return None, 0.0

    @property
    def online(self) -> bool:
        return state.is_online(self.id)

    def info(self) -> dict:
        st = state.stats(self.id)
        calls = st.get("calls", 0)
        return {"id": self.id, "name": self.name, "issuer": self.issuer, "docTypes": list(self.doc_types),
                "method": self.method, "online": self.online, "lastLatencyMs": st.get("lastLatencyMs"),
                "successRate": round(st["successes"] / calls, 3) if calls else None, "calls": calls,
                "lastCheckedAt": st.get("lastCheckedAt"), "description": self.description,
                "simulated": True}

    # -- transport
    def lookup(self, doc_type: str, ref: str) -> SourceResponse:
        path = self.paths.get(doc_type) or next(iter(self.paths.values()))
        path = path.format(ref=quote(ref, safe=""))
        mode = os.environ.get("VERISENSE_MOCK_MODE", "auto").lower()
        base = os.environ.get("VERISENSE_MOCK_BASE", DEFAULT_BASE).rstrip("/")
        t0 = time.perf_counter()
        if mode in ("auto", "http"):
            import httpx

            try:
                r = httpx.get(base + path, timeout=httpx.Timeout(float(os.environ.get("VERISENSE_MOCK_TIMEOUT", "5")), connect=1.5))
                try:
                    body = r.json()
                except ValueError:
                    body = {"raw": r.text[:300]}
                return SourceResponse(r.status_code, body, (time.perf_counter() - t0) * 1000, "http")
            except httpx.TimeoutException as exc:
                if isinstance(exc, httpx.ConnectTimeout) and mode == "auto":
                    pass
                else:
                    return SourceResponse(-1, {}, (time.perf_counter() - t0) * 1000, "http", f"timeout: {exc}")
            except httpx.TransportError as exc:
                if mode == "http":
                    return SourceResponse(0, {}, (time.perf_counter() - t0) * 1000, "http", f"connection failed: {exc}")
        from app.mock_authorities import service

        t0 = time.perf_counter()
        code, body = service.lookup(self.id, doc_type, ref)
        return SourceResponse(code, body, (time.perf_counter() - t0) * 1000, "inprocess")
