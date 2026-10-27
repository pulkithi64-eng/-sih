// Types mirroring docs/CONTRACT.md section 3 (camelCase JSON).

export type Role = "INSTITUTION" | "SCRUTINY_OFFICER" | "REGIONAL_DIRECTOR" | "ADMIN";
export type Region = "NR" | "WR" | "SR" | "ER" | "CR" | "SWR" | "SER" | "NWR";
export type Id = string | number;

export type ApplicationCategory =
  | "EOA"
  | "NEW_INSTITUTION"
  | "INTAKE_INCREASE"
  | "NEW_COURSE"
  | "CHANGE_OF_NAME"
  | "CHANGE_OF_SITE"
  | "CLOSURE";

export type ApplicationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_VALIDATION"
  | "DEFICIENCIES_FLAGGED"
  | "RECTIFICATION_REQUESTED"
  | "SOURCE_VERIFICATION_PENDING"
  | "UNDER_REVIEW"
  | "INSPECTION_ORDERED"
  | "RECOMMENDED"
  | "DECIDED";

export type VerificationStatus =
  | "VERIFIED"
  | "MISMATCH_DETECTED"
  | "EXPIRED"
  | "VERIFICATION_PENDING"
  | "SOURCE_UNAVAILABLE"
  | "MANUAL_REVIEW_REQUIRED"
  | "NOT_APPLICABLE";

export type FindingKind =
  | "MISSING_DOCUMENT"
  | "MISSING_FIELD"
  | "EXPIRED_DOCUMENT"
  | "INCONSISTENCY"
  | "RECORD_MISMATCH"
  | "ANOMALY"
  | "DUPLICATE"
  | "VERIFICATION"
  | "COMPLIANCE_GAP"
  | "INFRASTRUCTURE";

export type Severity = "CRITICAL" | "MAJOR" | "MINOR" | "INFO";
export type FindingStatus = "OPEN" | "ACKNOWLEDGED" | "RECTIFIED" | "DISMISSED" | "ESCALATED";
export type RiskBand = "LOW" | "MEDIUM" | "HIGH";
export type ChecklistStatus = "PRESENT" | "MISSING" | "EXPIRED" | "INVALID" | "NOT_REQUIRED";
export type VerificationMethod = "API" | "QR_SIGNATURE" | "DIGILOCKER" | "PORTAL" | "MANUAL";

export type DecisionAction = string;

export interface User {
  id: Id;
  username: string;
  fullName: string;
  role: Role;
  region?: Region | string | null;
  institutionId?: Id | null;
}

export interface Institution {
  id: Id;
  permanentId: string;
  name: string;
  type: string;
  state: string;
  city: string;
  region: Region | string;
  establishedYear: number;
  trustName: string;
  address: string;
  campusGps?: { lat: number; lng: number } | null;
  stats?: {
    applicationsCount: number;
    latestStatus: string;
    latestAcademicYear?: string | null;
    latestAppId?: Id | null;
    openFindings: number;
    averageCompliance: number;
    riskBand: RiskBand;
    programmesCount: number;
    totalIntake: number;
    facultyCount: number;
    naacGrade?: string | null;
    landAreaAcres?: number | null;
  };
}

export interface InstitutionOverviewStats {
  totalInstitutions: number;
  totalApplications: number;
  totalApprovedProgrammes: number;
  totalSanctionedIntake: number;
  totalRecordedFaculty: number;
  highRiskInstitutions: number;
  byRegion: Record<string, number>;
  byType: Record<string, number>;
}

export interface CrossVerificationDocRef {
  docId: Id;
  docType: string;
  docTypeLabel: string;
  fileName: string;
  value: string | number;
  status: "MATCH" | "PARTIAL_MATCH" | "MISMATCH";
  similarity?: number;
  diffPct?: number;
  page?: number;
}

export interface CrossVerificationField {
  field: string;
  label: string;
  status: "MATCH" | "PARTIAL_MATCH" | "MISMATCH";
  referenceValue: string;
  documents: CrossVerificationDocRef[];
}

export interface CrossVerificationDiscrepancy {
  id: string;
  field: string;
  fieldLabel: string;
  severity: Severity;
  docA: { id: Id; type: string; fileName: string; value: string };
  docB: { id: Id; type: string; fileName: string; value: string };
  description: string;
  clause?: string;
  similarity?: number;
  diff?: number;
}

