"""Shared human-review invariants. Acknowledgement and escalation are unresolved."""

ACTIVE_FINDING_STATUSES = frozenset({"OPEN", "ACKNOWLEDGED", "ESCALATED"})
RESOLVED_FINDING_STATUSES = frozenset({"RECTIFIED", "DISMISSED"})


def approval_blockers(findings):
    return [f for f in findings if f.severity == "CRITICAL" and f.status not in RESOLVED_FINDING_STATUSES]
