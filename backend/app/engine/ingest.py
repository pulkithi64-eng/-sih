"""Document ingestion service (contract section 6). Used by the upload API AND the seeder.

Every stage is isolated: a failure is recorded on the document (pipeline_errors), the
verification falls back to MANUAL_REVIEW_REQUIRED and an audit event notes the error.
"""
from __future__ import annotations

import logging
import mimetypes
import re
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from .. import audit
from ..config import get_settings
from ..models import Application, Document, Finding, User
from . import pipeline_bridge as pb
from .doc_findings import document_findings
from .fields import get_date, get_field, get_value, similarity, to_number
from .rules_loader import doc_type_label, infra_evidence_type, load_doc_types, load_rules

log = logging.getLogger("verisense.ingest")

VALID_DOC_TYPES = None


def _valid_doc_types() -> set[str]:
    return set(load_doc_types().keys())


def _safe_name(name: str) -> str:
    base = Path(name or "upload").name
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)[:120] or "upload"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    import calendar

    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


# ------------------------------------------------------------------ findings persistence
def sync_findings(db: Session, app: Application, generated: list[dict], document_id: int | None = None,
                  origin: str = "VALIDATOR", fingerprint_prefixes: tuple[str, ...] | None = None) -> dict:
    """Idempotently replace auto-generated OPEN findings, keeping human-modified ones.

    Scope: all findings of the application (validator) or only one document's (upload).
    Returns {created, removed, kept}.
    """
    existing = [f for f in app.findings if document_id is None or f.document_id == document_id]
    if fingerprint_prefixes:
        existing = [f for f in existing if f.fingerprint.startswith(fingerprint_prefixes)]
    kept_fps = set()
    removed = 0
    for f in list(existing):
        human = f.human_modified or f.status != "OPEN" or f.origin == "OFFICER"
        if human:
            kept_fps.add(f.fingerprint)
        else:
            app.findings.remove(f)
            db.delete(f)
            removed += 1
    created = 0
    seen = set()
    for g in generated:
        fp = g["fingerprint"]
        if fp in kept_fps or fp in seen:
            continue
        seen.add(fp)
        app.findings.append(Finding(
            application_id=app.id, document_id=g.get("document_id"), kind=g["kind"], severity=g["severity"],
            title=g["title"][:256], reason=g["reason"], rule_id=g.get("rule_id"), clause=g.get("clause"),
            evidence=pb.to_plain(g.get("evidence") or []), status="OPEN", fingerprint=fp, origin=origin,
        ))
        created += 1
    db.flush()
    return {"created": created, "removed": removed, "kept": len(kept_fps)}


# ------------------------------------------------------------------ QR
def _compare(claim_val, field_val) -> bool:
    d1, d2 = pb.norm_date(claim_val), pb.norm_date(field_val)
    if d1 and d2:
        return d1 == d2
    n1, n2 = to_number(claim_val), to_number(field_val)
    if n1 is not None and n2 is not None and not re.search(r"[A-Za-z]{2,}", f"{claim_val}{field_val}"):
        return abs(n1 - n2) <= max(1e-6, 0.005 * max(abs(n1), abs(n2)))
    return similarity(claim_val, field_val) >= 0.9


def _qr_stage(path: str, extracted: dict) -> tuple[dict, list[str]]:
    payloads = pb.decode_qr(path)
    qr = {"found": bool(payloads), "payloadCount": len(payloads), "signature": None, "claims": None, "comparisons": []}
    if not payloads:
        return qr, []
    results = []
    for p in payloads:
        try:
            results.append(pb.verify_signed_payload(p))
        except Exception as e:  # noqa: BLE001
            results.append({"valid": False, "reason": f"signature check failed: {e}"})
    qr["results"] = results
    best = next((r for r in results if r.get("valid")), results[0])
    qr["signature"] = {k: best.get(k) for k in ("valid", "issuer", "keyId", "reason")}
    claims = best.get("claims") or {}
    qr["claims"] = claims
    comps = []
    if isinstance(claims, dict):
        for k, cv in claims.items():
            if k in ("iss", "kid", "iat", "exp", "sig", "nonce", "v", "issuer", "keyId", "docType", "type"):
                continue
            fobj = get_field(extracted, k)
            if fobj is None or isinstance(cv, (dict, list)):
                continue
            comps.append({"field": k, "submitted": fobj.get("value"), "source": cv,
                          "match": _compare(cv, fobj.get("value"))})
    qr["comparisons"] = comps
    return qr, [f"QR payloads: {len(payloads)}, signature {'valid' if best.get('valid') else 'INVALID'}"]


