"""Adapter registry: maps docTypes to issuing-authority sources and produces the 6-state verification verdict.

    from app.adapters import registry
    registry.list_sources()                                   -> [Source]
    registry.set_online("nba", False)                         (persisted in backend/data/sources_state.json)
    registry.verify(doc_type, reference_no, extracted_fields, qr_claims, today=None) -> {
        status, source, sourceName, method, checkedAt, responseSummary, comparisons[{field, submitted, source, match}],
        reason, latencyMs, transport, qr?: {...}}

Decision logic (documented for officers - all outcomes are advisory):
 1. Doc types that are evidence, not issued documents (INFRA_PHOTO_*, FACULTY_ROSTER) -> NOT_APPLICABLE.
 2. A signed issuer QR is checked first (offline-verifiable):
      signature invalid / unknown key               -> MISMATCH_DETECTED (method QR_SIGNATURE)
      signature valid but claims != printed text    -> MISMATCH_DETECTED (QR_SIGNATURE)
      signature valid, claims expired               -> EXPIRED
      signature valid and matching                  -> VERIFIED (QR_SIGNATURE), unless the online source
                                                       additionally reports revoked/expired/mismatch.
 3. Without a usable QR the authority source is queried by reference number:
      no source registered for the doc type          -> MANUAL_REVIEW_REQUIRED
      reference number not extracted                 -> MANUAL_REVIEW_REQUIRED
      source toggled offline / HTTP 5xx / refused    -> SOURCE_UNAVAILABLE
      HTTP 202 (queued) or read timeout              -> VERIFICATION_PENDING
      HTTP 404: reference extracted with conf>=0.8   -> MISMATCH_DETECTED (authority has no such record)
                otherwise                            -> MANUAL_REVIEW_REQUIRED (likely OCR error)
      record REVOKED                                 -> MISMATCH_DETECTED
      record EXPIRED or validity date in the past    -> EXPIRED
      any compared field differs                     -> MISMATCH_DETECTED
      otherwise                                      -> VERIFIED
"""
from __future__ import annotations

from datetime import date, datetime

from app.pipeline import signature as sigmod

from . import state
from .base import Adapter, build_comparisons, is_past

NOT_APPLICABLE_TYPES = {"FACULTY_ROSTER", "INFRA_PHOTO_CLASSROOM", "INFRA_PHOTO_COMPUTER_LAB", "INFRA_PHOTO_LIBRARY",
                        "INFRA_PHOTO_LABORATORY", "INFRA_PHOTO_ACCESSIBILITY"}

DISCLAIMER = "Simulated issuing-authority service (prototype). Production would use authorised APIs."


