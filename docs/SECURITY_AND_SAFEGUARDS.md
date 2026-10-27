# Security and Safeguards

PS 26261 asks that the platform be configurable, use authorised role-based access, never bypass
access controls, protect data (confidentiality, access logging, retention), produce explainable,
evidence-backed flags, and remain decision support with final decisions taken by the competent
authority. This document describes how the prototype meets each of these, and what is designed but
not yet implemented.

| Safeguard | Status |
|---|---|
| Role-based access control, server-side scoping | Built |
| Tamper-evident (hash-chained) audit log | Built |
| Explainable, evidence-backed findings | Built |
| Human-in-the-loop decision workflow | Built |
| Configurable rules, checklists and sources | Built |
| PII masking (PAN), scoped file access | Built |
| Per-view read-access logging | Designed |
| Data retention schedule and purge jobs | Designed |
| SSO with the AICTE identity provider | Designed |

---

## 1. Authentication

- Username and password login (`POST /api/auth/login`) returns a JWT signed with HS256.
- Tokens carry `sub` (user id), `username`, `role`, `iat` and `exp`; expiry is 8 hours
  (`VERISENSE_JWT_EXPIRY_HOURS`).
- Passwords are stored as bcrypt hashes (cost 10). Plain passwords are never logged or returned.
- The signing secret comes from `VERISENSE_SECRET`. The default value is for local development only
  and **must** be replaced in any deployment.
- Inactive users are rejected even with a valid token.

Production design: officials sign in through the AICTE identity provider (OIDC or SAML). VeriSense
would trust the provider's token and map role and region from its claims, so no AICTE passwords are
held by VeriSense.

## 2. Roles and authorisation (RBAC)

Four roles are defined in `backend/app/security.py`. Every route declares the roles it accepts
(`require_roles(...)`), and every query over applications is scoped by `scope_applications` /
`ensure_app_access`.

| Capability | INSTITUTION | SCRUTINY_OFFICER | REGIONAL_DIRECTOR | ADMIN |
|---|:-:|:-:|:-:|:-:|
| Create and edit own application (draft / rectification) | yes | – | – | – |
| Upload and delete documents (editable states) | own | – | – | – |
| View applications | own institution | own region | own region | all |
| View validation report, findings, PDF | own | region | region | all |
| Run pre-check validation on a draft | own | – | – | – |
| Re-run validation, re-run source verification | – | region | region | all |
| View ELA heatmaps | – | region | region | all |
| Update finding status | acknowledged / rectified, note required | any status (dismissal needs a reason) | any status (dismissal needs a reason) | – (administrators do not review findings) |
| Add observation, request rectification | – | region | region | all |
| Record a recommendation (`RECOMMEND_*`) | – | region | – | – |
| Record the final decision | – | – | region, note required | – |
| Export validation report PDF | own | region | region | all |
| Edit rules and checklists, toggle sources | – | – | – | yes |
| Read audit log | – | region-related | region-related | full |
| Verify audit chain | – | yes | yes | yes |

Notes:

- **No bypass.** Access checks are applied on the server in each router; the frontend only hides
  what a role cannot do. Calling the API directly gives the same result.
