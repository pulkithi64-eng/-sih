"""Seed demo data (idempotent).

    cd backend && uv run python -m seed.seed            # seed (skips what exists)
    cd backend && uv run python -m seed.seed --reset    # wipe DB + storage first

Creates the demo users (contract section 2), institutions / institutional records / applications from
samples/scenarios.json, uploads every listed sample file through the SAME ingestion service as the API
(so the full document pipeline runs), then validates. Adds a few generated lightweight applications for
dashboard volume. If scenarios.json is missing, only users are created.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import random
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import audit  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import SessionLocal, init_db, reset_engine  # noqa: E402
from app.engine.ingest import ingest_document  # noqa: E402
from app.engine.validator import run_validation  # noqa: E402
from app.models import Alert, Application, Institution, User  # noqa: E402
from app.routers.applications import assign_officer, next_application_no  # noqa: E402
from app.security import hash_password  # noqa: E402

log = logging.getLogger("verisense.seed")

PASSWORD = "Demo@2026"
USERS = [
    # username, full name, role, region, institution key
    ("inst.piat", "Nodal Officer — PIAT", "INSTITUTION", None, "piat"),
    ("inst.apex", "Nodal Officer — Apex", "INSTITUTION", None, "apex"),
    ("officer.wro", "Smt. A. Kulkarni (Scrutiny Officer, WRO)", "SCRUTINY_OFFICER", "WR", None),
    ("officer.nro", "Shri R. Malhotra (Scrutiny Officer, NRO)", "SCRUTINY_OFFICER", "NR", None),
    ("rd.wro", "Dr. S. Deshpande (Regional Director, WRO)", "REGIONAL_DIRECTOR", "WR", None),
    ("admin", "AICTE IT / Regulation Bureau Admin", "ADMIN", None, None),
]


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seed_users(db) -> dict[str, User]:
    out = {}
    pw = None
    for username, name, role, region, _ in USERS:
        u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if u is None:
            pw = pw or hash_password(PASSWORD)
            u = User(username=username, full_name=name, role=role, region=region, password_hash=pw)
            db.add(u)
            db.flush()
            audit.record(db, "seed", "USER_CREATED", "User", u.id, {"username": username, "role": role, "region": region},
                         commit=False)
        out[username] = u
    db.commit()
    return out


def _institution(db, data: dict) -> Institution:
    inst = db.execute(select(Institution).where(Institution.key == data["key"])).scalar_one_or_none()
    if inst is None:
        inst = db.execute(select(Institution).where(Institution.permanent_id == data["permanentId"])).scalar_one_or_none()
    if inst is not None:
        return inst
    inst = Institution(
        key=data["key"], permanent_id=data["permanentId"], name=data["name"],
        type=data.get("type", "Private-Self Financing"), state=data.get("state", ""), city=data.get("city", ""),
        region=data.get("region", "WR"), established_year=data.get("establishedYear"),
        trust_name=data.get("trustName", ""), address=data.get("address", ""), campus_gps=data.get("campusGps"),
        records=data.get("records") or {},
    )
    db.add(inst)
    db.flush()
    audit.record(db, "seed", "INSTITUTION_CREATED", "Institution", inst.id,
                 {"permanentId": inst.permanent_id, "name": inst.name, "region": inst.region}, commit=False)
    return inst


def _application(db, inst: Institution, key: str | None, category: str, ay: str, form: dict,
                 scenario: str | None = None, expected: list | None = None) -> tuple[Application, bool]:
    if key:
        existing = db.execute(select(Application).where(Application.key == key)).scalar_one_or_none()
        if existing is not None:
            return existing, False
    app = Application(application_no=next_application_no(db, category, ay, inst), key=key, institution_id=inst.id,
                      category=category, academic_year=ay, status="DRAFT", region=inst.region, form_data=form or {},
                      scenario=scenario, expected_findings=expected)
    db.add(app)
    db.flush()
    audit.record(db, "seed", "APPLICATION_CREATED", "Application", app.id,
                 {"applicationNo": app.application_no, "category": category, "academicYear": ay, "seeded": True},
                 commit=False)
    db.commit()
    return app, True


def _submit_and_validate(db, app: Application, target_status: str, actor) -> None:
    if target_status == "DRAFT":
        run_validation(db, app.id, actor, update_status=False)
        return
    app.status = "SUBMITTED"
    app.submitted_at = _now() - timedelta(days=random.randint(1, 12))
    app.assigned_officer = assign_officer(db, app.region)
    audit.record(db, actor, "APPLICATION_SUBMITTED", "Application", app.id,
                 {"applicationNo": app.application_no, "documents": len(app.documents), "seeded": True})
    run_validation(db, app.id, "system")


def _apply_workflow(db, app: Application, status: str, users: dict[str, User]) -> None:
    """Move generated applications into later workflow states, with audit trail."""
    officer = users.get("officer.wro") if app.region == "WR" else users.get("officer.nro")
    rd = users.get("rd.wro")
    now = _now().isoformat() + "Z"
    if status == "RECOMMENDED" and officer:
        app.recommendation = {"action": "RECOMMEND_ISSUE_DEFICIENCY_LETTER", "note": "Seeded: deficiencies require rectification.",
                              "decidedBy": officer.username, "decidedByName": officer.full_name, "role": officer.role, "decidedAt": now}
        app.status = "RECOMMENDED"
        audit.record(db, officer, "RECOMMENDATION_RECORDED", "Application", app.id, {**app.recommendation, "seeded": True})
    elif status == "INSPECTION_ORDERED" and rd:
        app.decision = {"action": "ORDER_INSPECTION", "note": "Seeded: physical verification of infrastructure ordered.",
                        "decidedBy": rd.username, "decidedByName": rd.full_name, "role": rd.role, "decidedAt": now}
        app.status = "INSPECTION_ORDERED"
        audit.record(db, rd, "DECISION_RECORDED", "Application", app.id, {**app.decision, "seeded": True})
    elif status == "RECTIFICATION_REQUESTED" and officer:
        app.status = "RECTIFICATION_REQUESTED"
        db.add(Alert(application_id=app.id, type="RECTIFICATION_REQUESTED", severity="MAJOR",
                     message=f"{app.application_no}: rectification requested — upload missing documents"))
        audit.record(db, officer, "RECTIFICATION_REQUESTED", "Application", app.id, {"note": "Seeded", "findingIds": []})
    db.commit()


GENERATED = [
    # key, name, city, state, region, category, status, intake, faculty, land, builtup, location
    ("gen-sinhgad", "Shreeyash College of Engineering & Technology (synthetic)", "Aurangabad", "Maharashtra", "WR",
     "EOA", "UNDER_REVIEW", 300, 82, 12.0, 15500, "URBAN"),
    ("gen-vidarbha", "Vidarbha Institute of Technology (synthetic)", "Nagpur", "Maharashtra", "WR",
     "INTAKE_INCREASE", "RECOMMENDED", 240, 50, 8.0, 9000, "URBAN"),
    ("gen-saurashtra", "Saurashtra Polytechnic Institute (synthetic)", "Rajkot", "Gujarat", "WR",
     "NEW_COURSE", "INSPECTION_ORDERED", 180, 40, 6.0, 7200, "URBAN"),
    ("gen-konkan", "Konkan Institute of Management Studies (synthetic)", "Ratnagiri", "Maharashtra", "WR",
     "CHANGE_OF_NAME", "RECTIFICATION_REQUESTED", 120, 30, 3.0, 4100, "URBAN"),
    ("gen-doaba", "Doaba Institute of Engineering (synthetic)", "Jalandhar", "Punjab", "NR",
     "EOA", "SUBMITTED", 360, 70, 15.0, 17000, "RURAL"),
    ("gen-yamuna", "Yamuna Group of Institutions (synthetic)", "Panipat", "Haryana", "NR",
     "NEW_INSTITUTION", "DRAFT", 300, 0, 9.5, 11000, "RURAL"),
]


def _gen_records(rng: random.Random, intake: int, faculty: int, land: float, builtup: float, ay_start: int) -> dict:
    desig = ["Professor"] * max(1, faculty // 9) + ["Associate Professor"] * max(1, 2 * faculty // 9)
    desig += ["Assistant Professor"] * max(0, faculty - len(desig))
    names = ["A. Sharma", "R. Iyer", "P. Kulkarni", "S. Gupta", "M. Khan", "N. Reddy", "K. Joshi", "V. Patil", "D. Singh", "T. Nair"]
    fac = []
    for i, d in enumerate(desig[:faculty]):
        pan = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(5)) + f"{rng.randint(1000, 9999)}" + rng.choice("ABCDEFGHJK")
        fac.append({"facultyId": f"F{rng.randint(100000, 999999)}", "name": f"Dr. {names[i % len(names)]} {i + 1}" if d != "Assistant Professor" else f"{names[i % len(names)]} {i + 1}",
                    "panMasked": pan[:2] + "XXX" + pan[5:], "designation": d, "qualification": "Ph.D." if d == "Professor" else "M.Tech",
                    "department": rng.choice(["CSE", "ME", "EE", "CE", "ECE"]), "joiningDate": f"{rng.randint(2010, 2023)}-0{rng.randint(1, 9)}-1{rng.randint(0, 9)}"})
    prev = f"{ay_start - 1}-{str(ay_start)[2:]}"
    return {
        "previousApprovals": [{"year": f"{ay_start - 2}-{str(ay_start - 1)[2:]}", "status": "APPROVED", "letterRef": f"F.No.WR/1-{rng.randint(10**9, 10**10)}/{ay_start - 2}", "date": f"{ay_start - 2}-06-15"},
                              {"year": prev, "status": "APPROVED", "letterRef": f"F.No.WR/1-{rng.randint(10**9, 10**10)}/{ay_start - 1}", "date": f"{ay_start - 1}-06-20"}],
        "approvedProgrammes": [{"level": "UG", "programme": "Engineering & Technology", "course": c, "shift": "1", "intake": intake // 3}
                               for c in ("Computer Science and Engineering", "Mechanical Engineering", "Civil Engineering")],
        "faculty": fac,
        "accreditations": [],
        "landAndBuilding": {"landAreaAcres": land, "builtUpAreaSqm": builtup, "ownership": "OWNED", "registryRef": f"REG/{rng.randint(1000, 9999)}/2008"},
        "terPayments": [{"year": f"{ay_start}-{str(ay_start + 1)[2:]}", "amount": 150000, "txnId": f"TER{ay_start}{rng.randint(100000, 999999)}", "status": "PAID", "paidOn": f"{ay_start}-02-10"}],
        "deficiencyHistory": [],
        "affidavits": [{"year": f"{ay_start}-{str(ay_start + 1)[2:]}", "type": "EOA", "ref": f"AFF/{rng.randint(1000, 9999)}", "notarisedOn": f"{ay_start}-01-20"}],
    }


def seed_generated(db, users: dict[str, User], ay: str = "2026-27", refresh: bool = False) -> int:
    rng = random.Random(2026)
    ay_start = int(ay[:4])
    created = 0
    for i, (key, name, city, state, region, cat, status, intake, fac, land, bua, loc) in enumerate(GENERATED):
        inst = _institution(db, {
            "key": key, "permanentId": f"1-{rng.randint(10**9, 10**10 - 1)}", "name": name, "type": "Private-Self Financing",
            "state": state, "city": city, "region": region, "establishedYear": rng.randint(1998, 2015),
            "trustName": f"{city} Education Society (synthetic)", "address": f"Plot {rng.randint(1, 99)}, MIDC Area, {city}, {state}",
            "campusGps": None, "records": _gen_records(rng, intake, fac, land, bua, ay_start)})
        rec = inst.records
        form = {"totalIntake": intake + (60 if cat == "INTAKE_INCREASE" else 0), "facultyCount": fac,
                "landAreaAcres": land, "builtUpAreaSqm": bua, "locationType": loc,
                "terTxnId": (rec.get("terPayments") or [{}])[0].get("txnId"),
                "programmes": [{**p, "intake": p["intake"] + (60 if cat == "INTAKE_INCREASE" and j == 0 else 0)}
                               for j, p in enumerate(rec.get("approvedProgrammes", []))]}
        if cat == "INTAKE_INCREASE":
            form["proposedIntake"] = form["totalIntake"]
        app, new = _application(db, inst, f"{key}-{cat.lower()}-{ay}", cat, ay, form,
                                scenario="Synthetic supporting documents with intentionally incomplete category checklists.")
        if not new:
            added = _generated_documents(db, app)
            if refresh:
                _refresh_documents(db, app)
            if added or refresh:
                run_validation(db, app.id, "seed", update_status=False)
            continue
        created += 1
        _generated_documents(db, app)
        _submit_and_validate(db, app, "DRAFT" if status == "DRAFT" else "SUBMITTED", "seed")
        db.refresh(app)
        if status in ("RECOMMENDED", "INSPECTION_ORDERED", "RECTIFICATION_REQUESTED"):
            _apply_workflow(db, app, status, users)
        elif status == "SUBMITTED":
            pass
    return created


def _generated_documents(db, app: Application) -> int:
    """Backfill distinct institution-owned evidence through the real ingestion pipeline.

    Required category-specific authority documents remain missing deliberately.
    Re-running seed is safe for existing databases and does not duplicate uploads.
    """
    from reportlab.pdfgen import canvas

    inst = app.institution
    prefix = inst.key
    uploads = []
    roster = io.StringIO()
    writer = csv.writer(roster)
    writer.writerow(["Name", "PAN", "Designation", "Qualification", "Department", "Joining Date"])
    for person in inst.records.get("faculty", []):
        writer.writerow([person.get(k, "") for k in
                         ("name", "panMasked", "designation", "qualification", "department", "joiningDate")])
    uploads.append((f"{prefix}_faculty_roster.csv", "FACULTY_ROSTER", roster.getvalue().encode()))
    for kind, title, lines in [
        ("AFFIDAVIT_UNDERTAKING", "AFFIDAVIT AND UNDERTAKING", [
            f"Academic Year: {app.academic_year}", "Notarised on: 2026-10-01",
            "The institution undertakes to rectify deficiencies before final scrutiny."]),
        ("FLOOR_PLAN", "FLOOR PLAN AND AREA STATEMENT", [
            f"Built-up Area: {app.form_data.get('builtUpAreaSqm', 0)} sq.m",
            "Schematic supporting evidence; physical inspection required."]),
    ]:
        buf = io.BytesIO()
        pdf = canvas.Canvas(buf, invariant=1)
        pdf.setTitle(f"{title} - {inst.name}")
        for i, line in enumerate([title, "SYNTHETIC DEMO DOCUMENT", f"Institution Name: {inst.name}",
                                  f"Permanent ID: {inst.permanent_id}", f"Reference No: {prefix}-{kind}-2026", *lines]):
            pdf.drawString(40, 800 - 24 * i, line)
        pdf.save()
        uploads.append((f"{prefix}_{kind.lower()}.pdf", kind, buf.getvalue()))
    existing = {d.file_name for d in app.documents}
    added = 0
    for filename, kind, data in uploads:
        if filename not in existing:
            ingest_document(db, app, data, filename, kind, "seed")
            added += 1
    return added


def seed(reset: bool = False, refresh: bool = False) -> dict:
    s = get_settings()
    if reset:
        db_path = Path(s.db)
        reset_engine()
        from app.db import get_engine

        get_engine().dispose()
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        shutil.rmtree(s.storage_path, ignore_errors=True)
        reset_engine()
    init_db()
    db = SessionLocal()
    stats = {"users": 0, "institutions": 0, "applications": 0, "documents": 0, "generated": 0, "warnings": []}
    try:
        users = seed_users(db)
        stats["users"] = len(users)
        scen_path = Path(s.samples) / "scenarios.json"
        if not scen_path.exists():
            msg = f"samples/scenarios.json not found at {scen_path} — seeded users only"
            log.warning(msg)
            stats["warnings"].append(msg)
            return stats
        scen = json.loads(scen_path.read_text(encoding="utf-8"))
        inst_by_key: dict[str, Institution] = {}
        for idata in scen.get("institutions", []):
            inst_by_key[idata["key"]] = _institution(db, idata)
            if refresh:
                inst_by_key[idata["key"]].records = idata.get("records") or {}
        db.commit()
        stats["institutions"] = len(inst_by_key)
        for username, *_rest, ikey in USERS:
            if ikey and ikey in inst_by_key and users[username].institution_id is None:
                users[username].institution_id = inst_by_key[ikey].id
        db.commit()
        inst_users = {u.institution_id: u for u in users.values() if u.institution_id}
        for adata in scen.get("applications", []):
            inst = inst_by_key.get(adata["institutionKey"])
            if inst is None:
                stats["warnings"].append(f"application {adata.get('key')}: unknown institution {adata.get('institutionKey')}")
                continue
            app, new = _application(db, inst, adata.get("key"), adata.get("category", "EOA"), adata.get("academicYear", "2026-27"),
                                    adata.get("formData") or {}, adata.get("scenario"), adata.get("expectedFindings"))
            if not new:
                if refresh:
                    _refresh_documents(db, app)
                    run_validation(db, app.id, "seed", update_status=False)
                continue
            stats["applications"] += 1
            actor = inst_users.get(inst.id) or "seed"
            for d in adata.get("documents", []):
                fp = Path(s.samples) / d["path"]
                if not fp.exists():
                    stats["warnings"].append(f"{adata.get('key')}: sample file missing {d['path']}")
                    continue
                ingest_document(db, app, fp.read_bytes(), fp.name, d.get("docType"), actor)
                stats["documents"] += 1
            db.refresh(app)
            _submit_and_validate(db, app, adata.get("status", "SUBMITTED"), actor)
        stats["generated"] = seed_generated(db, users, refresh=refresh)
    finally:
        db.close()
    for w in stats["warnings"]:
        log.warning(w)
    log.info("seed complete: %s", {k: v for k, v in stats.items() if k != "warnings"})
    return stats


def _refresh_documents(db, app):
    """Recompute derived analysis from retained OCR/QR; preserve uploads and reviews."""
    from app.engine import pipeline_bridge as pb
    from app.engine.ingest import _derive_metadata, _verify

    for doc in app.documents:
        doc.extracted_fields = pb.extract_fields(doc.doc_type, doc.ocr_text)
        _derive_metadata(doc)
        result = pb.analyse_forensics(doc.file_path, str(Path(doc.file_path).parent / "ela"))
        heat = result.get("elaHeatmapPath")
        doc.ela_path = heat if heat and Path(heat).exists() else None
        doc.forensics = {"elaScore": result.get("elaScore"), "hasElaHeatmap": bool(doc.ela_path),
                         "metadata": result.get("metadata") or {}, "flags": result.get("flags") or []}
        doc.verification = _verify(doc, doc.qr)
        audit.record(db, "seed", "DEMO_ANALYSIS_REFRESHED", "Document", doc.id,
                     {"applicationId": app.id, "retainedOcr": True, "retainedQr": True}, commit=False)
    db.commit()


def seed_if_empty() -> dict | None:
    init_db()
    db = SessionLocal()
    try:
        empty = db.execute(select(User.id).limit(1)).first() is None
    finally:
        db.close()
    if empty:
        log.info("database empty — seeding demo data")
        return seed()
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Seed VeriSense demo data")
    ap.add_argument("--reset", action="store_true", help="delete the database and stored files first")
    ap.add_argument("--refresh", action="store_true", help="refresh demo records and derived analysis; preserve workflow and reviewer decisions")
    args = ap.parse_args()
    res = seed(reset=args.reset, refresh=args.refresh)
    print(json.dumps(res, indent=2))
