# VeriSense — Engineering Contract (source of truth for all modules)

This file fixes the repo layout, data model, API and design tokens so that the backend,
AI pipeline, portal UI and website can be built in parallel. Change it only by agreement.

## 1. Repo layout

```
backend/                FastAPI service (Python 3.11, uv)
  app/main.py           FastAPI app, CORS, router registration, startup seeding
  app/config.py         settings (env: VERISENSE_SECRET, VERISENSE_DB, VERISENSE_STORAGE)
  app/db.py             SQLAlchemy 2.x engine/session (SQLite file backend/data/verisense.db)
  app/models.py         ORM models (section 3)
  app/schemas.py        Pydantic v2 response/request models (section 3, camelCase JSON via alias)
  app/security.py       JWT (HS256), password hashing, role guards
  app/audit.py          hash-chained audit log: record(actor, action, entity_type, entity_id, details)
  app/routers/*.py      one router per resource (section 4)
  app/engine/           rule engine + validation orchestration (CORE agent)
    rules_loader.py     loads backend/config/*.yaml, versioned
    validator.py        run_validation(application_id) -> ValidationReport; creates Findings + Alerts
    report_pdf.py       deficiency/validation report PDF (reportlab)
  app/pipeline/         document AI (AI agent) — pure functions, no DB access
    ocr.py              extract_text(path) -> OcrResult{text, pages, method: "pdf-text"|"rapidocr", confidence, blocks[{text,bbox,page,conf}]}
    classify.py         classify(text, filename) -> {docType, confidence, signals[]}
    extract.py          extract_fields(doc_type, text) -> {fieldName: {value, confidence, sourceText, page}}
    forensics.py        analyse(path) -> ForensicResult{elaScore, elaHeatmapPath?, metadata{producer, creator, created, modified, software}, flags[{code, severity, reason, evidence}]}
    hashing.py          sha256(path), phash(path) (imagehash; first page rendered for PDFs)
    qr.py               decode_qr(path) -> [payload strings] (OpenCV QRCodeDetector on rendered pages)
    signature.py        verify_signed_payload(payload) -> {valid, issuer, keyId, claims, reason}
    infra_cv.py         analyse_infra(path, evidence_type) -> {detections[{label,conf,bbox}], counts{}, quality{blurScore, brightness}, exif{takenAt, gps, device}, flags[]}
  app/adapters/         issuing-authority adapters (AI agent): base.py + one per source
  app/mock_authorities/ simulated issuing-authority services mounted at /mock/* (AI agent)
  config/
    checklists.yaml     category -> required documents (docType, mandatory, conditions, clause)
    rules.yaml          rule definitions (section 5)
    doc_types.yaml      docType catalogue (label, issuer, validityMonths, verifiable source)
    authority_keys/     Ed25519 public keys of simulated issuers (private keys only in samples/tools)
  seed/seed.py          creates users, institutions, institutional records, 6 demo applications with real sample files run through the pipeline
  tests/                pytest
samples/                synthetic documents (PDF/JPG) incl. tampered variants + generator script samples/tools/generate.py
frontend/               React 18 + Vite + TS + Tailwind + shadcn/ui
docs/                   architecture, how-it-works, API, demo script, PS mapping
```

Ports: backend `http://localhost:8001`, frontend `http://localhost:5176` (Vite proxies `/api` and `/mock` to 8001).

## 2. Roles (RBAC)

| role | who | can |
|---|---|---|
| `INSTITUTION` | college nodal officer | create/edit own applications, upload docs, see own validation report & findings, respond/rectify |
| `SCRUTINY_OFFICER` | AICTE scrutiny officer | see assigned region's applications, re-run validation, trigger source verification, update finding status, add observations, record a recommendation |
| `REGIONAL_DIRECTOR` | AICTE RO | everything officer can + final decision (`APPROVE_FOR_EOA`, `ISSUE_DEFICIENCY_LETTER`, `ORDER_INSPECTION`, `REJECT`) — always requires a note |
| `ADMIN` | AICTE IT / Regulation Bureau | manage rules & checklists, toggle sources, view full audit, verify audit chain |

Demo users (password `Demo@2026` for all): `inst.piat`, `inst.apex`, `officer.wro`, `officer.nro`, `rd.wro`, `admin`.

## 3. Data model (JSON field names are camelCase)

