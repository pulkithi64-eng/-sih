"""Pydantic v2 request/response models (camelCase JSON via alias generator) + serializers."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .engine.rules_loader import doc_type_label


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    def out(self) -> dict:
        return self.model_dump(by_alias=True, mode="json")


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


# ------------------------------------------------------------------ requests
class LoginRequest(CamelModel):
    username: str
    password: str


class PasswordChangeRequest(CamelModel):
    old_password: str
    new_password: str


class InstitutionCreate(CamelModel):
    permanent_id: str
    name: str
    type: str = "Private-Self Financing"
    state: str = ""
    city: str = ""
    region: str
    established_year: int | None = None
    trust_name: str = ""
    address: str = ""
    campus_gps: dict[str, Any] | None = None
    records: dict[str, Any] = Field(default_factory=dict)


class InstitutionPatch(CamelModel):
    name: str | None = None
    type: str | None = None
    state: str | None = None
    city: str | None = None
    region: str | None = None
    established_year: int | None = None
    trust_name: str | None = None
    address: str | None = None
    campus_gps: dict[str, Any] | None = None
    records: dict[str, Any] | None = None


class ApplicationCreate(CamelModel):
    category: Literal["EOA", "NEW_INSTITUTION", "INTAKE_INCREASE", "NEW_COURSE", "CHANGE_OF_NAME", "CHANGE_OF_SITE", "CLOSURE"]
    academic_year: str = Field(pattern=r"^\d{4}-\d{2}$")
    form_data: dict[str, Any] = Field(default_factory=dict)


class ApplicationPatch(CamelModel):
    form_data: dict[str, Any]


class FindingPatch(CamelModel):
    status: Literal["OPEN", "ACKNOWLEDGED", "RECTIFIED", "DISMISSED", "ESCALATED"]
    note: str | None = None


class NoteRequest(CamelModel):
    note: str = Field(min_length=1)


class RectificationRequest(CamelModel):
    note: str = Field(min_length=1)
    finding_ids: list[int] = Field(default_factory=list)


DECISION_ACTIONS = ("APPROVE_FOR_EOA", "ISSUE_DEFICIENCY_LETTER", "ORDER_INSPECTION", "REJECT")
RECOMMEND_ACTIONS = tuple(f"RECOMMEND_{a}" for a in DECISION_ACTIONS)


class DecisionRequest(CamelModel):
    action: str
    note: str = ""


class RulePatch(CamelModel):
    enabled: bool | None = None
    params: dict[str, Any] | None = None
    severity: Literal["CRITICAL", "MAJOR", "MINOR", "INFO"] | None = None


class ChecklistItemTemplate(CamelModel):
    doc_type: str
    mandatory: bool = False
    clause: str = ""
    when: dict[str, Any] | None = None


# ------------------------------------------------------------------ responses
class UserOut(CamelModel):
    id: int
    username: str
    full_name: str
    role: str
    region: str | None = None
    institution_id: int | None = None


class InstitutionOut(CamelModel):
    id: int
    permanent_id: str
    name: str
    type: str
    state: str
    city: str
    region: str
    established_year: int | None = None
    trust_name: str
    address: str
    campus_gps: dict | None = None
    stats: dict | None = None


class EvidenceOut(CamelModel):
    type: str
    label: str
    document_id: int | None = None
    page: int | None = None
    bbox: Any = None
    excerpt: str | None = None
    submitted: str | None = None
    reference: str | None = None


class FindingOut(CamelModel):
    id: int
    application_id: int
    document_id: int | None = None
    kind: str
    severity: str
    title: str
    reason: str
    rule_id: str | None = None
    clause: str | None = None
    evidence: list[dict]
    status: str
    created_at: str
    updated_at: str
    reviewer_note: str | None = None
    origin: str
    advisory: bool = True


class AlertOut(CamelModel):
    id: int
    application_id: int
    application_no: str
    type: str
    severity: str
    message: str
    created_at: str
    read: bool


class AuditEventOut(CamelModel):
    id: int
    ts: str
    actor: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    details: dict
    prev_hash: str
    hash: str


def user_out(u) -> dict:
    return UserOut.model_validate(u).out()


def institution_out(i) -> dict:
    return InstitutionOut.model_validate(i).out()


def _evidence(ev: list) -> list[dict]:
    out = []
    for e in ev or []:
        if not isinstance(e, dict):
            continue
        clean = {k: e.get(k) for k in ("type", "label", "documentId", "page", "bbox", "excerpt", "submitted", "reference")}
        clean["type"] = clean["type"] or "RULE"
        clean["label"] = clean["label"] or ""
        for k in ("excerpt", "submitted", "reference"):
            if clean[k] is not None and not isinstance(clean[k], str):
                clean[k] = str(clean[k])
        out.append({k: v for k, v in clean.items() if v is not None or k in ("type", "label")})
    return out


def finding_out(f) -> dict:
    return FindingOut(
        id=f.id, application_id=f.application_id, document_id=f.document_id, kind=f.kind, severity=f.severity,
        title=f.title, reason=f.reason, rule_id=f.rule_id, clause=f.clause, evidence=_evidence(f.evidence),
        status=f.status, created_at=_iso(f.created_at), updated_at=_iso(f.updated_at), reviewer_note=f.reviewer_note,
        origin=f.origin,
    ).out()


def alert_out(a) -> dict:
    return AlertOut(id=a.id, application_id=a.application_id, application_no=a.application.application_no,
                    type=a.type, severity=a.severity, message=a.message, created_at=_iso(a.created_at), read=a.read).out()


def audit_out(e) -> dict:
    return AuditEventOut.model_validate(e).out()


def document_out(d) -> dict:
    f = d.forensics or {}
    return {
        "id": d.id,
        "applicationId": d.application_id,
        "docType": d.doc_type,
        "docTypeLabel": doc_type_label(d.doc_type),
        "declaredDocType": d.declared_doc_type,
        "fileName": d.file_name,
        "mimeType": d.mime_type,
        "sizeBytes": d.size_bytes,
        "sha256": d.sha256,
        "phash": d.phash,
        "uploadedAt": _iso(d.uploaded_at),
        "uploadedBy": d.uploaded_by,
        "classification": d.classification or {"docType": d.doc_type, "confidence": 0, "signals": []},
        "ocr": {"method": (d.ocr or {}).get("method"), "confidence": (d.ocr or {}).get("confidence"),
                "pageCount": (d.ocr or {}).get("pageCount"), "textPreview": (d.ocr or {}).get("textPreview", "")},
        "extractedFields": d.extracted_fields or {},
        "issuer": d.issuer,
        "referenceNo": d.reference_no,
        "issueDate": d.issue_date,
        "expiryDate": d.expiry_date,
        "verification": d.verification or {"status": "VERIFICATION_PENDING"},
        "qr": d.qr,
        "forensics": {"elaScore": f.get("elaScore"), "hasElaHeatmap": bool(d.ela_path), "metadata": f.get("metadata") or {},
                      "flags": f.get("flags") or []},
        "infra": d.infra,
        "pipelineErrors": d.pipeline_errors or [],
        "processingMs": d.processing_ms,
    }


ACTIVE = ("OPEN", "ACKNOWLEDGED", "ESCALATED")


def application_out(a) -> dict:
    active = [f for f in a.findings if f.status in ACTIVE]
    vs = [(d.verification or {}).get("status") for d in a.documents]
    return {
        "id": a.id,
        "applicationNo": a.application_no,
        "institutionId": a.institution_id,
        "institution": institution_out(a.institution),
        "category": a.category,
        "academicYear": a.academic_year,
        "status": a.status,
        "submittedAt": _iso(a.submitted_at),
        "createdAt": _iso(a.created_at),
        "updatedAt": _iso(a.updated_at),
        "region": a.region,
        "assignedOfficer": a.assigned_officer,
        "formData": a.form_data or {},
        "complianceScore": a.compliance_score,
        "riskScore": a.risk_score,
        "riskBand": a.risk_band,
        "checklist": a.checklist or [],
        "counts": {
            "documents": len(a.documents),
            "findingsOpen": len(active),
            "critical": sum(f.severity == "CRITICAL" for f in active),
            "major": sum(f.severity == "MAJOR" for f in active),
            "minor": sum(f.severity == "MINOR" for f in active),
            "verified": sum(s == "VERIFIED" for s in vs),
            "pending": sum(s in ("VERIFICATION_PENDING", "SOURCE_UNAVAILABLE") for s in vs),
        },
        "lastValidatedAt": _iso(a.last_validated_at),
        "recommendation": a.recommendation,
        "decision": a.decision,
        "scenario": a.scenario,
    }


def application_detail_out(a) -> dict:
    out = application_out(a)
    out["documents"] = [document_out(d) for d in a.documents]
    out["findings"] = [finding_out(f) for f in a.findings]
    out["records"] = a.institution.records or {}
    return out
