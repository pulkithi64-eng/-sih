from pathlib import Path

from app.pipeline.extract import extract_fields
from app.pipeline.forensics import analyse
from app.adapters.registry import Registry


SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def test_ocr_can_remove_space_in_noc_reference_label():
    fields = extract_fields("STATE_GOVT_NOC", "NOCNo.:CTE/NOC/2026/3381  Date:30.09.2026")
    assert fields["referenceNo"]["value"] == "CTE/NOC/2026/3381"


def test_document_header_date_wins_over_date_mentioned_in_body():
    fields = extract_fields("UNIVERSITY_AFFILIATION", "Letter No.: UNIVERSITY/1  Date: 05/09/2026\nResolution dated 12/07/2026")
    assert fields["issueDate"]["value"] == "2026-09-05"


def test_narrative_name_change_does_not_override_institution_label():
    fields = extract_fields("AFFIDAVIT_UNDERTAKING", "Change in Name of the Institution for the academic year.\nName of the Institution:  Example Institute of Technology")
    assert fields["institutionName"]["value"] == "Example Institute of Technology"


def test_outage_runs_through_real_mock_source(monkeypatch):
    monkeypatch.setenv("VERISENSE_SAMPLES", str(SAMPLES))
    monkeypatch.setenv("VERISENSE_MOCK_MODE", "inprocess")
    fields = extract_fields("STATE_GOVT_NOC", "NOCNo.:CTE/NOC/2026/3381  Date:30.09.2026")
    verdict = Registry().verify("STATE_GOVT_NOC", fields["referenceNo"]["value"], fields)
    assert verdict["status"] == "SOURCE_UNAVAILABLE"
    assert verdict["source"] == "digilocker"
    assert verdict["checkedAt"]


def test_rotated_seal_text_is_not_an_overlay():
    for filename in ("fire_noc.pdf", "land_sale_deed.pdf"):
        assert "TEXT_OVERLAY" not in {f["code"] for f in analyse(SAMPLES / "nvie" / filename)["flags"]}


def test_true_text_overlay_still_detected(tmp_path):
    import pymupdf

    path = tmp_path / "overlay.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Original amount: 150000")
    page.insert_text((72, 72), "Altered amount: 9999999")
    doc.save(path)
    doc.close()
    assert "TEXT_OVERLAY" in {f["code"] for f in analyse(path)["flags"]}
