from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..models import Alert, Application, User
from ..schemas import alert_out
from ..security import can_access_application, get_current_user, scope_applications

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(unread: bool | None = None, limit: int = 200, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    app_ids = scope_applications(select(Application.id), user)
    stmt = select(Alert).where(Alert.application_id.in_(app_ids))
    if unread:
        stmt = stmt.where(Alert.read.is_(False))
    rows = db.execute(stmt.order_by(Alert.id.desc()).limit(max(1, min(limit, 1000)))).unique().scalars().all()
    return [alert_out(a) for a in rows]


@router.post("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = db.get(Alert, alert_id)
    if a is None or not can_access_application(user, a.application):
        raise HTTPException(404, "Alert not found")
    a.read = True
    audit.record(db, user, "ALERT_READ", "Alert", a.id, {"applicationId": a.application_id})
    db.refresh(a)
    return alert_out(a)