export interface CrossVerificationResult {
  applicationId: Id;
  applicationNo: string;
  overallScore: number;
  status: "CONSISTENT" | "DISCREPANCIES_FLAGGED" | "CRITICAL_CONFLICT";
  totalDocumentsAnalyzed: number;
  fieldsChecked: CrossVerificationField[];
  discrepancies: CrossVerificationDiscrepancy[];
  discrepanciesCount: number;
  criticalCount: number;
  majorCount: number;
}

export interface ProcessingSummary {
  applicationId: Id;
  applicationNo: string;
  category: ApplicationCategory;
  academicYear: string;
  status: ApplicationStatus;
  region: string;
  institution: {
    id: Id;
    name: string;
    permanentId: string;
    city: string;
    state: string;
  };
  scores: {
    complianceScore: number;
    riskScore: number;
    riskBand: RiskBand;
    crossDocScore: number;
  };
  processingMetrics: {
    totalDocuments: number;
    ocrCompleted: number;
    qrVerified: number;
    verified: number;
    mismatch: number;
    pending: number;
    manualReview: number;
    forensicFlagsCount: number;
    highElaCount: number;
    totalProcessingTimeMs: number;
  };
  issuingAuthorityBreakdown: {
    documentId: Id;
    docType: string;
    fileName: string;
    status: VerificationStatus;
    source: string;
    method: string;
    checkedAt?: string | null;
  }[];
  crossVerificationSummary: {
    score: number;
    status: string;
    fieldsAnalyzed: number;
    discrepanciesCount: number;
    criticalCount: number;
  };
  findingsDigest: {
    totalActive: number;
    critical: Finding[];
    major: Finding[];
    minor: Finding[];
  };
  advisoryRecommendation: {
    recommendedAction: string;
    title: string;
    reason: string;
  };
  lastValidatedAt?: string | null;
  generatedAt: string;
}

export interface InstitutionalRecords {
  previousApprovals: { year: string; status: string; letterRef: string; date: string }[];
  approvedProgrammes: { level: string; programme: string; course: string; shift: string; intake: number }[];
  faculty: {
    facultyId: string;
    name: string;
    panMasked: string;
    designation: string;
    qualification: string;
    department: string;
    joiningDate: string;
  }[];
  accreditations: { body: string; programme?: string | null; grade?: string | null; validFrom: string; validTo: string; ref: string }[];
  landAndBuilding: { landAreaAcres: number; builtUpAreaSqm: number; ownership: string; registryRef: string };
  terPayments: { year: string; amount: number; txnId: string; status: string; paidOn?: string | null }[];
  deficiencyHistory: { year: string; item: string; status: string }[];
  affidavits: { year: string; type: string; ref: string; notarisedOn: string }[];
}

export interface ChecklistItem {
  docType: string;
  label: string;
  mandatory: boolean;
  clause?: string | null;
  status?: ChecklistStatus;
  documentId?: Id | null;
  conditions?: unknown;
}

export interface Decision {
  action: DecisionAction;
  note: string;
  decidedBy: string;
  decidedAt: string;
}

export interface AppCounts {
  documents: number;
  findingsOpen: number;
  critical: number;
  major: number;
  minor: number;
  verified: number;
  pending: number;
}

export interface Application {
  id: Id;
  applicationNo: string;
  institutionId: Id;
  institution: Institution;
  category: ApplicationCategory;
  academicYear: string;
  status: ApplicationStatus;
  submittedAt?: string | null;
  updatedAt: string;
  region: Region | string;
  assignedOfficer?: string | null;
  formData: Record<string, any>;
  complianceScore: number;
  riskScore: number;
  riskBand: RiskBand;
  checklist: ChecklistItem[];
  counts: AppCounts;
  lastValidatedAt?: string | null;
  decision?: Decision | null;
}

export interface ExtractedField {
  value: any;
  confidence: number;
  sourceText?: string | null;
  page?: number | null;
}

export interface FieldComparison {
  field: string;
  submitted: any;
  source: any;
  match: boolean;
}

export interface ForensicFlag {
  code: string;
  severity: Severity | string;
  reason: string;
  evidence?: any;
}

export interface Detection {
  label: string;
  conf: number;
  bbox: number[];
}

export interface InfraResult {
  evidenceType: string;
  detections: Detection[];
  counts: Record<string, number>;
  quality: Record<string, any>;
  exif: Record<string, any>;
  flags: (ForensicFlag | string)[];
  [k: string]: any;
}

