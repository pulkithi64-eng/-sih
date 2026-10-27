# VeriSense backend (FastAPI)

AI-assisted application validation, document authentication and compliance verification for AICTE
Extension-of-Approval style applications — SIH 2026 prototype (PS 26261). Every output is **advisory
decision support**; the final decision always rests with the competent AICTE authority.

The binding interface is [`docs/CONTRACT.md`](../docs/CONTRACT.md).

## Run

```bash
# from backend/
./run.sh            # or:  powershell -File run.ps1
# = uv sync && uv run uvicorn app.main:app --port 8001 --reload
```

* API: `http://localhost:8001/api` (OpenAPI UI at `http://localhost:8001/docs`)
* Simulated issuing authorities: `http://localhost:8001/mock/*`
* On first start an empty database is seeded automatically (users, institutions, demo applications with
  real sample files run through the pipeline). Re-seed from scratch:

```bash
uv run python -m seed.seed --reset
```

Demo users (password `Demo@2026`): `inst.piat`, `inst.apex`, `officer.wro`, `officer.nro`, `rd.wro`, `admin`.

Tests: `uv run pytest -q`.

Configuration: see [`.env.example`](.env.example) (`VERISENSE_SECRET`, `VERISENSE_DB`, `VERISENSE_STORAGE`,
`VERISENSE_SAMPLES`, `VERISENSE_AUTOSEED`, `VERISENSE_REFERENCE_DATE`, …).

## Layout

| path | purpose |
|---|---|
| `app/main.py` | app, CORS (`http://localhost:5176`), router registration, `/mock` mount, startup seeding |
| `app/config.py`, `app/db.py`, `app/models.py` | settings, SQLAlchemy 2 engine (SQLite `data/verisense.db`), ORM |
| `app/schemas.py` | Pydantic v2 models (camelCase aliases) and serializers |
| `app/security.py` | JWT HS256 (8 h), bcrypt, role guards, RBAC scoping |
| `app/audit.py` | append-only, SHA-256 hash-chained audit log + chain verification |
| `app/routers/*` | one router per resource (contract section 4) |
| `app/engine/ingest.py` | upload pipeline orchestration (contract section 6), used by API **and** seeder |
| `app/engine/pipeline_bridge.py` | guarded calls into `app/pipeline` + `app/adapters` (AI module) |
| `app/engine/validator.py` | `run_validation()` — rule evaluation, findings, scores, alerts, report |
| `app/engine/rules_loader.py` | YAML baseline + admin overrides, ruleset versioning |
| `app/engine/report_pdf.py` | Preliminary Validation Report (reportlab) |
| `config/rules.yaml`, `config/checklists.yaml`, `config/doc_types.yaml` | configurable rules / checklists / doc catalogue |
| `seed/seed.py` | idempotent demo seeding |

## Roles and scoping

* `INSTITUTION` — only its own institution's applications, documents, findings, alerts, records.
* `SCRUTINY_OFFICER` — applications of its region; validate, re-verify, disposition findings, observations,
  request rectification, record a **recommendation** (`RECOMMEND_*`) only.
* `REGIONAL_DIRECTOR` — region scope; final decision `APPROVE_FOR_EOA | ISSUE_DEFICIENCY_LETTER | ORDER_INSPECTION | REJECT`.
* `ADMIN` — all regions; rules/checklists/sources; full audit.

Cross-tenant access returns 404 (existence is not leaked).

## Upload pipeline (per document)

`POST /api/applications/{id}/documents` (multipart `file`, optional `docType`) runs synchronously:

1. store `storage/{applicationId}/{uuid}_{name}`, SHA-256 + perceptual hash
2. OCR (PDF text layer, else RapidOCR) → text + blocks
3. classify; declared vs predicted type disagreement at confidence > 0.7 → `INCONSISTENCY` finding
4. field extraction; issuer / referenceNo / issueDate / expiryDate derived (expiry falls back to issue date +
   doc-type `validityMonths`, marked `_derivedExpiry`)
5. forensics (ELA heatmap, PDF/EXIF metadata, incremental updates, text-layer anomalies) → `ANOMALY` findings
6. QR decode → Ed25519 signature verification
7. issuing-authority verification via the adapter registry (QR results are passed in; the registry owns
   the verdict) → `VERIFICATION` / `EXPIRED_DOCUMENT` findings
8. infrastructure photos: image analysis (counts, quality, EXIF date/GPS vs campus) → `INFRASTRUCTURE` findings

Every stage writes an audit event (`PIPELINE_STAGE`, e.g. *"OCR completed: 2 page(s), method pdf-text"*).
A failing stage is recorded in `pipelineErrors`, the verification becomes `MANUAL_REVIEW_REQUIRED`
and the upload still succeeds (never a 500).

## Validation engine

