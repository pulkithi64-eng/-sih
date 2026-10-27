"""Per-document findings derived from stored pipeline results.

Used both right after upload (origin PIPELINE) and by the validator (which regenerates them
idempotently), so the two never disagree.
"""
from __future__ import annotations

from ..models import Document
from .rules_loader import doc_type_label

SEV_MAP = {
    "CRITICAL": "CRITICAL", "HIGH": "MAJOR", "MAJOR": "MAJOR", "MEDIUM": "MINOR", "MINOR": "MINOR",
    "LOW": "INFO", "INFO": "INFO", "WARNING": "MINOR", "WARN": "MINOR",
}
SEV_ORDER = {"CRITICAL": 3, "MAJOR": 2, "MINOR": 1, "INFO": 0}
CLASSIFY_CLAUSE = "VeriSense pipeline check — declared document type vs content"


def norm_sev(s) -> str:
    return SEV_MAP.get(str(s or "MINOR").upper(), "MINOR")


def _doc_ev(doc: Document, label: str | None = None, page=None, excerpt=None) -> dict:
    return {"type": "DOCUMENT", "label": label or f"{doc_type_label(doc.doc_type)} — {doc.file_name}",
            "documentId": doc.id, "page": page, "excerpt": excerpt}


def classification_findings(doc: Document) -> list[dict]:
    cls = doc.classification or {}
    pred, conf = cls.get("docType"), float(cls.get("confidence") or 0)
    declared = doc.declared_doc_type
    if not declared or declared == "OTHER" or not pred or pred == "OTHER" or pred == declared or conf <= 0.7:
        return []
    return [{
        "fingerprint": f"CLS:{doc.id}",
        "kind": "INCONSISTENCY", "severity": "MAJOR", "document_id": doc.id, "rule_id": None,
        "clause": CLASSIFY_CLAUSE,
        "title": f"Uploaded as {doc_type_label(declared)} but content looks like {doc_type_label(pred)}",
        "reason": (f"The document was declared as {declared} but the classifier predicts {pred} with "
                   f"confidence {conf:.2f}. Signals: {', '.join(map(str, cls.get('signals', [])[:5])) or 'n/a'}."),
        "evidence": [
            _doc_ev(doc),
            {"type": "FIELD", "label": "Declared document type", "documentId": doc.id, "submitted": declared,
             "reference": pred, "excerpt": f"classifier confidence {conf:.2f}"},
        ],
    }]


def forensic_findings(doc: Document, rule: dict | None, min_severity: str = "MINOR") -> list[dict]:
    out = []
    flags = (doc.forensics or {}).get("flags") or []
    for i, fl in enumerate(flags):
        if not isinstance(fl, dict):
            continue
        sev = norm_sev(fl.get("severity"))
        if SEV_ORDER[sev] < SEV_ORDER.get(min_severity, 1):
            continue
        code = fl.get("code") or f"FLAG_{i}"
        evid = fl.get("evidence")
        ev = [_doc_ev(doc, page=(evid or {}).get("page") if isinstance(evid, dict) else None)]
        if isinstance(evid, dict):
            ev.append({"type": "IMAGE_REGION" if evid.get("bbox") else "METADATA",
                       "label": f"Forensic evidence ({code})", "documentId": doc.id,
                       "page": evid.get("page"), "bbox": evid.get("bbox"),
                       "excerpt": ", ".join(f"{k}: {v}" for k, v in evid.items() if k not in ("bbox", "page"))[:400] or None})
        elif evid:
            ev.append({"type": "METADATA", "label": f"Forensic evidence ({code})", "documentId": doc.id,
                       "excerpt": str(evid)[:400]})
        md = (doc.forensics or {}).get("metadata") or {}
        if md and code.upper().startswith(("META", "PDF", "EDIT", "PRODUCER", "MODIF", "INCREMENT", "SOFTWARE")):
            ev.append({"type": "METADATA", "label": "PDF / file metadata", "documentId": doc.id,
                       "excerpt": "; ".join(f"{k}={v}" for k, v in md.items() if v)[:400]})
        out.append({
            "fingerprint": f"FOR:{doc.id}:{code}",
            "kind": "ANOMALY", "severity": sev, "document_id": doc.id,
            "rule_id": rule["id"] if rule else "R-FOR-001", "clause": rule.get("clause") if rule else None,
            "title": f"Possible tampering indicator on {doc_type_label(doc.doc_type)}: {code}",
            "reason": str(fl.get("reason") or code) + " (indicator only — requires officer review)",
            "evidence": ev,
        })
    return out