def _adapters() -> list[Adapter]:
    return [
        Adapter("digilocker", "DigiLocker - Issued Documents (simulated)",
                "DigiLocker issuer network: affiliating universities, State technical-education departments, registrars of societies",
                ["UNIVERSITY_AFFILIATION", "STATE_GOVT_NOC", "SOCIETY_TRUST_REGISTRATION"], "DIGILOCKER",
                {"UNIVERSITY_AFFILIATION": "/digilocker/issued/{ref}", "STATE_GOVT_NOC": "/digilocker/issued/{ref}",
                 "SOCIETY_TRUST_REGISTRATION": "/digilocker/issued/{ref}"},
                {"UNIVERSITY_AFFILIATION": ["institutionName", "university", "academicYear", "totalIntake", "course", "proposedName"],
                 "STATE_GOVT_NOC": ["institutionName", "academicYear", "proposedName", "course", "totalIntake"],
                 "SOCIETY_TRUST_REGISTRATION": ["trustName", "newInstitutionName", "issueDate"]},
                description="Pulls the issuer-signed copy by document URI (Requester API pattern)."),
        Adapter("nba", "NBA Accreditation Registry (simulated)", "National Board of Accreditation",
                ["NBA_ACCREDITATION"], "API", {"NBA_ACCREDITATION": "/nba/accreditations/{ref}"},
                {"NBA_ACCREDITATION": ["institutionName", "programme", "validFrom", "expiryDate"]},
                description="Programme accreditation status and validity by accreditation reference."),
        Adapter("naac", "NAAC Accreditation Registry (simulated)", "National Assessment and Accreditation Council",
                ["NAAC_ACCREDITATION"], "API", {"NAAC_ACCREDITATION": "/naac/assessments/{ref}"},
                {"NAAC_ACCREDITATION": ["institutionName", "grade", "cgpa", "expiryDate"]},
                description="Institutional grade, CGPA and validity by EC/certificate number."),
        Adapter("municipal_fire", "Municipal Building & Fire NOC Portal (simulated)",
                "Municipal Fire & Emergency Services / Building Permission Cell",
                ["FIRE_NOC", "OCCUPANCY_CERTIFICATE", "BUILDING_PLAN_APPROVAL"], "PORTAL",
                {"FIRE_NOC": "/fire/noc/{ref}", "OCCUPANCY_CERTIFICATE": "/municipal/occupancy/{ref}",
                 "BUILDING_PLAN_APPROVAL": "/municipal/permits/{ref}"},
                {"FIRE_NOC": ["institutionName", "issueDate", "expiryDate"],
                 "OCCUPANCY_CERTIFICATE": ["institutionName", "builtUpAreaSqm", "issueDate"],
                 "BUILDING_PLAN_APPROVAL": ["institutionName", "builtUpAreaSqm", "issueDate"]},
                description="NOC / permit status lookup on the urban local body portal."),
        Adapter("land_records", "State Land Records (simulated)", "State Revenue Department / Sub-Registrar",
                ["LAND_DOCUMENT"], "PORTAL", {"LAND_DOCUMENT": "/land/records/{ref}"},
                {"LAND_DOCUMENT": ["surveyNo", "landAreaAcres", "ownerName", "village", "district"]},
                description="Record-of-rights / registered deed lookup by registration number."),
        Adapter("ter_payments", "AICTE TER Payment Gateway (simulated)", "AICTE",
                ["TER_PAYMENT_RECEIPT"], "API", {"TER_PAYMENT_RECEIPT": "/ter/txn/{ref}"},
                {"TER_PAYMENT_RECEIPT": ["amount", "applicationNo", "issueDate"]},
                description="Transaction settlement status by transaction id."),
        Adapter("aicte_eoa", "AICTE Approval Records (simulated)", "AICTE",
                ["PREVIOUS_EOA_LETTER"], "API", {"PREVIOUS_EOA_LETTER": "/aicte/eoa/{ref}"},
                {"PREVIOUS_EOA_LETTER": ["institutionName", "permanentId", "academicYear", "totalIntake"]},
                description="Previously issued EoA letters by file number."),
        Adapter("ca_udin", "UDIN Verification (simulated)", "Institute of Chartered Accountants (UDIN registry)",
                ["AUDITED_FINANCIAL_STATEMENT"], "API", {"AUDITED_FINANCIAL_STATEMENT": "/udin/{ref}"},
                {"AUDITED_FINANCIAL_STATEMENT": ["financialYear", "membershipNo", "institutionName"]},
                ref_field="udin", description="Unique Document Identification Number of the certifying CA."),
    ]


def _fv(extracted: dict, name: str):
    v = extracted.get(name)
    return v.get("value") if isinstance(v, dict) and "value" in v else v