def _merge_verification(doc_type: str, adapter: dict, qr: dict | None) -> dict:
    v = dict(adapter or {})
    v.setdefault("checkedAt", _now_iso())
    v.setdefault("comparisons", [])
    sig = (qr or {}).get("signature") or {}
    qr_comps = (qr or {}).get("comparisons") or []
    qr_bad = [c for c in qr_comps if c.get("match") is False]
    if qr and qr.get("found"):
        if sig.get("valid") is False:
            v.update(status="MISMATCH_DETECTED", method=v.get("method") or "QR_SIGNATURE",
                     reason=("QR code present but its digital signature is INVALID "
                             f"({sig.get('reason') or 'signature does not verify'}). "
                             + (v.get("reason") or "")).strip())
        elif qr_bad and v.get("status") in (None, "VERIFIED", "SOURCE_UNAVAILABLE", "MANUAL_REVIEW_REQUIRED",
                                            "VERIFICATION_PENDING", "NOT_APPLICABLE"):
            v.update(status="MISMATCH_DETECTED", method="QR_SIGNATURE",
                     reason="Signed QR claims from the issuer differ from the printed document: "
                            + ", ".join(f"{c['field']} (printed {c['submitted']!r} vs signed {c['source']!r})" for c in qr_bad))
            v["comparisons"] = list(v.get("comparisons") or []) + qr_bad
        elif sig.get("valid") and v.get("status") in ("SOURCE_UNAVAILABLE", "MANUAL_REVIEW_REQUIRED", None):
            # offline verification through the issuer-signed QR code
            v.update(status="VERIFIED", method="QR_SIGNATURE", source=v.get("source") or sig.get("issuer"),
                     reason=("Verified offline via issuer-signed QR (key " + str(sig.get("keyId")) + ")"
                             + ("; live source unavailable: " + adapter.get("reason") if adapter.get("reason") else "")),
                     comparisons=list(v.get("comparisons") or []) + qr_comps)
    dt_meta = load_doc_types().get(doc_type, {})
    if (v.get("status") == "MANUAL_REVIEW_REQUIRED" and not dt_meta.get("verifiable")
            and not (qr and qr.get("found"))):
        v.update(status="NOT_APPLICABLE", method=None,
                 reason="No issuing-authority source exists for this document type; covered by rule-based checks.")
    v.setdefault("status", "MANUAL_REVIEW_REQUIRED")
    return v


def doc_rules(db: Session) -> dict[str, dict]:
    """Rules that govern per-document findings, keyed for document_findings()."""
    out = {}
    for r in load_rules(db):
        if r["type"] in ("FORENSIC_FLAG", "SOURCE_VERIFICATION"):
            out[r["type"]] = r
        elif r["type"] == "INFRA_EVIDENCE" and (r.get("params") or {}).get("evidenceType") == "ANY":
            out["INFRA_ANY"] = r
    return out


def _verify(doc: Document, qr: dict | None) -> dict:
    """QR signature results are handed to the adapter registry, which owns the verdict logic.
    The local merge is only used when no adapter registry is installed."""
    from .validator import reference_today

    qr_results = (qr or {}).get("results") if (qr or {}).get("found") else None
    today = reference_today() if get_settings().reference_date else None
    adapter = pb.verify_with_source(doc.doc_type, doc.reference_no, doc.extracted_fields or {}, qr_results, today=today)
    if adapter.pop("_fallback", False):
        return _merge_verification(doc.doc_type, adapter, qr)
    adapter.setdefault("checkedAt", _now_iso())
    adapter.setdefault("status", "MANUAL_REVIEW_REQUIRED")
    if adapter.get("sourceName") and adapter.get("source"):
        adapter["sourceId"] = adapter["source"]
        adapter["source"] = adapter["sourceName"]
    return adapter


