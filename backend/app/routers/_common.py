"""Shared router helpers."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Application, Document, User
from ..security import ensure_app_access

EDITABLE_BY_INSTITUTION = ("DRAFT", "RECTIFICATION_REQUESTED", "DEFICIENCIES_FLAGGED")


def get_app(db: Session, app_id: int, user: User) -> Application:
    return ensure_app_access(user, db.get(Application, app_id))


def get_doc(db: Session, doc_id: int, user: User) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    ensure_app_access(user, doc.application)
    return doc
