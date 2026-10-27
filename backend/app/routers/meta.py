from fastapi import APIRouter, Depends

from ..engine.rules_loader import CATEGORIES, RULE_TYPES, SEVERITIES, load_doc_types
from ..schemas import DECISION_ACTIONS, RECOMMEND_ACTIONS
from ..security import get_current_user

router = APIRouter(tags=["meta"])

STATUSES = ["DRAFT", "SUBMITTED", "UNDER_VALIDATION", "DEFICIENCIES_FLAGGED", "RECTIFICATION_REQUESTED",
            "SOURCE_VERIFICATION_PENDING", "UNDER_REVIEW", "INSPECTION_ORDERED", "RECOMMENDED", "DECIDED"]
VERIFICATION_STATUSES = ["VERIFIED", "MISMATCH_DETECTED", "EXPIRED", "VERIFICATION_PENDING", "SOURCE_UNAVAILABLE",
                         "MANUAL_REVIEW_REQUIRED", "NOT_APPLICABLE"]
FINDING_KINDS = ["MISSING_DOCUMENT", "MISSING_FIELD", "EXPIRED_DOCUMENT", "INCONSISTENCY", "RECORD_MISMATCH", "ANOMALY",
                 "DUPLICATE", "VERIFICATION", "COMPLIANCE_GAP", "INFRASTRUCTURE"]
FINDING_STATUSES = ["OPEN", "ACKNOWLEDGED", "RECTIFIED", "DISMISSED", "ESCALATED"]


@router.get("/meta")
def meta(_user=Depends(get_current_user)):
    dts = load_doc_types()
    return {
        "categories": [{"id": k, "label": v} for k, v in CATEGORIES.items()],
        "docTypes": [{"id": k, "label": v.get("label", k), "issuer": v.get("issuer"),
                      "validityMonths": v.get("validityMonths"), "verifiable": bool(v.get("verifiable")),
                      "infraEvidenceType": v.get("infra")} for k, v in dts.items()],
        "statuses": STATUSES,
        "verificationStatuses": VERIFICATION_STATUSES,
        "findingKinds": FINDING_KINDS,
        "findingStatuses": FINDING_STATUSES,
        "severities": SEVERITIES,
        "ruleTypes": RULE_TYPES,
        "decisionActions": list(DECISION_ACTIONS),
        "recommendActions": list(RECOMMEND_ACTIONS),
        "regions": ["NR", "WR", "SR", "ER", "CR", "SWR", "SER", "NWR"],
    }
