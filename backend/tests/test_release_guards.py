"""Independent security regressions; each workflow creates its own application."""
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.db import SessionLocal
from app.models import Application, Finding, User
from app.security import can_access_application, create_token, scope_applications
from app.upload_validation import MAX_UPLOAD_BYTES, validate_upload
from app.workflow import approval_blockers
from sqlalchemy import select


@pytest.mark.parametrize("state", ["OPEN", "ACKNOWLEDGED", "ESCALATED", "UNKNOWN"])
def test_unresolved_critical_blocks_approval(state):
    finding = SimpleNamespace(severity="CRITICAL", status=state)
    assert approval_blockers([finding]) == [finding]


@pytest.mark.parametrize("state", ["RECTIFIED", "DISMISSED"])
def test_reviewed_resolution_allows_approval(state):
    assert not approval_blockers([SimpleNamespace(severity="CRITICAL", status=state)])


@pytest.mark.parametrize("filename,data,mime,code", [
    ("bad.pdf", b"%PDF-1.4 garbage", "application/pdf", 400),
    ("script.html", b"<script>alert(1)</script>", "text/html", 415),
    ("fake.png", b"MZ executable", "image/png", 400),
    ("fake.pdf", b"%PDF-1.4", "image/png", 415),
    ("empty.pdf", b"", "application/pdf", 400),
    ("large.pdf", b"x" * (MAX_UPLOAD_BYTES + 1), "application/pdf", 413),
], ids=["malformed-pdf", "unsupported-html", "spoofed-png", "mime-mismatch", "empty-pdf", "oversized-pdf"])
def test_upload_rejection(filename, data, mime, code):
    with pytest.raises(HTTPException) as exc:
        validate_upload(data, filename, mime)
    assert exc.value.status_code == code


def test_pdf_and_image_content_validation(tmp_path):
    from .conftest import make_pdf
    from PIL import Image
    from io import BytesIO

    pdf = make_pdf(tmp_path / "valid.pdf", ["Synthetic document"])
    assert validate_upload(pdf.read_bytes(), "../../valid.pdf", "application/pdf") == "application/pdf"
    image = BytesIO()
    Image.new("RGB", (16, 16), "white").save(image, format="PNG")
    assert validate_upload(image.getvalue(), "valid.png", None) == "image/png"
    with pytest.raises(HTTPException):
        validate_upload(image.getvalue(), "spoof.jpg", "image/jpeg")


@pytest.mark.parametrize("role", ["SCRUTINY_OFFICER", "REGIONAL_DIRECTOR"])
def test_unassigned_region_denies_all(client, role):
    db = SessionLocal()
    try:
        user = User(username=f"unassigned-{role}", full_name="Unassigned staff", role=role,
                    region=None, password_hash="disabled", active=True)
        db.add(user)
        db.commit()
        token = create_token(user)
        assert not can_access_application(user, SimpleNamespace(region="WR", institution_id=1))
        assert not db.execute(scope_applications(select(Application), user)).scalars().all()
        headers = {"Authorization": f"Bearer {token}"}
        for path in ("applications", "institutions", "audit"):
            response = client.get(f"/api/{path}", headers=headers)
            assert response.status_code == 200 and response.json() == []
        assert client.get("/api/institutions/overview/stats", headers=headers).json()["totalInstitutions"] == 0
    finally:
        db.close()


def test_institution_cannot_rewrite_regulatory_records(client, tokens):
    institution = client.get("/api/institutions", headers=tokens["inst.piat"]).json()[0]
    for body in ({"records": {"terPayments": []}}, {"name": "Replaced"}, {"region": "NR"}):
        r = client.patch(f"/api/institutions/{institution['id']}", json=body, headers=tokens["inst.piat"])
        assert r.status_code == 403


def test_unvalidated_summary_never_asserts_success(client, tokens):
    created = client.post("/api/applications", json={"category": "EOA", "academicYear": "2026-27", "formData": {}},
                          headers=tokens["inst.piat"])
    aid = created.json()["id"]
    summary = client.get(f"/api/applications/{aid}/processing-summary", headers=tokens["officer.wro"])
    assert summary.json()["advisoryRecommendation"]["recommendedAction"] != "APPROVE_FOR_EOA"