def verification_findings(doc: Document, rule: dict | None) -> list[dict]:
    v = doc.verification or {}
    st = v.get("status")
    rid = rule["id"] if rule else "R-SRC-001"
    clause = rule.get("clause") if rule else None
    params = (rule or {}).get("params", {})
    label = doc_type_label(doc.doc_type)
    src = v.get("source") or "issuing authority"
    src_ev = {"type": "SOURCE_RESPONSE", "label": f"{src} response ({v.get('method') or 'n/a'}, {v.get('checkedAt') or 'n/a'})",
              "documentId": doc.id, "excerpt": (v.get("responseSummary") or v.get("reason") or "")[:400] or None}
    comps = [c for c in (v.get("comparisons") or []) if isinstance(c, dict)]
    if st == "MISMATCH_DETECTED":
        ev = [_doc_ev(doc), src_ev]
        bad = [c for c in comps if c.get("match") is False]
        for c in bad:
            ev.append({"type": "FIELD", "label": f"{c.get('field')}: submitted vs {src}", "documentId": doc.id,
                       "submitted": None if c.get("submitted") is None else str(c.get("submitted")),
                       "reference": None if c.get("source") is None else str(c.get("source"))})
        fields = ", ".join(str(c.get("field")) for c in bad) or "document authenticity"
        return [{
            "fingerprint": f"SRC:{doc.id}:MISMATCH", "kind": "VERIFICATION",
            "severity": params.get("mismatchSeverity", "CRITICAL"), "document_id": doc.id, "rule_id": rid, "clause": clause,
            "title": f"{label} does not match {src} records ({fields})",
            "reason": v.get("reason") or f"Source verification reported a mismatch on: {fields}.",
            "evidence": ev,
        }]
    if st == "EXPIRED":
        return [{
            "fingerprint": f"SRC:{doc.id}:EXPIRED", "kind": "EXPIRED_DOCUMENT", "severity": "CRITICAL",
            "document_id": doc.id, "rule_id": rid, "clause": clause,
            "title": f"{label} reported expired / revoked by {src}",
            "reason": v.get("reason") or "The issuing authority reports this document as no longer valid.",
            "evidence": [_doc_ev(doc), src_ev],
        }]
    if st == "MANUAL_REVIEW_REQUIRED":
        return [{
            "fingerprint": f"SRC:{doc.id}:MANUAL", "kind": "VERIFICATION",
            "severity": params.get("manualReviewSeverity", "MINOR"), "document_id": doc.id, "rule_id": rid, "clause": clause,
            "title": f"{label} needs manual verification",
            "reason": v.get("reason") or "Automatic source verification was not possible.",
            "evidence": [_doc_ev(doc), src_ev],
        }]
    if st in ("SOURCE_UNAVAILABLE", "VERIFICATION_PENDING"):
        return [{
            "fingerprint": f"SRC:{doc.id}:PENDING", "kind": "VERIFICATION", "severity": "INFO",
            "document_id": doc.id, "rule_id": rid, "clause": clause,
            "title": f"{label}: source verification pending ({src} {'unavailable' if st == 'SOURCE_UNAVAILABLE' else 'pending'})",
            "reason": v.get("reason") or "The issuing authority could not be reached; verification will be retried.",
            "evidence": [_doc_ev(doc), src_ev],
        }]
    return []


def infra_flag_findings(doc: Document, rule: dict | None = None) -> list[dict]:
    out = []
    infra = doc.infra or {}
    for i, fl in enumerate(infra.get("flags") or []):
        if isinstance(fl, str):
            fl = {"code": fl, "severity": "MINOR", "reason": fl}
        if not isinstance(fl, dict):
            continue
        code = fl.get("code") or f"INFRA_{i}"
        out.append({
            "fingerprint": f"INF:{doc.id}:{code}", "kind": "INFRASTRUCTURE", "severity": norm_sev(fl.get("severity")),
            "document_id": doc.id, "rule_id": (rule or {}).get("id", "R-INF-003"), "clause": (rule or {}).get("clause"),
            "title": f"{doc_type_label(doc.doc_type)}: {code}",
            "reason": str(fl.get("reason") or code),
            "evidence": [_doc_ev(doc), {"type": "IMAGE_REGION" if isinstance(fl.get("evidence"), dict) and fl["evidence"].get("bbox") else "METADATA",
                                        "label": "Image analysis", "documentId": doc.id,
                                        "bbox": fl.get("evidence", {}).get("bbox") if isinstance(fl.get("evidence"), dict) else None,
                                        "excerpt": str(fl.get("evidence") or infra.get("quality") or "")[:300]}],
        })
    return out


def pipeline_error_findings(doc: Document) -> list[dict]:
    errs = doc.pipeline_errors or []
    if not errs:
        return []
    stages = ", ".join(e.get("stage", "?") for e in errs)
    return [{
        "fingerprint": f"PIPE:{doc.id}", "kind": "VERIFICATION", "severity": "MINOR", "document_id": doc.id,
        "rule_id": None, "clause": "VeriSense pipeline check — automated processing completeness",
        "title": f"Automated processing incomplete for {doc.file_name} ({stages})",
        "reason": "Some automated checks could not run on this document; manual review required. "
                  + "; ".join(f"{e.get('stage')}: {e.get('error')}" for e in errs)[:600],
        "evidence": [_doc_ev(doc)],
    }]


def document_findings(doc: Document, rules_by_type: dict[str, dict] | None = None) -> list[dict]:
    """All per-document findings. If rules_by_type is given, disabled rule types are skipped."""
    rules_by_type = rules_by_type if rules_by_type is not None else {}
    out = classification_findings(doc) + pipeline_error_findings(doc)
    ir = rules_by_type.get("INFRA_ANY")
    if ir is None or ir.get("enabled", True):
        out += infra_flag_findings(doc, ir)
    fr = rules_by_type.get("FORENSIC_FLAG")
    if fr is None or fr.get("enabled", True):
        out += forensic_findings(doc, fr, (fr or {}).get("params", {}).get("minSeverity", "MINOR"))
    sr = rules_by_type.get("SOURCE_VERIFICATION")
    if sr is None or sr.get("enabled", True):
        out += verification_findings(doc, sr)
    return out
