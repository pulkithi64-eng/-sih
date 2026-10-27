"""Application-level validation: evaluates every configured rule (contract section 5) against
form data, extracted document fields, institutional records, other institutions and
verification / infrastructure results. Produces a fully traceable ValidationReport.

Outputs are ADVISORY decision support; nothing here approves or rejects an application.
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..config import get_settings
from ..models import Alert, Application, Document, Institution, User, ValidationRun
from .doc_findings import (
    classification_findings,
    forensic_findings,
    infra_flag_findings,
    pipeline_error_findings,
    verification_findings,
)
from .fields import get_field, get_value, similarity, to_number
from .ingest import sync_findings
from .rules_loader import (
    checklist_for,
    doc_type_label,
    load_doc_types,
    load_rules,
    rule_applies,
    ruleset_version,
    severity_weights,
)

SEV_POINTS = {"CRITICAL": 30, "MAJOR": 15, "MINOR": 5, "INFO": 0}
KIND_MULT = {"ANOMALY": 1.0, "DUPLICATE": 1.0, "VERIFICATION": 1.0, "RECORD_MISMATCH": 0.8, "INCONSISTENCY": 0.8,
             "EXPIRED_DOCUMENT": 0.5, "COMPLIANCE_GAP": 0.5, "MISSING_DOCUMENT": 0.4, "MISSING_FIELD": 0.3,
             "INFRASTRUCTURE": 0.4}
ACTIVE_STATUSES = ("OPEN", "ACKNOWLEDGED", "ESCALATED")
# statuses that validation may move (others reflect a human workflow step and are left untouched)
AUTO_STATUS_FROM = {"SUBMITTED", "UNDER_VALIDATION", "DEFICIENCIES_FLAGGED", "SOURCE_VERIFICATION_PENDING",
                    "UNDER_REVIEW", "RECTIFICATION_REQUESTED"}
LEVEL_YEARS = {"UG": 4, "PG": 2, "DIPLOMA": 3, "PGDM": 2, "PGCM": 1}


# ------------------------------------------------------------------ helpers
def reference_today() -> date:
    s = getattr(get_settings(), "reference_date", None)
    if s:
        try:
            return date.fromisoformat(str(s))
        except ValueError:
            pass
    return date.today()


def ay_bounds(ay: str) -> tuple[int, str]:
    """'2026-27' -> (2026, '2025-26')"""
    m = re.match(r"(\d{4})", ay or "")
    start = int(m.group(1)) if m else reference_today().year
    return start, f"{start - 1}-{str(start)[2:]}"


def _d(s: Any) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def _fmt(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _hamming(a: str, b: str) -> int | None:
    try:
        return (int(a, 16) ^ int(b, 16)).bit_count()
    except (ValueError, TypeError):
        return None


def _haversine_km(a: dict, b: dict) -> float | None:
    try:
        lat1, lon1, lat2, lon2 = map(math.radians, [float(a["lat"]), float(a["lng"]), float(b["lat"]), float(b["lng"])])
    except (KeyError, TypeError, ValueError):
        return None
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _norm_pan(p: Any) -> str | None:
    s = re.sub(r"[^A-Z0-9*]", "", str(p or "").upper())
    if len(s) < 6 or sum(ch not in "X*" for ch in s) < 5:
        return None
    return s


@dataclass
class Outcome:
    result: str = "PASS"
    detail: str = ""
    checks: int = 0
    failed: int = 0
    findings: list[dict] = field(default_factory=list)
    records: list[str] = field(default_factory=list)


class Ctx:
    def __init__(self, db: Session, app: Application):
        self.db = db
        self.app = app
        self.inst: Institution = app.institution
        self.records: dict = app.institution.records or {}
        self.form: dict = app.form_data or {}
        self.category = app.category
        self.docs: list[Document] = list(app.documents)
        self.by_type: dict[str, list[Document]] = {}
        for d in self.docs:
            self.by_type.setdefault(d.doc_type, []).append(d)
        self.today = reference_today()
        self.ay_start, self.prev_ay = ay_bounds(app.academic_year)
        self.doc_types = load_doc_types()
        self.records_checked: dict[str, int] = {}

    def touch(self, name: str, n: int = 1):
        self.records_checked[name] = self.records_checked.get(name, 0) + n

    def doc_ev(self, doc: Document, label: str | None = None, field_name: str | None = None) -> dict:
        ev = {"type": "DOCUMENT", "label": label or f"{doc_type_label(doc.doc_type)} — {doc.file_name}",
              "documentId": doc.id}
        if field_name:
            f = get_field(doc.extracted_fields, field_name)
            if f:
                ev.update(type="FIELD", page=f.get("page"), excerpt=_fmt(f.get("sourceText")), submitted=_fmt(f.get("value")))
        return ev

    def form_ev(self, name: str, value: Any) -> dict:
        return {"type": "FIELD", "label": f"Application form: {name}", "submitted": _fmt(value)}

    def rec_ev(self, path: str, value: Any, label: str | None = None) -> dict:
        return {"type": "RECORD", "label": label or f"AICTE record: {path}", "reference": _fmt(value)}

    def finding(self, rule: dict, fp: str, title: str, reason: str, evidence: list[dict], severity: str | None = None,
                kind: str | None = None, document_id: int | None = None) -> dict:
        return {"fingerprint": f"{rule['id']}:{fp}", "kind": kind or rule.get("kind") or "COMPLIANCE_GAP",
                "severity": severity or rule["severity"], "title": title, "reason": reason,
                "rule_id": rule["id"], "clause": rule.get("clause"), "evidence": evidence + [
                    {"type": "RULE", "label": f"{rule['id']} v{rule.get('version', 1)} — {rule['name']}",
                     "excerpt": rule.get("clause")}],
                "document_id": document_id}

    # --- doc expiry status used by checklist too
    def doc_expired(self, doc: Document, grace: int = 0) -> bool:
        exp = _d(doc.expiry_date)
        if exp and (exp - self.today).days < -grace:
            return True
        return (doc.verification or {}).get("status") == "EXPIRED"


# ------------------------------------------------------------------ record path mini-language
def resolve_record(records: dict, expr: str) -> Any:
    """Supports: a.b.c | sum(list.field) | count(list) | count(list[k=v]) | latest(list).field"""
    expr = expr.strip()
    m = re.fullmatch(r"(sum|count|latest)\(([^)\[]+)(?:\[(\w+)=(\w+)\])?\)(?:\.(.+))?", expr)
    if not m:
        cur: Any = records
        for part in expr.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        return cur
    fn, inner, fk, fv, tail = m.groups()
    parts = inner.split(".")
    lst = records.get(parts[0]) or []
    if not isinstance(lst, list):
        return None
    if fk:
        lst = [x for x in lst if isinstance(x, dict) and str(x.get(fk)) == fv]
    if fn == "count":
        return len(lst)
    if fn == "sum":
        return sum((to_number(x.get(parts[1])) or 0) for x in lst if isinstance(x, dict)) if len(parts) > 1 else len(lst)
    if fn == "latest":
        if not lst:
            return None
        def key(x):
            return str(x.get("year") or x.get("date") or x.get("validTo") or "")
        item = sorted(lst, key=key)[-1]
        return item.get(tail) if tail else item
    return None


def eval_condition(cond: dict | None, ctx: Ctx) -> bool:
    if not cond:
        return True
    fld = str(cond.get("field", ""))
    if fld.startswith("formData."):
        val = ctx.form.get(fld[len("formData."):])
    elif fld.startswith("records."):
        val = resolve_record(ctx.records, fld[len("records."):])
    elif fld == "category":
        val = ctx.category
    else:
        val = ctx.form.get(fld)
    if "equals" in cond:
        return val == cond["equals"]
    if "in" in cond:
        return val in cond["in"]
    if "gt" in cond:
        return (to_number(val) or 0) > cond["gt"]
    if "gte" in cond:
        return (to_number(val) or 0) >= cond["gte"]
    if "lt" in cond:
        return (to_number(val) or 0) < cond["lt"]
    if "exists" in cond:
        return (val is not None) == bool(cond["exists"])
    if "truthy" in cond:
        truthy = bool(val) and str(val).lower() not in ("false", "no", "0", "none")
        return truthy == bool(cond["truthy"])
    return bool(val)


# ------------------------------------------------------------------ checklist
def build_checklist(ctx: Ctx) -> list[dict]:
    out = []
    for it in checklist_for(ctx.db, ctx.category):
        dt = it["docType"]
        cond = it.get("when")
        required = bool(it.get("mandatory")) or (bool(cond) and eval_condition(cond, ctx))
        docs = ctx.by_type.get(dt, [])
        item = {"docType": dt, "label": it.get("label") or doc_type_label(dt), "mandatory": required,
                "conditional": bool(cond), "clause": it.get("clause", ""), "documentId": None}
        if docs:
            # prefer the most recent valid one
            best = sorted(docs, key=lambda d: (not ctx.doc_expired(d), d.id))[-1]
            item["documentId"] = best.id
            vs = (best.verification or {}).get("status")
            if ctx.doc_expired(best):
                item["status"] = "EXPIRED"
            elif vs == "MISMATCH_DETECTED":
                item["status"] = "INVALID"
            else:
                item["status"] = "PRESENT"
        else:
            item["status"] = "MISSING" if required else "NOT_REQUIRED"
        out.append(item)
    return out


# ------------------------------------------------------------------ rule evaluators
def r_required_document(rule, ctx: Ctx, checklist: list[dict]) -> Outcome:
    o = Outcome()
    required = [c for c in checklist if c["mandatory"]]
    o.checks = len(required)
    for c in required:
        if c["status"] == "MISSING":
            o.failed += 1
            o.findings.append(ctx.finding(
                rule, c["docType"], f"Missing mandatory document: {c['label']}",
                f"{c['label']} is required for a {ctx.category} application"
                + (" (conditional: required because of a declared claim)" if c.get("conditional") else "")
                + " but has not been uploaded.",
                [{"type": "RULE", "label": "Checklist requirement", "excerpt": c["clause"], "reference": c["docType"]}],
            ))
    o.result = "FAIL" if o.failed else "PASS"
    present = sum(1 for c in required if c["status"] != "MISSING")
    o.detail = f"{present}/{len(required)} required documents present" + (
        f"; missing: {', '.join(c['docType'] for c in required if c['status'] == 'MISSING')}" if o.failed else "")
    return o


def r_document_expiry(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    types = p.get("docTypes") or ["ALL"]
    excl = set(p.get("excludeDocTypes") or [])
    grace = int(p.get("graceDays", 0))
    warn = int(p.get("warnDays", 0) or 0)
    max_age = p.get("maxAgeDays")
    o = Outcome()
    targets = [d for d in ctx.docs if ("ALL" in types or d.doc_type in types) and d.doc_type not in excl]
    notes = []
    for d in targets:
        exp, iss = _d(d.expiry_date), _d(d.issue_date)
        derived = "_derivedExpiry" in (d.extracted_fields or {})
        if exp is None and not (max_age and iss):
            continue
        o.checks += 1
        label = doc_type_label(d.doc_type)
        fname = "expiryDate"
        if exp is not None:
            days = (exp - ctx.today).days
            if days < -grace:
                o.failed += 1
                o.findings.append(ctx.finding(
                    rule, f"{d.id}:EXPIRED", f"{label} expired on {exp.isoformat()}",
                    f"{label} validity ended {abs(days)} day(s) before the scrutiny date {ctx.today.isoformat()}"
                    + (" (expiry derived from issue date + standard validity)" if derived else "") + ".",
                    [ctx.doc_ev(d, field_name="_derivedExpiry" if derived else fname),
                     {"type": "RULE", "label": "Scrutiny date", "reference": ctx.today.isoformat()}],
                    document_id=d.id))
                notes.append(f"{d.doc_type} expired {exp}")
                continue
            if warn and days <= warn:
                o.findings.append(ctx.finding(
                    rule, f"{d.id}:EXPIRING", f"{label} expires soon ({exp.isoformat()})",
                    f"{label} expires in {days} day(s); renewal should be ensured before the academic year.",
                    [ctx.doc_ev(d, field_name=fname)], severity="MINOR", document_id=d.id))
                notes.append(f"{d.doc_type} expiring in {days}d")
        if max_age and iss:
            age = (ctx.today - iss).days
            if age > int(max_age):
                o.failed += 1
                o.findings.append(ctx.finding(
                    rule, f"{d.id}:STALE", f"{label} is not for the current year (dated {iss.isoformat()})",
                    f"{label} is dated {age} days before the scrutiny date; it must be executed within {max_age} days "
                    f"for academic year {ctx.app.academic_year}.",
                    [ctx.doc_ev(d, field_name="issueDate")], document_id=d.id))
                notes.append(f"{d.doc_type} dated {iss} ({age}d old)")
    if p.get("checkRecords"):
        types_set = set(types)
        if types_set & {"NBA_ACCREDITATION", "NAAC_ACCREDITATION"}:
            accs = ctx.records.get("accreditations") or []
            ctx.touch("accreditations", len(accs))
            for a in accs:
                body = str(a.get("body", "")).upper()
                claimed = ctx.form.get("nbaAccredited") if body == "NBA" else ctx.form.get("naacAccredited")
                if not claimed:
                    continue
                o.checks += 1
                vt = _d(a.get("validTo"))
                if vt and vt < ctx.today:
                    o.failed += 1
                    o.findings.append(ctx.finding(
                        rule, f"REC:{body}:{a.get('ref')}", f"{body} accreditation on record expired {vt.isoformat()}",
                        f"The application claims {body} accreditation but AICTE records show validity ended on {vt}"
                        f"{' for ' + a['programme'] if a.get('programme') else ''}.",
                        [ctx.form_ev(f"{body.lower()}Accredited", claimed),
                         ctx.rec_ev("accreditations", f"{body} {a.get('grade') or ''} valid {a.get('validFrom')} to {a.get('validTo')} (ref {a.get('ref')})")]))
                    notes.append(f"record {body} expired {vt}")
        if "AFFIDAVIT_UNDERTAKING" in types_set:
            affs = ctx.records.get("affidavits") or []
            ctx.touch("affidavits", len(affs))
            has_doc = bool(ctx.by_type.get("AFFIDAVIT_UNDERTAKING"))
            has_rec = any(str(a.get("year")) == ctx.app.academic_year for a in affs)
            if not has_doc and not has_rec and ctx.category != "NEW_INSTITUTION":
                o.checks += 1
                o.failed += 1
                o.findings.append(ctx.finding(
                    rule, "REC:AFFIDAVIT", f"No affidavit for {ctx.app.academic_year} on record or uploaded",
                    "Neither an uploaded affidavit nor an AICTE record of an affidavit for the current year was found.",
                    [ctx.rec_ev("affidavits", ", ".join(str(a.get('year')) for a in affs) or "none")]))
    if o.checks == 0:
        return Outcome("SKIPPED", "No dated documents of the targeted types uploaded", findings=o.findings)
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"{o.checks - o.failed}/{o.checks} validity checks passed" + (f" ({'; '.join(notes)})" if notes else "")
    return o


def r_field_present(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    o = Outcome()
    missing = []
    for f in p.get("fields") or []:
        o.checks += 1
        v = ctx.form.get(f)
        if v in (None, "", []):
            o.failed += 1
            missing.append(f)
            o.findings.append(ctx.finding(rule, f"FORM:{f}", f"Declared field missing: {f}",
                                          f"The application form does not declare '{f}', which is needed for rule checks.",
                                          [ctx.form_ev(f, None)]))
    for dt, flds in (p.get("documentFields") or {}).items():
        for d in ctx.by_type.get(dt, []):
            for f in flds:
                o.checks += 1
                if get_field(d.extracted_fields, f) is None:
                    o.failed += 1
                    missing.append(f"{dt}.{f}")
                    o.findings.append(ctx.finding(
                        rule, f"DOC:{d.id}:{f}", f"{doc_type_label(dt)}: '{f}' not readable",
                        f"The field '{f}' could not be extracted from {d.file_name}; the document cannot be checked at source automatically.",
                        [ctx.doc_ev(d)], document_id=d.id))
    if o.checks == 0:
        return Outcome("SKIPPED", "No applicable fields / documents")
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"{o.checks - o.failed}/{o.checks} fields present" + (f"; missing: {', '.join(missing)}" if missing else "")
    return o


def _within(a: float, b: float, tol: float) -> bool:
    if tol <= 0:
        return abs(a - b) < 1e-9
    return abs(a - b) <= tol * max(abs(b), 1e-9)


def r_field_match_record(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    path = p.get("recordPath", "")
    rec_val = resolve_record(ctx.records, path)
    ctx.touch(path.split("(")[-1].split(")")[0].split(".")[0].split("[")[0])
    o = Outcome(records=[path])
    if "expectedIn" in p:
        o.checks = 1
        latest = resolve_record(ctx.records, path.split(").")[0] + ")") if path.startswith("latest(") else None
        ok = rec_val in p["expectedIn"]
        problems = []
        if not ok:
            problems.append(f"latest value is {rec_val!r}, expected one of {p['expectedIn']}")
        if ok and p.get("requirePreviousYear") and isinstance(latest, dict):
            if str(latest.get("year")) not in (ctx.prev_ay, ctx.app.academic_year):
                ok = False
                problems.append(f"latest record is for {latest.get('year')}, expected {ctx.prev_ay}")
        if not ok:
            o.failed = 1
            o.findings.append(ctx.finding(
                rule, "EXPECT", f"{rule['name']}: not satisfied",
                f"AICTE records check failed for '{path}': {'; '.join(problems)}.",
                [ctx.rec_ev(path, (f"{latest.get('year')} {latest.get('status')} ({latest.get('letterRef')})"
                                   if isinstance(latest, dict) else rec_val))]))
        o.result = "FAIL" if o.failed else "PASS"
        o.detail = (f"{path} = {_fmt(rec_val)}" + (f" ({latest.get('year')})" if isinstance(latest, dict) else "")
                    + ("" if ok else " — " + "; ".join(problems)))
        return o
    if "expectedMax" in p:
        lst_key = re.match(r"(?:\w+\()?(\w+)", path)
        if lst_key and lst_key.group(1) not in ctx.records:
            return Outcome("SKIPPED", f"no '{lst_key.group(1)}' data in institutional records", records=[path])
        o.checks = 1
        n = to_number(rec_val) or 0
        if n > p["expectedMax"]:
            o.failed = 1
            lst_name = re.search(r"\((\w+)", path)
            items = [x for x in (ctx.records.get(lst_name.group(1)) if lst_name else []) or []
                     if isinstance(x, dict) and str(x.get("status")) == "OPEN"]
            o.findings.append(ctx.finding(
                rule, "MAX", f"{int(n)} open deficiency item(s) from earlier cycles",
                f"AICTE records show {int(n)} open item(s): " + "; ".join(f"{x.get('year')}: {x.get('item')}" for x in items)[:500],
                [ctx.rec_ev(path, f"{x.get('year')}: {x.get('item')} ({x.get('status')})") for x in items[:5]]))
        o.result = "FAIL" if o.failed else "PASS"
        o.detail = f"{path} = {_fmt(rec_val)} (max {p['expectedMax']})"
        return o

    ff = p.get("formField")
    base_key = re.match(r"(?:\w+\()?(\w+)", path)
    if base_key and base_key.group(1) not in ctx.records:
        return Outcome("SKIPPED", f"no '{base_key.group(1)}' data in institutional records", records=[path])
    form_val = to_number(ctx.form.get(ff))
    rv = to_number(rec_val)
    if form_val is None or rv is None:
        return Outcome("SKIPPED", f"{ff}={_fmt(ctx.form.get(ff))}, record {path}={_fmt(rec_val)} — not comparable")
    tol = float(p.get("tolerance", 0))
    allow_inc = ctx.category in (p.get("allowIncreaseCategories") or [])
    cmp = p.get("comparison", "eq")
    details = []
    if p.get("perProgramme") and isinstance(ctx.form.get("programmes"), list):
        approved = [x for x in (ctx.records.get("approvedProgrammes") or []) if isinstance(x, dict)]
        ctx.touch("approvedProgrammes", len(approved))
        for prog in ctx.form["programmes"]:
            if not isinstance(prog, dict):
                continue
            o.checks += 1
            match = next((a for a in approved if similarity(a.get("course"), prog.get("course")) >= 0.9
                          and str(a.get("shift", "1")) == str(prog.get("shift", a.get("shift", "1")))
                          and (not prog.get("level") or not a.get("level") or str(a.get("level")).upper() == str(prog.get("level")).upper())), None)
            declared = to_number(prog.get("intake")) or 0
            if match is None:
                if allow_inc and ctx.category == "NEW_COURSE":
                    details.append(f"{prog.get('course')}: new course (allowed for {ctx.category})")
                    continue
                o.failed += 1
                o.findings.append(ctx.finding(
                    rule, f"PROG:{prog.get('course')}", f"Programme not approved on record: {prog.get('course')}",
                    f"The application declares {prog.get('course')} (intake {declared:g}) which is not among AICTE-approved "
                    f"programmes for this institution.",
                    [ctx.form_ev(f"programmes[{prog.get('course')}].intake", declared),
                     ctx.rec_ev("approvedProgrammes", ", ".join(f"{a.get('course')} ({a.get('intake')})" for a in approved))]))
                continue
            appr = to_number(match.get("intake")) or 0
            if declared > appr and not allow_inc:
                o.failed += 1
                o.findings.append(ctx.finding(
                    rule, f"PROG:{prog.get('course')}", f"Intake for {prog.get('course')} exceeds approved intake ({declared:g} > {appr:g})",
                    f"Declared intake {declared:g} for {prog.get('course')} is higher than the AICTE-approved intake {appr:g}. "
                    f"An increase requires an Increase-in-Intake application.",
                    [ctx.form_ev(f"programmes[{prog.get('course')}].intake", declared),
                     ctx.rec_ev(f"approvedProgrammes[{match.get('course')}].intake", appr)]))
            elif declared != appr:
                details.append(f"{prog.get('course')}: {declared:g} vs approved {appr:g}"
                               + (" (increase requested)" if declared > appr else ""))
    # aggregate comparison
    o.checks += 1
    agg_ok = True
    if cmp == "lte":
        agg_ok = form_val <= rv * (1 + tol) or allow_inc
    else:
        agg_ok = _within(form_val, rv, tol)
    if not agg_ok and not any(f["fingerprint"].startswith(f"{rule['id']}:PROG:") for f in o.findings):
        o.failed += 1
        o.findings.append(ctx.finding(
            rule, f"AGG:{ff}", f"{ff}: declared {form_val:g} vs record {rv:g}",
            f"Declared {ff} ({form_val:g}) does not match AICTE records ({path} = {rv:g})"
            + (f" within tolerance {tol:.0%}" if tol else "") + ".",
            [ctx.form_ev(ff, ctx.form.get(ff)), ctx.rec_ev(path, rv)]))
    elif not agg_ok:
        o.failed += 1
    if allow_inc and form_val > rv:
        details.append(f"increase from {rv:g} to {form_val:g} requested under {ctx.category}")
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"{ff}={form_val:g} vs {path}={rv:g}" + (f"; {'; '.join(details)}" if details else "")
    return o


def r_field_match_document(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    ff = p.get("formField", "")
    if ff.startswith("@institution."):
        form_val = getattr(ctx.inst, ff.split(".", 1)[1], None)
        form_label = "Registered institution name"
    else:
        form_val = ctx.form.get(ff)
        form_label = f"Application form: {ff}"
    types = p.get("docType")
    types = types if isinstance(types, list) else [types]
    ef = p.get("extractedField")
    o = Outcome()
    if form_val in (None, ""):
        return Outcome("SKIPPED", f"form value '{ff}' not declared")
    notes = []
    for dt in types:
        for d in ctx.by_type.get(dt, []):
            fobj = get_field(d.extracted_fields, ef)
            if fobj is None:
                continue
            o.checks += 1
            dv = fobj.get("value")
            if "minSimilarity" in p:
                sim = similarity(form_val, dv)
                ok = sim >= float(p["minSimilarity"])
                cmp_txt = f"similarity {sim:.2f}"
            else:
                a, b = to_number(form_val), to_number(dv)
                if a is None or b is None:
                    ok = similarity(form_val, dv) >= 0.9
                    cmp_txt = "text"
                else:
                    ok = _within(a, b, float(p.get("tolerance", 0)))
                    cmp_txt = f"diff {a - b:+g}"
            if not ok:
                o.failed += 1
                notes.append(f"{dt}: {dv!r} ({cmp_txt})")
                o.findings.append(ctx.finding(
                    rule, f"{d.id}:{ef}", f"{doc_type_label(dt)}: {ef} differs from declared value",
                    f"{form_label} is {form_val!r} but {d.file_name} states {dv!r} ({cmp_txt}).",
                    [{"type": "FIELD", "label": form_label, "submitted": _fmt(form_val)},
                     {"type": "FIELD", "label": f"{doc_type_label(dt)}: {ef}", "documentId": d.id,
                      "page": fobj.get("page"), "excerpt": _fmt(fobj.get("sourceText")), "reference": _fmt(dv)}],
                    document_id=d.id))
    if o.checks == 0:
        return Outcome("SKIPPED", f"No uploaded {'/'.join(types)} with readable '{ef}'")
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"{o.checks - o.failed}/{o.checks} documents consistent with {ff}" + (f"; {'; '.join(notes)}" if notes else "")
    return o


def _total_intake(ctx: Ctx) -> float | None:
    v = to_number(ctx.form.get("proposedIntake")) if ctx.category == "INTAKE_INCREASE" else None
    return v or to_number(ctx.form.get("totalIntake")) or (
        sum(to_number(p.get("intake")) or 0 for p in ctx.form.get("programmes") or [] if isinstance(p, dict)) or None)


def _students(ctx: Ctx, default_years: int) -> tuple[float | None, str]:
    s = to_number(ctx.form.get("studentCount"))
    if s:
        return s, "declared studentCount"
    progs = [p for p in ctx.form.get("programmes") or [] if isinstance(p, dict)]
    if progs:
        tot = sum((to_number(p.get("intake")) or 0) * LEVEL_YEARS.get(str(p.get("level", "UG")).upper(), default_years) for p in progs)
        return tot, "sum(programme intake x duration)"
    ti = _total_intake(ctx)
    return (ti * default_years if ti else None), f"totalIntake x {default_years} years"


def r_threshold(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    metric = p.get("metric")
    if metric == "faculty_student_ratio":
        students, basis = _students(ctx, int(p.get("programmeDurationYears", 4)))
        declared = to_number(ctx.form.get("facultyCount"))
        rec_fac = len(ctx.records.get("faculty") or []) or None
        ctx.touch("faculty", rec_fac or 0)
        if not students or not (declared or rec_fac):
            return Outcome("SKIPPED", "student or faculty numbers unavailable")
        mx = float(p.get("max", 20))
        o = Outcome(checks=0)
        parts = []
        for label, fac in (("declared", declared), ("AICTE records", rec_fac)):
            if not fac:
                continue
            o.checks += 1
            ratio = students / fac
            parts.append(f"{label}: 1:{ratio:.1f}")
            if ratio > mx:
                o.failed += 1
                needed = math.ceil(students / mx)
                o.findings.append(ctx.finding(
                    rule, f"FSR:{label}", f"Faculty-student ratio 1:{ratio:.1f} exceeds 1:{mx:g} ({label} faculty)",
                    f"With {students:g} students ({basis}) and {fac:g} faculty ({label}) the ratio is 1:{ratio:.1f}; "
                    f"at least {needed} faculty are required (shortfall {needed - fac:g}).",
                    [{"type": "FIELD", "label": f"Students ({basis})", "submitted": _fmt(students)},
                     ctx.form_ev("facultyCount", declared) if label == "declared" else ctx.rec_ev("count(faculty)", rec_fac),
                     {"type": "RULE", "label": "Norm (illustrative)", "reference": f"1:{mx:g}"}]))
        o.result = "FAIL" if o.failed else "PASS"
        o.detail = f"students {students:g} ({basis}); " + ", ".join(parts) + f"; max 1:{mx:g}"
        return o
    if metric == "land_area_acres":
        land = to_number(ctx.form.get("landAreaAcres"))
        if land is None:
            land = to_number((ctx.records.get("landAndBuilding") or {}).get("landAreaAcres"))
        if land is None:
            return Outcome("SKIPPED", "land area not declared")
        loc = str(ctx.form.get("locationType") or "").upper()
        mn = float((p.get("minByLocation") or {}).get(loc, p.get("defaultMin", 0)))
        o = Outcome(checks=1)
        if land < mn:
            o.failed = 1
            o.findings.append(ctx.finding(
                rule, "LAND", f"Land area {land:g} acres below minimum {mn:g} acres ({loc or 'default'})",
                f"Declared land {land:g} acres is below the illustrative minimum of {mn:g} acres for location type {loc or 'unspecified'}.",
                [ctx.form_ev("landAreaAcres", land), ctx.form_ev("locationType", loc or None),
                 {"type": "RULE", "label": "Minimum land (illustrative)", "reference": f"{mn:g} acres"}]))
        o.result = "FAIL" if o.failed else "PASS"
        o.detail = f"land {land:g} acres vs min {mn:g} ({loc or 'default'})"
        return o
    if metric == "builtup_area_per_intake":
        area = to_number(ctx.form.get("builtUpAreaSqm"))
        intake = _total_intake(ctx)
        if not area or not intake:
            return Outcome("SKIPPED", "built-up area or intake not declared")
        per = area / intake
        mn = float(p.get("min", 0))
        o = Outcome(checks=1)
        if per < mn:
            o.failed = 1
            o.findings.append(ctx.finding(
                rule, "BUA", f"Built-up area {per:.1f} sqm per intake below {mn:g}",
                f"{area:g} sqm for an annual intake of {intake:g} gives {per:.1f} sqm per seat; at least {mn:g} is expected "
                f"(i.e. {mn * intake:,.0f} sqm, shortfall {mn * intake - area:,.0f} sqm).",
                [ctx.form_ev("builtUpAreaSqm", area), {"type": "FIELD", "label": "Annual intake", "submitted": _fmt(intake)},
                 {"type": "RULE", "label": "Norm (illustrative)", "reference": f"{mn:g} sqm / seat"}]))
        o.result = "FAIL" if o.failed else "PASS"
        o.detail = f"{per:.1f} sqm per seat (built-up {area:g} / intake {intake:g}) vs min {mn:g}"
        return o
    return Outcome("SKIPPED", f"unknown metric {metric}")


_DESIG = {"professor": "professor", "prof": "professor", "associate": "associateProfessor",
          "assistant": "assistantProfessor"}


def _cadre_from_designations(items: list) -> dict[str, int]:
    c = {"professor": 0, "associateProfessor": 0, "assistantProfessor": 0}
    for x in items:
        d = str((x.get("designation") if isinstance(x, dict) else x) or "").lower()
        if "assoc" in d:
            c["associateProfessor"] += 1
        elif "assist" in d or "asst" in d:
            c["assistantProfessor"] += 1
        elif "prof" in d:
            c["professor"] += 1
    return c


def r_cadre_ratio(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    ratio = p.get("ratio", [1, 2, 6])
    tol = float(p.get("tolerance", 0.5))
    cad, basis = None, ""
    if isinstance(ctx.form.get("cadre"), dict):
        cad = {k: int(to_number(ctx.form["cadre"].get(k)) or 0) for k in ("professor", "associateProfessor", "assistantProfessor")}
        basis = "declared cadre"
    if cad is None:
        for d in ctx.by_type.get("FACULTY_ROSTER", []):
            lst = get_value(d.extracted_fields, "faculty") or get_value(d.extracted_fields, "facultyList")
            cd = get_value(d.extracted_fields, "cadre")
            if isinstance(cd, dict):
                cad, basis = {k: int(to_number(cd.get(k)) or 0) for k in ("professor", "associateProfessor", "assistantProfessor")}, "faculty roster"
                break
            if isinstance(lst, list) and lst:
                cad, basis = _cadre_from_designations(lst), "faculty roster"
                break
    if cad is None and ctx.records.get("faculty"):
        cad, basis = _cadre_from_designations(ctx.records["faculty"]), "AICTE faculty records"
        ctx.touch("faculty", len(ctx.records["faculty"]))
    if not cad or sum(cad.values()) == 0:
        return Outcome("SKIPPED", "no cadre information available")
    total = sum(cad.values())
    unit = total / sum(ratio)
    exp_prof, exp_assoc = unit * ratio[0], unit * ratio[1]
    o = Outcome(checks=2)
    short = []
    if cad["professor"] < exp_prof * (1 - tol):
        short.append(f"Professors {cad['professor']} (expected ~{exp_prof:.1f})")
    if cad["associateProfessor"] < exp_assoc * (1 - tol):
        short.append(f"Associate Professors {cad['associateProfessor']} (expected ~{exp_assoc:.1f})")
    o.failed = len(short)
    actual = f"{cad['professor']}:{cad['associateProfessor']}:{cad['assistantProfessor']}"
    if short:
        o.findings.append(ctx.finding(
            rule, "CADRE", f"Cadre ratio {actual} deviates from 1:2:6 norm",
            f"Based on {basis} ({total} faculty): " + "; ".join(short) + f". Tolerance {tol:.0%}.",
            [{"type": "FIELD" if basis != "AICTE faculty records" else "RECORD", "label": f"Cadre ({basis})",
              "submitted": actual}, {"type": "RULE", "label": "Norm (illustrative)", "reference": ":".join(map(str, ratio))}]))
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"cadre {actual} from {basis}; expected ~{exp_prof:.1f}:{exp_assoc:.1f}:{unit * ratio[2]:.1f}"
    return o


def r_ter_payment(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    pays = [x for x in ctx.records.get("terPayments") or [] if isinstance(x, dict)]
    ctx.touch("terPayments", len(pays))
    cur = [x for x in pays if str(x.get("year")) == ctx.app.academic_year]
    o = Outcome(checks=1)
    notes = []
    declared = ctx.form.get(p.get("formField", "terTxnId"))
    paid_records = [x for x in cur if str(x.get("status")).upper() == "PAID"]
    paid = next((x for x in paid_records if str(x.get("txnId", "")).upper() == str(declared or "").upper()),
                paid_records[0] if paid_records else None)
    if not paid:
        o.failed += 1
        st = cur[0].get("status") if cur else "no record"
        o.findings.append(ctx.finding(
            rule, "UNPAID", f"TER for {ctx.app.academic_year} not paid ({st})",
            f"AICTE payment records show no PAID TER transaction for {ctx.app.academic_year} (found: {st}).",
            [ctx.rec_ev("terPayments", "; ".join(f"{x.get('year')} {x.get('status')} {x.get('txnId')}" for x in pays) or "none")]))
        notes.append(f"record status {st}")
    else:
        notes.append(f"record PAID {paid.get('txnId')} on {paid.get('paidOn')}")
    if declared and paid:
        o.checks += 1
        if str(declared).strip().upper() != str(paid.get("txnId", "")).strip().upper():
            o.failed += 1
            o.findings.append(ctx.finding(
                rule, "TXN_FORM", "Declared TER transaction ID does not match payment records",
                f"Form declares {declared} but the PAID transaction on record is {paid.get('txnId')}.",
                [ctx.form_ev("terTxnId", declared), ctx.rec_ev("terPayments.txnId", paid.get("txnId"))],
                kind="RECORD_MISMATCH"))
    for d in ctx.by_type.get(p.get("docType", "TER_PAYMENT_RECEIPT"), []):
        txn = get_value(d.extracted_fields, p.get("extractedField", "txnId"))
        if not txn:
            continue
        o.checks += 1
        ref = (paid or {}).get("txnId") or declared
        if ref and str(txn).strip().upper() != str(ref).strip().upper():
            o.failed += 1
            o.findings.append(ctx.finding(
                rule, f"TXN_DOC:{d.id}", "TER receipt transaction ID differs from records",
                f"Receipt {d.file_name} shows {txn} but {'payment records show' if paid else 'the form declares'} {ref}.",
                [ctx.doc_ev(d, field_name=p.get("extractedField", "txnId")),
                 ctx.rec_ev("terPayments.txnId", ref) if paid else ctx.form_ev("terTxnId", ref)],
                kind="INCONSISTENCY", document_id=d.id))
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = "; ".join(notes) + f"; {o.checks - o.failed}/{o.checks} TER checks passed"
    return o


def r_duplicate_document(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    max_h = int(p.get("maxHamming", 6))
    ignore = set(p.get("ignoreDocTypes") or [])
    mine = [d for d in ctx.docs if d.doc_type not in ignore]
    if not mine:
        return Outcome("SKIPPED", "no documents uploaded")
    others = ctx.db.execute(
        select(Document, Application, Institution)
        .join(Application, Document.application_id == Application.id)
        .join(Institution, Application.institution_id == Institution.id)
        .where(Application.institution_id != ctx.inst.id)
    ).all()
    ctx.touch("otherInstitutionDocuments", len(others))
    o = Outcome(checks=len(mine))
    for d in mine:
        hits = []
        for od, oa, oi in others:
            # Do not penalise an identifiable original owner for another
            # institution claiming its evidence.
            owner = get_value(d.extracted_fields, "institutionName")
            if owner and similarity(owner, ctx.inst.name) >= 0.9 and similarity(owner, oi.name) < 0.9:
                continue
            gps = ((d.infra or {}).get("exif") or {}).get("gps")
            own_distance = _haversine_km(gps, ctx.inst.campus_gps) if gps and ctx.inst.campus_gps else None
            other_distance = _haversine_km(gps, oi.campus_gps) if gps and oi.campus_gps else None
            if own_distance is not None and other_distance is not None and own_distance <= 2 < other_distance:
                continue
            if od.sha256 == d.sha256:
                hits.append((od, oa, oi, "identical file (SHA-256)", 0))
            elif d.phash and od.phash and d.doc_type == od.doc_type:
                h = _hamming(d.phash, od.phash)
                # pHash captures page layout; common templates collide.
                # Require independent content evidence for near-duplicates.
                same_ref = bool(d.reference_no and od.reference_no and
                                re.sub(r"\W", "", d.reference_no).upper() == re.sub(r"\W", "", od.reference_no).upper())
                text = re.sub(r"\s+", "", d.ocr_text or "").casefold()
                other_text = re.sub(r"\s+", "", od.ocr_text or "").casefold()
                same_text = len(text) >= 80 and text == other_text
                if h is not None and h <= max_h and (same_ref or same_text):
                    hits.append((od, oa, oi, f"visually near-identical (pHash distance {h}), corroborated by matching reference/text", h))
        if hits:
            o.failed += 1
            od, oa, oi, how, _ = sorted(hits, key=lambda x: x[4])[0]
            o.findings.append(ctx.finding(
                rule, f"{d.id}", f"{doc_type_label(d.doc_type)} also submitted by another institution",
                f"{d.file_name} is {how} to a document in application {oa.application_no} of {oi.name}"
                + (f" (+{len(hits) - 1} more)" if len(hits) > 1 else "") + ".",
                [ctx.doc_ev(d), {"type": "RECORD", "label": f"Other institution: {oi.name} ({oi.permanent_id})",
                                 "reference": f"{oa.application_no} / {od.file_name}",
                                 "excerpt": f"sha256 {od.sha256[:16]}…, phash {od.phash}"}],
                document_id=d.id))
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"{len(mine)} document(s) compared against {len(others)} from other institutions; {o.failed} duplicate(s)"
    return o


def _faculty_of(records: dict, form: dict | None) -> list[dict]:
    out = []
    for f in records.get("faculty") or []:
        if isinstance(f, dict):
            out.append({"name": f.get("name"), "pan": f.get("panMasked") or f.get("pan"), "src": "records",
                        "designation": f.get("designation")})
    for f in (form or {}).get("faculty") or []:
        if isinstance(f, dict):
            out.append({"name": f.get("name"), "pan": f.get("pan") or f.get("panMasked"), "src": "form",
                        "designation": f.get("designation")})
    return out


def r_duplicate_faculty(rule, ctx: Ctx) -> Outcome:
    mine = _faculty_of(ctx.records, ctx.form)
    for d in ctx.by_type.get("FACULTY_ROSTER", []):
        lst = get_value(d.extracted_fields, "faculty") or get_value(d.extracted_fields, "facultyList") or []
        for f in lst if isinstance(lst, list) else []:
            if isinstance(f, dict):
                mine.append({"name": f.get("name"), "pan": f.get("pan") or f.get("panMasked"), "src": f"roster#{d.id}",
                             "designation": f.get("designation"), "documentId": d.id})
    mine = [m for m in mine if _norm_pan(m.get("pan"))]
    if not mine:
        return Outcome("SKIPPED", "no faculty PANs available")
    index: dict[str, list[tuple[Institution, dict]]] = {}
    insts = ctx.db.execute(select(Institution).where(Institution.id != ctx.inst.id)).scalars().all()
    other_apps = ctx.db.execute(select(Application).where(Application.institution_id != ctx.inst.id)).scalars().all()
    forms_by_inst: dict[int, dict] = {}
    for a in other_apps:
        if a.form_data and a.form_data.get("faculty"):
            forms_by_inst[a.institution_id] = a.form_data
    for oi in insts:
        for f in _faculty_of(oi.records or {}, forms_by_inst.get(oi.id)):
            k = _norm_pan(f.get("pan"))
            if k:
                index.setdefault(k, []).append((oi, f))
    ctx.touch("otherInstitutionFaculty", sum(len(v) for v in index.values()))
    o = Outcome()
    seen = set()
    for m in mine:
        k = _norm_pan(m["pan"])
        if k in seen:
            continue
        seen.add(k)
        o.checks += 1
        hits = index.get(k)
        if not hits:
            continue
        o.failed += 1
        oi, of = hits[0]
        sim = similarity(m.get("name"), of.get("name")) if m.get("name") and of.get("name") else None
        o.findings.append(ctx.finding(
            rule, k, f"Faculty {m.get('name') or k} also listed at {oi.name}",
            f"PAN {k} ({m.get('name')}, {m.get('designation') or 'n/a'}, source: {m['src']}) also appears in the "
            f"{of['src']} of {oi.name} ({oi.permanent_id}) as {of.get('name')}"
            + (f" — name similarity {sim:.2f}" if sim is not None else "") + ".",
            [{"type": "FIELD" if m["src"] != "records" else "RECORD", "label": f"This institution ({m['src']})",
              "submitted": f"{m.get('name')} / {k}", "documentId": m.get("documentId")},
             {"type": "RECORD", "label": f"{oi.name} ({of['src']})", "reference": f"{of.get('name')} / {k}"}],
            document_id=m.get("documentId")))
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"{o.checks} unique faculty PAN(s) checked against {len(insts)} other institution(s); {o.failed} conflict(s)"
    return o


def r_forensic_flag(rule, ctx: Ctx) -> Outcome:
    min_sev = rule.get("params", {}).get("minSeverity", "MINOR")
    o = Outcome(checks=len(ctx.docs))
    if not ctx.docs:
        return Outcome("SKIPPED", "no documents uploaded")
    flagged = []
    for d in ctx.docs:
        fs = forensic_findings(d, rule, min_sev)
        if fs:
            o.failed += 1
            flagged.append(f"{d.doc_type}({len(fs)})")
            o.findings += fs
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"{len(ctx.docs)} document(s) analysed; flagged: {', '.join(flagged) or 'none'}"
    return o


def r_source_verification(rule, ctx: Ctx) -> Outcome:
    if not ctx.docs:
        return Outcome("SKIPPED", "no documents uploaded")
    counts: dict[str, int] = {}
    o = Outcome()
    for d in ctx.docs:
        st = (d.verification or {}).get("status") or "VERIFICATION_PENDING"
        counts[st] = counts.get(st, 0) + 1
        if st == "NOT_APPLICABLE":
            continue
        o.checks += 1
        if st in ("MISMATCH_DETECTED", "EXPIRED"):
            o.failed += 1
        o.findings += verification_findings(d, rule)
    if o.checks == 0:
        return Outcome("SKIPPED", "no verifiable documents", findings=o.findings)
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    return o


def r_infra_evidence(rule, ctx: Ctx) -> Outcome:
    p = rule.get("params", {})
    et = p.get("evidenceType")
    o = Outcome()
    if et and et != "ANY":
        docs = ctx.by_type.get(p.get("docType"), []) or [d for d in ctx.docs if (d.infra or {}).get("evidenceType") == et]
        docs = [d for d in docs if d.infra]
        if not docs:
            return Outcome("SKIPPED", f"no analysed {et} evidence uploaded")
        labels = p.get("label") or []
        labels = labels if isinstance(labels, list) else [labels]
        mn = int(p.get("minCount", 1))
        best = 0
        for d in docs:
            counts = (d.infra or {}).get("counts") or {}
            # several keys may describe the same objects (e.g. monitors/computers) -> take the max, not the sum
            n = max([int(to_number(v) or 0) for k, v in counts.items() if any(lb.lower() in str(k).lower() for lb in labels)] or [0])
            if not counts:
                n = sum(1 for det in (d.infra or {}).get("detections") or []
                        if isinstance(det, dict) and any(lb.lower() in str(det.get("label", "")).lower() for lb in labels))
            best = max(best, n)
        o.checks = 1
        if best < mn:
            d = docs[0]
            o.failed = 1
            o.findings.append(ctx.finding(
                rule, f"COUNT:{et}", f"{doc_type_label(d.doc_type)}: only {best} {'/'.join(labels)} detected (min {mn})",
                f"Image analysis detected {best} item(s) matching {labels} across {len(docs)} photo(s); at least {mn} expected.",
                [ctx.doc_ev(d), {"type": "IMAGE_REGION", "label": "Detections", "documentId": d.id,
                                 "excerpt": str((d.infra or {}).get("counts"))[:300]}],
                document_id=d.id))
        o.result = "FAIL" if o.failed else "PASS"
        o.detail = f"max {best} {'/'.join(labels)} detected in {len(docs)} photo(s); min {mn}"
        return o
    # ANY: photo authenticity / quality — evaluated from the image-analysis flags (EXIF age, geo-tag vs
    # campus, blur, editing software, objects not detected); one finding per flag.
    docs = [d for d in ctx.docs if d.infra]
    if not docs:
        return Outcome("SKIPPED", "no analysed infrastructure photos uploaded")
    o.checks = len(docs)
    codes = []
    for d in docs:
        fs = infra_flag_findings(d, rule)
        if fs:
            o.failed += 1
            o.findings += fs
            codes += [f["fingerprint"].split(":")[-1] for f in fs]
    o.result = "FAIL" if o.failed else "PASS"
    o.detail = f"{len(docs)} photo(s) analysed; {o.failed} with flags" + (f" ({', '.join(sorted(set(codes)))})" if codes else "")
    return o


EVALUATORS = {
    "DOCUMENT_EXPIRY": r_document_expiry,
    "FIELD_PRESENT": r_field_present,
    "FIELD_MATCH_RECORD": r_field_match_record,
    "FIELD_MATCH_DOCUMENT": r_field_match_document,
    "THRESHOLD": r_threshold,
    "CADRE_RATIO": r_cadre_ratio,
    "TER_PAYMENT": r_ter_payment,
    "DUPLICATE_DOCUMENT": r_duplicate_document,
    "DUPLICATE_FACULTY": r_duplicate_faculty,
    "FORENSIC_FLAG": r_forensic_flag,
    "SOURCE_VERIFICATION": r_source_verification,
    "INFRA_EVIDENCE": r_infra_evidence,
}


# ------------------------------------------------------------------ scores / status / alerts
def compute_scores(rules_applied: list[dict], findings, weights: dict) -> tuple[float, float, str]:
    num = den = 0.0
    for r in rules_applied:
        if r["result"] == "SKIPPED":
            continue
        w = float(weights.get(r["severity"], 1))
        if w <= 0:
            continue
        frac = (1 - r["failed"] / r["checks"]) if r.get("checks") else (1.0 if r["result"] == "PASS" else 0.0)
        num += w * max(0.0, frac)
        den += w
    compliance = round(100 * num / den, 1) if den else 100.0
    # Repeated indicators from the same family are correlated evidence, not
    # independent reasons to escalate. Minor-only applications stay LOW.
    groups: dict[tuple[str, str], list[float]] = {}
    critical_integrity = False
    for f in findings:
        if f.status not in ACTIVE_STATUSES:
            continue
        points = SEV_POINTS.get(f.severity, 0) * KIND_MULT.get(f.kind, 0.4)
        groups.setdefault((f.kind, f.severity), []).append(points)
        if f.severity == "CRITICAL" and f.kind in {"VERIFICATION", "ANOMALY", "DUPLICATE", "RECORD_MISMATCH"}:
            critical_integrity = True
    minor = substantive = 0.0
    for (_, severity), points in groups.items():
        peak = max(points)
        contribution = min(2 * peak, peak + 0.25 * (sum(points) - peak))
        if severity == "MINOR":
            minor += contribution
        else:
            substantive += contribution
    risk = substantive + min(15.0, minor)
    if critical_integrity:
        risk = max(60.0, risk)
    risk = round(min(100.0, risk), 1)
    band = "LOW" if risk < 30 else ("MEDIUM" if risk < 60 else "HIGH")
    return compliance, risk, band


def _alert(db: Session, app: Application, typ: str, sev: str, msg: str) -> bool:
    exists = db.execute(select(Alert).where(Alert.application_id == app.id, Alert.type == typ,
                                            Alert.message == msg, Alert.read.is_(False))).first()
    if exists:
        return False
    db.add(Alert(application_id=app.id, type=typ, severity=sev, message=msg))
    return True


def make_alerts(db: Session, app: Application, checklist: list[dict]) -> int:
    n = 0
    no = app.application_no
    missing = [c["docType"] for c in checklist if c["status"] == "MISSING" and c["mandatory"]]
    if missing:
        n += _alert(db, app, "MISSING_DOCUMENTS", "MAJOR", f"{no}: {len(missing)} mandatory document(s) missing ({', '.join(missing[:4])}{'…' if len(missing) > 4 else ''})")
    expired = [c["docType"] for c in checklist if c["status"] == "EXPIRED"]
    if expired:
        n += _alert(db, app, "DOCUMENT_EXPIRED", "CRITICAL", f"{no}: expired document(s): {', '.join(expired)}")
    docs = app.documents
    unavailable = [d for d in docs if (d.verification or {}).get("status") == "SOURCE_UNAVAILABLE"]
    pending = [d for d in docs if (d.verification or {}).get("status") == "VERIFICATION_PENDING"]
    if unavailable:
        srcs = sorted({str((d.verification or {}).get("source") or "issuing authority") for d in unavailable})
        n += _alert(db, app, "SOURCE_UNAVAILABLE", "MINOR", f"{no}: source unavailable for {len(unavailable)} document(s) ({', '.join(srcs)}); verification will be retried")
    if pending or unavailable:
        n += _alert(db, app, "SOURCE_VERIFICATION_PENDING", "INFO", f"{no}: {len(pending) + len(unavailable)} document(s) awaiting source verification")
    active = [f for f in app.findings if f.status in ACTIVE_STATUSES]
    anomalies = [f for f in active if f.kind in ("ANOMALY", "VERIFICATION") and f.severity in ("CRITICAL", "MAJOR")]
    if anomalies:
        n += _alert(db, app, "SUSPECTED_ANOMALY", "CRITICAL", f"{no}: {len(anomalies)} suspected tampering / verification anomaly(ies) — e.g. {anomalies[0].title}")
    dups = [f for f in active if f.kind == "DUPLICATE"]
    if dups:
        n += _alert(db, app, "DUPLICATE_DETECTED", "CRITICAL", f"{no}: {len(dups)} cross-institution duplicate(s) — e.g. {dups[0].title}")
    return n


# ------------------------------------------------------------------ main
def run_validation(db: Session, application_id: int, actor: User | str | None = None,
                   update_status: bool = True) -> dict:
    from ..schemas import finding_out  # local import to avoid a cycle

    t0 = time.perf_counter()
    app = db.get(Application, application_id)
    if app is None:
        raise KeyError(application_id)
    actor = actor or "system"
    db.refresh(app)
    ctx = Ctx(db, app)
    version = ruleset_version(db)
    all_rules = load_rules(db)
    weights = severity_weights()

    checklist = build_checklist(ctx)
    rules_applied: list[dict] = []
    generated: list[dict] = []
    for rule in all_rules:
        base = {"ruleId": rule["id"], "name": rule["name"], "type": rule["type"], "severity": rule["severity"],
                "clause": rule.get("clause"), "version": rule.get("version", 1)}
        if not rule.get("enabled", True):
            rules_applied.append({**base, "result": "SKIPPED", "detail": "rule disabled by administrator", "checks": 0, "failed": 0})
            continue
        if not rule_applies(rule, ctx.category):
            rules_applied.append({**base, "result": "SKIPPED", "detail": f"not applicable to category {ctx.category}", "checks": 0, "failed": 0})
            continue
        try:
            if rule["type"] == "REQUIRED_DOCUMENT":
                out = r_required_document(rule, ctx, checklist)
            elif rule["type"] in EVALUATORS:
                out = EVALUATORS[rule["type"]](rule, ctx)
            else:
                out = Outcome("SKIPPED", f"unknown rule type {rule['type']}")
        except Exception as e:  # noqa: BLE001 - a broken rule must not abort validation
            out = Outcome("SKIPPED", f"rule evaluation error: {type(e).__name__}: {e}")
        generated += out.findings
        rules_applied.append({**base, "result": out.result, "detail": out.detail, "checks": out.checks, "failed": out.failed})

    # rule-independent per-document pipeline checks
    for d in ctx.docs:
        generated += classification_findings(d) + pipeline_error_findings(d)

    # Cross-document consistency verification
    from .cross_verification import run_cross_verification
    xdoc_result = run_cross_verification(app)
    for disc in xdoc_result.get("discrepancies", []):
        doc_a_id = disc["docA"]["id"] if disc["docA"]["id"] > 0 else None
        generated.append({
            "fingerprint": f"XDOC:{disc['id']}",
            "kind": "INCONSISTENCY",
            "severity": disc["severity"],
            "document_id": doc_a_id,
            "rule_id": "R-XDOC-001",
            "clause": disc.get("clause", "APH 2024-27 — Ch. I, Cross-document verification"),
            "title": f"Cross-document disparity: {disc['fieldLabel']}",
            "reason": disc["description"],
            "evidence": [
                {"type": "FIELD", "label": f"{disc['docA']['type']} Value", "documentId": doc_a_id, "submitted": str(disc["docA"]["value"])},
                {"type": "FIELD", "label": f"{disc['docB']['type']} Value", "documentId": disc["docB"]["id"] if disc["docB"]["id"] > 0 else None, "reference": str(disc["docB"]["value"])},
            ],
        })

    sync = sync_findings(db, app, generated, origin="VALIDATOR")
    db.refresh(app)
    compliance, risk, band = compute_scores(rules_applied, app.findings, weights)

    active = [f for f in app.findings if f.status in ACTIVE_STATUSES]
    pending_src = [d for d in app.documents if (d.verification or {}).get("status") in ("SOURCE_UNAVAILABLE", "VERIFICATION_PENDING")]
    old_status = app.status
    if update_status and app.status in AUTO_STATUS_FROM:
        if any(f.severity in ("CRITICAL", "MAJOR") for f in active):
            app.status = "DEFICIENCIES_FLAGGED"
        elif pending_src:
            app.status = "SOURCE_VERIFICATION_PENDING"
        else:
            app.status = "UNDER_REVIEW"
    app.checklist = checklist
    app.compliance_score = compliance
    app.risk_score = risk
    app.risk_band = band
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    app.last_validated_at = now
    n_alerts = make_alerts(db, app, checklist)

    duration = round(time.perf_counter() - t0, 3)
    counts = {
        "documents": len(app.documents),
        "findingsOpen": len(active),
        "critical": sum(f.severity == "CRITICAL" for f in active),
        "major": sum(f.severity == "MAJOR" for f in active),
        "minor": sum(f.severity == "MINOR" for f in active),
        "info": sum(f.severity == "INFO" for f in active),
        "verified": sum((d.verification or {}).get("status") == "VERIFIED" for d in app.documents),
        "pending": len(pending_src),
        "mismatches": sum((d.verification or {}).get("status") == "MISMATCH_DETECTED" for d in app.documents),
    }
    report = {
        "applicationId": app.id,
        "applicationNo": app.application_no,
        "category": app.category,
        "academicYear": app.academic_year,
        "status": app.status,
        "generatedAt": now.isoformat() + "Z",
        "rulesetVersion": version,
        "durationSeconds": duration,
        "scrutinyDate": ctx.today.isoformat(),
        "summary": {**counts, "complianceScore": compliance, "riskScore": risk, "riskBand": band,
                    "rulesPassed": sum(r["result"] == "PASS" for r in rules_applied),
                    "rulesFailed": sum(r["result"] == "FAIL" for r in rules_applied),
                    "rulesSkipped": sum(r["result"] == "SKIPPED" for r in rules_applied)},
        "checklist": checklist,
        "findings": [finding_out(f) for f in app.findings],
        "verifications": [{"documentId": d.id, "docType": d.doc_type, "docTypeLabel": doc_type_label(d.doc_type),
                           "fileName": d.file_name, "status": (d.verification or {}).get("status"),
                           "source": (d.verification or {}).get("source"), "method": (d.verification or {}).get("method"),
                           "checkedAt": (d.verification or {}).get("checkedAt"),
                           "reason": (d.verification or {}).get("reason")} for d in app.documents],
        "rulesApplied": rules_applied,
        "recordsChecked": ctx.records_checked,
        "crossVerification": {
            "score": xdoc_result.get("overallScore", 100.0),
            "status": xdoc_result.get("status", "CONSISTENT"),
            "discrepanciesCount": xdoc_result.get("discrepanciesCount", 0),
        },
        "advisory": True,
        "disclaimer": "Advisory decision support generated by VeriSense. Findings require officer review; "
                      "the final decision rests with the competent AICTE authority.",
    }
    db.add(ValidationRun(application_id=app.id, ruleset_version=version, duration_seconds=duration,
                         triggered_by=actor.username if isinstance(actor, User) else str(actor), report=report))
    audit.record(db, actor, "VALIDATION_RUN", "Application", app.id, {
        "applicationNo": app.application_no, "rulesetVersion": version, "durationSeconds": duration,
        "rules": {"pass": report["summary"]["rulesPassed"], "fail": report["summary"]["rulesFailed"],
                  "skipped": report["summary"]["rulesSkipped"]},
        "failedRules": [r["ruleId"] for r in rules_applied if r["result"] == "FAIL"],
        "findings": sync, "complianceScore": compliance, "riskScore": risk, "riskBand": band,
        "statusFrom": old_status, "statusTo": app.status, "alertsCreated": n_alerts,
        "recordsChecked": ctx.records_checked, "documentsChecked": len(app.documents),
    }, commit=False)
    db.commit()
    return report
