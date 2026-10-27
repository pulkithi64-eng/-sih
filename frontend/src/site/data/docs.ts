// In-site documentation content. Mirrors docs/USER_GUIDE.md and docs/DEMO_SCRIPT.md.

export const DEMO_USERS = [
  { username: "inst.piat", role: "Institution", scope: "Own applications (PIAT)" },
  { username: "inst.apex", role: "Institution", scope: "Own applications (Apex)" },
  { username: "officer.wro", role: "Scrutiny officer", scope: "Western region" },
  { username: "officer.nro", role: "Scrutiny officer", scope: "Northern region" },
  { username: "rd.wro", role: "Regional director", scope: "Western region, final decisions" },
  { username: "admin", role: "Administrator", scope: "Rules, checklists, sources, full audit" },
];

export type RoleGuide = { id: string; role: string; intro: string; steps: { t: string; b: string }[] };

export const ROLE_GUIDES: RoleGuide[] = [
  {
    id: "guide-institution",
    role: "Institution",
    intro: "The institution's nodal officer prepares the application, uploads documents and responds to deficiencies.",
    steps: [
      { t: "Create an application", b: "Open New application, choose the category and fill in the application details: programmes and intake, faculty and students, land and building, fee and accreditation. The required documents for that category appear immediately." },
      { t: "Upload documents", b: "Upload each file against a required document, or under Other documents and let VeriSense detect the type. Live processing results show the detected type, extracted fields and verification state within seconds." },
      { t: "Run self-check", b: "Validate the draft before submitting to see missing, expired or inconsistent items while they can still be fixed." },
      { t: "Submit to AICTE", b: "Submission runs full validation, assigns a scrutiny officer and moves the application into the regional queue." },
      { t: "Respond to findings", b: "When AICTE requests rectification, upload corrected documents and use Mark rectified (or Acknowledge) on each listed finding with a note." },
    ],
  },
  {
    id: "guide-officer",
    role: "Scrutiny officer",
    intro: "The scrutiny officer works through the region's queue, verifies findings against evidence and recommends an outcome.",
    steps: [
      { t: "Prioritise from the dashboard", b: "The queue shows each application's compliance score, risk band and open critical findings. Alerts highlight new critical issues and source failures." },
      { t: "Review the application", b: "Work through the tabs: Overview (checklist and institutional records), Documents (viewer, extracted fields, forensics and ELA), Verification, Infrastructure, Report and Audit trail." },
      { t: "Work the findings", b: "For each finding, check the cited evidence, then Acknowledge, Dismiss (a reason is required) or Escalate. Re-run source verification where a source was unavailable." },
      { t: "Request rectification", b: "Select the findings the institution must address and send a rectification request with instructions; Add observation records any other remark in the audit trail." },
      { t: "Record recommendation", b: "Recommend an outcome to the Regional Director with a note. Approval cannot be recommended while a critical finding is still open. Download the report PDF for the file." },
    ],
  },
  {
    id: "guide-director",
    role: "Regional director",
    intro: "The Regional Director is the competent authority for the decision in the prototype.",
    steps: [
      { t: "Review the recommendation", b: "See the officer's recommendation and notes alongside the findings and evidence." },
      { t: "Record decision", b: "Choose approve for EoA, issue deficiency letter, order inspection or reject. A written note is mandatory and is stored in the audit chain; approval is blocked while any critical finding is open." },
    ],
  },
  {
    id: "guide-admin",
    role: "Administrator",
    intro: "The administrator (AICTE IT or Regulation Bureau) maintains the rules, checklists and sources, and oversees the audit log.",
    steps: [
      { t: "Rules & checklists", b: "Enable or disable rules, edit thresholds and severity, and edit the required documents per category. Each change creates a new ruleset version." },
            { t: "Verification sources", b: "See each issuing-authority source with its latency and success rate, and switch a source off to simulate an outage or maintenance." },
      { t: "Audit log", b: "Browse every event and verify the hash chain to confirm no event has been altered since it was written." },
    ],
  },
];

export const DEMO_SCRIPT = [
  { time: "0:00-0:45", title: "Context", user: "website", body: "Landing page: the problem, five modules and the human-in-the-loop principle. Show the PS mapping page briefly." },
  { time: "0:45-2:00", title: "Institution uploads and pre-checks", user: "inst.piat", body: "Open the PIAT Extension of Approval application, show the checklist, upload a document and watch it get classified and read. Run the pre-check." },
  { time: "2:00-3:45", title: "Officer reviews evidence", user: "officer.wro", body: "From the dashboard open the PIAT application: expired Fire NOC with the cited page, faculty-ratio finding against records, verification states with source and timestamp." },
  { time: "3:45-5:00", title: "Forgery indicators", user: "officer.wro", body: "Open the Apex application: ELA heatmap and metadata on the land document, duplicate faculty across institutions, mismatch between QR payload and printed values." },
  { time: "5:00-6:00", title: "Rectification and decision", user: "officer.wro, rd.wro", body: "Request rectification on PIAT; as Regional Director record a decision with a note. Show that the officer cannot make a final decision." },
  { time: "6:00-7:00", title: "Configurability and audit", user: "admin", body: "Change a threshold, re-run validation and see the ruleset version change. Toggle a source off to show Source unavailable. Verify the audit chain." },
];

export const REFERENCE_DOCS = [
  { file: "ARCHITECTURE.md", title: "Architecture", body: "Components, sequence diagram and data model." },
  { file: "HOW_IT_WORKS.md", title: "How it works", body: "Pipeline, each check, verification states and scoring." },
  { file: "API.md", title: "API reference", body: "Every endpoint with role, request and response." },
  { file: "RULES_AND_CHECKLISTS.md", title: "Rules and checklists", body: "Configuring rules.yaml and checklists.yaml." },
  { file: "VERIFICATION_SOURCES.md", title: "Verification sources", body: "Adapter model and how real sources plug in." },
  { file: "SECURITY_AND_SAFEGUARDS.md", title: "Security and safeguards", body: "RBAC matrix, audit chain, data protection." },
  { file: "USER_GUIDE.md", title: "User guide", body: "Step-by-step guide for each role." },
  { file: "DEMO_SCRIPT.md", title: "Demo script", body: "The seven-minute evaluator walkthrough." },
  { file: "PS_MAPPING.md", title: "PS mapping", body: "Requirement-by-requirement mapping to features." },
  { file: "EVALUATION.md", title: "Evaluation", body: "Methodology and results per criterion." },
];
