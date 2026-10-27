// Static copy for the public website. Kept in one place so docs/ and the site stay in sync.

export const REPO_URL = "https://github.com/LearnCodeZaid/aicte-verisense";
export const docUrl = (file: string) => `${REPO_URL}/blob/main/docs/${file}`;

export const NAV = [
  { to: "/how-it-works", label: "How it works" },
  { to: "/architecture", label: "Architecture" },
  { to: "/compliance", label: "PS mapping" },
  { to: "/evaluation", label: "Evaluation" },
  { to: "/docs", label: "Docs" },
] as const;

export type VerificationStateId =
  | "VERIFIED"
  | "MISMATCH_DETECTED"
  | "EXPIRED"
  | "VERIFICATION_PENDING"
  | "SOURCE_UNAVAILABLE"
  | "MANUAL_REVIEW_REQUIRED";

export const VERIFICATION_STATES: {
  id: VerificationStateId;
  label: string;
  meaning: string;
  trigger: string;
  next: string;
}[] = [
  {
    id: "VERIFIED",
    label: "Verified",
    meaning: "The issuing authority's record, or a valid signed QR payload, confirms the document.",
    trigger: "Reference number found at source, status valid, and every compared field matches.",
    next: "No action. Source, method and timestamp are kept in the audit trail.",
  },
  {
    id: "MISMATCH_DETECTED",
    label: "Mismatch detected",
    meaning: "The source holds a record, but one or more fields differ from what was submitted.",
    trigger: "Field comparison fails (for example a different validity date or holder name), or the signature does not check out.",
    next: "A finding with a side-by-side comparison is raised for the scrutiny officer.",
  },
  {
    id: "EXPIRED",
    label: "Expired",
    meaning: "The document, or the source record, is no longer valid on the date of submission.",
    trigger: "Validity date earlier than the submission date (with a configurable grace period), or source status EXPIRED.",
    next: "Deficiency is flagged; the institution can upload a renewed document in the rectification loop.",
  },
  {
    id: "VERIFICATION_PENDING",
    label: "Verification pending",
    meaning: "A request to the source has been queued or not yet completed.",
    trigger: "Document awaiting a source check, for example right after upload or during a retry.",
    next: "The officer can re-run verification at any time from the document panel.",
  },
  {
    id: "SOURCE_UNAVAILABLE",
    label: "Source unavailable",
    meaning: "The issuing authority's service could not be reached or is switched off.",
    trigger: "Timeout, network error, or the source disabled by an administrator.",
    next: "Nothing is assumed. The item stays open and can be retried or verified manually.",
  },
  {
    id: "MANUAL_REVIEW_REQUIRED",
    label: "Manual review required",
    meaning: "The system cannot reach a conclusion automatically.",
    trigger: "No verifiable source for the document type, missing reference number, or conflicting signals.",
    next: "Routed to the scrutiny officer's queue with whatever evidence was gathered.",
  },
];

export const MODULES = [
  {
    key: "validation",
    title: "Application & document validation",
    summary:
      "Identifies the application category, builds the applicable checklist, and reads every upload with OCR, classification and field extraction.",
    points: [
      "Category-specific checklists (EoA, new institution, intake increase, new course, change of name or site, closure)",
      "Institutional records already held by AICTE pulled in automatically",
      "Missing, incomplete, expired and inconsistent items flagged with the rule that fired",
      "Structured validation report and PDF with a rectification list",
    ],
  },
  {
    key: "forensics",
    title: "Anomaly & potential-forgery detection",
    summary:
      "Looks for signs of alteration and duplication and presents them as preliminary indicators, each with its evidence and reason.",
    points: [
      "Error Level Analysis heatmaps for images and rasterised pages",
      "PDF and EXIF metadata: editing software, created vs modified, incremental saves",
      "Duplicate files across institutions (SHA-256 and perceptual hash)",
      "Same faculty PAN claimed by more than one institution; irregular dates and identifiers",
    ],
  },
  {
    key: "verification",
    title: "Issuing-authority verification",
    summary:
      "Checks documents against the authority that issued them and records the source, timestamp and result for every check.",
    points: [
      "Signed QR payloads verified with the issuer's Ed25519 public key",
      "Registry-style lookups by reference number through a pluggable adapter layer",
      "Six explicit outcome states; inconclusive results go to manual review",
      "Sources can be toggled and monitored by the administrator",
    ],
  },
  {
    key: "compliance",
    title: "Regulatory & infrastructure compliance assistance",
    summary:
      "Evaluates declared values and evidence against configurable norms drawn from the Approval Process Handbook, and reviews infrastructure photographs.",
    points: [
      "Faculty-student ratio, cadre ratio, land and built-up area thresholds, TER payment",
      "Computer-vision review of classroom, lab, library and accessibility photographs",
      "Image quality, EXIF capture date and location checks",
      "Advisory only: discrepancies suggest where physical inspection may be needed",
    ],
  },
  {
    key: "dashboard",
    title: "Decision-support dashboard & audit trail",
    summary:
      "Gives scrutiny officers and regional directors one queue with risk, alerts and evidence, and records every action in a tamper-evident log.",
    points: [
      "Region-scoped queues with compliance score, risk band and open findings",
      "Alerts for critical findings, source failures and status changes",
      "Hash-chained audit log of rules applied, records checked, source responses and actions",
      "Final decision by the competent authority, always with a written note",
    ],
  },
] as const;

