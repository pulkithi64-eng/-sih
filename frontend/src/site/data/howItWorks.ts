export type HowStep = {
  id: string;
  nav: string;
  title: string;
  body: string;
  output?: string;
  checks: { name: string; detail: string }[];
};

export const HOW_STEPS: HowStep[] = [
  {
    id: "checklist",
    nav: "Checklist",
    title: "Identify the category and its checklist",
    body: "The institution starts an application by choosing its category and academic year and declaring key values: programmes and intake, faculty count, land and built-up area, TER transaction ID and accreditation claims. The category selects a checklist from configuration; conditional items are added when the declared values call for them, for example an NBA certificate when accreditation is claimed.",
    output: "A checklist with each required document, whether it is mandatory, the clause it relates to, and its live status: present, missing, expired, invalid or not required.",
    checks: [
      { name: "Seven categories", detail: "Extension of Approval, new institution, intake increase, new course, change of name, change of site, closure." },
      { name: "Mandatory and conditional items", detail: "Conditions are evaluated on the declared form data, so the checklist adapts to each application." },
      { name: "Pre-check before submission", detail: "Institutions can run validation on a draft and fix gaps before they submit." },
    ],
  },
  {
    id: "records",
    nav: "Records",
    title: "Retrieve records AICTE already holds",
    body: "Many answers are already in AICTE systems. VeriSense loads the institution's records so the application is checked against them rather than taken at face value.",
    output: "Institutional records available to the rule engine and shown to the officer next to the application.",
    checks: [
      { name: "Previous approvals", detail: "Year, status and letter reference of earlier Extension of Approval decisions." },
      { name: "Approved programmes and intake", detail: "Level, programme, course, shift and approved intake." },
      { name: "Faculty", detail: "Faculty IDs, masked PAN, designation, qualification and joining date." },
      { name: "Accreditation, land, TER, deficiencies, affidavits", detail: "NBA and NAAC validity, land and built-up area, fee payment history, open deficiencies and affidavits on file." },
    ],
  },
  {
    id: "read",
    nav: "Read",
    title: "OCR, classification and field extraction",
    body: "Each upload is stored with its SHA-256 and perceptual hash. Text is taken from the PDF text layer where one exists, and otherwise recognised with RapidOCR, keeping word positions and confidence. A classifier scores the text and filename against signals for each document type, and type-specific extractors pull out the fields that matter.",
    output: "Document type with confidence and the signals that drove it; extracted fields, each with value, confidence, the source text it came from and the page.",
    checks: [
      { name: "Declared vs detected type", detail: "If the institution labelled a file as one type and the classifier is confident it is another, an inconsistency is raised." },
      { name: "Key fields", detail: "Reference numbers, issuer, holder name, issue and expiry dates (normalised), amounts, areas, intake figures." },
      { name: "Low-confidence reads", detail: "Fields extracted with low confidence are shown as such so the officer knows to check the original." },
    ],
  },
  {
    id: "forensics",
    nav: "Forensics",
    title: "Anomaly and potential-forgery indicators",
    body: "Forensic checks look for traces that a document was edited after issue, or that the same document or person appears where it should not. Results are indicators with evidence, never verdicts.",
    output: "Forensic score and flags per document, each with a code, severity, reason and evidence; an ELA heatmap for officers.",
    checks: [
      { name: "Error Level Analysis", detail: "Re-compresses images and rasterised pages and highlights regions whose error level differs from the rest — typical of pasted or retouched areas." },
      { name: "Metadata", detail: "Producer and creator software (image editors on an issued certificate), creation vs modification dates, incremental PDF updates, EXIF." },
      { name: "Font and text-layer anomalies", detail: "Mixed fonts within a field, or a text layer that disagrees with what is rendered on the page." },
      { name: "Duplicate files", detail: "Identical (SHA-256) or visually near-identical (perceptual hash) documents submitted by different institutions." },
      { name: "Duplicate faculty", detail: "The same PAN listed by more than one institution for the same period." },
      { name: "Irregular dates and identifiers", detail: "Issue after expiry, dates in the future, reference numbers that do not fit the issuer's pattern." },
    ],
  },
  {
    id: "verification",
    nav: "Verification",
    title: "Verification with the issuing authority",
    body: "Where a document type has a verifiable source, VeriSense asks the source rather than trusting the scan. Each document type maps to an adapter; each adapter returns a normalised result with the source, method, timestamp, a response summary and a field-by-field comparison.",
    output: "One of six states — Verified, Mismatch detected, Expired, Verification pending, Source unavailable, Manual review required — with the full source response kept for audit.",
    checks: [
      { name: "Signature", detail: "QR payload signature valid for the claimed issuer's key." },
      { name: "Existence and status", detail: "Reference number known to the source; status valid, expired or revoked." },
      { name: "Field comparison", detail: "Holder, dates, amounts and other claims compared with the extracted values." },
      { name: "Availability", detail: "Timeouts and disabled sources are recorded as such, never treated as a pass." },
    ],
  },
  {
    id: "rules",
    nav: "Rules",
    title: "Configurable rule engine",
    body: "When the application is submitted (or an officer re-runs validation), the rule engine evaluates every enabled rule for the category against the checklist, the extracted fields, the institutional records and the verification and forensic results. Each rule has an ID, type, parameters, severity and a clause, and records PASS, FAIL or SKIPPED in the report.",
    output: "Findings with evidence, alerts for critical issues, compliance and risk scores, and a validation report stamped with the ruleset version.",
    checks: [
      { name: "Completeness", detail: "REQUIRED_DOCUMENT and FIELD_PRESENT." },
      { name: "Validity", detail: "DOCUMENT_EXPIRY with a configurable grace period." },
      { name: "Consistency", detail: "FIELD_MATCH_RECORD (declared vs AICTE records) and FIELD_MATCH_DOCUMENT (declared vs document)." },
      { name: "Norms", detail: "THRESHOLD (faculty-student ratio, land area, built-up area per intake), CADRE_RATIO, TER_PAYMENT." },
      { name: "Integrity", detail: "DUPLICATE_DOCUMENT, DUPLICATE_FACULTY, FORENSIC_FLAG, SOURCE_VERIFICATION." },
      { name: "Infrastructure", detail: "INFRA_EVIDENCE: required counts, image quality and capture date." },
    ],
  },
  {
    id: "infra",
    nav: "Infrastructure",
    title: "Infrastructure evidence review",
    body: "Photographs of classrooms, computer labs, libraries, laboratories and accessibility features are analysed with computer vision: a deterministic OpenCV detector by default, or a YOLOv8n model where one is installed. Detected objects are counted and compared with what the norms and declared intake imply; image quality and EXIF data show whether the photo is usable and recent.",
    output: "Detections with bounding boxes, counts, quality and EXIF summary, and flags where evidence is insufficient or suggests a physical inspection may be needed. Advisory only.",
    checks: [
      { name: "Counts against norms", detail: "For example computer workstations in a lab compared with the configured ratio to intake." },
      { name: "Image quality", detail: "Blur and brightness, so unusable evidence is asked for again rather than judged." },
      { name: "Capture date and location", detail: "EXIF date older than the configured limit or in the future, GPS missing or far from the registered campus." },
      { name: "Edited or reused photos", detail: "Editing software in EXIF; the same photo (SHA-256 or perceptual hash) submitted by another institution." },
    ],
  },
  {
    id: "review",
    nav: "Review & decision",
    title: "Officer review and decision",
    body: "The scrutiny officer sees the application with its checklist, documents side by side with extracted fields, forensic and verification panels, and the findings list. They acknowledge, dismiss or escalate findings with notes, add observations, request rectification, re-run verification and record a recommendation. The Regional Director records the final decision — approve for EoA, issue deficiency letter, order inspection, or reject — and must write a note.",
    output: "A decision recorded by the competent authority, with the complete history of rules, sources, findings and actions in the audit chain.",
    checks: [
      { name: "Region-scoped queue", detail: "Officers see only applications in their region; institutions only their own." },
      { name: "Every action audited", detail: "Status changes, notes, verification re-runs and decisions are chained in the audit log." },
      { name: "No automated decisions", detail: "The system never changes a decision field by itself." },
    ],
  },
];

