from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..models import Application, AuditEvent, Document, Finding, User
from ..schemas import audit_out
from ..security import ADMIN, OFFICER_PLUS, require_roles, scope_applications

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/verify")
def verify(db: Session = Depends(get_db), user: User = Depends(require_roles(*OFFICER_PLUS))):
    res = audit.verify_chain(db)
    audit.record(db, user, "AUDIT_CHAIN_VERIFIED", "Audit", "chain",
                 {"valid": res["valid"], "checked": res["checked"], "brokenAt": res.get("brokenAt")})
    return res


@router.get("")
def list_events(entityId: str | None = None, action: str | None = None, entityType: str | None = None,
                applicationId: int | None = None, limit: int = 200, db: Session = Depends(get_db),
                user: User = Depends(require_roles(*OFFICER_PLUS))):
    stmt = select(AuditEvent)
    if entityId:
        stmt = stmt.where(AuditEvent.entity_id == str(entityId))
    if action:
        stmt = stmt.where(AuditEvent.action.in_(action.split(",")))
    if entityType:
        stmt = stmt.where(AuditEvent.entity_type == entityType)
    limit = max(1, min(limit, 2000))
    scoped = user.role != ADMIN
    if scoped and not user.region:
        return []
    if not scoped and applicationId is None:
        rows = db.execute(stmt.order_by(AuditEvent.id.desc()).limit(limit)).scalars().all()
        return [audit_out(e) for e in rows]
    # region / application scoping: keep events that concern visible applications
    app_q = scope_applications(select(Application.id), user) if scoped else select(Application.id)
    if applicationId is not None:
        app_q = app_q.where(Application.id == applicationId)
    app_ids_int = list(db.execute(app_q).scalars())
    app_ids = {str(i) for i in app_ids_int}
    doc_ids = {str(i) for i in db.execute(select(Document.id).where(Document.application_id.in_(app_ids_int))).scalars()}
    fnd_ids = {str(i) for i in db.execute(select(Finding.id).where(Finding.application_id.in_(app_ids_int))).scalars()}
    out = []
    for e in db.execute(stmt.order_by(AuditEvent.id.desc()).limit(20000)).scalars():
        aid = str((e.details or {}).get("applicationId", ""))
        ok = ((e.entity_type == "Application" and e.entity_id in app_ids)
              or (e.entity_type == "Document" and e.entity_id in doc_ids)
              or (e.entity_type == "Finding" and e.entity_id in fnd_ids)
              or aid in app_ids
              or (applicationId is None and e.entity_type in ("Rule", "Checklist", "Source")))
        if ok:
            out.append(audit_out(e))
            if len(out) >= limit:
                break
    return out
