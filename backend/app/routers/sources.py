from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..engine import pipeline_bridge as pb
from ..models import User
from ..security import ADMIN, OFFICER_PLUS, require_roles

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(_u: User = Depends(require_roles(*OFFICER_PLUS))):
    return pb.list_sources()


@router.post("/{source_id}/toggle")
def toggle(source_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN))):
    src = next((s for s in pb.list_sources() if s.get("id") == source_id), None)
    if src is None:
        raise HTTPException(404, "Source not found")
    new = not bool(src.get("online", True))
    res = pb.set_source_online(source_id, new) or {**src, "online": new}
    audit.record(db, user, "SOURCE_TOGGLED", "Source", source_id, {"online": new, "name": src.get("name")})
    return res
