import json
from sqlalchemy import text

from app.db import SessionLocal, get_engine
from app.engine.rules_loader import load_rules
from app.models import AuditEvent, AuditImmutableError, install_audit_triggers

from .conftest import make_pdf


# ------------------------------------------------------------------ auth
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_login_and_me(client, tokens):
    r = client.get("/api/auth/me", headers=tokens["officer.wro"])
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "SCRUTINY_OFFICER" and body["region"] == "WR" and "fullName" in body


def test_login_bad_password(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_requires_token(client):
    assert client.get("/api/applications").status_code == 401
    assert client.get("/api/applications", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_meta(client, tokens):
    r = client.get("/api/meta", headers=tokens["inst.piat"])
    assert r.status_code == 200
    ids = {d["id"] for d in r.json()["docTypes"]}
    assert {"FIRE_NOC", "INFRA_PHOTO_COMPUTER_LAB", "OTHER"} <= ids
    assert len(r.json()["categories"]) == 7


# ------------------------------------------------------------------ RBAC
def test_rbac_scoping(client, tokens, eoa_app):
    aid = eoa_app["id"]
    assert eoa_app["status"] == "DRAFT" and eoa_app["applicationNo"].startswith("VS/2026-27/EOA/WR/")
    # owner and WR staff can see it
    for u in ("inst.piat", "officer.wro", "rd.wro", "admin"):
        assert client.get(f"/api/applications/{aid}", headers=tokens[u]).status_code == 200, u
    # other institution and other region cannot
    for u in ("inst.apex", "officer.nro"):
        assert client.get(f"/api/applications/{aid}", headers=tokens[u]).status_code == 404, u
        assert all(a["id"] != aid for a in client.get("/api/applications", headers=tokens[u]).json())
    # only institutions create applications
    r = client.post("/api/applications", json={"category": "EOA", "academicYear": "2026-27", "formData": {}},
                    headers=tokens["officer.wro"])
    assert r.status_code == 403
    # dashboard is officer+
    assert client.get("/api/dashboard/summary", headers=tokens["inst.piat"]).status_code == 403
    # rules write is admin only
    assert client.put("/api/rules/R-THR-001", json={"enabled": True}, headers=tokens["officer.wro"]).status_code == 403
    # records scoped
    inst_id = eoa_app["institutionId"]
    assert client.get(f"/api/institutions/{inst_id}/records", headers=tokens["inst.apex"]).status_code == 404
    assert client.get(f"/api/institutions/{inst_id}/records", headers=tokens["inst.piat"]).status_code == 200


# ------------------------------------------------------------------ upload + pipeline
def test_upload_pipeline(client, tokens, eoa_app, tmpdir_session):
    pdf = make_pdf(tmpdir_session / "fire_noc.pdf", [
        "MAHARASHTRA FIRE AND EMERGENCY SERVICES",
        "FIRE SAFETY NO OBJECTION CERTIFICATE",
        "NOC No: MFS/PUNE/2024/0451",
        "Name of Institution: Pune Institute of Advanced Technology",
        "Date of Issue: 01/04/2024",
        "Valid Upto: 31/03/2025",
        "This NOC is issued for an educational occupancy.",
    ])
    with open(pdf, "rb") as fh:
        r = client.post(f"/api/applications/{eoa_app['id']}/documents", files={"file": ("fire_noc.pdf", fh, "application/pdf")},
                        data={"docType": "FIRE_NOC"}, headers=tokens["inst.piat"])
    assert r.status_code == 201, r.text
    d = r.json()
    assert len(d["sha256"]) == 64
    assert d["docType"] == "FIRE_NOC"
    assert d["verification"]["status"] in {"VERIFIED", "MISMATCH_DETECTED", "EXPIRED", "VERIFICATION_PENDING",
                                           "SOURCE_UNAVAILABLE", "MANUAL_REVIEW_REQUIRED", "NOT_APPLICABLE"}
    assert "forensics" in d and "flags" in d["forensics"]
    # stage audit events were written
    ev = client.get(f"/api/audit?entityId={d['id']}&action=PIPELINE_STAGE", headers=tokens["admin"]).json()
    stages = {e["details"]["stage"] for e in ev}
    assert {"hashing", "ocr", "classify", "extract", "forensics", "source_verification"} <= stages
    # text endpoint and file endpoint
    assert client.get(f"/api/documents/{d['id']}/text", headers=tokens["officer.wro"]).status_code == 200
    assert client.get(f"/api/documents/{d['id']}/file", headers=tokens["inst.piat"]).status_code == 200
    assert client.get(f"/api/documents/{d['id']}/file", headers=tokens["inst.apex"]).status_code == 404


def test_upload_rejects_unknown_type_and_wrong_role(client, tokens, eoa_app):
    r = client.post(f"/api/applications/{eoa_app['id']}/documents", files={"file": ("x.txt", b"hello", "text/plain")},
                    data={"docType": "NOT_A_TYPE"}, headers=tokens["inst.piat"])
    assert r.status_code == 415
    r = client.post(f"/api/applications/{eoa_app['id']}/documents", files={"file": ("x.txt", b"hello", "text/plain")},
                    headers=tokens["officer.wro"])
    assert r.status_code == 403


def test_pipeline_failure_is_tolerated(client, tokens, eoa_app):
    # Reject malformed PDF before storage or pipeline execution.
    r = client.post(f"/api/applications/{eoa_app['id']}/documents",
                    files={"file": ("broken.pdf", b"%PDF-1.4 garbage \x00\x01\x02", "application/pdf")},
                    data={"docType": "AFFIDAVIT_UNDERTAKING"}, headers=tokens["inst.piat"])
    assert r.status_code == 400, r.text


# ------------------------------------------------------------------ validator
def test_validation_rules(client, tokens, eoa_app):
    r = client.post(f"/api/applications/{eoa_app['id']}/submit", headers=tokens["inst.piat"])
    assert r.status_code == 200, r.text
    rep = r.json()
    applied = {x["ruleId"]: x for x in rep["rulesApplied"]}
    # traceability: every configured rule has a result
    assert set(applied) == {r["id"] for r in load_rules()}
    assert all(x["result"] in ("PASS", "FAIL", "SKIPPED") and x["detail"] for x in rep["rulesApplied"])
    assert applied["R-CHK-001"]["result"] == "FAIL"           # many mandatory docs missing
    assert applied["R-THR-001"]["result"] == "FAIL"           # 6 declared faculty for 720 students
    assert applied["R-TER-001"]["result"] == "FAIL"           # TER PENDING in records
    assert applied["R-REC-001"]["result"] == "PASS"           # previous EoA 2025-26 approved
    assert applied["R-REC-002"]["result"] == "FAIL"           # CSE 150 > approved 120
    assert applied["R-REC-006"]["result"] == "FAIL"           # open deficiency from 2024-25
    assert applied["R-DUP-002"]["result"] == "FAIL"           # shared PAN with Apex
    assert applied["R-CAD-001"]["result"] in ("PASS", "FAIL")
    kinds = {f["kind"] for f in rep["findings"]}
    assert {"MISSING_DOCUMENT", "COMPLIANCE_GAP", "RECORD_MISMATCH", "DUPLICATE"} <= kinds
    # evidence points at concrete submitted vs record values
    intake = next(f for f in rep["findings"] if f["ruleId"] == "R-REC-002")
    assert any(e.get("submitted") == "150" for e in intake["evidence"])
    assert any(e.get("reference") == "120" for e in intake["evidence"])
    assert rep["status"] == "DEFICIENCIES_FLAGGED"
    assert 0 <= rep["summary"]["complianceScore"] <= 100 and rep["summary"]["riskBand"] in ("LOW", "MEDIUM", "HIGH")
    assert rep["rulesetVersion"]
    # alerts were raised
    alerts = client.get("/api/alerts", headers=tokens["officer.wro"]).json()
    assert any(a["type"] == "MISSING_DOCUMENTS" and a["applicationId"] == eoa_app["id"] for a in alerts)
    assert not any(a["applicationId"] == eoa_app["id"] for a in client.get("/api/alerts", headers=tokens["inst.apex"]).json())


def test_validation_idempotent_and_keeps_human(client, tokens, eoa_app):
    aid = eoa_app["id"]
    det = client.get(f"/api/applications/{aid}", headers=tokens["officer.wro"]).json()
    f = next(x for x in det["findings"] if x["kind"] == "MISSING_DOCUMENT")
    r = client.patch(f"/api/findings/{f['id']}", json={"status": "ACKNOWLEDGED", "note": "Institution to upload"},
                     headers=tokens["officer.wro"])
    assert r.status_code == 200
    before = client.post(f"/api/applications/{aid}/validate", headers=tokens["officer.wro"]).json()
    after = client.post(f"/api/applications/{aid}/validate", headers=tokens["officer.wro"]).json()
    assert len(before["findings"]) == len(after["findings"])
    kept = [x for x in after["findings"] if x["id"] == f["id"]]
    assert kept and kept[0]["status"] == "ACKNOWLEDGED"


def test_rule_toggle_bumps_version(client, tokens, eoa_app):
    v0 = client.get("/api/rules/version", headers=tokens["admin"]).json()["rulesetVersion"]
    r = client.put("/api/rules/R-CAD-001", json={"enabled": False}, headers=tokens["admin"])
    assert r.status_code == 200 and r.json()["enabled"] is False and r.json()["version"] == 2
    v1 = client.get("/api/rules/version", headers=tokens["admin"]).json()["rulesetVersion"]
    assert v1 != v0
    rep = client.post(f"/api/applications/{eoa_app['id']}/validate", headers=tokens["officer.wro"]).json()
    cad = next(x for x in rep["rulesApplied"] if x["ruleId"] == "R-CAD-001")
    assert cad["result"] == "SKIPPED" and "disabled" in cad["detail"]
    assert rep["rulesetVersion"] == v1
    client.put("/api/rules/R-CAD-001", json={"enabled": True}, headers=tokens["admin"])


def test_report_pdf(client, tokens, eoa_app):
    r = client.get(f"/api/applications/{eoa_app['id']}/report.pdf", headers=tokens["inst.piat"])
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and len(r.content) > 3000
    r = client.get(f"/api/applications/{eoa_app['id']}/report", headers=tokens["officer.wro"])
    assert r.status_code == 200 and r.json()["rulesApplied"]


def test_dashboard(client, tokens, eoa_app):
    d = client.get("/api/dashboard/summary", headers=tokens["officer.wro"]).json()
    assert d["totals"]["applications"] >= 1
    assert "manualEffortSavedHours" in d and d["avgValidationSeconds"] > 0
    assert d["findingsBySeverity"]["CRITICAL"] >= 1
    # NR officer sees nothing from WR
    assert client.get("/api/dashboard/summary", headers=tokens["officer.nro"]).json()["totals"]["applications"] == 0


# ------------------------------------------------------------------ decision guard
def test_decision_guard(client, tokens, eoa_app):
    aid = eoa_app["id"]
    # officer cannot decide
    r = client.post(f"/api/applications/{aid}/decision", json={"action": "APPROVE_FOR_EOA", "note": "looks fine"},
                    headers=tokens["officer.wro"])
    assert r.status_code == 403
    # note required
    r = client.post(f"/api/applications/{aid}/decision", json={"action": "APPROVE_FOR_EOA", "note": ""}, headers=tokens["rd.wro"])
    assert r.status_code == 422
    # open critical findings block approval (also for officer recommendation)
    r = client.post(f"/api/applications/{aid}/decision", json={"action": "RECOMMEND_APPROVE_FOR_EOA", "note": "recommend"},
                    headers=tokens["officer.wro"])
    assert r.status_code == 409
    r = client.post(f"/api/applications/{aid}/decision", json={"action": "APPROVE_FOR_EOA", "note": "approve it"},
                    headers=tokens["rd.wro"])
    assert r.status_code == 409 and "CRITICAL" in r.json()["detail"]
    # officer records a recommendation for inspection
    r = client.post(f"/api/applications/{aid}/decision",
                    json={"action": "RECOMMEND_ORDER_INSPECTION", "note": "Physical verification needed"}, headers=tokens["officer.wro"])
    assert r.status_code == 200 and r.json()["status"] == "RECOMMENDED"
    # RD resolves every critical finding with a reason, then approval is allowed
    det = client.get(f"/api/applications/{aid}", headers=tokens["rd.wro"]).json()
    for f in det["findings"]:
        if f["severity"] == "CRITICAL" and f["status"] in ("OPEN", "ACKNOWLEDGED", "ESCALATED"):
            rr = client.patch(f"/api/findings/{f['id']}", json={"status": "DISMISSED", "note": "Synthetic test: manually inspected and documented evidence"},
                              headers=tokens["rd.wro"])
            assert rr.status_code == 200
    r = client.post(f"/api/applications/{aid}/decision", json={"action": "APPROVE_FOR_EOA", "note": "Approved subject to conditions"},
                    headers=tokens["rd.wro"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "DECIDED" and r.json()["decision"]["decidedBy"] == "rd.wro"
    ev = client.get(f"/api/audit?entityId={aid}&action=DECISION_RECORDED", headers=tokens["admin"]).json()
    assert ev and ev[0]["details"]["note"] == "Approved subject to conditions"


def test_institution_finding_permissions(client, tokens, eoa_app):
    det = client.get(f"/api/applications/{eoa_app['id']}", headers=tokens["inst.piat"]).json()
    f = det["findings"][0]
    assert client.patch(f"/api/findings/{f['id']}", json={"status": "DISMISSED", "note": "x"},
                        headers=tokens["inst.piat"]).status_code == 409
    assert client.patch(f"/api/findings/{f['id']}", json={"status": "RECTIFIED"},
                        headers=tokens["inst.piat"]).status_code == 409


# ------------------------------------------------------------------ audit chain
def test_audit_chain_and_tamper_detection(client, tokens):
    r = client.get("/api/audit/verify", headers=tokens["admin"])
    assert r.status_code == 200 and r.json()["valid"] is True and r.json()["checked"] > 10

    db = SessionLocal()
    try:
        ev = db.query(AuditEvent).order_by(AuditEvent.id).offset(5).first()
        original_details = json.dumps(ev.details)
        # ORM refuses updates
        ev.action = "TAMPERED"
        try:
            db.flush()
            raised = False
        except AuditImmutableError:
            raised = True
        db.rollback()
        assert raised
        # DB trigger refuses raw updates
        try:
            db.execute(text("UPDATE audit_events SET action='X' WHERE id=:i"), {"i": ev.id})
            db.commit()
            trig = False
        except Exception:
            trig = True
            db.rollback()
        assert trig
        # an attacker with file access drops the trigger and edits a row -> verify detects it
        db.execute(text("DROP TRIGGER audit_no_update"))
        db.execute(text("UPDATE audit_events SET details='{\"tampered\": true}' WHERE id=:i"), {"i": ev.id})
        db.commit()
        target = ev.id
    finally:
        db.close()
    res = client.get("/api/audit/verify", headers=tokens["admin"]).json()
    assert res["valid"] is False and res["brokenAt"] == target
    # Restore the deliberate corruption so later regressions keep a valid chain.
    with SessionLocal() as restore:
        restore.execute(text("UPDATE audit_events SET details=:details WHERE id=:id"),
                        {"details": original_details, "id": target})
        restore.commit()
    install_audit_triggers(get_engine())


# ------------------------------------------------------------------ security & reliability
def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers
    assert "frame-src 'self' blob:;" in r.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none';" in r.headers["Content-Security-Policy"]


def test_auth_session_and_refresh(client, tokens):
    r = client.get("/api/auth/session", headers=tokens["officer.wro"])
    assert r.status_code == 200
    data = r.json()
    assert data["authenticated"] is True
    assert data["role"] == "SCRUTINY_OFFICER"

    ref = client.post("/api/auth/refresh", headers=tokens["officer.wro"])
    assert ref.status_code == 200
    assert "accessToken" in ref.json()


def test_health_probes(client, tokens):
    live = client.get("/api/health/live")
    assert live.status_code == 200 and live.json()["status"] == "alive"

    ready = client.get("/api/health/ready")
    assert ready.status_code == 200 and ready.json()["ready"] is True

    assert client.get("/api/health/system").status_code == 401
    system = client.get("/api/health/system", headers=tokens["admin"])
    assert system.status_code == 200 and system.json()["status"] == "healthy"


# ------------------------------------------------------------------ institution management
def test_institution_management_endpoints(client, tokens):
    # Overview stats (Officer+)
    r_stats = client.get("/api/institutions/overview/stats", headers=tokens["officer.wro"])
    assert r_stats.status_code == 200
    assert "totalInstitutions" in r_stats.json()
    assert "byRegion" in r_stats.json()

    # List institutions
    r_list = client.get("/api/institutions", headers=tokens["officer.wro"])
    assert r_list.status_code == 200
    items = r_list.json()
    assert len(items) >= 1
    assert "stats" in items[0]

    # Create new institution (Admin)
    new_inst = {
        "permanentId": "1-9999999999",
        "name": "National Test Institute",
        "type": "Government",
        "region": "WR",
        "state": "Maharashtra",
        "city": "Mumbai",
        "establishedYear": 2012,
        "trustName": "State Tech Trust",
        "address": "Bandra, Mumbai",
    }
    r_create = client.post("/api/institutions", json=new_inst, headers=tokens["admin"])
    assert r_create.status_code == 201
    created_id = r_create.json()["id"]

    # Update institution
    r_patch = client.patch(f"/api/institutions/{created_id}", json={"city": "Navi Mumbai"}, headers=tokens["admin"])
    assert r_patch.status_code == 200
    assert r_patch.json()["city"] == "Navi Mumbai"


# ------------------------------------------------------------------ cross-doc & summary
def test_cross_verification_and_summary_endpoints(client, tokens, eoa_app):
    aid = eoa_app["id"]

    # Cross-verification endpoint
    xdoc = client.get(f"/api/applications/{aid}/cross-verification", headers=tokens["officer.wro"])
    assert xdoc.status_code == 200
    body = xdoc.json()
    assert "overallScore" in body
    assert "status" in body
    assert "fieldsChecked" in body

    # Processing summary endpoint
    summary = client.get(f"/api/applications/{aid}/processing-summary", headers=tokens["officer.wro"])
    assert summary.status_code == 200
    s_body = summary.json()
    assert "scores" in s_body
    assert "processingMetrics" in s_body
    assert "advisoryRecommendation" in s_body