Enums:
- `ApplicationCategory`: `EOA` (Extension of Approval), `NEW_INSTITUTION`, `INTAKE_INCREASE`, `NEW_COURSE`, `CHANGE_OF_NAME`, `CHANGE_OF_SITE`, `CLOSURE`
- `ApplicationStatus`: `DRAFT`, `SUBMITTED`, `UNDER_VALIDATION`, `DEFICIENCIES_FLAGGED`, `RECTIFICATION_REQUESTED`, `SOURCE_VERIFICATION_PENDING`, `UNDER_REVIEW`, `INSPECTION_ORDERED`, `RECOMMENDED`, `DECIDED`
- `VerificationStatus`: `VERIFIED`, `MISMATCH_DETECTED`, `EXPIRED`, `VERIFICATION_PENDING`, `SOURCE_UNAVAILABLE`, `MANUAL_REVIEW_REQUIRED`, `NOT_APPLICABLE`
- `FindingKind`: `MISSING_DOCUMENT`, `MISSING_FIELD`, `EXPIRED_DOCUMENT`, `INCONSISTENCY`, `RECORD_MISMATCH`, `ANOMALY`, `DUPLICATE`, `VERIFICATION`, `COMPLIANCE_GAP`, `INFRASTRUCTURE`
- `Severity`: `CRITICAL`, `MAJOR`, `MINOR`, `INFO`
- `FindingStatus`: `OPEN`, `ACKNOWLEDGED`, `RECTIFIED`, `DISMISSED`, `ESCALATED`
- `RiskBand`: `LOW`, `MEDIUM`, `HIGH`

Objects:
```ts
User { id, username, fullName, role, region?: "NR"|"WR"|"SR"|"ER"|"CR"|"SWR"|"SER"|"NWR", institutionId? }
Institution { id, permanentId, name, type, state, city, region, establishedYear, trustName, address, campusGps?: {lat,lng} }
InstitutionalRecords {             // "already in AICTE systems" — served by /institutions/{id}/records
  previousApprovals: [{year, status: "APPROVED"|"APPROVED_WITH_CONDITIONS"|"WITHDRAWN", letterRef, date}],
  approvedProgrammes: [{level, programme, course, shift, intake}],
  faculty: [{facultyId, name, panMasked, designation, qualification, department, joiningDate}],
  accreditations: [{body:"NBA"|"NAAC", programme?, grade?, validFrom, validTo, ref}],
  landAndBuilding: {landAreaAcres, builtUpAreaSqm, ownership, registryRef},
  terPayments: [{year, amount, txnId, status:"PAID"|"PENDING"|"FAILED", paidOn}],
  deficiencyHistory: [{year, item, status:"OPEN"|"CLOSED"}],
  affidavits: [{year, type, ref, notarisedOn}]
}
Application {
  id, applicationNo, institutionId, institution: Institution, category, academicYear, status,
  submittedAt?, updatedAt, region, assignedOfficer?,
  formData: { [field]: value },          // declared values (intake, faculty count, land area, built-up area, programmes[], TER txn id, ...)
  complianceScore: number (0-100), riskScore: number (0-100), riskBand,
  checklist: ChecklistItem[], counts: { documents, findingsOpen, critical, major, minor, verified, pending },
  lastValidatedAt?, decision?: Decision
}
ChecklistItem { docType, label, mandatory, clause, status: "PRESENT"|"MISSING"|"EXPIRED"|"INVALID"|"NOT_REQUIRED", documentId? }
Document {
  id, applicationId, docType, docTypeLabel, fileName, mimeType, sizeBytes, sha256, uploadedAt, uploadedBy,
  classification: { docType, confidence, signals: string[] },
  ocr: { method, confidence, pageCount, textPreview },       // full text via GET /documents/{id}/text
  extractedFields: { [name]: { value, confidence, sourceText, page } },
  issuer?: string, referenceNo?: string, issueDate?: string, expiryDate?: string,
  verification: { status: VerificationStatus, source?: string, method?: "API"|"QR_SIGNATURE"|"DIGILOCKER"|"PORTAL"|"MANUAL",
                  checkedAt?, responseSummary?, comparisons?: [{field, submitted, source, match}], reason? },
  forensics: { elaScore?, hasElaHeatmap: boolean, metadata: {...}, flags: [{code, severity, reason, evidence}] },
  infra?: { evidenceType, detections: [...], counts: {...}, quality: {...}, exif: {...}, flags: [...] }
}
Evidence { type: "DOCUMENT"|"FIELD"|"RECORD"|"SOURCE_RESPONSE"|"IMAGE_REGION"|"METADATA"|"RULE", label, documentId?, page?, bbox?, excerpt?, submitted?, reference? }
Finding { id, applicationId, documentId?, kind, severity, title, reason, ruleId?, clause?, evidence: Evidence[],
          status, createdAt, updatedAt, reviewerNote?, advisory: true }
Alert { id, applicationId, applicationNo, type, severity, message, createdAt, read }
AuditEvent { id, ts, actor, actorRole, action, entityType, entityId, details, prevHash, hash }
Decision { action, note, decidedBy, decidedAt }
Rule { id, name, description, categories: string[], type, params, severity, clause, enabled, version }
Source { id, name, issuer, docTypes: string[], method, online: boolean, lastLatencyMs?, successRate? }
ValidationReport { applicationId, generatedAt, rulesetVersion, summary: {...counts, complianceScore, riskScore, riskBand},
                   checklist, findings, verifications: [{documentId, docType, status, source, checkedAt}], rulesApplied: [{ruleId, result: "PASS"|"FAIL"|"SKIPPED", detail}] }
```