`run_validation(db, application_id, actor)` evaluates **every** rule in `config/rules.yaml` and records
`PASS | FAIL | SKIPPED` with a human-readable detail (traceability) in `rulesApplied`:

| type | what it checks |
|---|---|
| `REQUIRED_DOCUMENT` | category checklist incl. conditional items (`when: {field: formData.nbaAccredited, truthy: true}`) |
| `DOCUMENT_EXPIRY` | expiry vs scrutiny date (`graceDays`, `warnDays`), `maxAgeDays` (affidavit for current year), accreditation validity in records |
| `FIELD_PRESENT` | declared form fields, readable reference numbers on verifiable documents |
| `FIELD_MATCH_RECORD` | form vs institutional records via a path mini-language: `a.b`, `sum(list.field)`, `count(list)`, `count(list[k=v])`, `latest(list).field`; `perProgramme` intake check; `expectedIn`; `expectedMax`; `allowIncreaseCategories` |
| `FIELD_MATCH_DOCUMENT` | form (or `@institution.name`) vs extracted document fields (numeric tolerance or fuzzy similarity) |
| `THRESHOLD` | `faculty_student_ratio` (declared and records), `land_area_acres` by location, `builtup_area_per_intake` |
| `CADRE_RATIO` | Professor : Associate : Assistant vs 1:2:6 (declared cadre → roster → records) |
| `TER_PAYMENT` | PAID TER for the academic year in records; form and receipt transaction IDs match |
| `DUPLICATE_DOCUMENT` | same SHA-256 or pHash Hamming distance ≤ `maxHamming` (6) in another institution's applications |
| `DUPLICATE_FACULTY` | same faculty PAN in another institution's records / roster / form |
| `FORENSIC_FLAG` | forensic indicators ≥ `minSeverity` |
| `SOURCE_VERIFICATION` | issuing-authority verdicts (mismatch, expired/revoked, pending, unavailable, manual) |
| `INFRA_EVIDENCE` | object counts per evidence type (`minCount`), photo authenticity flags (`evidenceType: ANY`) |

Findings carry `Evidence[]` pointing at concrete values (`submitted` vs `reference`, document/page/excerpt,
source response, rule + clause). Re-validation is idempotent: auto-generated `OPEN` findings are replaced
(stable fingerprints), human-modified findings are kept.

Scores:

* `complianceScore` = Σ w(severity) × (1 − failed/checks) / Σ w(severity) over non-skipped rules,
  weights `CRITICAL 5, MAJOR 3, MINOR 1, INFO 0` (configurable `severityWeights`).
* `riskScore` = min(100, Σ points(severity) × multiplier(kind)) over active findings
  (points `CRITICAL 30, MAJOR 15, MINOR 5`; multiplier 1.0 for anomaly/duplicate/verification,
  0.8 record-mismatch/inconsistency, ≤ 0.5 others). Band: `<30 LOW`, `<60 MEDIUM`, else `HIGH`.
* status → `DEFICIENCIES_FLAGGED` (any active CRITICAL/MAJOR) → else `SOURCE_VERIFICATION_PENDING`
  (any source pending/unavailable) → else `UNDER_REVIEW`. Human workflow states are not overridden.

Alerts: `MISSING_DOCUMENTS`, `DOCUMENT_EXPIRED`, `SOURCE_UNAVAILABLE`, `SOURCE_VERIFICATION_PENDING`,
`SUSPECTED_ANOMALY`, `DUPLICATE_DETECTED`, plus workflow alerts (`RECTIFICATION_REQUESTED`, `DECISION_RECORDED`, …).

Rule clauses are marked *"APH 2024-27 (illustrative)"*: they mirror the handbook's structure but are
configurable parameters, not official text.

## Human in the loop

`POST /api/applications/{id}/decision {action, note}`:

* note (≥ 5 chars) always required (422);
* officers may only `RECOMMEND_*` (→ `RECOMMENDED`); the RD decides;
* `APPROVE_FOR_EOA` / `RECOMMEND_APPROVE_FOR_EOA` is refused with **409** while any CRITICAL finding is still
  `OPEN` (no officer disposition) — the response lists the blocking findings;
* the application must have been validated at least once.

## Audit

`hash_n = sha256(hash_{n-1} + canonical_json({ts, actor, actorRole, action, entityType, entityId, details}))`,
genesis `"0"*64`. Rows cannot be updated/deleted (ORM listeners + SQLite triggers). `GET /api/audit/verify`
recomputes the chain and returns `{valid, checked, brokenAt, headHash}`.

## Dashboard estimates

`manualEffortSavedHours = (documentsAutoChecked × 12 min + applicationsValidated × 45 min − automatedMinutes) / 60`
— the per-item minutes are configurable planning assumptions; `automatedMinutes` and
`avgValidationSeconds` are measured from stored pipeline and validation timings.
