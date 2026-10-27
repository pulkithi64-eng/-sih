# Problem Statement Mapping — PS 26261

**AI-Powered Application Validation, Document Authentication and Regulatory Compliance Verification** — AICTE, Regulation Bureau · Smart India Hackathon 2026 · Theme: Smart Automation.

Every objective, functional requirement, deliverable, expected outcome and safeguard of the problem statement, the feature that addresses it, where it is in the product, and its status. The same table is published on the website at `/compliance`; this file is generated from `frontend/src/site/data/psMapping.ts` so the two never drift.

| Status | Meaning | Count |
|---|---|---|
| **Built** | Implemented and working in the prototype | 22 / 27 |
| **Prototype-simulated** | Implemented end to end against simulated external systems or seeded data | 3 / 27 |
| **Designed** | Specified in the architecture and docs, not yet implemented | 2 / 27 |

> Issuing-authority APIs are **simulated** in this prototype, behind an adapter layer ready for authorised real APIs. Institutional records are seeded synthetic data standing in for AICTE databases. Clause references and norms are illustrative and configurable.

## Objectives and functional requirements

| # | Requirement | Feature | Where in product | Status |
|---|---|---|---|---|
| 1 | Identify the application category and the applicable checklist | Category selected at application creation drives a checklist loaded from checklists.yaml (mandatory flag, conditions, clause) | Institution › New application; Application › Checklist tab | Built |
| 2 | Retrieve institutional records already available in AICTE systems | Institutional records (previous approvals, approved programmes and intake, faculty, accreditations, land and building, TER payments, deficiency history, affidavits) fetched by institution and used by the rules. *Records are seeded to stand in for AICTE databases; the read path is an API so a live AICTE source can replace it.* | Application › Institutional records panel; GET /api/institutions/{id}/records | Prototype-simulated |
| 3 | OCR, document classification and data extraction | PDF text layer with RapidOCR fallback; keyword/regex classifier with confidence and signals; per-type field extractors with source text and page | Document panel › Extracted fields; GET /api/documents/{id}/text | Built |
| 4 | Flag missing, incomplete, expired or inconsistent information | REQUIRED_DOCUMENT, FIELD_PRESENT, DOCUMENT_EXPIRY, FIELD_MATCH_RECORD and FIELD_MATCH_DOCUMENT rules; declared-vs-detected document type check | Application › Findings | Built |
| 5 | Structured validation report and rectification guidance | ValidationReport (summary, checklist, findings, verifications, rules applied, ruleset version) and PDF; officer requests rectification for selected findings; institution re-uploads and marks rectified | Application › Report; Download PDF; Request rectification | Built |
| 6 | Detect anomalies and potential forgery: alterations, duplicates, metadata, mismatched identifiers, irregular dates | ELA score and heatmap, PDF/EXIF metadata flags, SHA-256 and perceptual-hash duplicates across institutions, duplicate faculty PAN, identifier and date consistency checks. *Presented as preliminary indicators requiring human verification.* | Document panel › Forensics; Findings of kind ANOMALY / DUPLICATE | Built |
| 7 | Verify documents with issuing authorities (APIs, portals, DigiLocker, QR codes, digital signatures, reference numbers) | Adapter per source; Ed25519-signed QR payloads verified against issuer public keys; reference-number lookups with field-by-field comparison. *Issuing authorities are simulated services at /mock/*. The adapter interface is ready for authorised real APIs.* | Document panel › Verification; Admin › Sources | Prototype-simulated |
| 8 | Record source, timestamp and result; use the six verification states; route inconclusive cases to manual review | Each verification stores source, method, checkedAt, response summary and comparisons; VERIFIED, MISMATCH_DETECTED, EXPIRED, VERIFICATION_PENDING, SOURCE_UNAVAILABLE, MANUAL_REVIEW_REQUIRED | Document panel › Verification; Report › Verifications | Built |
| 9 | Compliance assistance against configurable checklists and norms from the Approval Process Handbook | THRESHOLD (faculty-student ratio, land area, built-up area per intake), CADRE_RATIO, TER_PAYMENT rules; clauses carried on every rule. *Thresholds and clause references are illustrative and editable.* | Application › Findings; Admin › Rules | Built |
| 10 | Review infrastructure evidence (photographs, videos, floor plans) with computer vision; flag discrepancies or need for inspection | Object detection and counting on infrastructure photographs (deterministic OpenCV detector by default, YOLOv8n when installed), quality (blur, brightness, resolution) and EXIF capture-date, editing-software and GPS-distance checks; INFRA_EVIDENCE rules compare counts with norms. *Photographs are analysed; video and floor-plan image analysis are on the roadmap. Detection counts are assistive estimates, not an inspection.* | Document panel › Infrastructure analysis; Findings of kind INFRASTRUCTURE | Built |
| 11 | Dashboard, alerts and audit trail of rules applied, records checked, source responses and actions | Officer dashboard with totals, status and severity breakdowns; alerts; hash-chained audit log with chain verification | Portal › Dashboard, Alerts, Audit | Built |

## Deliverables

| # | Requirement | Feature | Where in product | Status |
|---|---|---|---|---|
| 1 | Working platform for application validation and document authentication | FastAPI backend and React portal with four roles and six seeded demo applications | Portal at /portal | Built |
| 2 | Validation and deficiency reports | Structured JSON report and generated PDF listing checklist status, findings with evidence and rectification items | GET /api/applications/{id}/report and /report.pdf | Built |
| 3 | Issuing-authority verification integration | Adapter layer and simulated authorities (QR-signed certificates and reference-number registries) | backend/app/adapters, backend/app/mock_authorities | Prototype-simulated |
| 4 | Configurable rules and checklists | rules.yaml, checklists.yaml and doc_types.yaml; admin editing through the API and console | Admin › Rules, Checklists | Built |
| 5 | Dashboard for officials | Region-scoped queue, risk bands, alerts and decision workflow | Portal › Dashboard | Built |
| 6 | Integration with the AICTE portal | REST API with OpenAPI schema; SSO and webhook integration points described in the architecture | docs/ARCHITECTURE.md, docs/API.md | Designed |

## Expected outcomes

| # | Requirement | Feature | Where in product | Status |
|---|---|---|---|---|
| 1 | Faster preliminary scrutiny | Pipeline runs on upload; full validation on submit; measured average verification time | Evaluation page; Dashboard › avg validation time | Built |
| 2 | Early detection of deficiencies by institutions | Pre-submission validation on drafts so institutions can fix gaps before submitting | Institution › Application › Run pre-check | Built |
| 3 | Reliable identification of suspicious documents | Forensic and duplicate indicators with evidence; measured on tampered synthetic samples | Evaluation page | Built |
| 4 | Transparent and accountable process | Rule IDs, clauses and evidence on every finding; ruleset version on every report; audit chain | Findings, Report, Audit | Built |

## Safeguards

| # | Requirement | Feature | Where in product | Status |
|---|---|---|---|---|
| 1 | Checks are configurable | Rules, thresholds, severities, checklists and sources edited by administrators; versioned and audited | Admin console | Built |
| 2 | Authorised, role-based access; no bypass of access controls | JWT authentication, four roles, server-side scoping by institution and region on every endpoint | backend/app/security.py and every router | Built |
| 3 | Data protection, confidentiality and access logging | PAN masking, scoped file access, mutating actions written to the audit log | Audit log; institutional records views | Built |
| 4 | Data retention | Retention periods per data class, archival and purge jobs | docs/SECURITY_AND_SAFEGUARDS.md | Designed |
| 5 | Explainable, evidence-backed flags | Each finding carries reason, rule ID, clause and typed evidence (document excerpt, record, source response, image region, metadata) | Findings panel | Built |
| 6 | AI is decision support only; final decisions rest with the competent authority | Advisory marker on all AI output; officers can only recommend; final decision restricted to the Regional Director with a mandatory note; approval blocked while any critical finding is open without an officer disposition | Application › Decision | Built |

## Evaluation criteria

Each criterion named in the problem statement is measured on the synthetic dataset; see [EVALUATION.md](EVALUATION.md).

- Extraction accuracy
- Validation accuracy
- Anomaly detection performance
- Source-verification success rate
- Discrepancy reliability
- Average verification time
- Alert timeliness
- Reduction in manual effort