## 4. HTTP API (prefix `/api`, JSON, Bearer JWT except login & /health)

| method & path | role | purpose |
|---|---|---|
| `GET /health` | – | `{status, version}` |
| `POST /auth/login` `{username,password}` | – | `{accessToken, user}` |
| `GET /auth/me` | any | `User` |
| `GET /meta` | any | `{categories:[{id,label}], docTypes:[{id,label,issuer,validityMonths,verifiable}], statuses, verificationStatuses}` |
| `GET /dashboard/summary` | officer+ | `{totals:{applications, pendingValidation, deficiencies, sourcePending, inspection, recommended}, byStatus:{}, byVerification:{}, byCategory:{}, findingsBySeverity:{}, recent:[Application], avgValidationSeconds, manualEffortSavedHours}` |
| `GET /applications?status&category&region&q&riskBand` | any (institution sees own) | `Application[]` |
| `POST /applications` `{category, academicYear, formData}` | INSTITUTION | `Application` (DRAFT) |
| `GET /applications/{id}` | scoped | `Application & {documents: Document[], findings: Finding[], records: InstitutionalRecords}` |
| `PATCH /applications/{id}` `{formData}` | INSTITUTION (DRAFT/RECTIFICATION_REQUESTED) | `Application` |
| `POST /applications/{id}/documents` multipart `file`, optional `docType` | INSTITUTION | `Document` (pipeline runs synchronously) |
| `DELETE /documents/{id}` | INSTITUTION (editable states) | 204 |
| `GET /documents/{id}/file` | scoped | original file |
| `GET /documents/{id}/text` | scoped | `{text, blocks}` |
| `GET /documents/{id}/ela` | officer+ | PNG heatmap |
| `POST /documents/{id}/verify` | officer+ | re-run source verification → `Document` |
| `POST /applications/{id}/submit` | INSTITUTION | runs validation → `ValidationReport` |
| `POST /applications/{id}/validate` | officer+ (or institution for pre-check on DRAFT) | `ValidationReport` |
| `GET /applications/{id}/report` | scoped | `ValidationReport` |
| `GET /applications/{id}/report.pdf` | scoped | PDF |
| `PATCH /findings/{id}` `{status, note}` | officer+ (institution may set `ACKNOWLEDGED`/`RECTIFIED` with note) | `Finding` |
| `POST /applications/{id}/observations` `{note}` | officer+ | `AuditEvent` |
| `POST /applications/{id}/request-rectification` `{note, findingIds}` | officer+ | `Application` |
| `POST /applications/{id}/decision` `{action, note}` | REGIONAL_DIRECTOR (officer may only `RECOMMEND_*`) | `Application` |
| `GET /alerts?unread=true` | any (scoped) | `Alert[]` ; `POST /alerts/{id}/read` |
| `GET /audit?entityId&action&limit` | officer+ (admin all) | `AuditEvent[]` ; `GET /audit/verify` → `{valid, checked, brokenAt?}` |
| `GET /rules` / `PUT /rules/{id}` `{enabled, params, severity}` | read officer+, write ADMIN | `Rule` (bumps ruleset version, audited) |
| `GET /checklists` / `PUT /checklists/{category}` | read any, write ADMIN | `{category: ChecklistItem-template[]}` |
| `GET /sources` / `POST /sources/{id}/toggle` | read officer+, toggle ADMIN | `Source` |
| `GET /institutions/{id}/records` | scoped | `InstitutionalRecords` |

Errors: `{detail: string}` with proper HTTP codes. Every mutating call writes an AuditEvent.

## 5. Rule types (config/rules.yaml)

`REQUIRED_DOCUMENT`, `DOCUMENT_EXPIRY` (params: graceDays), `FIELD_PRESENT` (field), `FIELD_MATCH_RECORD`
(formField, recordPath, tolerance), `FIELD_MATCH_DOCUMENT` (formField, docType, extractedField), `THRESHOLD`
(metric e.g. `faculty_student_ratio` max 20, `land_area_acres` min by region/type, `builtup_area_per_intake`),
`CADRE_RATIO` (1:2:6), `TER_PAYMENT`, `DUPLICATE_DOCUMENT` (sha256/phash across institutions),
`DUPLICATE_FACULTY` (same PAN across institutions), `FORENSIC_FLAG`, `SOURCE_VERIFICATION`, `INFRA_EVIDENCE`
(evidenceType, minCount label e.g. computers ≥ 1 per 2 students per lab spec, quality, exif age).
Each rule carries `clause` (e.g. "APH 2024-27 Ch. II, 2.x") — mark clauses as illustrative/configurable, never claim exact official numbering unless sourced.