- **No existence leaks.** Requests for an application outside the caller's scope return `404 Not
  found`, not `403`, so one institution cannot probe another's application numbers.
- **File access is scoped too.** `GET /documents/{id}/file`, `/text` and `/ela` check access to the
  parent application before streaming anything.
- **Separation of duties.** Administrators configure the system but do not review findings or take
  decisions; officers recommend; only the Regional Director decides.
- **Approval guard.** Neither a recommendation to approve nor an approval can be recorded while any
  CRITICAL finding is still `OPEN` without an officer disposition; the blocked attempt is itself
  audited (`DECISION_BLOCKED`).

## 3. Audit trail

Implemented in `backend/app/audit.py`.

- Every mutating action (application create/update/submit, upload, delete, validation run,
  verification, finding status change, observation, rectification request, recommendation,
  decision, rule/checklist/source change), every login and failed login, report PDF exports and
  audit-chain verifications append an `AuditEvent`.
- Actions recorded: `LOGIN`, `LOGIN_FAILED`, `APPLICATION_CREATED`, `APPLICATION_UPDATED`,
  `APPLICATION_SUBMITTED`, `DOCUMENT_UPLOADED`, `DOCUMENT_PROCESSED`, `PIPELINE_STAGE` (stage
  errors), `DOCUMENT_REVERIFIED`, `DOCUMENT_DELETED`, `VALIDATION_RUN`, `FINDING_UPDATED`,
  `OBSERVATION_ADDED`, `RECTIFICATION_REQUESTED`, `RECOMMENDATION_RECORDED`, `DECISION_RECORDED`,
  `DECISION_BLOCKED`, `REPORT_EXPORTED`, `ALERT_READ`, `RULE_UPDATED`, `CHECKLIST_UPDATED`,
  `SOURCE_TOGGLED`, `AUDIT_CHAIN_VERIFIED`.
- Each event stores `ts, actor, actorRole, action, entityType, entityId, details, prevHash, hash`.
- `hash = SHA-256(prevHash + canonical_json(event))`, where the first event chains from a genesis
  value of 64 zeros. Canonical JSON uses sorted keys and fixed separators so the hash is
  reproducible.
- Rows are append-only: ORM listeners refuse `UPDATE`/`DELETE` on audit rows, and SQLite triggers
  (`audit_no_update`, `audit_no_delete`) block them even for raw SQL.
- `GET /api/audit/verify` (officer and above) recomputes the chain and returns
  `{valid, checked, brokenAt, reason, headHash}`. Any edit to an earlier event breaks every
  following hash.
- Validation runs record the rules applied (`PASS` / `FAIL` / `SKIPPED` with detail), the ruleset
  version and the source responses, so the audit answers "what was checked, against what, and what
  did the source say".

Production design: periodically anchor the head hash outside the database (for example in a signed
daily digest held by the Regulation Bureau) so that even a full database rewrite is detectable.

## 4. Data protection

**Confidentiality**

- Faculty PANs in institutional records are held and displayed in masked form (`panMasked`).
  Duplicate-faculty detection runs on the server over the PAN values held in records and rosters.
  (Production: keep full PANs only in an encrypted column or tokenised vault, comparing by keyed
  hash.)
- Uploaded files are stored under `storage/{applicationId}/` with a random prefix and are served only
  through scoped endpoints, never as static files.
- Full OCR text is returned only to users who can see the application.

**Access logging**

- Logins (successful and failed), every state-changing call and report exports are in the audit
  chain with actor and role.
- Read access to individual files and text is scoped but not yet logged per view (designed: a
  lightweight `DOCUMENT_VIEWED` event).

**Retention (designed)**

| Data class | Proposed retention | Action at end |
|---|---|---|
| Submitted documents and extracted text | Approval cycle + period set by AICTE records policy | Archive to cold storage, then purge |
| Rejected or withdrawn drafts | 1 year after last change | Purge |
| Findings, reports, decisions | As per AICTE records policy | Archive |
| Audit events | Not deleted; archived with head-hash anchor | Archive |
| ELA heatmaps and derived images | Same as parent document | Purge with parent |

Retention values are placeholders for AICTE to set; the purge job is not implemented in the
prototype.

**Hosting**

- No document data leaves the deployment: OCR, classification, forensics and computer vision run
  locally on CPU; there are no calls to external AI services.
- Designed for NIC / MeghRaj government cloud, with storage encryption provided by the platform and
  HTTPS terminated at the gateway.

## 5. Explainability

Every finding carries:

- `kind`, `severity`, `title` and a plain-language `reason`;
- `ruleId` and `clause` (clause references are **illustrative and configurable** — they show the
  link to the Approval Process Handbook but do not reproduce official numbering);
- `evidence[]` of typed items: `DOCUMENT` (excerpt and page), `FIELD`, `RECORD` (value held by
  AICTE), `SOURCE_RESPONSE`, `IMAGE_REGION` (bounding box), `METADATA`, `RULE`;
- `advisory: true`.

The validation report lists every rule evaluated with its result, so an officer can also see what
passed.

## 6. Human in the loop

- All AI output is labelled **"Advisory — requires officer review"** in the portal.
- Forensic and infrastructure results are described as preliminary indicators, never as proof.
- The system never changes an application's decision. Officers can recommend; the final decision
  (`APPROVE_FOR_EOA`, `ISSUE_DEFICIENCY_LETTER`, `ORDER_INSPECTION`, `REJECT`) is restricted to the
  `REGIONAL_DIRECTOR` role and requires a non-empty note, which is written to the audit chain.
- Officers can dismiss any finding with a note; dismissed findings no longer affect scores, and the
  dismissal itself is audited.
- Inconclusive verifications are routed to `MANUAL_REVIEW_REQUIRED` instead of being guessed.

## 7. Configurability

- Rules (`backend/config/rules.yaml`), checklists (`checklists.yaml`) and the document catalogue
  (`doc_types.yaml`) are configuration, not code.
- Administrators edit rules (enabled, params, severity) and checklists through the API / console.
  Each change is stored as a versioned override, bumps the ruleset version and is audited.
- Every validation report records the ruleset version it was produced with.
- Sources can be switched off by the administrator (for example during an issuer outage); affected
  checks then return `SOURCE_UNAVAILABLE` rather than failing silently.

See [RULES_AND_CHECKLISTS.md](RULES_AND_CHECKLISTS.md).

## 8. Known limitations of the prototype

- Single shared JWT secret; no refresh tokens, no MFA (to be provided by SSO).
- SQLite database and local file storage; production would use PostgreSQL and an object store.
- Issuing authorities are simulated; real integrations need authorisation from each authority.
- Retention and archival are designed but not implemented.
- Demo passwords are shared and public; they exist only for evaluation.

## Updated review boundary (27 October 2026)

Acknowledgement/escalation does not resolve a critical finding. Only reviewer-confirmed rectification or reasoned dismissal permits approval; institutions may respond but cannot self-confirm resolution. Finalized evidence/findings cannot be mutated through validation/re-verification/review endpoints. Missing region is deny-by-default. Institution official records are administrator-controlled. JWT revocation, concurrent decision locking, PostgreSQL triggers/migrations, malware quarantine, complete secret/dependency auditing and independently held-out evaluation remain incomplete; see TEAM_AUDIT.md and RELEASE_BLOCKERS.md. No audit certification or official regulatory compliance is claimed.
