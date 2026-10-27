"""SIMULATED issuing-authority back-ends for the prototype.

Records come from samples/scenarios.json -> authorityRecords {sourceId: [{referenceNo, docType?, fields, status,
simulate?}]}. `simulate` lets a scenario reproduce real-world behaviour of an issuer:
  "OUTAGE"  -> HTTP 503 (issuer endpoint not responding)
  "PENDING" -> HTTP 202 (request accepted / awaiting issuer consent or bank settlement)
Real integration would use authorised APIs (DigiLocker Issuer/Requester APIs, NBA / NAAC registries, state
land-record and fire-NOC portals, ICAI UDIN, AICTE TER gateway) under the appropriate MoUs.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path

from app.adapters import state

DISCLAIMER = ("SIMULATED issuing authority for the VeriSense prototype; data is synthetic. Real integration would use "
              "authorized APIs (DigiLocker Issuer/Requester APIs, NBA, NAAC, state land-records and fire-NOC portals, "
              "ICAI UDIN, AICTE TER gateway).")
ISSUER_NAMES = {
    "digilocker": "DigiLocker issuer network (simulated)",
    "nba": "NBA accreditation registry (simulated)",
    "naac": "NAAC accreditation registry (simulated)",
    "municipal_fire": "Municipal building permission & fire NOC portal (simulated)",
    "land_records": "State land records portal (simulated)",
    "ter_payments": "AICTE TER payment gateway (simulated)",
    "aicte_eoa": "AICTE approval records (simulated)",
    "ca_udin": "UDIN registry (simulated)",
}
_lock = threading.Lock()
_cache: dict = {"mtime": None, "index": {}, "path": None}


def scenarios_path() -> Path:
    env = os.environ.get("VERISENSE_SAMPLES")
    root = Path(env) if env else Path(__file__).resolve().parents[3] / "samples"
    return root / "scenarios.json"


def _norm(ref: str) -> str:
    return "".join(str(ref).split()).upper()


def _index() -> dict:
    p = scenarios_path()
    with _lock:
        mtime = p.stat().st_mtime if p.exists() else None
        if _cache["mtime"] != mtime or _cache["path"] != str(p):
            idx: dict = {}
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                for sid, recs in (data.get("authorityRecords") or {}).items():
                    idx[sid] = {_norm(r["referenceNo"]): r for r in recs}
            _cache.update(mtime=mtime, index=idx, path=str(p))
        return _cache["index"]


def records(source_id: str) -> list[dict]:
    return list(_index().get(source_id, {}).values())


def lookup(source_id: str, doc_type: str | None, ref: str) -> tuple[int, dict]:
    """Return (http_status, body) exactly as the HTTP endpoint would."""
    now = datetime.now().isoformat(timespec="seconds")
    common = {"source": source_id, "issuer": ISSUER_NAMES.get(source_id, source_id), "referenceNo": ref,
              "checkedAt": now, "simulated": True, "disclaimer": DISCLAIMER}
    if not state.is_online(source_id):
        return 503, {**common, "error": "SERVICE_UNAVAILABLE",
                     "message": f"{ISSUER_NAMES.get(source_id, source_id)} is not responding (simulated outage)"}
    rec = _index().get(source_id, {}).get(_norm(ref))
    if rec is None:
        return 404, {**common, "found": False, "message": f"No record found for reference '{ref}'"}
    sim = (rec.get("simulate") or "").upper()
    if sim == "OUTAGE":
        return 503, {**common, "error": "ISSUER_ENDPOINT_DOWN",
                     "message": rec.get("message") or "Issuer endpoint behind this source is not responding (simulated)"}
    if sim == "PENDING":
        return 202, {**common, "status": "PENDING", "requestId": f"REQ-{abs(hash(_norm(ref))) % 10**8:08d}",
                     "message": rec.get("message") or "Request accepted; issuer has not yet responded", "retryAfterSec": 3600}
    body = {**common, "found": True, "status": rec.get("status", "VALID"), "fields": rec.get("fields", {}),
            "docType": rec.get("docType"), "remarks": rec.get("remarks")}
    return 200, body
