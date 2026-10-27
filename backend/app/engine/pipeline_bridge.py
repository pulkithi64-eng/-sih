"""Thin bridge to the document-AI pipeline (app/pipeline, owned by the AI module) and the
issuing-authority adapters (app/adapters).

Every call is wrapped so that a missing module or a failing stage never breaks the upload
(the caller records MANUAL_REVIEW_REQUIRED + an error note). Minimal fallbacks keep the
service usable before/without the AI modules.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("verisense.pipeline")


def _mod(name: str):
    try:
        return importlib.import_module(name)
    except ImportError as e:  # module not present yet / optional dependency missing
        log.debug("pipeline module %s unavailable: %s", name, e)
        return None
    except Exception as e:  # noqa: BLE001 - broken module must not break the service
        log.warning("pipeline module %s failed to import: %s", name, e)
        return None


def to_plain(obj: Any) -> Any:
    """dataclass / pydantic / namedtuple / plain -> JSON-able python structure."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return to_plain(dataclasses.asdict(obj))
    if hasattr(obj, "model_dump"):
        return to_plain(obj.model_dump(by_alias=True))
    if hasattr(obj, "_asdict"):
        return to_plain(obj._asdict())
    if isinstance(obj, dict):
        return {str(k): to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_plain(v) for v in obj]
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.hex()
    if hasattr(obj, "item"):  # numpy scalar
        try:
            return obj.item()
        except Exception:  # noqa: BLE001
            pass
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "__dict__"):
        return to_plain(vars(obj))
    return str(obj)


def available() -> dict[str, bool]:
    names = ["ocr", "classify", "extract", "forensics", "hashing", "qr", "signature", "infra_cv"]
    out = {n: _mod(f"app.pipeline.{n}") is not None for n in names}
    out["adapters"] = _registry() is not None
    return out


# ------------------------------------------------------------------ hashing
def sha256(path: str) -> str:
    m = _mod("app.pipeline.hashing")
    if m and hasattr(m, "sha256"):
        return str(m.sha256(path))
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def phash(path: str) -> str | None:
    m = _mod("app.pipeline.hashing")
    if m and hasattr(m, "phash"):
        v = m.phash(path)
        return str(v) if v is not None else None
    raise RuntimeError("perceptual hashing module not available")


# ------------------------------------------------------------------ OCR
def extract_text(path: str) -> dict:
    m = _mod("app.pipeline.ocr")
    if m and hasattr(m, "extract_text"):
        r = to_plain(m.extract_text(path)) or {}
        return r
    # fallback: PDF text layer via PyMuPDF if installed
    if path.lower().endswith(".pdf"):
        fitz = _mod("fitz")
        if fitz:
            with fitz.open(path) as pdf:
                texts = [p.get_text() for p in pdf]
            return {"text": "\n".join(texts), "pages": len(texts), "method": "pdf-text", "confidence": 1.0, "blocks": []}
    raise RuntimeError("OCR module not available")


# ------------------------------------------------------------------ classify
_FALLBACK_HINTS = {
    "FIRE_NOC": ["fire"], "TER_PAYMENT_RECEIPT": ["ter", "payment", "receipt"], "FACULTY_ROSTER": ["faculty", "roster"],
    "AFFIDAVIT_UNDERTAKING": ["affidavit", "undertaking"], "PREVIOUS_EOA_LETTER": ["eoa", "approval"],
    "NBA_ACCREDITATION": ["nba"], "NAAC_ACCREDITATION": ["naac"], "OCCUPANCY_CERTIFICATE": ["occupancy"],
    "LAND_DOCUMENT": ["land"], "UNIVERSITY_AFFILIATION": ["affiliation", "university"],
    "BUILDING_PLAN_APPROVAL": ["building"], "FLOOR_PLAN": ["floor"], "INFRA_PHOTO_COMPUTER_LAB": ["computer", "lab"],
    "INFRA_PHOTO_CLASSROOM": ["classroom"], "INFRA_PHOTO_LIBRARY": ["library"],
}


