// Mapping of Problem Statement 26261 to what is built. Mirrors docs/PS_MAPPING.md.

export type MapStatus = "Built" | "Prototype-simulated" | "Designed";

export type MapRow = {
  requirement: string;
  feature: string;
  where: string;
  status: MapStatus;
  note?: string;
};

export type MapGroup = { id: string; title: string; rows: MapRow[] };

export const PS_MAPPING: MapGroup[] = [
  {
    id: "objectives",
    title: "Objectives and functional requirements",
    rows: [
      {
        requirement: "Identify the application category and the applicable checklist",
        feature: "Category selected at application creation drives a checklist loaded from checklists.yaml (mandatory flag, conditions, clause)",
        where: "Portal › New application (category step); Application › Overview (checklist)",
        status: "Built",
      },
      {
        requirement: "Retrieve institutional records already available in AICTE systems",
        feature: "Institutional records (previous approvals, approved programmes and intake, faculty, accreditations, land and building, TER payments, deficiency history, affidavits) fetched by institution and used by the rules",
        where: "Application › Overview (institutional records); GET /api/institutions/{id}/records",
        status: "Prototype-simulated",
        note: "Records are seeded to stand in for AICTE databases; the read path is an API so a live AICTE source can replace it.",
      },
      {
        requirement: "OCR, document classification and data extraction",
        feature: "PDF text layer with RapidOCR fallback; keyword/regex classifier with confidence and signals; per-type field extractors with source text and page",
        where: "Application › Documents (viewer with extracted fields); GET /api/documents/{id}/text",
        status: "Built",
      },
      {
        requirement: "Flag missing, incomplete, expired or inconsistent information",
        feature: "REQUIRED_DOCUMENT, FIELD_PRESENT, DOCUMENT_EXPIRY, FIELD_MATCH_RECORD and FIELD_MATCH_DOCUMENT rules; declared-vs-detected document type check",
        where: "Application › Findings",
        status: "Built",
      },
      {
        requirement: "Structured validation report and rectification guidance",
        feature: "ValidationReport (summary, checklist, findings, verifications, rules applied, ruleset version) and PDF; officer requests rectification for selected findings; institution re-uploads and marks rectified",
        where: "Application › Report (PDF download); Request rectification; Respond to findings",
        status: "Built",
      },
      {
        requirement: "Detect anomalies and potential forgery: alterations, duplicates, metadata, mismatched identifiers, irregular dates",
        feature: "ELA score and heatmap, PDF/EXIF metadata flags, SHA-256 and perceptual-hash duplicates across institutions, duplicate faculty PAN, identifier and date consistency checks",
        where: "Application › Documents (forensics, ELA overlay); Findings of kind ANOMALY / DUPLICATE",
        status: "Built",
        note: "Presented as preliminary indicators requiring human verification.",
      },
      {
        requirement: "Verify documents with issuing authorities (APIs, portals, DigiLocker, QR codes, digital signatures, reference numbers)",
        feature: "Adapter per source; Ed25519-signed QR payloads verified against issuer public keys; reference-number lookups with field-by-field comparison",
        where: "Application › Verification; Portal › Verification sources",
        status: "Prototype-simulated",
        note: "Issuing authorities are simulated services at /mock/*. The adapter interface is ready for authorised real APIs.",
      },
      {
        requirement: "Record source, timestamp and result; use the six verification states; route inconclusive cases to manual review",
        feature: "Each verification stores source, method, checkedAt, response summary and comparisons; VERIFIED, MISMATCH_DETECTED, EXPIRED, VERIFICATION_PENDING, SOURCE_UNAVAILABLE, MANUAL_REVIEW_REQUIRED",
        where: "Application › Verification; Report",
        status: "Built",
      },
      {
        requirement: "Compliance assistance against configurable checklists and norms from the Approval Process Handbook",
        feature: "THRESHOLD (faculty-student ratio, land area, built-up area per intake), CADRE_RATIO, TER_PAYMENT rules; clauses carried on every rule",
        where: "Application › Findings; Portal › Rules & checklists",
        status: "Built",
        note: "Thresholds and clause references are illustrative and editable.",
      },
      {
        requirement: "Review infrastructure evidence (photographs, videos, floor plans) with computer vision; flag discrepancies or need for inspection",
        feature: "Object detection and counting on infrastructure photographs (deterministic OpenCV detector by default, YOLOv8n when installed), quality (blur, brightness, resolution) and EXIF capture-date, editing-software and GPS-distance checks; INFRA_EVIDENCE rules compare counts with norms",
        where: "Application › Infrastructure; Findings of kind INFRASTRUCTURE",
        status: "Built",
        note: "Photographs are analysed; video and floor-plan image analysis are on the roadmap. Detection counts are assistive estimates, not an inspection.",
      },
      {
        requirement: "Dashboard, alerts and audit trail of rules applied, records checked, source responses and actions",
        feature: "Officer dashboard with totals, status and severity breakdowns; alerts; hash-chained audit log with chain verification",
        where: "Portal › Dashboard, Alerts, Audit log; Application › Audit trail",
        status: "Built",
      },
    ],
  },
  {
    id: "deliverables",
    title: "Deliverables",
    rows: [
      {
        requirement: "Working platform for application validation and document authentication",
        feature: "FastAPI backend and React portal with four roles and six seeded demo applications",
        where: "Portal at /portal",
        status: "Built",
      },
      {
        requirement: "Validation and deficiency reports",
        feature: "Structured JSON report and generated PDF listing checklist status, findings with evidence and rectification items",
        where: "GET /api/applications/{id}/report and /report.pdf",
        status: "Built",
      },
      {
        requirement: "Issuing-authority verification integration",
        feature: "Adapter layer and simulated authorities (QR-signed certificates and reference-number registries)",
        where: "backend/app/adapters, backend/app/mock_authorities",
        status: "Prototype-simulated",
      },
      {
        requirement: "Configurable rules and checklists",
        feature: "rules.yaml, checklists.yaml and doc_types.yaml; admin editing through the API and console",
        where: "Portal › Rules & checklists",
        status: "Built",
      },
      {
        requirement: "Dashboard for officials",
        feature: "Region-scoped queue, risk bands, alerts and decision workflow",
        where: "Portal › Dashboard",
        status: "Built",
      },
      {
        requirement: "Integration with the AICTE portal",
        feature: "REST API with OpenAPI schema; SSO and webhook integration points described in the architecture",
        where: "docs/ARCHITECTURE.md, docs/API.md",
        status: "Designed",
      },
    ],
  },
  {
    id: "outcomes",
    title: "Expected outcomes",
    rows: [
      {
        requirement: "Faster preliminary scrutiny",
        feature: "Pipeline runs on upload; full validation on submit; measured average verification time",
        where: "Evaluation page; Dashboard › avg validation time",
        status: "Built",
      },
      {
        requirement: "Early detection of deficiencies by institutions",
        feature: "Pre-submission validation on drafts so institutions can fix gaps before submitting",
        where: "Portal › New application › Run self-check",
        status: "Built",
      },
      {
        requirement: "Reliable identification of suspicious documents",
        feature: "Forensic and duplicate indicators with evidence; measured on tampered synthetic samples",
        where: "Evaluation page",
        status: "Built",
      },
      {
        requirement: "Transparent and accountable process",
        feature: "Rule IDs, clauses and evidence on every finding; ruleset version on every report; audit chain",
        where: "Findings, Report, Audit",
        status: "Built",
      },
    ],
  },
  {
    id: "safeguards",
    title: "Safeguards",
    rows: [
      {
        requirement: "Checks are configurable",
        feature: "Rules, thresholds, severities, checklists and sources edited by administrators; versioned and audited",
        where: "Portal › Rules & checklists, Verification sources",
        status: "Built",
      },
      {
        requirement: "Authorised, role-based access; no bypass of access controls",
        feature: "JWT authentication, four roles, server-side scoping by institution and region on every endpoint",
        where: "backend/app/security.py and every router",
        status: "Built",
      },
      {
        requirement: "Data protection, confidentiality and access logging",
        feature: "PAN masking, scoped file access, mutating actions written to the audit log",
        where: "Portal › Audit log; institutional records views",
        status: "Built",
      },
      {
        requirement: "Data retention",
        feature: "Retention periods per data class, archival and purge jobs",
        where: "docs/SECURITY_AND_SAFEGUARDS.md",
        status: "Designed",
      },
      {
        requirement: "Explainable, evidence-backed flags",
        feature: "Each finding carries reason, rule ID, clause and typed evidence (document excerpt, record, source response, image region, metadata)",
        where: "Findings panel",
        status: "Built",
      },
      {
        requirement: "AI is decision support only; final decisions rest with the competent authority",
        feature: "Advisory marker on all AI output; officers can only recommend; final decision restricted to the Regional Director with a mandatory note; approval blocked while any critical finding is open without an officer disposition",
        where: "Application › Record recommendation / Record decision",
        status: "Built",
      },
    ],
  },
];

export const EVALUATION_CRITERIA = [
  "Extraction accuracy",
  "Validation accuracy",
  "Anomaly detection performance",
  "Source-verification success rate",
  "Discrepancy reliability",
  "Average verification time",
  "Alert timeliness",
  "Reduction in manual effort",
] as const;
