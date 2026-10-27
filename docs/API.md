# API Reference

Generated from the FastAPI OpenAPI schema (`GET /openapi.json`; interactive docs at `http://localhost:8001/docs`). Roles are enforced on the server in every router.

- Base URL: `http://localhost:8001` (the Vite dev server proxies `/api` and `/mock`).
- Auth: `Authorization: Bearer <accessToken>` from `POST /api/auth/login`, except `health` and `login`. Tokens expire after 8 hours.
- JSON uses camelCase field names. Errors are `{"detail": "..."}` with a matching status code: 401 unauthenticated, 403 role not allowed, 404 not found **or outside your scope** (existence is not leaked), 409 invalid state transition, 422 validation error.
- Every mutating call writes an entry to the hash-chained audit log.
- Role shorthand: *officer+* = SCRUTINY_OFFICER, REGIONAL_DIRECTOR, ADMIN; *scoped* = any role, limited to the caller's institution or region.

## Endpoints

### Auth

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| POST | `/api/auth/login` | public | Log in; successful and failed attempts are audited | body: `username`, `password` | `{accessToken, tokenType, user}` |
| GET | `/api/auth/me` | any | Current user | – | `User` |

### Meta

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/health` | public | Service status and version | – | `{status, version}` |
| GET | `/api/meta` | any | Categories, document types, status enums | – | `{categories, docTypes, statuses, verificationStatuses, ...}` |

### Dashboard

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/dashboard/summary` | officer+ | Totals and breakdowns for the caller's scope | – | `{totals, byStatus, byVerification, byCategory, findingsBySeverity, recent, avgValidationSeconds, manualEffortSavedHours}` |

### Applications

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/applications` | any (scoped) | List applications; institutions see their own, officers their region | query: `status`, `category`, `region`, `q`, `riskBand` | `Application[]` |
| POST | `/api/applications` | INSTITUTION | Create a DRAFT application | body: `category`, `academicYear`, `formData`? | `Application` |
| GET | `/api/applications/{app_id}` | scoped | Application with documents, findings and institutional records | – | `Application & {documents, findings, records}` |
| PATCH | `/api/applications/{app_id}` | INSTITUTION (editable states) | Update declared form data | body: `formData` | `Application` |
| POST | `/api/applications/{app_id}/documents` | INSTITUTION (editable states) | Upload a file (multipart `file`, optional `docType`); the pipeline runs synchronously | multipart: `file`, `docType`? | `Document` |
| POST | `/api/applications/{app_id}/submit` | INSTITUTION | Submit, assign an officer and run validation | – | `ValidationReport` |
| POST | `/api/applications/{app_id}/validate` | officer+; INSTITUTION on DRAFT (pre-check) | Run validation now | – | `ValidationReport` |
| GET | `/api/applications/{app_id}/report` | scoped | Latest validation report (with current finding statuses) | – | `ValidationReport` |
| GET | `/api/applications/{app_id}/report.pdf` | scoped | Validation / deficiency report as PDF; export is audited | – | PDF |
| POST | `/api/applications/{app_id}/observations` | officer+ | Add an officer observation to the audit trail | body: `note` | `AuditEvent` |
| POST | `/api/applications/{app_id}/request-rectification` | officer+ | Escalate selected findings and request rectification | body: `note`, `findingIds`? | `Application` |
| POST | `/api/applications/{app_id}/decision` | SCRUTINY_OFFICER (`RECOMMEND_*`), REGIONAL_DIRECTOR (final) | Record a recommendation or the final decision; note required; approval blocked while CRITICAL findings are OPEN | body: `action`, `note`? | `Application` |

### Documents

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/documents/{doc_id}` | scoped | Document with classification, fields, verification, forensics | – | `Document` |
| DELETE | `/api/documents/{doc_id}` | INSTITUTION (editable states) | Delete an uploaded document | – | 204 |
| GET | `/api/documents/{doc_id}/file` | scoped | Original file | – | file |
| GET | `/api/documents/{doc_id}/text` | scoped | Full OCR text and line blocks | – | `{text, blocks}` |
| GET | `/api/documents/{doc_id}/ela` | officer+ | ELA heatmap | – | PNG |
| POST | `/api/documents/{doc_id}/verify` | officer+ | Re-run issuing-authority verification | – | `Document` |

