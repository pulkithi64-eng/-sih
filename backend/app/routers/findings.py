from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..engine.rules_loader import severity_weights
from ..engine.validator import compute_scores
from ..models import Finding, User, ValidationRun
from ..schemas import FindingPatch, finding_out
from ..security import ADMIN, INSTITUTION, get_current_user
from ._common import get_app

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("/{finding_id}")
def get_finding(finding_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.get(Finding, finding_id)
    if f is None:
        raise HTTPException(404, "Finding not found")
    get_app(db, f.application_id, user)
    return finding_out(f)


@router.patch("/{finding_id}")
def patch_finding(finding_id: int, body: FindingPatch, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    f = db.get(Finding, finding_id)
    if f is None:
        raise HTTPException(404, "Finding not found")
    app = get_app(db, f.application_id, user)
    note = (body.note or "").strip()
    if app.status == "DECIDED":
        raise HTTPException(409, "Findings on finalized applications cannot be changed")
    if user.role == INSTITUTION:
        if body.status != "ACKNOWLEDGED":
            raise HTTPException(403, "Institutions may acknowledge and respond; reviewers must confirm resolution")
        if f.status in ("RECTIFIED", "DISMISSED"):
            raise HTTPException(409, "Institutions cannot overwrite reviewer resolutions")
        if not note:
            raise HTTPException(422, "A note describing the response/rectification is required")
    elif user.role == ADMIN:
        raise HTTPException(403, "Administrators do not review findings")
    if body.status in ("DISMISSED", "RECTIFIED") and not note:
        raise HTTPException(422, "Resolving a finding requires an evidence-based reason")
    prev = f.status
    f.status = body.status
    if note:
        f.reviewer_note = f"[{user.role} {user.username}] {note}"
    f.human_modified = True
    # refresh the risk score so dashboards reflect human dispositions
    run = db.execute(select(ValidationRun).where(ValidationRun.application_id == app.id)
                     .order_by(ValidationRun.id.desc()).limit(1)).scalar_one_or_none()
    if run is not None:
        _, app.risk_score, app.risk_band = compute_scores(run.report.get("rulesApplied", []), app.findings,
                                                          severity_weights())
    audit.record(db, user, "FINDING_UPDATED", "Finding", f.id,
                 {"applicationId": app.id, "from": prev, "to": f.status, "note": note, "kind": f.kind,
                  "severity": f.severity, "ruleId": f.rule_id})
    db.refresh(f)
    return finding_out(f)
