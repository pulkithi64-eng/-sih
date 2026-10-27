"""Data masking and redaction utilities for PII / sensitive data."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Union


PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$", re.IGNORECASE)
AADHAAR_REGEX = re.compile(r"^\d{4}\s?\d{4}\s?\d{4}$")
PHONE_REGEX = re.compile(r"^(\+91[\-\s]?)?[6-9]\d{9}$")


def mask_pan(pan: str | None) -> str:
    """Masks PAN: ABCDE1234F -> AB****34F"""
    if not pan:
        return ""
    pan = str(pan).strip().upper()
    if len(pan) == 10:
        return f"{pan[:2]}****{pan[6:]}"
    return pan[:2] + "****" if len(pan) > 4 else "****"


def mask_aadhaar(aadhaar: str | None) -> str:
    """Masks Aadhaar: 1234 5678 9012 -> **** **** 9012"""
    if not aadhaar:
        return ""
    digits = re.sub(r"\D", "", str(aadhaar))
    if len(digits) == 12:
        return f"**** **** {digits[-4:]}"
    return "****" + digits[-4:] if len(digits) >= 4 else "****"


def mask_phone(phone: str | None) -> str:
    if not phone:
        return ""
    p = str(phone).strip()
    if len(p) >= 10:
        return f"{p[:3]}****{p[-3:]}"
    return "****"


def mask_pii_in_dict(data: Union[Dict, List, Any]) -> Any:
    """Recursively masks known sensitive field names in dictionaries."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            lower_k = k.lower()
            if "pan" in lower_k and isinstance(v, str):
                masked[k] = mask_pan(v)
            elif "aadhaar" in lower_k and isinstance(v, str):
                masked[k] = mask_aadhaar(v)
            elif "password" in lower_k or "secret" in lower_k:
                masked[k] = "********"
            elif isinstance(v, (dict, list)):
                masked[k] = mask_pii_in_dict(v)
            else:
                masked[k] = v
        return masked
    elif isinstance(data, list):
        return [mask_pii_in_dict(item) for item in data]
    return data
