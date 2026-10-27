from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..engine import rules_loader as rl
from ..models import User
from ..schemas import ChecklistItemTemplate, RulePatch
from ..security import ADMIN, OFFICER_PLUS, get_current_user, require_roles

router = APIRouter(tags=["rules"])


def _rule_out(r: dict) -> dict:
    return {k: r.get(k) for k in ("id", "name", "description", "categories", "type", "params", "severity",
                                  "clause", "enabled", "version", "kind")}


@router.get("/rules")
def list_rules(db: Session = Depends(get_db), _u: User = Depends(require_roles(*OFFICER_PLUS))):
    return [_rule_out(r) for r in rl.load_rules(db)]


@router.get("/rules/version")
def rules_version(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    return {"rulesetVersion": rl.ruleset_version(db)}


@router.put("/rules/{rule_id}")
def update_rule(rule_id: str, body: RulePatch, db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN))):
    before = rl.get_rule(db, rule_id)
    if before is None:
        raise HTTPException(404, "Rule not found")
    after = rl.update_rule(db, rule_id, body.model_dump(exclude_none=True), user.username)
    changes = {k: {"from": before.get(k), "to": after.get(k)} for k in ("enabled", "severity", "params")
               if before.get(k) != after.get(k)}
    audit.record(db, user, "RULE_UPDATED", "Rule", rule_id,
                 {"changes": changes, "ruleVersion": after["version"], "rulesetVersion": rl.ruleset_version(db)})
    return _rule_out(after)


@router.get("/checklists")
def get_checklists(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    return {cat: body.get("items", []) for cat, body in rl.load_checklists(db).items()}


@router.put("/checklists/{category}")
def put_checklist(category: str, items: list[ChecklistItemTemplate], db: Session = Depends(get_db),
                  user: User = Depends(require_roles(ADMIN))):
    before = rl.checklist_for(db, category)
    try:
        after = rl.update_checklist(db, category, [i.model_dump(by_alias=True, exclude_none=True) for i in items],
                                    user.username)
    except KeyError:
        raise HTTPException(404, "Unknown category")
    except ValueError as e:
        raise HTTPException(422, str(e))
    audit.record(db, user, "CHECKLIST_UPDATED", "Checklist", category,
                 {"before": [i["docType"] for i in before], "after": [i["docType"] for i in after],
                  "rulesetVersion": rl.ruleset_version(db)})
    return {category: after}
