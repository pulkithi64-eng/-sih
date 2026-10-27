from types import SimpleNamespace

from app.engine.validator import compute_scores


def finding(kind, severity, status="OPEN"):
    return SimpleNamespace(kind=kind, severity=severity, status=status)


def test_minor_indicators_do_not_overwhelm_compliant_application():
    rules = [{"severity": "MAJOR", "result": "PASS", "checks": 1000, "failed": 29}]
    findings = [finding("VERIFICATION", "MINOR") for _ in range(20)]
    compliance, risk, band = compute_scores(rules, findings, {"MAJOR": 3})
    assert compliance == 97.1
    assert risk <= 15
    assert band == "LOW"


def test_critical_integrity_evidence_remains_high_despite_compliance():
    assert compute_scores([], [finding("VERIFICATION", "CRITICAL")], {}) == (100.0, 60.0, "HIGH")


def test_missing_document_is_not_treated_as_confirmed_integrity_mismatch():
    assert compute_scores([], [finding("MISSING_DOCUMENT", "CRITICAL")], {})[2] == "LOW"


def test_resolved_findings_stop_contributing():
    findings = [finding("ANOMALY", "CRITICAL", s) for s in ("DISMISSED", "RECTIFIED")]
    assert compute_scores([], findings, {}) == (100.0, 0.0, "LOW")


def test_major_independent_families_can_reach_medium():
    findings = [finding("ANOMALY", "MAJOR"), finding("VERIFICATION", "MAJOR")]
    assert compute_scores([], findings, {})[2] == "MEDIUM"