def classify(text: str, filename: str) -> dict:
    m = _mod("app.pipeline.classify")
    if m and hasattr(m, "classify"):
        return to_plain(m.classify(text, filename)) or {}
    name = filename.lower()
    best, score = "OTHER", 0
    for dt, kws in _FALLBACK_HINTS.items():
        s = sum(1 for k in kws if k in name or k in (text or "").lower()[:2000])
        if s > score:
            best, score = dt, s
    return {"docType": best, "confidence": min(0.4 + 0.15 * score, 0.69) if score else 0.1,
            "signals": [f"fallback keyword classifier (score {score})"]}


# ------------------------------------------------------------------ extract
def extract_fields(doc_type: str, text: str) -> dict:
    m = _mod("app.pipeline.extract")
    if m and hasattr(m, "extract_fields"):
        return to_plain(m.extract_fields(doc_type, text)) or {}
    raise RuntimeError("field extraction module not available")


# ------------------------------------------------------------------ forensics
def analyse_forensics(path: str, out_dir: str | None = None) -> dict:
    m = _mod("app.pipeline.forensics")
    if m and hasattr(m, "analyse"):
        try:
            return to_plain(m.analyse(path, out_dir)) or {}
        except TypeError:  # older signature analyse(path)
            return to_plain(m.analyse(path)) or {}
    raise RuntimeError("forensics module not available")


# ------------------------------------------------------------------ QR + signature
def decode_qr(path: str) -> list[str]:
    m = _mod("app.pipeline.qr")
    if m and hasattr(m, "decode_qr"):
        return [str(p) for p in (m.decode_qr(path) or [])]
    raise RuntimeError("QR module not available")


def verify_signed_payload(payload: str) -> dict:
    m = _mod("app.pipeline.signature")
    if m and hasattr(m, "verify_signed_payload"):
        return to_plain(m.verify_signed_payload(payload)) or {}
    raise RuntimeError("signature module not available")


# ------------------------------------------------------------------ infra
def analyse_infra(path: str, evidence_type: str, **kwargs) -> dict:
    m = _mod("app.pipeline.infra_cv")
    if m and hasattr(m, "analyse_infra"):
        try:
            return to_plain(m.analyse_infra(path, evidence_type, **kwargs)) or {}
        except TypeError:  # older signature analyse_infra(path, evidence_type)
            return to_plain(m.analyse_infra(path, evidence_type)) or {}
    raise RuntimeError("infrastructure CV module not available")


# ------------------------------------------------------------------ adapters
def _registry():
    m = _mod("app.adapters")
    if m is None:
        return None
    reg = getattr(m, "registry", None)
    if reg is None:
        reg = _mod("app.adapters.registry")
    return reg


def verify_with_source(doc_type: str, reference_no: str | None, extracted: dict, qr_claims: Any,
                       today=None) -> dict:
    """Returns the adapter verdict. `_fallback: True` marks the built-in fallback (no adapters installed)."""
    reg = _registry()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if reg is None or not hasattr(reg, "verify"):
        return {"status": "MANUAL_REVIEW_REQUIRED", "method": "MANUAL", "checkedAt": now, "_fallback": True,
                "reason": "No issuing-authority adapter available in this deployment"}
    if today is not None:
        try:
            return to_plain(reg.verify(doc_type, reference_no, extracted, qr_claims, today=today)) or {}
        except TypeError:
            pass
    return to_plain(reg.verify(doc_type, reference_no, extracted, qr_claims)) or {}


def list_sources() -> list[dict]:
    reg = _registry()
    if reg is None or not hasattr(reg, "list_sources"):
        return []
    return to_plain(reg.list_sources()) or []


def set_source_online(source_id: str, online: bool) -> dict | None:
    reg = _registry()
    if reg is None or not hasattr(reg, "set_online"):
        return None
    res = reg.set_online(source_id, online)
    res = to_plain(res)
    if isinstance(res, dict):
        return res
    return next((s for s in list_sources() if s.get("id") == source_id), None)


# ------------------------------------------------------------------ helpers
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}")


def norm_date(v: Any) -> str | None:
    """Return YYYY-MM-DD if parsable."""
    if v is None:
        return None
    s = str(v).strip()
    if _ISO.match(s):
        return s[:10]
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None
