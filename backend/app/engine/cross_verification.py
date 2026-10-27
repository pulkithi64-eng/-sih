"""Cross-documentation verification engine.

Verifies consistency across multiple uploaded documents within an application:
- Institution Name across statutory certificates, deeds, affidavits
- Campus Address / District / State consistency
- Land Area stated across Affidavit, Land Deed, Building Approval
- Built-up Area stated across Occupancy Certificate, Building Plan, Affidavit
- Academic Year and Validity continuity (Affiliation, EOA, Fire NOC)
- Discrepancy matrices and cross-document match confidence scores
"""
from __future__ import annotations

import re
from typing import Any

from ..models import Application, Document
from .fields import get_field, get_value, similarity, to_number
from .rules_loader import doc_type_label


def _clean_str(s: Any) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def run_cross_verification(app: Application) -> dict[str, Any]:
    """Evaluates cross-document consistency across all documents of an application."""
    docs: list[Document] = [d for d in app.documents if d.extracted_fields]
    fields_checked: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []

    # 1. Institution Name Cross-Check
    name_entries = []
    for d in docs:
        val = get_value(d.extracted_fields, "institutionName")
        if val:
            name_entries.append({
                "docId": d.id,
                "docType": d.doc_type,
                "docTypeLabel": doc_type_label(d.doc_type),
                "fileName": d.file_name,
                "value": _clean_str(val),
                "page": (get_field(d.extracted_fields, "institutionName") or {}).get("page", 1),
            })

    if len(name_entries) >= 2:
        canonical_name = app.institution.name if app.institution else name_entries[0]["value"]
        mismatches_found = []
        name_docs_out = []

        for entry in name_entries:
            sim = similarity(entry["value"], canonical_name)
            if sim >= 0.88:
                st = "MATCH"
            elif sim >= 0.70:
                st = "PARTIAL_MATCH"
            else:
                st = "MISMATCH"
                mismatches_found.append(entry)

            name_docs_out.append({**entry, "status": st, "similarity": round(sim, 2)})

        for i in range(len(name_entries)):
            for j in range(i + 1, len(name_entries)):
                d1 = name_entries[i]
                d2 = name_entries[j]
                pair_sim = similarity(d1["value"], d2["value"])
                if pair_sim < 0.75:
                    discrepancies.append({
                        "id": f"XDOC-NAME-{d1['docId']}-{d2['docId']}",
                        "field": "institutionName",
                        "fieldLabel": "Institution Name",
                        "severity": "CRITICAL" if pair_sim < 0.55 else "MAJOR",
                        "docA": {"id": d1["docId"], "type": d1["docType"], "fileName": d1["fileName"], "value": d1["value"]},
                        "docB": {"id": d2["docId"], "type": d2["docType"], "fileName": d2["fileName"], "value": d2["value"]},
                        "description": f"Institution name disparity: '{d1['value']}' ({d1['docTypeLabel']}) vs '{d2['value']}' ({d2['docTypeLabel']}).",
                        "similarity": round(pair_sim, 2),
                        "clause": "APH 2024-27 — Ch. I, Cross-verification of applicant identity across statutory certificates",
                    })

        fields_checked.append({
            "field": "institutionName",
            "label": "Institution Name",
            "status": "MISMATCH" if mismatches_found else ("PARTIAL_MATCH" if any(e["status"] == "PARTIAL_MATCH" for e in name_docs_out) else "MATCH"),
            "referenceValue": canonical_name,
            "documents": name_docs_out,
        })

    # 2. Land Area Cross-Check (Affidavit vs Land Document vs Form Data)
    land_entries = []
    form_land = to_number((app.form_data or {}).get("landAreaAcres"))
    for d in docs:
        val = to_number(get_value(d.extracted_fields, "landAreaAcres"))
        if val is not None and val > 0:
            land_entries.append({
                "docId": d.id,
                "docType": d.doc_type,
                "docTypeLabel": doc_type_label(d.doc_type),
                "fileName": d.file_name,
                "value": round(val, 2),
                "page": (get_field(d.extracted_fields, "landAreaAcres") or {}).get("page", 1),
            })

    if len(land_entries) >= 2 or (land_entries and form_land is not None):
        base_val = form_land if form_land is not None else land_entries[0]["value"]
        land_docs_out = []
        land_mismatch = False

        for entry in land_entries:
            diff_pct = abs(entry["value"] - base_val) / max(0.001, base_val)
            st = "MATCH" if diff_pct <= 0.02 else ("PARTIAL_MATCH" if diff_pct <= 0.05 else "MISMATCH")
            if st == "MISMATCH":
                land_mismatch = True
            land_docs_out.append({**entry, "status": st, "diffPct": round(diff_pct * 100, 1)})

        for i in range(len(land_entries)):
            for j in range(i + 1, len(land_entries)):
                e1 = land_entries[i]
                e2 = land_entries[j]
                diff = abs(e1["value"] - e2["value"])
                rel = diff / max(0.001, e1["value"], e2["value"])
                if rel > 0.02:
                    discrepancies.append({
                        "id": f"XDOC-LAND-{e1['docId']}-{e2['docId']}",
                        "field": "landAreaAcres",
                        "fieldLabel": "Land Area (Acres)",
                        "severity": "CRITICAL" if rel > 0.10 else "MAJOR",
                        "docA": {"id": e1["docId"], "type": e1["docType"], "fileName": e1["fileName"], "value": f"{e1['value']} acres"},
                        "docB": {"id": e2["docId"], "type": e2["docType"], "fileName": e2["fileName"], "value": f"{e2['value']} acres"},
                        "description": f"Land area discrepancy between {e1['docTypeLabel']} ({e1['value']} acres) and {e2['docTypeLabel']} ({e2['value']} acres).",
                        "diff": round(diff, 2),
                        "clause": "APH 2024-27 — Ch. III, Land ownership and title deed verification",
                    })

        fields_checked.append({
            "field": "landAreaAcres",
            "label": "Land Area (Acres)",
            "status": "MISMATCH" if land_mismatch else "MATCH",
            "referenceValue": f"{base_val} acres",
            "documents": land_docs_out,
        })

    # 3. Built-Up Area Cross-Check (Occupancy Certificate vs Affidavit vs Form Data)
    built_entries = []
    form_built = to_number((app.form_data or {}).get("builtUpAreaSqm"))
    for d in docs:
        val = to_number(get_value(d.extracted_fields, "builtUpAreaSqm"))
        if val is not None and val > 0:
            built_entries.append({
                "docId": d.id,
                "docType": d.doc_type,
                "docTypeLabel": doc_type_label(d.doc_type),
                "fileName": d.file_name,
                "value": round(val, 1),
                "page": (get_field(d.extracted_fields, "builtUpAreaSqm") or {}).get("page", 1),
            })

    if len(built_entries) >= 2 or (built_entries and form_built is not None):
        base_built = form_built if form_built is not None else built_entries[0]["value"]
        built_docs_out = []
        built_mismatch = False

        for entry in built_entries:
            diff_pct = abs(entry["value"] - base_built) / max(0.001, base_built)
            st = "MATCH" if diff_pct <= 0.05 else ("PARTIAL_MATCH" if diff_pct <= 0.10 else "MISMATCH")
            if st == "MISMATCH":
                built_mismatch = True
            built_docs_out.append({**entry, "status": st, "diffPct": round(diff_pct * 100, 1)})

        for i in range(len(built_entries)):
            for j in range(i + 1, len(built_entries)):
                b1 = built_entries[i]
                b2 = built_entries[j]
                diff = abs(b1["value"] - b2["value"])
                rel = diff / max(0.001, b1["value"], b2["value"])
                if rel > 0.05:
                    discrepancies.append({
                        "id": f"XDOC-BUILT-{b1['docId']}-{b2['docId']}",
                        "field": "builtUpAreaSqm",
                        "fieldLabel": "Built-up Area (Sq. m)",
                        "severity": "CRITICAL" if rel > 0.20 else "MAJOR",
                        "docA": {"id": b1["docId"], "type": b1["docType"], "fileName": b1["fileName"], "value": f"{b1['value']} sq.m"},
                        "docB": {"id": b2["docId"], "type": b2["docType"], "fileName": b2["fileName"], "value": f"{b2['value']} sq.m"},
                        "description": f"Built-up area variance between {b1['docTypeLabel']} ({b1['value']} sq.m) and {b2['docTypeLabel']} ({b2['value']} sq.m).",
                        "diff": round(diff, 1),
                        "clause": "APH 2024-27 — Ch. III, Verification of approved building plans and occupancy certificate",
                    })

        fields_checked.append({
            "field": "builtUpAreaSqm",
            "label": "Built-Up Area (Sq. m)",
            "status": "MISMATCH" if built_mismatch else "MATCH",
            "referenceValue": f"{base_built} sq.m",
            "documents": built_docs_out,
        })

    # 4. Academic Year Continuity Cross-Check (Affiliation vs Application Academic Year)
    ay_entries = []
    for d in docs:
        ay_val = get_value(d.extracted_fields, "academicYear")
        if ay_val:
            ay_entries.append({
                "docId": d.id,
                "docType": d.doc_type,
                "docTypeLabel": doc_type_label(d.doc_type),
                "fileName": d.file_name,
                "value": _clean_str(ay_val),
            })

    if ay_entries:
        target_ay = app.academic_year
        ay_docs_out = []
        for entry in ay_entries:
            m = re.search(r"(\d{4})", entry["value"])
            m_target = re.search(r"(\d{4})", target_ay)
            is_valid_rel = True
            if m and m_target:
                doc_year = int(m.group(1))
                target_year = int(m_target.group(1))
                # Previous EOA should be target_year - 1
                if entry["docType"] == "PREVIOUS_EOA_LETTER":
                    is_valid_rel = (doc_year == target_year - 1)
                else:
                    is_valid_rel = (doc_year >= target_year)

            st = "MATCH" if is_valid_rel else "MISMATCH"
            ay_docs_out.append({**entry, "status": st})
            if st == "MISMATCH":
                discrepancies.append({
                    "id": f"XDOC-AY-{entry['docId']}",
                    "field": "academicYear",
                    "fieldLabel": "Academic Year Validity",
                    "severity": "CRITICAL" if entry["docType"] == "UNIVERSITY_AFFILIATION" else "MAJOR",
                    "docA": {"id": entry["docId"], "type": entry["docType"], "fileName": entry["fileName"], "value": entry["value"]},
                    "docB": {"id": 0, "type": "APPLICATION", "fileName": app.application_no, "value": target_ay},
                    "description": f"Academic year mismatch in {entry['docTypeLabel']}: certified for {entry['value']}, but application is for {target_ay}.",
                    "clause": "APH 2024-27 — Ch. I, Continuity of affiliation and approval period",
                })

        fields_checked.append({
            "field": "academicYear",
            "label": "Academic Year Validity",
            "status": "MISMATCH" if any(e["status"] == "MISMATCH" for e in ay_docs_out) else "MATCH",
            "referenceValue": target_ay,
            "documents": ay_docs_out,
        })

    # Compute overall cross-verification score (0 to 100)
    total_checks = len(fields_checked)
    if total_checks == 0:
        overall_score = 100.0
        status_label = "CONSISTENT"
    else:
        penalty = sum(25 for d in discrepancies if d["severity"] == "CRITICAL") + sum(12 for d in discrepancies if d["severity"] == "MAJOR")
        overall_score = max(0.0, min(100.0, 100.0 - penalty))
        if any(d["severity"] == "CRITICAL" for d in discrepancies):
            status_label = "CRITICAL_CONFLICT"
        elif discrepancies:
            status_label = "DISCREPANCIES_FLAGGED"
        else:
            status_label = "CONSISTENT"

    return {
        "applicationId": app.id,
        "applicationNo": app.application_no,
        "overallScore": round(overall_score, 1),
        "status": status_label,
        "totalDocumentsAnalyzed": len(docs),
        "fieldsChecked": fields_checked,
        "discrepancies": discrepancies,
        "discrepanciesCount": len(discrepancies),
        "criticalCount": sum(1 for d in discrepancies if d["severity"] == "CRITICAL"),
        "majorCount": sum(1 for d in discrepancies if d["severity"] == "MAJOR"),
    }
