import os
import shutil
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="verisense-test-"))
os.environ["VERISENSE_DB"] = str(_TMP / "test.db")
os.environ["VERISENSE_STORAGE"] = str(_TMP / "storage")
os.environ["VERISENSE_AUTOSEED"] = "0"
os.environ["VERISENSE_SAMPLES"] = str(_TMP / "no-samples")
os.environ["VERISENSE_REFERENCE_DATE"] = "2026-10-26"
os.environ["VERISENSE_SOURCES_STATE"] = str(_TMP / "sources_state.json")
os.environ["VERISENSE_ENVIRONMENT"] = "local"
os.environ["VERISENSE_DEMO_MODE"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Institution, User  # noqa: E402
from seed.seed import seed_users  # noqa: E402

SHARED_PAN = "ABXXX1234K"


def _records(pan_extra: str, ter_status: str = "PAID") -> dict:
    fac = [{"facultyId": f"F{i}", "name": f"Faculty {i}", "panMasked": f"PQXXX{1000 + i}Z",
            "designation": "Professor" if i < 2 else ("Associate Professor" if i < 5 else "Assistant Professor"),
            "qualification": "PhD", "department": "CSE", "joiningDate": "2015-07-01"} for i in range(12)]
    fac.append({"facultyId": "FX", "name": "Dr. Shared Person", "panMasked": pan_extra, "designation": "Professor",
                "qualification": "PhD", "department": "ME", "joiningDate": "2016-01-01"})
    return {
        "previousApprovals": [{"year": "2025-26", "status": "APPROVED", "letterRef": "F.No.WR/1-123/2025", "date": "2025-06-20"}],
        "approvedProgrammes": [{"level": "UG", "programme": "Engineering", "course": "Computer Science and Engineering", "shift": "1", "intake": 120},
                               {"level": "UG", "programme": "Engineering", "course": "Mechanical Engineering", "shift": "1", "intake": 60}],
        "faculty": fac,
        "accreditations": [],
        "landAndBuilding": {"landAreaAcres": 10.0, "builtUpAreaSqm": 9000, "ownership": "OWNED", "registryRef": "R1"},
        "terPayments": [{"year": "2026-27", "amount": 100000, "txnId": "TER2026000111", "status": ter_status, "paidOn": "2026-02-01"}],
        "deficiencyHistory": [{"year": "2024-25", "item": "Library books shortfall", "status": "OPEN"}],
        "affidavits": [{"year": "2026-27", "type": "EOA", "ref": "AFF-1", "notarisedOn": "2026-01-15"}],
    }


@pytest.fixture(scope="session")
def client():
    init_db()
    db = SessionLocal()
    users = seed_users(db)
    piat = Institution(key="piat", permanent_id="1-3948291012", name="Pune Institute of Advanced Technology",
                       type="Private-Self Financing", state="Maharashtra", city="Pune", region="WR", established_year=2009,
                       trust_name="PIAT Trust", address="Pune", campus_gps={"lat": 18.52, "lng": 73.85},
                       records=_records(SHARED_PAN, ter_status="PENDING"))
    apex = Institution(key="apex", permanent_id="1-2222222222", name="Apex College of Engineering", type="Private-Self Financing",
                       state="Haryana", city="Karnal", region="NR", established_year=2005, trust_name="Apex Trust",
                       address="Karnal", records=_records(SHARED_PAN))
    db.add_all([piat, apex])
    db.flush()
    users["inst.piat"].institution_id = piat.id
    users["inst.apex"].institution_id = apex.id
    db.commit()
    db.close()
    with TestClient(app) as c:
        yield c
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(scope="session")
def tokens(client):
    out = {}
    for u in ("inst.piat", "inst.apex", "officer.wro", "officer.nro", "rd.wro", "admin"):
        r = client.post("/api/auth/login", json={"username": u, "password": "Demo@2026"})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": f"Bearer {r.json()['accessToken']}"}
    return out


def make_pdf(path: Path, lines: list[str]) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    for ln in lines:
        c.drawString(60, y, ln)
        y -= 18
    c.save()
    return path


@pytest.fixture(scope="session")
def eoa_app(client, tokens):
    form = {"totalIntake": 180, "facultyCount": 6, "landAreaAcres": 10.0, "builtUpAreaSqm": 9000, "locationType": "URBAN",
            "terTxnId": "TER2026000111",
            "programmes": [{"level": "UG", "course": "Computer Science and Engineering", "shift": "1", "intake": 150},
                           {"level": "UG", "course": "Mechanical Engineering", "shift": "1", "intake": 30}]}
    r = client.post("/api/applications", json={"category": "EOA", "academicYear": "2026-27", "formData": form},
                    headers=tokens["inst.piat"])
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="session")
def tmpdir_session():
    d = Path(tempfile.mkdtemp(prefix="verisense-files-"))
    yield d
    shutil.rmtree(d, ignore_errors=True)
