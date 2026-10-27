"""Document-AI pipeline (pure functions, no DB access).

Modules: ocr, classify, extract, forensics, hashing, qr, signature, infra_cv.
`process_document` runs contract section 6 steps 1-6 and 8 for one file (step 7, issuing-authority verification,
is optional here via `verify_source=True` and otherwise done by the caller through app.adapters.registry).
"""
from __future__ import annotations

import time
from datetime import date
from pathlib import Path

INFRA_TYPES = {"INFRA_PHOTO_CLASSROOM", "INFRA_PHOTO_COMPUTER_LAB", "INFRA_PHOTO_LIBRARY",
               "INFRA_PHOTO_LABORATORY", "INFRA_PHOTO_ACCESSIBILITY"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
MISMATCH_CONFIDENCE = 0.7


def _value(fields: dict, name: str):
    f = fields.get(name)
    return f.get("value") if isinstance(f, dict) else None


def process_document(path: str | Path, filename: str | None = None, declared_doc_type: str | None = None,
                     campus_gps: dict | None = None, out_dir: str | Path | None = None,
                     verify_source: bool = False, today: date | None = None) -> dict:
    """Run the per-document pipeline. Returns a dict shaped like contract `Document` (minus DB ids):

    {sha256, phash, ocr{method, confidence, pageCount, textPreview}, text, blocks, classification{docType, confidence,
     signals}, docType, classificationMismatch?, extractedFields, issuer, referenceNo, issueDate, expiryDate,
     forensics{elaScore, hasElaHeatmap, elaHeatmapPath, metadata, flags}, qr[{payload, valid, issuer, keyId, claims, reason}],
     infra?, verification?, timings{step: seconds}}
    """
    from . import classify as _classify
    from . import extract, forensics, hashing, infra_cv, ocr, qr, signature

    path = Path(path)
    filename = filename or path.name
    timings: dict[str, float] = {}

    def timed(name, fn, *a, **kw):
        t0 = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            timings[name] = round(time.perf_counter() - t0, 3)

    sha = timed("sha256", hashing.sha256, path)
    ph = timed("phash", hashing.phash, path)
    o = timed("ocr", ocr.extract_text, path)
    cls = timed("classify", _classify.classify, o["text"], filename)
    doc_type = declared_doc_type or cls["docType"]
    mismatch = None
    if declared_doc_type and cls["docType"] != declared_doc_type and cls["confidence"] > MISMATCH_CONFIDENCE:
        mismatch = {"declared": declared_doc_type, "predicted": cls["docType"], "confidence": cls["confidence"],
                    "signals": cls["signals"]}
    fields = timed("extract", extract.extract_fields, doc_type, o["text"], o["confidence"])
    fx = timed("forensics", forensics.analyse, path, out_dir)
    payloads = timed("qr", qr.decode_qr, path) if path.suffix.lower() in IMAGE_EXT | {".pdf"} else []
    qr_results = [{"payload": p, **signature.verify_signed_payload(p)} for p in payloads]

    result = {
        "fileName": filename,
        "sha256": sha,
        "phash": ph,
        "ocr": {"method": o["method"], "confidence": o["confidence"], "pageCount": o["pageCount"],
                "textPreview": o["text"].replace("\f", "\n")[:600]},
        "text": o["text"],
        "blocks": o["blocks"],
        "pageSizes": o.get("pageSizes"),
        "classification": {"docType": cls["docType"], "confidence": cls["confidence"], "signals": cls["signals"]},
        "docType": doc_type,
        "classificationMismatch": mismatch,
        "extractedFields": fields,
        "issuer": _value(fields, "issuer"),
        "referenceNo": _value(fields, "referenceNo") or _value(fields, "udin"),
        "issueDate": _value(fields, "issueDate"),
        "expiryDate": _value(fields, "expiryDate"),
        "forensics": {"elaScore": fx.get("elaScore"), "hasElaHeatmap": bool(fx.get("elaHeatmapPath")),
                      "elaHeatmapPath": fx.get("elaHeatmapPath"), "metadata": fx.get("metadata", {}),
                      "flags": fx.get("flags", [])},
        "qr": qr_results,
        "infra": None,
        "verification": None,
        "timings": timings,
    }
    if doc_type in INFRA_TYPES and path.suffix.lower() in IMAGE_EXT:
        result["infra"] = timed("infra", infra_cv.analyse_infra, path, doc_type, campus_gps, ref_date=today)
    if verify_source:
        from app.adapters import registry

        result["verification"] = timed("verify", registry.verify, doc_type, result["referenceNo"], fields,
                                       [{k: v for k, v in r.items() if k != "payload"} for r in qr_results], today)
    timings["total"] = round(sum(v for k, v in timings.items() if k != "total"), 3)
    return result