export interface Verification {
  status: VerificationStatus;
  source?: string | null;
  method?: VerificationMethod | string | null;
  checkedAt?: string | null;
  responseSummary?: string | null;
  comparisons?: FieldComparison[] | null;
  reason?: string | null;
}

export interface DocumentT {
  id: Id;
  applicationId: Id;
  docType: string;
  docTypeLabel: string;
  fileName: string;
  mimeType: string;
  sizeBytes: number;
  sha256: string;
  uploadedAt: string;
  uploadedBy: string;
  classification: { docType: string; confidence: number; signals: string[] };
  ocr: { method: string; confidence: number; pageCount: number; textPreview: string };
  extractedFields: Record<string, ExtractedField>;
  issuer?: string | null;
  referenceNo?: string | null;
  issueDate?: string | null;
  expiryDate?: string | null;
  verification: Verification;
  forensics: {
    elaScore?: number | null;
    hasElaHeatmap: boolean;
    metadata: Record<string, any>;
    flags: ForensicFlag[];
    [k: string]: any;
  };
  infra?: InfraResult | null;
}

export type EvidenceType = "DOCUMENT" | "FIELD" | "RECORD" | "SOURCE_RESPONSE" | "IMAGE_REGION" | "METADATA" | "RULE";

export interface Evidence {
  type: EvidenceType | string;
  label: string;
  documentId?: Id | null;
  page?: number | null;
  bbox?: number[] | null;
  excerpt?: string | null;
  submitted?: any;
  reference?: any;
}

export interface Finding {
  id: Id;
  applicationId: Id;
  documentId?: Id | null;
  kind: FindingKind;
  severity: Severity;
  title: string;
  reason: string;
  ruleId?: string | null;
  clause?: string | null;
  evidence: Evidence[];
  status: FindingStatus;
  createdAt: string;
  updatedAt: string;
  reviewerNote?: string | null;
  advisory: boolean;
}

export interface ApplicationDetail extends Application {
  documents: DocumentT[];
  findings: Finding[];
  records: InstitutionalRecords | null;
}

export interface Alert {
  id: Id;
  applicationId: Id;
  applicationNo: string;
  type: string;
  severity: Severity;
  message: string;
  createdAt: string;
  read: boolean;
}

export interface AuditEvent {
  id: Id;
  ts: string;
  actor: string;
  actorRole: string;
  action: string;
  entityType: string;
  entityId: string;
  details: any;
  prevHash: string;
  hash: string;
}

export interface Rule {
  id: string;
  name: string;
  description: string;
  categories: string[];
  type: string;
  params: Record<string, any>;
  severity: Severity;
  clause: string;
  enabled: boolean;
  version: number | string;
}

export interface Source {
  id: string;
  name: string;
  issuer: string;
  docTypes: string[];
  method: VerificationMethod | string;
  online: boolean;
  lastLatencyMs?: number | null;
  successRate?: number | null;
}

export interface ValidationReport {
  applicationId: Id;
  generatedAt: string;
  rulesetVersion: string | number;
  summary: Partial<AppCounts> & { complianceScore: number; riskScore: number; riskBand: RiskBand; [k: string]: any };
  checklist: ChecklistItem[];
  findings: Finding[];
  verifications: { documentId: Id; docType: string; status: VerificationStatus; source?: string | null; checkedAt?: string | null }[];
  rulesApplied: { ruleId: string; result: "PASS" | "FAIL" | "SKIPPED"; detail?: string | null }[];
}

export interface Meta {
  categories: { id: ApplicationCategory; label: string }[];
  docTypes: { id: string; label: string; issuer?: string; validityMonths?: number | null; verifiable?: boolean }[];
  statuses: string[];
  verificationStatuses: string[];
}

export interface DashboardSummary {
  totals: {
    applications: number;
    pendingValidation: number;
    deficiencies: number;
    sourcePending: number;
    inspection: number;
    recommended: number;
  };
  byStatus: Record<string, number>;
  byVerification: Record<string, number>;
  byCategory: Record<string, number>;
  findingsBySeverity: Record<string, number>;
  recent: Application[];
  avgValidationSeconds: number;
  manualEffortSavedHours: number;
}

export type Checklists = Record<string, ChecklistItem[]>;

export interface AuditVerifyResult {
  valid: boolean;
  checked: number;
  brokenAt?: Id | null;
}