class Registry:
    def __init__(self):
        self.adapters = {a.id: a for a in _adapters()}
        self.by_doc_type = {dt: a for a in self.adapters.values() for dt in a.doc_types}

    # ------------------------------------------------------------------ admin
    def list_sources(self) -> list[dict]:
        return [a.info() for a in self.adapters.values()]

    def get_source(self, source_id: str) -> dict | None:
        a = self.adapters.get(source_id)
        return a.info() if a else None

    def set_online(self, source_id: str, online: bool) -> dict:
        if source_id not in self.adapters:
            raise KeyError(source_id)
        state.set_online(source_id, online)
        return self.adapters[source_id].info()

    def source_for(self, doc_type: str) -> str | None:
        a = self.by_doc_type.get(doc_type)
        return a.id if a else None

    # ------------------------------------------------------------------ verification
    def verify(self, doc_type: str, reference_no: str | None, extracted_fields: dict | None,
               qr_claims=None, today: date | None = None) -> dict:
        today = today or date.today()
        extracted = extracted_fields or {}
        now = datetime.now().isoformat(timespec="seconds")
        adapter = self.by_doc_type.get(doc_type)
        base = {"status": None, "source": adapter.id if adapter else None, "sourceName": adapter.name if adapter else None,
                "method": None, "checkedAt": now, "responseSummary": None, "comparisons": [], "reason": None,
                "latencyMs": None, "transport": None}

        from app.config import get_settings

        if not get_settings().demo_mode:
            return {**base, "status": "MANUAL_REVIEW_REQUIRED", "trustLevel": "UNCONFIGURED",
                    "reason": "No authorised authority integration is configured; simulated sources and demo QR keys are disabled"}
        base["trustLevel"] = "SIMULATED"

        if doc_type in NOT_APPLICABLE_TYPES:
            return {**base, "status": "NOT_APPLICABLE", "method": "MANUAL",
                    "reason": "Institution-generated evidence; checked by cross-record rules and image analysis, not by an issuing authority"}

        # printed expiry on the submitted document itself
        printed_expiry = _fv(extracted, "expiryDate")
        qr = self._qr_verdict(doc_type, extracted, qr_claims, today)
        if qr is not None and qr["decisive"]:
            out = {**base, "status": qr["status"], "method": "QR_SIGNATURE", "comparisons": qr["comparisons"],
                   "reason": qr["reason"], "responseSummary": qr["summary"], "qr": qr["detail"],
                   "source": qr.get("sourceId") or base["source"]}
            return out

        src = None
        if adapter is not None:
            src = self._source_verdict(adapter, doc_type, reference_no, extracted, today)

        if qr is not None and qr["status"] == "VERIFIED":
            # valid, matching signed QR: strong verification. Source can only downgrade it with a definitive negative.
            if src and src["status"] in ("MISMATCH_DETECTED", "EXPIRED") and src.get("definitive"):
                src.pop("definitive", None)
                return {**base, **src, "qr": qr["detail"],
                        "reason": f"{src['reason']} (QR signature itself was valid)"}
            note = ""
            if src:
                note = {"VERIFIED": "; record also confirmed at source",
                        "SOURCE_UNAVAILABLE": "; online source unavailable - QR verified offline",
                        "VERIFICATION_PENDING": "; online source check pending"}.get(src["status"], f"; source check: {src['status']}")
            return {**base, "status": "VERIFIED", "method": "QR_SIGNATURE", "comparisons": qr["comparisons"] + (src or {}).get("comparisons", []),
                    "reason": qr["reason"] + note, "responseSummary": qr["summary"], "qr": qr["detail"],
                    "latencyMs": (src or {}).get("latencyMs"), "transport": (src or {}).get("transport")}

        if src is None:
            reason = "No issuing-authority source is registered for this document type"
            if qr is not None:
                reason += f"; QR: {qr['reason']}"
            if doc_type == "OTHER":
                reason = "Document type could not be determined; route to officer"
            return {**base, "status": "MANUAL_REVIEW_REQUIRED", "method": "MANUAL", "reason": reason,
                    **({"qr": qr["detail"]} if qr else {})}
        src.pop("definitive", None)
        if src["status"] == "VERIFIED" and is_past(printed_expiry, today):
            src["status"] = "EXPIRED"
            src["reason"] = f"Printed validity ended {printed_expiry}"
        out = {**base, **src}
        if qr is not None:
            out["qr"] = qr["detail"]
        return out

    # ------------------------------------------------------------------ QR
    def _qr_verdict(self, doc_type, extracted, qr_claims, today):
        items = self._normalise_qr(qr_claims)
        if not items:
            return None
        signed = [r for r in items if r.get("keyId") or r.get("valid")]
        if not signed:
            return {"decisive": False, "status": None, "reason": "QR present but not an issuer-signed payload",
                    "comparisons": [], "summary": None, "detail": {"results": items}}
        good = [r for r in signed if r.get("valid")]
        if not good:
            r = signed[0]
            return {"decisive": True, "status": "MISMATCH_DETECTED", "reason": r.get("reason") or "QR signature invalid",
                    "comparisons": [], "summary": f"Signed QR claims issuer '{r.get('issuer')}' (key {r.get('keyId')}) - verification failed",
                    "detail": {"valid": False, "issuer": r.get("issuer"), "keyId": r.get("keyId"), "claims": r.get("claims")}}
        r = good[0]
        claims = r.get("claims") or {}
        fields = [k for k in claims.keys() if k not in ("docType", "issuer", "v")]
        comps = build_comparisons(fields, extracted, claims)
        detail = {"valid": True, "issuer": r.get("issuer"), "keyId": r.get("keyId"), "claims": claims}
        summary = f"Signed QR from '{r.get('issuer')}' (key {r.get('keyId')}); {len(comps)} field(s) compared with printed text"
        if claims.get("docType") and claims["docType"] != doc_type:
            return {"decisive": True, "status": "MISMATCH_DETECTED", "comparisons": comps, "summary": summary, "detail": detail,
                    "reason": f"Signed QR is for a {claims['docType']} but the document is classified as {doc_type} - QR may be transplanted"}
        bad = [c for c in comps if not c["match"]]
        if bad:
            diffs = "; ".join(f"{c['field']}: printed '{c['submitted']}' vs signed '{c['source']}'" for c in bad[:4])
            return {"decisive": True, "status": "MISMATCH_DETECTED", "comparisons": comps, "summary": summary, "detail": detail,
                    "reason": f"Issuer-signed QR content differs from the printed document ({diffs}) - printed text may have been altered"}
        if is_past(claims.get("expiryDate"), today):
            return {"decisive": True, "status": "EXPIRED", "comparisons": comps, "summary": summary, "detail": detail,
                    "reason": f"Issuer-signed validity ended {claims.get('expiryDate')}"}
        return {"decisive": False, "status": "VERIFIED", "comparisons": comps, "summary": summary, "detail": detail,
                "sourceId": r.get("sourceId"),
                "reason": f"Issuer signature valid ({r.get('issuer')}, key {r.get('keyId')}) and {len(comps)} signed field(s) match the printed document"}

    @staticmethod
    def _normalise_qr(qr_claims) -> list[dict]:
        if not qr_claims:
            return []
        if isinstance(qr_claims, (str, dict)):
            qr_claims = [qr_claims]
        out = []
        for q in qr_claims:
            if isinstance(q, str):
                out.append(sigmod.verify_signed_payload(q))
            elif isinstance(q, dict) and "valid" in q:
                out.append(q)
            elif isinstance(q, dict):  # bare claims dict (already verified upstream)
                out.append({"valid": True, "issuer": q.get("issuer"), "keyId": None, "claims": q, "reason": "claims supplied"})
        return out

    # ------------------------------------------------------------------ source
    def _source_verdict(self, adapter: Adapter, doc_type, reference_no, extracted, today) -> dict:
        res = {"source": adapter.id, "sourceName": adapter.name, "method": adapter.method, "comparisons": [],
               "latencyMs": None, "transport": None, "definitive": False}
        if not adapter.online:
            state.record_call(adapter.id, None, False)
            return {**res, "status": "SOURCE_UNAVAILABLE", "reason": f"{adapter.name} is marked offline by the administrator",
                    "responseSummary": "source disabled"}
        ref, ref_conf = adapter.reference_for(doc_type, reference_no, extracted)
        if not ref:
            return {**res, "status": "MANUAL_REVIEW_REQUIRED", "method": "MANUAL",
                    "reason": "Reference number could not be extracted from the document - cannot query the issuing authority"}
        r = adapter.lookup(doc_type, ref)
        res["latencyMs"] = round(r.latency_ms, 1)
        res["transport"] = r.transport
        body = r.body or {}
        if r.status_code in (0, 502, 503, 504) or r.status_code >= 500:
            state.record_call(adapter.id, r.latency_ms, False)
            return {**res, "status": "SOURCE_UNAVAILABLE",
                    "reason": body.get("message") or r.error or f"{adapter.name} did not respond (HTTP {r.status_code})",
                    "responseSummary": f"HTTP {r.status_code}" if r.status_code > 0 else "connection failed"}
        if r.status_code == -1 or r.status_code == 202:
            state.record_call(adapter.id, r.latency_ms, r.status_code == 202)
            return {**res, "status": "VERIFICATION_PENDING",
                    "reason": body.get("message") or "Source did not answer within the timeout; re-check queued",
                    "responseSummary": f"request {body.get('requestId', '')} queued".strip() if r.status_code == 202 else "timeout"}
        state.record_call(adapter.id, r.latency_ms, r.status_code in (200, 404))
        if r.status_code == 404:
            if ref_conf >= 0.8:
                return {**res, "status": "MISMATCH_DETECTED", "definitive": True,
                        "reason": f"Issuing authority has no record of reference '{ref}'", "responseSummary": "record not found"}
            return {**res, "status": "MANUAL_REVIEW_REQUIRED",
                    "reason": f"No record for '{ref}' but the reference was read with low confidence ({ref_conf:.2f}) - verify manually",
                    "responseSummary": "record not found"}
        if r.status_code != 200:
            return {**res, "status": "MANUAL_REVIEW_REQUIRED", "reason": f"Unexpected response HTTP {r.status_code}",
                    "responseSummary": f"HTTP {r.status_code}"}
        rec_fields = body.get("fields", {}) or {}
        rec_status = (body.get("status") or "VALID").upper()
        comps = build_comparisons(adapter.compare.get(doc_type, []), extracted, rec_fields)
        res["comparisons"] = comps
        summary = f"{body.get('issuer') or adapter.issuer}: record {ref} status {rec_status}"
        if body.get("docType") and body["docType"] != doc_type:
            return {**res, "status": "MISMATCH_DETECTED", "definitive": True, "responseSummary": summary,
                    "reason": f"Reference '{ref}' belongs to a {body['docType']} at the source, not a {doc_type}"}
        if rec_status == "REVOKED":
            return {**res, "status": "MISMATCH_DETECTED", "definitive": True, "responseSummary": summary,
                    "reason": f"Source reports the document as REVOKED{(' - ' + body['remarks']) if body.get('remarks') else ''}"}
        if rec_status == "EXPIRED" or is_past(rec_fields.get("expiryDate"), today):
            return {**res, "status": "EXPIRED", "definitive": True, "responseSummary": summary,
                    "reason": f"Source reports validity ended {rec_fields.get('expiryDate') or '(date not given)'}"}
        bad = [c for c in comps if not c["match"]]
        if bad:
            diffs = "; ".join(f"{c['field']}: submitted '{c['submitted']}' vs source '{c['source']}'" for c in bad[:4])
            return {**res, "status": "MISMATCH_DETECTED", "definitive": True, "responseSummary": summary,
                    "reason": f"Submitted document differs from the issuing authority's record ({diffs})"}
        return {**res, "status": "VERIFIED", "definitive": True, "responseSummary": summary,
                "reason": f"Record found at {adapter.name}; {len(comps)} field(s) match"}


registry = Registry()
