// Demo scenarios seeded into the portal. Synced with samples/scenarios.json.

export type Scenario = {
  key: string;
  category: string;
  login: string;
  institution: string;
  title: string;
  description: string;
  expect: string[];
};

export const SCENARIOS: Scenario[] = [
  {
    key: "piat-eoa-2027",
    category: "Extension of Approval",
    login: "officer.wro",
    institution: "Pragati Institute of Advanced Technology (WR)",
    title: "Deficiencies hidden in a routine renewal",
    description: "A normal-looking EoA bundle whose problems only show up when every page is read and cross-checked.",
    expect: [
      "Fire NOC expired 10 Oct 2026, 16 days before scrutiny",
      "Faculty declared 52, roster lists 47, AICTE records 49",
      "Faculty-student ratio 25.5 against a limit of 20",
      "TER payment pending settlement; lab photo shows 38 of 40 terminals",
    ],
  },
  {
    key: "apex-intake-2027",
    category: "Increase in intake",
    login: "officer.nro",
    institution: "Apex Valley Institute of Technology & Management (NR)",
    title: "Altered land deed and borrowed evidence",
    description: "A high-risk intake increase that exercises the forensic, signature and duplicate checks.",
    expect: [
      "Land deed edited in an image editor: survey 118/2 to 148/2, 5.20 to 12.50 acres",
      "NBA QR signed for a different, expired programme; building-plan QR signature fails",
      "Three faculty PANs also on another institution's roster",
      "Classroom photo identical to another college's, geo-tagged about 900 km away",
    ],
  },
  {
    key: "nvie-eoa-2027",
    category: "Extension of Approval",
    login: "officer.wro",
    institution: "Narmada Valley Institute of Engineering (WR)",
    title: "Clean application",
    description: "Every document present, current and verified at source — the baseline that shows the system does not over-flag.",
    expect: [
      "Issuer-signed QR codes valid; authority records match",
      "Faculty records consistent; ratio within 1:20",
      "High compliance, low risk; only the affidavit routed to manual review",
    ],
  },
  {
    key: "nvie-newcourse-2027",
    category: "New course",
    login: "officer.wro",
    institution: "Narmada Valley Institute of Engineering (WR)",
    title: "When sources do not answer",
    description: "Issuing-authority edge cases that must be recorded honestly rather than passed or failed.",
    expect: [
      "State NOC issuer down: Source unavailable",
      "University consent queued: Verification pending",
      "Corpus FDR and floor plan: Manual review required",
      "Application held at Source verification pending",
    ],
  },
  {
    key: "piat-name-change-2027",
    category: "Change of name",
    login: "officer.wro",
    institution: "Pragati Institute of Advanced Technology (WR)",
    title: "Genuine document, wrong name",
    description: "Every document verifies, but one genuinely issued NOC names a different proposed institution name.",
    expect: [
      "State NOC QR valid, yet proposed name differs from the application",
      "Cross-document inconsistency raised for the officer",
    ],
  },
  {
    key: "apex-eoa-2027-draft",
    category: "Extension of Approval (draft)",
    login: "inst.apex",
    institution: "Apex Valley Institute of Technology & Management (NR)",
    title: "Self-check before submission",
    description: "The institution's view: a half-finished draft checked before it reaches AICTE.",
    expect: [
      "Five mandatory documents still missing",
      "Occupancy certificate uploaded as a building plan — classifier disagrees",
      "NAAC accreditation expired March 2025",
    ],
  },
];