### Findings

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/findings/{finding_id}` | scoped | One finding | – | `Finding` |
| PATCH | `/api/findings/{finding_id}` | officer / RD (any status); INSTITUTION (`ACKNOWLEDGED`, `RECTIFIED`, note required) | Change finding status with a note; dismissal requires a reason | body: `status`, `note`? | `Finding` |

### Alerts

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/alerts` | any (scoped) | Alerts, optionally unread only | query: `unread`, `limit` | `Alert[]` |
| POST | `/api/alerts/{alert_id}/read` | any (scoped) | Mark an alert read | – | `Alert` |

### Audit

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/audit/verify` | officer+ | Recompute the audit hash chain | – | `{valid, checked, brokenAt, reason?, headHash?}` |
| GET | `/api/audit` | officer+ (region-scoped; admin all) | Audit events filtered by entity, action, type, application | query: `entityId`, `action`, `entityType`, `applicationId`, `limit` | `AuditEvent[]` |

### Rules

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/rules` | officer+ | Rules with admin overrides applied | – | `Rule[]` |
| GET | `/api/rules/version` | any | Current ruleset version | – | `{rulesetVersion}` |
| PUT | `/api/rules/{rule_id}` | ADMIN | Change `enabled`, `params`, `severity`; bumps versions; audited | body: `enabled`?, `params`?, `severity`? | `Rule` |
| GET | `/api/checklists` | any | Checklist templates for all categories | – | `{category: ChecklistItemTemplate[]}` |
| PUT | `/api/checklists/{category}` | ADMIN | Replace a category checklist; audited | body: [`docType`, `mandatory`?, `clause`?, `when`?] | `{category: ChecklistItemTemplate[]}` |

### Sources

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/sources` | officer+ | Verification sources with online flag, latency, success rate | – | `Source[]` |
| POST | `/api/sources/{source_id}/toggle` | ADMIN | Switch a source on or off; audited | – | `Source` |

### Institutions

| Method | Path | Role | Purpose | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/institutions` | any (scoped) | Institutions visible to the caller | – | `Institution[]` |
| GET | `/api/institutions/{inst_id}` | scoped | Institution | – | `Institution` |
| GET | `/api/institutions/{inst_id}/records` | scoped | Records already held by AICTE | – | `InstitutionalRecords` |

### Simulated issuing authorities (`/mock`, prototype only)

Unauthenticated stand-ins for external authorities, called by the adapters. Records come from the synthetic scenario data; a source switched off by the administrator reports an outage.

| Method | Path |
|---|---|
| GET | `/mock/` |
| GET | `/mock/keys` |
| GET | `/mock/digilocker/issued/{uri}` |
| GET | `/mock/nba/accreditations/{ref}` |
| GET | `/mock/naac/assessments/{ref}` |
| GET | `/mock/fire/noc/{ref}` |
| GET | `/mock/municipal/occupancy/{ref}` |
| GET | `/mock/municipal/permits/{ref}` |
| GET | `/mock/land/records/{ref}` |
| GET | `/mock/ter/txn/{txn_id}` |
| GET | `/mock/aicte/eoa/{ref}` |
| GET | `/mock/udin/{udin}` |

## Enumerations

