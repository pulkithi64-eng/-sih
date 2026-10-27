"""HTTP endpoints of the simulated issuing authorities (mounted at /mock by app.main)."""
from __future__ import annotations

import asyncio
import random

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.pipeline.signature import known_keys

from . import service

router = APIRouter(tags=["simulated-authorities"])

SIMULATED_LATENCY_MS = (40, 260)   # realistic jitter for the demo


async def _respond(source_id: str, doc_type: str | None, ref: str) -> JSONResponse:
    await asyncio.sleep(random.uniform(*SIMULATED_LATENCY_MS) / 1000)
    code, body = service.lookup(source_id, doc_type, ref)
    return JSONResponse(status_code=code, content=body)


@router.get("/")
async def index():
    from app.adapters import registry

    return {"simulated": True, "disclaimer": service.DISCLAIMER,
            "services": [{**s, "records": len(service.records(s["id"]))} for s in registry.list_sources()],
            "endpoints": ["/mock/digilocker/issued/{uri}", "/mock/nba/accreditations/{ref}", "/mock/naac/assessments/{ref}",
                          "/mock/fire/noc/{ref}", "/mock/municipal/occupancy/{ref}", "/mock/municipal/permits/{ref}",
                          "/mock/land/records/{ref}", "/mock/ter/txn/{id}", "/mock/aicte/eoa/{ref}", "/mock/udin/{udin}",
                          "/mock/keys"]}


@router.get("/keys")
async def keys():
    """Public-key directory of simulated issuers (Ed25519) used to verify signed QR codes offline."""
    return {"simulated": True, "keys": known_keys()}


@router.get("/digilocker/issued/{uri:path}")
async def digilocker_issued(uri: str):
    return await _respond("digilocker", None, uri)


@router.get("/nba/accreditations/{ref:path}")
async def nba(ref: str):
    return await _respond("nba", "NBA_ACCREDITATION", ref)


@router.get("/naac/assessments/{ref:path}")
async def naac(ref: str):
    return await _respond("naac", "NAAC_ACCREDITATION", ref)


@router.get("/fire/noc/{ref:path}")
async def fire_noc(ref: str):
    return await _respond("municipal_fire", "FIRE_NOC", ref)


@router.get("/municipal/occupancy/{ref:path}")
async def occupancy(ref: str):
    return await _respond("municipal_fire", "OCCUPANCY_CERTIFICATE", ref)


@router.get("/municipal/permits/{ref:path}")
async def permits(ref: str):
    return await _respond("municipal_fire", "BUILDING_PLAN_APPROVAL", ref)


@router.get("/land/records/{ref:path}")
async def land(ref: str):
    return await _respond("land_records", "LAND_DOCUMENT", ref)


@router.get("/ter/txn/{txn_id:path}")
async def ter(txn_id: str):
    return await _respond("ter_payments", "TER_PAYMENT_RECEIPT", txn_id)


@router.get("/aicte/eoa/{ref:path}")
async def eoa(ref: str):
    return await _respond("aicte_eoa", "PREVIOUS_EOA_LETTER", ref)


@router.get("/udin/{udin:path}")
async def udin(udin: str):
    return await _respond("ca_udin", "AUDITED_FINANCIAL_STATEMENT", udin)