def test_trace_ids_on_errors_and_audit(client, tokens):
    rid = "regression-request-1234"
    denied = client.get("/api/applications", headers={"X-Request-ID": rid})
    assert denied.status_code == 401
    assert denied.headers["x-request-id"] == denied.json()["requestId"] == rid
    created = client.post("/api/applications", json={"category": "EOA", "academicYear": "2026-27", "formData": {}},
                          headers={**tokens["inst.piat"], "X-Request-ID": rid})
    events = client.get(f"/api/audit?entityType=Application&entityId={created.json()['id']}&action=APPLICATION_CREATED",
                        headers=tokens["admin"]).json()
    assert events[0]["details"]["requestId"] == rid
    replaced = client.get("/api/health/live", headers={"X-Request-ID": "invalid id"})
    assert replaced.headers["x-request-id"] != "invalid id"


@pytest.mark.parametrize("options", [
    {"environment": "production", "demo_mode": True},
    {"environment": "staging", "secret": "short"},
    {"demo_mode": False, "autoseed": True},
    {"jwt_expiry_hours": 0},
])
def test_unsafe_configuration_rejected(options):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **options)


def test_non_demo_cannot_use_fixture_authority_or_qr(monkeypatch):
    from app.adapters.registry import Registry
    import app.config

    monkeypatch.setattr(app.config, "get_settings", lambda: SimpleNamespace(demo_mode=False))
    result = Registry().verify("FIRE_NOC", "synthetic-ref", {}, qr_claims=[{"valid": True}])
    assert result["status"] == "MANUAL_REVIEW_REQUIRED"
    assert result["trustLevel"] == "UNCONFIGURED"


def test_signed_invalid_subject_returns_unauthorized(client):
    import jwt
    from app.config import get_settings

    token = jwt.encode({"sub": "not-a-user-number"}, get_settings().secret, algorithm="HS256")
    result = client.get("/api/applications", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 401


@pytest.mark.parametrize("state", ["OPEN", "ACKNOWLEDGED", "ESCALATED"])
def test_endpoint_blocks_unresolved_and_self_resolution(client, tokens, state):
    created = client.post("/api/applications", json={"category": "EOA", "academicYear": "2026-27", "formData": {}},
                          headers=tokens["inst.piat"])
    aid = created.json()["id"]
    db = SessionLocal()
    try:
        app = db.get(Application, aid)
        app.status = "UNDER_REVIEW"
        app.last_validated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        finding = Finding(application_id=aid, kind="COMPLIANCE_GAP", severity="CRITICAL", title="Synthetic blocker",
                          reason="Fixture", status=state, fingerprint=f"guard-{aid}", origin="OFFICER", evidence=[])
        db.add(finding)
        db.commit()
        fid = finding.id
    finally:
        db.close()
    for account, action in (("rd.wro", "APPROVE_FOR_EOA"), ("officer.wro", "RECOMMEND_APPROVE_FOR_EOA")):
        result = client.post(f"/api/applications/{aid}/decision", json={"action": action, "note": "Review regression"},
                             headers=tokens[account])
        assert result.status_code == 409
    assert client.patch(f"/api/findings/{fid}", json={"status": "RECTIFIED", "note": "Applicant assertion"},
                        headers=tokens["inst.piat"]).status_code == 403
    assert client.patch(f"/api/findings/{fid}", json={"status": "RECTIFIED", "note": "Reviewer checked synthetic evidence"},
                        headers=tokens["officer.wro"]).status_code == 200
    decided = client.post(f"/api/applications/{aid}/decision", json={"action": "APPROVE_FOR_EOA", "note": "Reviewed resolution"},
                          headers=tokens["rd.wro"])
    assert decided.status_code == 200
    assert client.patch(f"/api/findings/{fid}", json={"status": "OPEN"}, headers=tokens["officer.wro"]).status_code == 409
    assert client.post(f"/api/applications/{aid}/validate", headers=tokens["officer.wro"]).status_code == 409