export const SAFEGUARDS = [
  {
    title: "Human in the loop",
    body: "Every finding is marked advisory. The system never approves, rejects or issues letters on its own; only a Regional Director records a final decision, with a mandatory note, and approval is blocked while any critical finding lacks an officer disposition.",
  },
  {
    title: "Role-based access",
    body: "Four roles — institution, scrutiny officer, regional director, administrator. Institutions see only their own applications; officers see their region. Scoping is enforced on the server for every request.",
  },
  {
    title: "Tamper-evident audit chain",
    body: "Each audit event stores the hash of the previous one. Any edit to history breaks the chain, and the administrator can verify the full chain from the console.",
  },
  {
    title: "Explainable, evidence-backed flags",
    body: "A finding always carries the rule ID, the clause it relates to, and evidence: a document excerpt and page, a record value, a source response or an image region.",
  },
  {
    title: "Configurable without code",
    body: "Checklists, rules, thresholds, severities and verification sources live in versioned configuration that administrators edit. Every change bumps the ruleset version and is audited.",
  },
  {
    title: "Data protection",
    body: "Faculty PANs are held and shown masked, files are served only through access-checked endpoints, logins and every change are logged, and no document leaves the deployment: all AI runs locally on CPU.",
  },
] as const;

export const PIPELINE_STEPS = [
  { short: "Application", label: "Application", detail: "Category, academic year and declared values" },
  { short: "Checklist", label: "Checklist", detail: "Applicable documents and clauses for the category" },
  { short: "Read", label: "OCR · classify · extract", detail: "Text, document type and key fields with confidence" },
  { short: "Forensics", label: "Forensics", detail: "ELA, metadata, duplicates, irregular dates" },
  { short: "Verify", label: "Issuing-authority verification", detail: "Signed QR, registry lookup, six-state outcome" },
  { short: "Rules", label: "Rule engine", detail: "Configurable checks, scores and findings" },
  { short: "Review", label: "Officer review", detail: "Evidence, observations, rectification requests" },
  { short: "Decision", label: "Decision", detail: "Recorded by the competent authority with a note" },
] as const;

export const TECH_STACK = [
  { group: "Frontend", items: ["React 18", "TypeScript", "Vite", "Tailwind CSS", "shadcn/ui", "TanStack Query"] },
  { group: "Backend", items: ["Python 3.11", "FastAPI", "Pydantic v2", "SQLAlchemy 2", "JWT (HS256)"] },
  { group: "Document AI", items: ["PyMuPDF text layer", "RapidOCR (ONNX, CPU)", "Rule-based classifier & extractors", "OpenCV detectors (YOLOv8n optional)"] },
  { group: "Forensics & trust", items: ["Error Level Analysis (Pillow)", "PDF/EXIF metadata", "SHA-256 + perceptual hash", "Ed25519 signatures"] },
  { group: "Reporting & audit", items: ["ReportLab PDF", "Hash-chained audit log", "YAML rule & checklist config"] },
] as const;

export const FAQ = [
  {
    q: "Does VeriSense approve or reject applications?",
    a: "No. It prepares a structured preliminary scrutiny: checklist status, findings with evidence, verification outcomes and scores. Officers review and act on it, and only a Regional Director records a final decision, with a mandatory note that is written to the audit trail.",
  },
  {
    q: "Is a forensic flag proof that a document is forged?",
    a: "No. Error level analysis, metadata and duplicate checks produce preliminary indicators. They say where to look and why, and the officer decides whether the concern is real. The interface labels every such output as advisory.",
  },
  {
    q: "Are the issuing-authority checks connected to real government systems?",
    a: "Not in this prototype. The issuers are simulated services with their own signing keys and records, accessed through the same adapter interface a real integration would use. Connecting to DigiLocker, NBA, state fire services or municipal portals requires authorisation from those bodies; the adapter layer is built so each can be added without changing the rule engine.",
  },
  {
    q: "How do rules change when the Approval Process Handbook is revised?",
    a: "Rules and checklists are stored as versioned configuration. An administrator can enable or disable a rule, change its threshold or severity, or edit a category checklist from the console. Each change creates a new ruleset version, and every validation report records the version it was run against.",
  },
  {
    q: "Are the handbook clause references official?",
    a: "Clause references in the prototype are illustrative and configurable. They show how each finding is tied to a regulatory basis; the actual numbering would be filled in by AICTE when the rules are adopted.",
  },
  {
    q: "What happens when a source is down?",
    a: "The check is recorded as Source unavailable with the timestamp, nothing is assumed about the document, and the item can be retried or verified manually. It is never silently marked as passed.",
  },
  {
    q: "What data does the demo use?",
    a: "Entirely synthetic institutions, people and documents generated for this submission, including deliberately tampered variants. No real institution's data is used.",
  },
] as const;