export const RULE_EXAMPLE = `# backend/config/rules.yaml
- id: R-EXP-001
  name: Fire NOC valid
  description: Fire safety NOC must be valid on the date of
    scrutiny (warn when expiring within warnDays).
  categories: [ALL]
  type: DOCUMENT_EXPIRY
  kind: EXPIRED_DOCUMENT
  params: {docTypes: [FIRE_NOC], graceDays: 0, warnDays: 60}
  severity: CRITICAL
  clause: "APH 2024-27 (illustrative) - Ch. III, Safety norms"
  enabled: true
  version: 1`;

export const SCORING = [
  {
    name: "Compliance score (0-100)",
    formula: "100 x sum(w[sev] x (1 - failed/checks)) / sum(w[sev])  over rules not skipped",
    note: "Each evaluated rule contributes the share of its checks that passed, weighted by severity (CRITICAL 5, MAJOR 3, MINOR 1; configurable in rules.yaml). Disabled and non-applicable rules are excluded.",
  },
  {
    name: "Risk score (0-100) and band",
    formula: "min(100, sum(points[sev] x mult[kind]))  over open, acknowledged and escalated findings",
    note: "Points: CRITICAL 30, MAJOR 15, MINOR 5. Integrity findings (anomaly, duplicate, verification) count fully; mismatches 0.8; expiry and compliance gaps 0.5; missing documents and infrastructure 0.4. Bands: LOW below 30, MEDIUM below 60, HIGH otherwise. Risk orders the queue; it never decides.",
  },
];
