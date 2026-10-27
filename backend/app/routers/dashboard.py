"""Dashboard aggregates.

manualEffortSavedHours (documented estimate):
    (documentsAutoChecked x minutesPerDocument + applicationsValidated x minutesPerApplication
     - automatedProcessingMinutes) / 60
where minutesPerDocument (default 12) is the typical time an officer spends opening, reading and
cross-checking one document against records/issuer, and minutesPerApplication (default 45) the time to
compile the checklist, norms computation and deficiency note per application. Both are configurable
(VERISENSE_MANUAL_MINUTES_PER_DOCUMENT / _PER_APPLICATION) and are planning assumptions, not measurements.
avgValidationSeconds is MEASURED: mean wall-clock duration of validation runs (+ mean per-document
pipeline time reported separately).
"""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Alert, Application, Document, User, ValidationRun
from ..schemas import application_out
from ..security import OFFICER_PLUS, require_roles, scope_applications

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
ACTIVE = ("OPEN", "ACKNOWLEDGED", "ESCALATED")


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(require_roles(*OFFICER_PLUS))):
    s = get_settings()
    apps = db.execute(scope_applications(select(Application), user).order_by(Application.updated_at.desc())).unique().scalars().all()
    ids = [a.id for a in apps]
    by_status = Counter(a.status for a in apps)
    by_cat = Counter(a.category for a in apps)
    by_risk = Counter(a.risk_band for a in apps if a.last_validated_at)
    docs = [d for a in apps for d in a.documents]
    by_ver = Counter((d.verification or {}).get("status") or "VERIFICATION_PENDING" for d in docs)
    active = [f for a in apps for f in a.findings if f.status in ACTIVE]
    by_sev = Counter(f.severity for f in active)
    by_kind = Counter(f.kind for f in active)
    for k in ("CRITICAL", "MAJOR", "MINOR", "INFO"):
        by_sev.setdefault(k, 0)

    runs = db.execute(select(func.count(ValidationRun.id), func.avg(ValidationRun.duration_seconds),
                             func.sum(ValidationRun.duration_seconds))
                      .where(ValidationRun.application_id.in_(ids))).one() if ids else (0, None, None)
    n_runs, avg_val, sum_val = runs[0] or 0, runs[1] or 0.0, runs[2] or 0.0
    validated_apps = sum(1 for a in apps if a.last_validated_at)
    docs_checked = len(docs)
    avg_doc_ms = (sum(d.processing_ms or 0 for d in docs) / docs_checked) if docs_checked else 0.0
    automated_min = (sum(d.processing_ms or 0 for d in docs) / 1000 + sum_val) / 60
    manual_min = docs_checked * s.manual_minutes_per_document + validated_apps * s.manual_minutes_per_application
    saved_h = max(0.0, (manual_min - automated_min) / 60)

    unread = db.execute(select(func.count(Alert.id)).where(Alert.application_id.in_(ids), Alert.read.is_(False))).scalar() if ids else 0
    pending_validation = sum(1 for a in apps if a.status in ("SUBMITTED", "UNDER_VALIDATION")
                             or (a.status != "DRAFT" and a.last_validated_at is None))
    return {
        "totals": {
            "applications": len(apps),
            "pendingValidation": pending_validation,
            "deficiencies": by_status.get("DEFICIENCIES_FLAGGED", 0) + by_status.get("RECTIFICATION_REQUESTED", 0),
            "sourcePending": by_status.get("SOURCE_VERIFICATION_PENDING", 0),
            "inspection": by_status.get("INSPECTION_ORDERED", 0),
            "recommended": by_status.get("RECOMMENDED", 0),
            "underReview": by_status.get("UNDER_REVIEW", 0),
            "decided": by_status.get("DECIDED", 0),
            "documents": docs_checked,
            "findingsOpen": len(active),
            "alertsUnread": unread or 0,
            "highRisk": by_risk.get("HIGH", 0),
        },
        "byStatus": dict(by_status),
        "byVerification": dict(by_ver),
        "byCategory": dict(by_cat),
        "byRiskBand": dict(by_risk),
        "findingsBySeverity": dict(by_sev),
        "findingsByKind": dict(by_kind),
        "recent": [application_out(a) for a in apps[:8]],
        "avgValidationSeconds": round(float(avg_val), 3),
        "avgDocumentProcessingSeconds": round(avg_doc_ms / 1000, 2),
        "validationRuns": n_runs,
        "manualEffortSavedHours": round(saved_h, 1),
        "effortModel": {
            "formula": "(documentsAutoChecked*minutesPerDocument + applicationsValidated*minutesPerApplication - automatedMinutes)/60",
            "documentsAutoChecked": docs_checked,
            "applicationsValidated": validated_apps,
            "minutesPerDocument": s.manual_minutes_per_document,
            "minutesPerApplication": s.manual_minutes_per_application,
            "automatedMinutes": round(automated_min, 2),
            "note": "Planning estimate; per-item minutes are configurable assumptions, automated time is measured.",
        },
    }
