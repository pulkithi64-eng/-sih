"""Hash-chained, append-only audit log.

hash_n = sha256(prev_hash + canonical_json(event_n)) where the event payload is
{ts, actor, actorRole, action, entityType, entityId, details}; the first event chains from GENESIS.
Rows are protected from UPDATE/DELETE by ORM listeners and SQLite triggers (see models.py).
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditEvent, User
from .tracing import request_id

GENESIS = "0" * 64
_lock = threading.Lock()


def _json_default(o: Any):
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_json_default)


def _payload(ev: AuditEvent | dict) -> dict:
    if isinstance(ev, dict):
        return ev
    return {
        "ts": ev.ts,
        "actor": ev.actor,
        "actorRole": ev.actor_role,
        "action": ev.action,
        "entityType": ev.entity_type,
        "entityId": ev.entity_id,
        "details": ev.details,
    }


def compute_hash(prev_hash: str, payload: dict) -> str:
    return hashlib.sha256((prev_hash + canonical(payload)).encode("utf-8")).hexdigest()


def record(
    db: Session,
    actor: User | str | None,
    action: str,
    entity_type: str,
    entity_id: Any,
    details: dict | None = None,
    actor_role: str | None = None,
    commit: bool = True,
) -> AuditEvent:
    """Append an audit event. `actor` may be a User, a username or None (system)."""
    if isinstance(actor, User):
        actor_name, role = actor.username, actor.role
    else:
        actor_name, role = (actor or "system"), (actor_role or "SYSTEM")
    if actor_role:
        role = actor_role
    # normalise details through JSON so the stored value hashes identically when re-read
    clean_details = json.loads(canonical(details or {}))
    if request_id.get():
        clean_details["requestId"] = request_id.get()
    with _lock:
        last = db.execute(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1)).scalar_one_or_none()
        prev = last.hash if last else GENESIS
        ts = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        payload = {
            "ts": ts,
            "actor": actor_name,
            "actorRole": role,
            "action": action,
            "entityType": entity_type,
            "entityId": str(entity_id),
            "details": clean_details,
        }
        ev = AuditEvent(
            ts=ts, actor=actor_name, actor_role=role, action=action, entity_type=entity_type,
            entity_id=str(entity_id), details=clean_details, prev_hash=prev, hash=compute_hash(prev, payload),
        )
        db.add(ev)
        if commit:
            db.commit()
        else:
            db.flush()
    return ev


def verify_chain(db: Session) -> dict:
    prev = GENESIS
    checked = 0
    for ev in db.execute(select(AuditEvent).order_by(AuditEvent.id)).scalars():
        checked += 1
        expected = compute_hash(prev, _payload(ev))
        if ev.prev_hash != prev or ev.hash != expected:
            return {"valid": False, "checked": checked, "brokenAt": ev.id,
                    "reason": "prevHash link broken" if ev.prev_hash != prev else "event content altered (hash mismatch)"}
        prev = ev.hash
    return {"valid": True, "checked": checked, "brokenAt": None, "headHash": prev}