# ------------------------------------------------------------------ main entry
def ingest_document(db: Session, app: Application, data: bytes, filename: str, declared_doc_type: str | None,
                    actor: User | str, mime_type: str | None = None) -> Document:
    t0 = time.perf_counter()
    valid = _valid_doc_types()
    if declared_doc_type and declared_doc_type not in valid:
        raise ValueError(f"Unknown docType '{declared_doc_type}'")
    actor_name = actor.username if isinstance(actor, User) else str(actor)

    # 1. store
    store_dir = get_settings().storage_path / str(app.id)
    store_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_name(filename)
    path = store_dir / f"{uuid.uuid4().hex[:12]}_{safe}"
    path.write_bytes(data)
    mime = mime_type if mime_type and mime_type != "application/octet-stream" else (
        mimetypes.guess_type(safe)[0] or "application/octet-stream")
    doc = Document(
        application_id=app.id, doc_type=declared_doc_type or "OTHER", declared_doc_type=declared_doc_type,
        file_name=Path(filename).name, file_path=str(path), mime_type=mime, size_bytes=len(data),
        sha256=pb.sha256(str(path)), uploaded_by=actor_name, classification={}, ocr={}, extracted_fields={},
        verification={"status": "VERIFICATION_PENDING"}, forensics={"hasElaHeatmap": False, "metadata": {}, "flags": []},
        pipeline_errors=[],
    )
    app.documents.append(doc)
    db.flush()
    errors: list[dict] = []
    stage_log: list[dict] = []

    def stage(name: str, fn):
        ts = time.perf_counter()
        try:
            log.info("pipeline stage %s started document_id=%s", name, doc.id)
            summary = fn()
            log.info("pipeline stage %s completed document_id=%s", name, doc.id)
            ms = int((time.perf_counter() - ts) * 1000)
            stage_log.append({"stage": name, "ok": True, "ms": ms})
            audit.record(db, actor, "PIPELINE_STAGE", "Document", doc.id,
                         {"applicationId": app.id, "stage": name, "ok": True, "ms": ms, "summary": summary},
                         commit=False)
        except Exception as e:  # noqa: BLE001
            ms = int((time.perf_counter() - ts) * 1000)
            log.warning("pipeline stage %s failed document_id=%s error_type=%s", name, doc.id, type(e).__name__)
            errors.append({"stage": name, "error": f"{type(e).__name__}: {e}"[:300]})
            stage_log.append({"stage": name, "ok": False, "ms": ms})
            audit.record(db, actor, "PIPELINE_STAGE", "Document", doc.id,
                         {"applicationId": app.id, "stage": name, "ok": False, "ms": ms,
                          "summary": f"{name} failed — manual review required", "error": f"{type(e).__name__}: {e}"[:300]},
                         commit=False)

    audit.record(db, actor, "DOCUMENT_UPLOADED", "Document", doc.id,
                 {"applicationId": app.id, "applicationNo": app.application_no, "fileName": doc.file_name,
                  "declaredDocType": declared_doc_type, "sizeBytes": len(data), "sha256": doc.sha256}, commit=False)

    def s_hash():
        doc.phash = pb.phash(str(path))
        return f"Hashes computed: sha256 {doc.sha256[:12]}…, phash {doc.phash or 'n/a'}"

    ocr_state: dict = {"text": ""}

    def s_ocr():
        r = pb.extract_text(str(path))
        text = r.get("text") or ""
        blocks = r.get("blocks") or []
        pages = r.get("pages")
        page_count = pages if isinstance(pages, int) else (len(pages) if isinstance(pages, list) else r.get("pageCount", 1))
        ocr_state["text"] = text
        doc.ocr_text = text
        doc.ocr_blocks = blocks
        doc.ocr = {"method": r.get("method"), "confidence": r.get("confidence"), "pageCount": page_count,
                   "textPreview": text[:600]}
        return f"OCR completed: {page_count} page(s), method {r.get('method')}, {len(text)} chars"

    def s_classify():
        r = pb.classify(ocr_state["text"], doc.file_name)
        pred = r.get("docType") if r.get("docType") in valid else "OTHER"
        conf = float(r.get("confidence") or 0)
        doc.classification = {"docType": pred, "confidence": round(conf, 3), "signals": [str(s) for s in r.get("signals", [])]}
        if not declared_doc_type or declared_doc_type == "OTHER":
            doc.doc_type = pred
        disagree = declared_doc_type and declared_doc_type != "OTHER" and pred != declared_doc_type and conf > 0.7
        return (f"Classified as {pred} (confidence {conf:.2f})"
                + (f"; DISAGREES with declared {declared_doc_type}" if disagree else ""))

    def s_extract():
        r = pb.extract_fields(doc.doc_type, ocr_state["text"])
        doc.extracted_fields = r
        return f"Extracted {len(r)} field(s): {', '.join(list(r)[:8])}"

    def s_forensics():
        r = pb.analyse_forensics(str(path), str(store_dir / "ela"))
        heat = r.get("elaHeatmapPath")
        doc.ela_path = heat if heat and Path(heat).exists() else None
        doc.forensics = {"elaScore": r.get("elaScore"), "hasElaHeatmap": bool(doc.ela_path),
                         "metadata": r.get("metadata") or {}, "flags": r.get("flags") or []}
        codes = [f.get("code") for f in doc.forensics["flags"] if isinstance(f, dict)]
        return f"Forensics: ELA score {r.get('elaScore')}, {len(codes)} flag(s){': ' + ', '.join(map(str, codes)) if codes else ''}"

    qr_state: dict = {"qr": None}

    def s_qr():
        qr, notes = _qr_stage(str(path), doc.extracted_fields or {})
        qr_state["qr"] = qr
        doc.qr = qr
        return notes[0] if notes else "No QR code found"

    def s_verify():
        doc.verification = _verify(doc, qr_state["qr"])
        v = doc.verification
        return f"Source verification: {v.get('status')} via {v.get('method') or '-'} ({v.get('source') or 'no source'})"

    def s_infra():
        et = infra_evidence_type(doc.doc_type)
        if not et:
            return "not an infrastructure evidence document"
        from .validator import reference_today

        prm = next((r_["params"] for r_ in load_rules(db) if r_["id"] == "R-INF-003"), {}) or {}
        r = pb.analyse_infra(str(path), et, campus_gps=app.institution.campus_gps,
                             max_age_months=max(1, int(prm.get("maxAgeDays", 365)) // 30),
                             max_distance_km=float(prm.get("maxDistanceKm", 2.0)), ref_date=reference_today())
        doc.infra = {"evidenceType": et, "detections": r.get("detections") or [], "counts": r.get("counts") or {},
                     "quality": r.get("quality") or {}, "exif": r.get("exif") or {}, "flags": r.get("flags") or [],
                     "method": r.get("method"), "methodNote": r.get("methodNote")}
        return f"Infra CV ({et}): counts {doc.infra['counts']}, {len(doc.infra['flags'])} flag(s)"

    stage("hashing", s_hash)
    stage("ocr", s_ocr)
    stage("classify", s_classify)
    stage("extract", s_extract)
    _derive_metadata(doc)
    stage("forensics", s_forensics)
    stage("qr_signature", s_qr)
    stage("source_verification", s_verify)
    if infra_evidence_type(doc.doc_type):
        stage("infra_cv", s_infra)

    if errors:
        doc.pipeline_errors = errors
        if any(e["stage"] in ("source_verification", "ocr", "extract") for e in errors) or \
                doc.verification.get("status") == "VERIFICATION_PENDING":
            doc.verification = {**(doc.verification or {}), "status": "MANUAL_REVIEW_REQUIRED",
                                "checkedAt": _now_iso(),
                                "reason": "Automated processing incomplete: "
                                          + "; ".join(f"{e['stage']}: {e['error']}" for e in errors)[:400]}
    doc.processing_ms = int((time.perf_counter() - t0) * 1000)

    res = sync_findings(db, app, document_findings(doc, doc_rules(db)), document_id=doc.id, origin="PIPELINE")
    audit.record(db, actor, "DOCUMENT_PROCESSED", "Document", doc.id, {
        "applicationId": app.id, "docType": doc.doc_type, "verification": doc.verification.get("status"),
        "findingsCreated": res["created"], "stages": stage_log, "errors": errors, "ms": doc.processing_ms,
    }, commit=False)
    app.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(doc)
    return doc


def _derive_metadata(doc: Document) -> None:
    f = doc.extracted_fields or {}
    meta = load_doc_types().get(doc.doc_type, {})
    doc.reference_no = (str(get_value(f, "referenceNo")) if get_value(f, "referenceNo") else None)
    doc.issuer = str(get_value(f, "issuer")) if get_value(f, "issuer") else meta.get("issuer")
    doc.issue_date = get_date(f, "issueDate")
    doc.expiry_date = get_date(f, "expiryDate")
    if not doc.expiry_date and doc.issue_date and meta.get("validityMonths"):
        try:
            d = date.fromisoformat(doc.issue_date)
            doc.expiry_date = _add_months(d, int(meta["validityMonths"])).isoformat()
            doc.extracted_fields = {**f, "_derivedExpiry": {
                "value": doc.expiry_date, "confidence": 1.0, "page": None,
                "sourceText": f"derived: issue date + {meta['validityMonths']} months (doc-type validity)"}}
        except ValueError:
            pass


def reverify_document(db: Session, doc: Document, actor: User) -> Document:
    """Re-run QR + source verification (e.g. after a source comes back online)."""
    app = doc.application
    try:
        qr, _ = _qr_stage(doc.file_path, doc.extracted_fields or {})
    except Exception:  # noqa: BLE001
        qr = doc.qr
    try:
        doc.verification = _verify(doc, qr)
    except Exception as e:  # noqa: BLE001
        doc.verification = {"status": "MANUAL_REVIEW_REQUIRED", "checkedAt": _now_iso(),
                            "reason": f"Source verification failed: {type(e).__name__}: {e}"[:300]}
    doc.qr = qr
    sync_findings(db, app, [g for g in document_findings(doc, doc_rules(db)) if g["fingerprint"].startswith("SRC:")],
                  document_id=doc.id, origin="PIPELINE", fingerprint_prefixes=("SRC:",))
    audit.record(db, actor, "DOCUMENT_REVERIFIED", "Document", doc.id, {
        "applicationId": app.id, "docType": doc.doc_type, "status": doc.verification.get("status"),
        "source": doc.verification.get("source"), "method": doc.verification.get("method"),
    }, commit=False)
    db.commit()
    db.refresh(doc)
    return doc


__all__ = ["ingest_document", "reverify_document", "sync_findings", "doc_type_label"]