## 6. Pipeline per uploaded document

1. store file (storage/{applicationId}/{uuid}_{name}), sha256 + phash
2. OCR (PDF text layer → else RapidOCR) → text + blocks
3. classify (keyword/regex scoring per docType, filename hint) — if user-declared docType disagrees with prediction at conf > .7 → `INCONSISTENCY` finding
4. extract fields per docType (regex/rules on text; dates normalised ISO)
5. forensics: ELA for images & rasterised PDF pages, PDF metadata (producer/creator incl. editing software, created≠modified, incremental updates), font/text-layer anomalies, EXIF
6. QR decode → signature verify (Ed25519 signed JSON from simulated issuers) → compare claims with extracted fields
7. adapter verification via /mock authority API by referenceNo (may be offline → SOURCE_UNAVAILABLE, unknown doc type → MANUAL_REVIEW_REQUIRED)
8. infra docs: infra_cv analysis
Then application-level validator runs rules & cross-document checks, writes Findings, Alerts, scores, audit.

## 7. Design tokens (frontend, light-first, government-grade)

- Font: "Inter" (UI), "Noto Sans Devanagari" for Hindi strings, "JetBrains Mono" for IDs/hashes.
- Primary navy `#0B2E59` (hsl 213 78% 20%), primary-600 `#1D4E89`, accent saffron `#E8772E` (use sparingly: highlights, active nav underline), success `#15803D`, warning `#B45309`, danger `#B91C1C`, info `#1D4ED8`, surface `#FFFFFF`, canvas `#F5F7FA`, border `#E2E8F0`, text `#0F172A`, muted `#475569`.
- Verification status colors: VERIFIED green, MISMATCH_DETECTED red, EXPIRED orange-red, VERIFICATION_PENDING blue, SOURCE_UNAVAILABLE slate, MANUAL_REVIEW_REQUIRED amber, NOT_APPLICABLE gray. One shared `<StatusBadge>` component in `frontend/src/components/common/`.
- Radius 8px, subtle shadows, dense-but-readable tables, no gradients-on-everything, no emoji in UI.
- Every AI output shows an "Advisory — requires officer review" marker.

## 8. Document type IDs (config/doc_types.yaml must use exactly these)

`SOCIETY_TRUST_REGISTRATION`, `LAND_DOCUMENT`, `BUILDING_PLAN_APPROVAL`, `OCCUPANCY_CERTIFICATE`, `FIRE_NOC`,
`STRUCTURAL_STABILITY_CERT`, `AFFIDAVIT_UNDERTAKING`, `UNIVERSITY_AFFILIATION`, `STATE_GOVT_NOC`, `PREVIOUS_EOA_LETTER`,
`NBA_ACCREDITATION`, `NAAC_ACCREDITATION`, `TER_PAYMENT_RECEIPT`, `FACULTY_ROSTER`, `AUDITED_FINANCIAL_STATEMENT`,
`CORPUS_FUND_FDR`, `FLOOR_PLAN`, `INFRA_PHOTO_CLASSROOM`, `INFRA_PHOTO_COMPUTER_LAB`, `INFRA_PHOTO_LIBRARY`,
`INFRA_PHOTO_LABORATORY`, `INFRA_PHOTO_ACCESSIBILITY`, `OTHER`.

## 9. Synthetic scenario data (samples/scenarios.json) — produced by the AI/samples module, consumed by seed + mock authorities

```jsonc
{
  "institutions": [{ "key": "piat", "permanentId": "1-3948291012", "name": "...", "type": "Private-Self Financing",
                     "state": "...", "city": "...", "region": "WR", "establishedYear": 2009, "trustName": "...",
                     "address": "...", "campusGps": {"lat":..,"lng":..}, "records": InstitutionalRecords }],
  "applications": [{ "key": "piat-eoa-2026", "institutionKey": "piat", "category": "EOA", "academicYear": "2026-27",
                     "status": "SUBMITTED", "formData": {...}, "scenario": "short human description of what should be flagged",
                     "expectedFindings": ["EXPIRED_DOCUMENT:FIRE_NOC", "..."],
                     "documents": [{ "path": "piat/fire_noc.pdf", "docType": "FIRE_NOC" }] }],
  "authorityRecords": { "<sourceId>": [{ "referenceNo": "...", "fields": {...}, "status": "VALID"|"REVOKED"|"EXPIRED" }] }
}
```
Paths are relative to `samples/`. Users are created by seed (section 2) and linked: `inst.piat` → `piat`, `inst.apex` → `apex`.
