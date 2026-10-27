"""Helpers to read extracted fields robustly (the extractor may use slightly different names)."""
from __future__ import annotations

import re
from typing import Any

from .pipeline_bridge import norm_date

ALIASES: dict[str, list[str]] = {
    "referenceNo": ["referenceNo", "refNo", "reference", "certificateNo", "certificateNumber", "nocNo", "nocNumber",
                    "letterRef", "letterNo", "registrationNo", "receiptNo", "accreditationRef", "approvalRef",
                    "documentNo", "serialNo"],
    "issueDate": ["issueDate", "dateOfIssue", "issuedOn", "issued", "date", "letterDate", "validFrom",
                  "notarisedOn", "notarizedOn", "paidOn", "paymentDate", "executionDate", "registrationDate"],
    "expiryDate": ["expiryDate", "validUntil", "validUpto", "validTo", "validTill", "expiresOn", "expiry", "validity"],
    "issuer": ["issuer", "issuedBy", "issuingAuthority", "authority"],
    "institutionName": ["institutionName", "institution", "nameOfInstitution", "collegeName", "instituteName"],
    "facultyCount": ["facultyCount", "totalFaculty", "numberOfFaculty", "faculty_count", "count"],
    "landAreaAcres": ["landAreaAcres", "landArea", "areaAcres", "area"],
    "builtUpAreaSqm": ["builtUpAreaSqm", "builtUpArea", "totalBuiltUpArea", "builtupArea", "areaSqm", "totalArea"],
    "txnId": ["txnId", "transactionId", "transactionNo", "utr", "paymentRef", "referenceNo", "receiptNo"],
    "academicYear": ["academicYear", "year", "forYear"],
    "amount": ["amount", "amountPaid", "fee"],
}


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def get_field(fields: dict | None, name: str) -> dict | None:
    """Return the extracted-field object {value, confidence, sourceText, page} for a logical name."""
    if not fields:
        return None
    index = {_key(k): k for k in fields}
    for cand in [name] + ALIASES.get(name, []):
        k = index.get(_key(cand))
        if k is not None:
            v = fields[k]
            if isinstance(v, dict):
                if v.get("value") not in (None, ""):
                    return v
            elif v not in (None, ""):
                return {"value": v, "confidence": None, "sourceText": None, "page": None}
    return None


def get_value(fields: dict | None, name: str) -> Any:
    f = get_field(fields, name)
    return f.get("value") if f else None


def get_date(fields: dict | None, name: str) -> str | None:
    return norm_date(get_value(fields, name))


def to_number(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, list):
        return float(len(v))
    m = re.search(r"-?\d[\d,]*\.?\d*", str(v))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def norm_text(s: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(s or "").lower())).strip()


def similarity(a: Any, b: Any) -> float:
    from difflib import SequenceMatcher

    na, nb = norm_text(a), norm_text(b)
    if not na or not nb:
        return 0.0
    if na == nb or na in nb or nb in na:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()