| Enum | Values |
|---|---|
| ApplicationCategory | `EOA`, `NEW_INSTITUTION`, `INTAKE_INCREASE`, `NEW_COURSE`, `CHANGE_OF_NAME`, `CHANGE_OF_SITE`, `CLOSURE` |
| ApplicationStatus | `DRAFT`, `SUBMITTED`, `UNDER_VALIDATION`, `DEFICIENCIES_FLAGGED`, `RECTIFICATION_REQUESTED`, `SOURCE_VERIFICATION_PENDING`, `UNDER_REVIEW`, `INSPECTION_ORDERED`, `RECOMMENDED`, `DECIDED` |
| VerificationStatus | `VERIFIED`, `MISMATCH_DETECTED`, `EXPIRED`, `VERIFICATION_PENDING`, `SOURCE_UNAVAILABLE`, `MANUAL_REVIEW_REQUIRED`, `NOT_APPLICABLE` |
| FindingKind | `MISSING_DOCUMENT`, `MISSING_FIELD`, `EXPIRED_DOCUMENT`, `INCONSISTENCY`, `RECORD_MISMATCH`, `ANOMALY`, `DUPLICATE`, `VERIFICATION`, `COMPLIANCE_GAP`, `INFRASTRUCTURE` |
| Severity | `CRITICAL`, `MAJOR`, `MINOR`, `INFO` |
| FindingStatus | `OPEN`, `ACKNOWLEDGED`, `RECTIFIED`, `DISMISSED`, `ESCALATED` |
| RiskBand | `LOW`, `MEDIUM`, `HIGH` |
| Decision actions (Regional Director) | `APPROVE_FOR_EOA`, `ISSUE_DEFICIENCY_LETTER`, `ORDER_INSPECTION`, `REJECT` |
| Recommendation actions (Scrutiny officer) | `RECOMMEND_` + any decision action |

## Request schemas

**ApplicationCreate**

| Field | Type | Required |
|---|---|---|
| `category` | string | yes |
| `academicYear` | string | yes |
| `formData` | object | no |

**ApplicationPatch**

| Field | Type | Required |
|---|---|---|
| `formData` | object | yes |

**ChecklistItemTemplate**

| Field | Type | Required |
|---|---|---|
| `docType` | string | yes |
| `mandatory` | boolean | no |
| `clause` | string | no |
| `when` | object | no |

**DecisionRequest**

| Field | Type | Required |
|---|---|---|
| `action` | string | yes |
| `note` | string | no |

**FindingPatch**

| Field | Type | Required |
|---|---|---|
| `status` | string | yes |
| `note` | string | no |

**LoginRequest**

| Field | Type | Required |
|---|---|---|
| `username` | string | yes |
| `password` | string | yes |

**NoteRequest**

| Field | Type | Required |
|---|---|---|
| `note` | string | yes |

**RectificationRequest**

| Field | Type | Required |
|---|---|---|
| `note` | string | yes |
| `findingIds` | array of integer | no |

**RulePatch**

| Field | Type | Required |
|---|---|---|
| `enabled` | boolean | no |
| `params` | object | no |
| `severity` | string | no |

## Example session

```bash
# log in as the Western Region scrutiny officer
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"officer.wro","password":"Demo@2026"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['accessToken'])")

curl -s -H "Authorization: Bearer $TOKEN" 'http://localhost:8001/api/applications?riskBand=HIGH'
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/applications/1/validate
curl -s -H "Authorization: Bearer $TOKEN" -o report.pdf http://localhost:8001/api/applications/1/report.pdf
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/audit/verify
```

## Integration hardening (27 October 2026)

REST paths and camelCase payloads remain compatible. X-Request-ID is returned on API responses, included in standard error requestId and new audit details, and exposed through CORS. Invalid caller IDs are replaced. API responses use Cache-Control: no-store.

GET /api/health/system now requires ADMIN; live/ready remain public with redacted dependency failures. Staff without an assigned region have no application/institution visibility. Institution PATCH permits address/campusGps/trustName only; administrator edits official records. Director institution creation is restricted to assigned region.

POST /api/applications/{id}/documents accepts PDF/PNG/JPEG up to 25 MiB with content/parser validation, unencrypted 1-200-page PDFs and images up to 25 million pixels. Unsupported types return 415, malformed content 400, excessive byte size 413. Storage and expensive processing begin after validation.

Approval/recommendation is blocked for CRITICAL findings in every state except reviewer-confirmed RECTIFIED/DISMISSED. Institutions can ACKNOWLEDGE/respond but cannot resolve findings. Reviewer resolution needs a reason. DECIDED applications reject validation, finding mutation and document re-verification with 409. Missing evidence never yields verified advice in processing-summary. Non-demo authority verification returns MANUAL_REVIEW_REQUIRED, and /mock routes are omitted. See TEAM_CONTRACTS.md and RELEASE_BLOCKERS.md for intentional permission tightening and remaining gaps.
