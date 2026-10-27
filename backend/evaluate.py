"""Reproduce synthetic evaluation: python evaluate.py (after python -m seed.seed).

Reads the configured demo DB, revalidates applications, never resets data or
changes officer workflow states. Use a dedicated demo database, not production.
Outputs raw counts, per-file results and the website's generated data together.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("VERISENSE_MOCK_MODE", "inprocess")
os.environ.setdefault("VERISENSE_REFERENCE_DATE", "2026-10-26")

from sqlalchemy import select
from app.config import get_settings
from app.db import SessionLocal
from app.engine.validator import run_validation
from app.engine.ingest import _verify
from app.pipeline.extract import extract_fields
from types import SimpleNamespace
from app.adapters.base import compare_values
from app.models import Application, Document
from app.pipeline.forensics import analyse

ROOT = Path(__file__).resolve().parent.parent


def ratio(a, b):
    return round(a / b, 4) if b else None


def percent(a, b):
    return f"{100 * a / b:.1f}%" if b else "Not measured"


def timing(values):
    values = sorted(values)
    return {"n": len(values), "meanSeconds": round(statistics.mean(values), 3) if values else None,
            "p95Seconds": round(values[max(0, __import__('math').ceil(.95 * len(values)) - 1)], 3) if values else None}


def main():
    settings = get_settings()
    manifest_path = Path(settings.samples) / "scenarios.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    db = SessionLocal()
    applications = {a.key: a for a in db.scalars(select(Application)).all()}
    missing = [a["key"] for a in manifest["applications"] if a["key"] not in applications]
    if missing:
        raise SystemExit(f"Seed the demo database first; missing applications: {missing}")
    validation_times = []
    for app in applications.values():
        start = time.perf_counter()
        run_validation(db, app.id, "evaluation", update_status=False)
        validation_times.append(time.perf_counter() - start)
    docs = db.scalars(select(Document)).all()
    by_hash = {}
    for doc in docs:
        by_hash.setdefault(doc.sha256, doc)
    fields_ok = fields_n = cls_ok = 0
    states = Counter()
    verification_ok = verification_n = 0
    mismatch_tp = mismatch_fp = mismatch_fn = 0
    rows = []
    processing = []
    for item in manifest["documents"]:
        path = Path(settings.samples) / item["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        doc = by_hash.get(digest)
        if doc is None:
            raise SystemExit(f"Missing ingested sample: {item['path']}; finish seeding first")
        expected = item["groundTruth"]
        cls_correct = (doc.classification or {}).get("docType") == expected["docType"]
        cls_ok += cls_correct
        predicted_type = (doc.classification or {}).get("docType") or "OTHER"
        extracted = extract_fields(predicted_type, doc.ocr_text)
        ref = extracted.get("referenceNo", {}).get("value")
        # Evaluate the classifier's type, not a deliberately wrong upload label.
        # Wrong-label behaviour remains covered by application validation/tests.
        verdict = _verify(SimpleNamespace(doc_type=predicted_type, reference_no=ref, extracted_fields=extracted), doc.qr)
        per_fields = []
        # Infrastructure counts/GPS are a different task, not text extraction.
        if not item["docType"].startswith("INFRA_PHOTO"):
            for key, truth in expected["fields"].items():
                if isinstance(truth, (dict, list)) or truth is None:
                    continue
                actual = extracted.get(key)
                if isinstance(actual, dict):
                    actual = actual.get("value")
                ok = actual is not None and compare_values(key, actual, truth)
                fields_n += 1
                fields_ok += ok
                per_fields.append({"field": key, "correct": ok, "expected": truth, "actual": actual})
        status = verdict.get("status", "UNKNOWN")
        if item["expectedVerification"] != "NOT_APPLICABLE":
            states[status] += 1
            verification_n += 1
            verification_ok += status == item["expectedVerification"]
            predicted = status == "MISMATCH_DETECTED"
            planted = item["expectedVerification"] == "MISMATCH_DETECTED"
            mismatch_tp += predicted and planted
            mismatch_fp += predicted and not planted
            mismatch_fn += planted and not predicted
        processing.append(doc.processing_ms / 1000)
        rows.append({"path": item["path"], "sha256": digest, "classificationCorrect": cls_correct,
                     "expectedVerification": item["expectedVerification"], "verification": status,
                     "fields": per_fields, "pipelineErrors": doc.pipeline_errors})
    forensic = []
    tp = fp = fn = tn = 0
    for item in manifest["benchmark"]:
        result = analyse(Path(settings.samples) / item["path"], out_dir=settings.storage_path / "evaluation-ela")
        predicted = any(f.get("severity") in ("MINOR", "MAJOR", "CRITICAL", "HIGH", "MEDIUM")
                        for f in result.get("flags", []))
        truth = item["tampered"]
        tp += predicted and truth
        fp += predicted and not truth
        fn += not predicted and truth
        tn += not predicted and not truth
        forensic.append({**item, "predictedTampered": predicted,
                         "flags": [f.get("code") for f in result.get("flags", [])]})
    # Free-text scenario expectations are not exhaustive negative labels. Report
    # coverage only; do not misrepresent all unlisted findings as false positives.
    scenario_rows = []
    detected = expected_n = 0
    for spec in manifest["applications"]:
        app = applications[spec["key"]]
        doc_types = {d.id: d.doc_type for d in app.documents}
        labels = []
        for label in spec.get("expectedFindings", []):
            kind, target = label.split(":", 1)
            target = target.split(" (")[0].split(" x")[0].split(".")[0]
            candidates = [f for f in app.findings if f.kind == kind and f.status in ("OPEN", "ACKNOWLEDGED", "ESCALATED")]
            if target in {d.doc_type for d in app.documents} or target.isupper() and target != "FACULTY_PAN":
                found = any(doc_types.get(f.document_id) == target or target in str(f.evidence) for f in candidates)
            else:
                normalise = lambda value: re.sub(r"[^a-z0-9]", "", value.casefold())
                found = any(normalise(target) in normalise(f.title + f.reason + str(f.evidence)) for f in candidates)
            # Where labels name a verification state, require that exact state.
            wanted_states = [state for state in ("VERIFIED", "MISMATCH_DETECTED", "EXPIRED", "SOURCE_UNAVAILABLE",
                            "VERIFICATION_PENDING", "MANUAL_REVIEW_REQUIRED") if state in label]
            if found and wanted_states:
                found = any(doc_types.get(f.document_id) == target and
                            next((d.verification.get("status") for d in app.documents if d.id == f.document_id), None)
                            in wanted_states for f in candidates)
            detected += found
            expected_n += 1
            labels.append({"label": label, "detected": found})
        scenario_rows.append({"key": app.key, "documents": len(app.documents), "compliance": app.compliance_score,
                              "risk": app.risk_score, "band": app.risk_band, "expectations": labels})
    conclusive = sum(states[s] for s in ("VERIFIED", "MISMATCH_DETECTED", "EXPIRED"))
    doc_times, app_times = timing(processing), timing(validation_times)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        revision = "unknown"
    results = {
        "extraction": {"headline": percent(fields_ok, fields_n), "detail": f"{fields_ok}/{fields_n} scalar text fields match using the production normaliser (not strict character equality); missing fields count as errors. Classification: {cls_ok}/{len(rows)} documents."},
        "validation": {"headline": percent(detected, expected_n), "detail": f"{detected}/{expected_n} scenario expectations detected by kind and target. Coverage proxy only: free-text labels are incomplete; precision/F1 need exhaustive adjudication."},
        "anomaly": {"headline": f"{percent(tp, tp + fp)} precision", "detail": f"Recall {percent(tp, tp + fn)}; clean false-positive rate {percent(fp, fp + tn)}. TP {tp}, FP {fp}, FN {fn}, TN {tn}; {len(forensic)} forensic fixtures."},
        "verification": {"headline": percent(conclusive, verification_n), "detail": f"{conclusive}/{verification_n} conclusive simulated-source verdicts; expected-state accuracy {percent(verification_ok, verification_n)}. " + ", ".join(f"{k}: {v}" for k, v in sorted(states.items()))},
        "discrepancy": {"headline": f"{percent(mismatch_tp, mismatch_tp + mismatch_fp)} precision", "detail": f"Source mismatches: TP {mismatch_tp}, FP {mismatch_fp}, FN {mismatch_fn}. Record-mismatch precision still needs independent labels."},
        "time": {"headline": f"{doc_times['meanSeconds']}s / document", "detail": f"Stored ingestion durations, p95 {doc_times['p95Seconds']}s ({doc_times['n']} distinct files); fresh validation mean {app_times['meanSeconds']}s, p95 {app_times['p95Seconds']}s ({app_times['n']} applications). Local Windows CPU run."},
        "alerts": {"headline": "Same transaction", "detail": "Code-confirmed transactional creation alongside findings. End-to-end alert delivery latency has not been measured; no seconds claim is made."},
        "effort": {"headline": "Estimate only", "detail": f"Assuming {settings.manual_minutes_per_document:g} manual minutes/document + {settings.manual_minutes_per_application:g} minutes/application: {round((len(docs) * settings.manual_minutes_per_document + len(applications) * settings.manual_minutes_per_application) / 60 / len(applications), 2)} manual hours/application before subtracting automated time. No officer time study yet."},
    }
    output = {"generatedAt": datetime.now(timezone.utc).isoformat(), "revision": revision, "workingTree": "includes local evaluation/scoring changes",
              "referenceDate": settings.reference_date, "manifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "dataset": {"summary": f"{len(rows)} distinct synthetic documents, {len(forensic)} forensic fixtures, {len(applications)} demo applications. Simulated sources; no real-world accuracy claim."},
              "results": results, "counts": {"fieldsCorrect": fields_ok, "fields": fields_n, "classificationCorrect": cls_ok,
              "verificationCorrect": verification_ok, "verificationTotal": verification_n, "states": dict(states),
              "anomaly": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "mismatch": {"tp": mismatch_tp, "fp": mismatch_fp, "fn": mismatch_fn}},
              "timing": {"documents": doc_times, "applications": app_times}, "documents": rows, "forensics": forensic, "scenarios": scenario_rows}
    encoded = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    (ROOT / "samples/evaluation.json").write_text(encoded, encoding="utf-8")
    public = ROOT / "frontend/src/site/data/evaluation.generated.json"
    public.write_text(json.dumps({"generatedAt": output["generatedAt"], "dataset": output["dataset"], "results": results}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": output["counts"], "results": results}, indent=2))
    db.close()


if __name__ == "__main__":
    main()
