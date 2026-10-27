"""Loads backend/config/*.yaml (versioned baseline) and applies admin overrides stored in the DB.

Ruleset version = "<yaml version>-r<revision>", where revision counts admin edits to rules/checklists.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ConfigOverride

CATEGORIES = {
    "EOA": "Extension of Approval",
    "NEW_INSTITUTION": "New Institution",
    "INTAKE_INCREASE": "Increase in Intake",
    "NEW_COURSE": "New Course / Programme",
    "CHANGE_OF_NAME": "Change of Name",
    "CHANGE_OF_SITE": "Change of Site",
    "CLOSURE": "Closure",
}
RULE_TYPES = [
    "REQUIRED_DOCUMENT", "DOCUMENT_EXPIRY", "FIELD_PRESENT", "FIELD_MATCH_RECORD", "FIELD_MATCH_DOCUMENT",
    "THRESHOLD", "CADRE_RATIO", "TER_PAYMENT", "DUPLICATE_DOCUMENT", "DUPLICATE_FACULTY", "FORENSIC_FLAG",
    "SOURCE_VERIFICATION", "INFRA_EVIDENCE",
]
SEVERITIES = ["CRITICAL", "MAJOR", "MINOR", "INFO"]


def _config_dir() -> Path:
    return Path(get_settings().config_dir)


@lru_cache(maxsize=8)
def _read_yaml(name: str, mtime: float) -> dict:  # mtime busts the cache when the file changes
    with open(_config_dir() / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _yaml(name: str) -> dict:
    p = _config_dir() / name
    return copy.deepcopy(_read_yaml(name, p.stat().st_mtime))


# ------------------------------------------------------------------ doc types
def load_doc_types() -> dict[str, dict]:
    return _yaml("doc_types.yaml").get("docTypes", {})


def doc_type_label(doc_type: str | None) -> str:
    if not doc_type:
        return "Unknown"
    return load_doc_types().get(doc_type, {}).get("label", doc_type.replace("_", " ").title())


def infra_evidence_type(doc_type: str) -> str | None:
    return load_doc_types().get(doc_type, {}).get("infra")


# ------------------------------------------------------------------ overrides / version
def _overrides(db: Session | None, kind: str) -> dict[str, ConfigOverride]:
    if db is None:
        return {}
    rows = db.execute(select(ConfigOverride).where(ConfigOverride.kind == kind)).scalars()
    return {r.key: r for r in rows}


def revision(db: Session | None) -> int:
    if db is None:
        return 0
    row = db.execute(
        select(ConfigOverride).where(ConfigOverride.kind == "META", ConfigOverride.key == "revision")
    ).scalar_one_or_none()
    return int(row.data.get("revision", 0)) if row else 0


def _bump_revision(db: Session, user: str) -> int:
    row = db.execute(
        select(ConfigOverride).where(ConfigOverride.kind == "META", ConfigOverride.key == "revision")
    ).scalar_one_or_none()
    if row is None:
        row = ConfigOverride(kind="META", key="revision", data={"revision": 0}, updated_by=user)
        db.add(row)
    n = int(row.data.get("revision", 0)) + 1
    row.data = {"revision": n}
    row.updated_by = user
    return n


def ruleset_version(db: Session | None) -> str:
    base = _yaml("rules.yaml").get("version", "0")
    return f"{base}-r{revision(db)}"


def severity_weights() -> dict[str, float]:
    return _yaml("rules.yaml").get("severityWeights", {"CRITICAL": 5, "MAJOR": 3, "MINOR": 1, "INFO": 0})


# ------------------------------------------------------------------ rules
def load_rules(db: Session | None = None) -> list[dict]:
    rules = _yaml("rules.yaml").get("rules", [])
    ov = _overrides(db, "RULE")
    out = []
    for r in rules:
        r.setdefault("enabled", True)
        r.setdefault("version", 1)
        r.setdefault("params", {})
        r.setdefault("categories", ["ALL"])
        if r["id"] in ov:
            patch = ov[r["id"]].data
            for k in ("enabled", "severity", "version"):
                if k in patch:
                    r[k] = patch[k]
            if "params" in patch:
                r["params"] = patch["params"]
        out.append(r)
    return out


def get_rule(db: Session | None, rule_id: str) -> dict | None:
    return next((r for r in load_rules(db) if r["id"] == rule_id), None)


def update_rule(db: Session, rule_id: str, patch: dict, user: str) -> dict:
    current = get_rule(db, rule_id)
    if current is None:
        raise KeyError(rule_id)
    ov = _overrides(db, "RULE").get(rule_id)
    data = dict(ov.data) if ov else {}
    for k in ("enabled", "severity", "params"):
        if patch.get(k) is not None:
            data[k] = patch[k]
    data["version"] = int(current.get("version", 1)) + 1
    if ov is None:
        db.add(ConfigOverride(kind="RULE", key=rule_id, data=data, updated_by=user))
    else:
        ov.data = data
        ov.updated_by = user
    _bump_revision(db, user)
    db.flush()
    return get_rule(db, rule_id)  # type: ignore[return-value]


def rule_applies(rule: dict, category: str) -> bool:
    cats = rule.get("categories") or ["ALL"]
    return "ALL" in cats or category in cats


# ------------------------------------------------------------------ checklists
def load_checklists(db: Session | None = None) -> dict[str, dict]:
    cl = _yaml("checklists.yaml").get("categories", {})
    ov = _overrides(db, "CHECKLIST")
    for cat, row in ov.items():
        cl.setdefault(cat, {"label": CATEGORIES.get(cat, cat)})
        cl[cat]["items"] = row.data
    for cat, body in cl.items():
        for it in body.get("items", []):
            it.setdefault("mandatory", False)
            it.setdefault("clause", "")
            it["label"] = doc_type_label(it["docType"])
    return cl


def checklist_for(db: Session | None, category: str) -> list[dict]:
    return load_checklists(db).get(category, {}).get("items", [])


def update_checklist(db: Session, category: str, items: list[dict], user: str) -> list[dict]:
    if category not in CATEGORIES:
        raise KeyError(category)
    known = load_doc_types()
    clean = []
    for it in items:
        dt = it.get("docType")
        if dt not in known:
            raise ValueError(f"unknown docType {dt}")
        row = {"docType": dt, "mandatory": bool(it.get("mandatory", False)), "clause": it.get("clause", "")}
        if it.get("when"):
            row["when"] = it["when"]
        clean.append(row)
    ov = _overrides(db, "CHECKLIST").get(category)
    if ov is None:
        db.add(ConfigOverride(kind="CHECKLIST", key=category, data=clean, updated_by=user))
    else:
        ov.data = clean
        ov.updated_by = user
    _bump_revision(db, user)
    db.flush()
    return checklist_for(db, category)
