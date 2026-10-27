import type {
  Alert,
  Application,
  ApplicationDetail,
  AuditEvent,
  AuditVerifyResult,
  Checklists,
  ChecklistItem,
  CrossVerificationResult,
  DashboardSummary,
  DocumentT,
  Finding,
  FindingStatus,
  Id,
  Institution,
  InstitutionOverviewStats,
  InstitutionalRecords,
  Meta,
  ProcessingSummary,
  Rule,
  Source,
  User,
  ValidationReport,
} from "./types";

const TOKEN_KEY = "verisense.token";
const USER_KEY = "verisense.user";
export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";
export const UNAUTHORIZED_EVENT = "verisense:unauthorized";

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export const session = {
  getToken: () => safeGet(TOKEN_KEY),
  getUser: (): User | null => {
    const raw = safeGet(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  },
  set(token: string, user: User) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch {
      /* storage unavailable */
    }
  },
  setUser(user: User) {
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch {
      /* ignore */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch {
      /* ignore */
    }
  },
};

export class ApiError extends Error {
  status: number;
  requestId?: string;
  constructor(status: number, message: string, requestId?: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
    this.requestId = requestId;
  }
}

function detailToMessage(detail: unknown, status: number): string {
  if (!detail) return `Request failed (${status})`;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => (d?.msg ? `${Array.isArray(d.loc) ? d.loc.slice(1).join(".") + ": " : ""}${d.msg}` : JSON.stringify(d)))
      .join("; ");
  }
  return JSON.stringify(detail);
}

interface RequestOpts {
  method?: string;
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
  raw?: boolean;
}

async function rawRequest(path: string, opts: RequestOpts = {}): Promise<Response> {
  const requestId = Array.from(crypto.getRandomValues(new Uint8Array(16)), (n) => n.toString(16).padStart(2, "0")).join("");
  const headers: Record<string, string> = { Accept: "application/json", "X-Request-ID": requestId };
  const token = session.getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { method: opts.method ?? "GET", headers, body, signal: opts.signal });
  } catch (e) {
    if ((e as Error)?.name === "AbortError") throw e;
    throw new ApiError(0, "Cannot reach the VeriSense service. Check that the backend is running.");
  }
  if (res.status === 401 && !path.startsWith("/auth/login")) {
    session.clear();
    window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
  }
  if (!res.ok) {
    let detail: unknown;
    try {
      const j = await res.json();
      detail = j?.detail ?? j;
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(res.status, detailToMessage(detail, res.status), res.headers.get("X-Request-ID") ?? undefined);
  }
  return res;
}

export async function request<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const res = await rawRequest(path, opts);
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

export async function requestBlob(path: string, signal?: AbortSignal): Promise<Blob> {
  const res = await rawRequest(path, { signal });
  return res.blob();
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== "ALL") p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : "";
}

export interface ApplicationFilters {
  status?: string;
  category?: string;
  region?: string;
  q?: string;
  riskBand?: string;
}

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),
  login: (username: string, password: string) =>
    request<{ accessToken: string; user: User; tokenType?: string }>("/auth/login", {
      method: "POST",
      body: { username, password },
    }),
  me: () => request<User>("/auth/me"),
  meta: () => request<Meta>("/meta"),
  dashboard: () => request<DashboardSummary>("/dashboard/summary"),

  applications: (f: ApplicationFilters = {}, signal?: AbortSignal) => request<Application[]>(`/applications${qs({ ...f })}`, { signal }),
  application: (id: Id, signal?: AbortSignal) => request<ApplicationDetail>(`/applications/${id}`, { signal }),
  createApplication: (body: { category: string; academicYear: string; formData: Record<string, unknown> }) =>
    request<Application>("/applications", { method: "POST", body }),
  updateApplication: (id: Id, formData: Record<string, unknown>) =>
    request<Application>(`/applications/${id}`, { method: "PATCH", body: { formData } }),
  uploadDocument: (id: Id, file: File, docType?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (docType) form.append("docType", docType);
    return request<DocumentT>(`/applications/${id}/documents`, { method: "POST", form });
  },
  deleteDocument: (docId: Id) => request<void>(`/documents/${docId}`, { method: "DELETE" }),
  documentText: (docId: Id) => request<{ text: string; blocks: any[] }>(`/documents/${docId}/text`),
  verifyDocument: (docId: Id) => request<DocumentT>(`/documents/${docId}/verify`, { method: "POST" }),
  submit: (id: Id) => request<ValidationReport>(`/applications/${id}/submit`, { method: "POST" }),
  validate: (id: Id) => request<ValidationReport>(`/applications/${id}/validate`, { method: "POST" }),
  report: (id: Id, signal?: AbortSignal) => request<ValidationReport>(`/applications/${id}/report`, { signal }),
  updateFinding: (fid: Id, status: FindingStatus, note: string) =>
    request<Finding>(`/findings/${fid}`, { method: "PATCH", body: { status, note } }),
  addObservation: (id: Id, note: string) =>
    request<AuditEvent>(`/applications/${id}/observations`, { method: "POST", body: { note } }),
  requestRectification: (id: Id, note: string, findingIds: Id[]) =>
    request<Application>(`/applications/${id}/request-rectification`, { method: "POST", body: { note, findingIds } }),
  decide: (id: Id, action: string, note: string) =>
    request<Application>(`/applications/${id}/decision`, { method: "POST", body: { action, note } }),

  alerts: (unread?: boolean) => request<Alert[]>(`/alerts${qs({ unread: unread ? "true" : undefined })}`),
  readAlert: (aid: Id) => request<unknown>(`/alerts/${aid}/read`, { method: "POST" }),

  audit: (p: { entityId?: string; action?: string; limit?: number } = {}) => request<AuditEvent[]>(`/audit${qs(p)}`),
  verifyAudit: () => request<AuditVerifyResult>("/audit/verify"),

  rules: () => request<Rule[]>("/rules"),
  updateRule: (id: string, body: { enabled?: boolean; params?: Record<string, unknown>; severity?: string }) =>
    request<Rule>(`/rules/${encodeURIComponent(id)}`, { method: "PUT", body }),
  checklists: () => request<Checklists>("/checklists"),
  updateChecklist: (category: string, items: ChecklistItem[]) =>
    request<unknown>(`/checklists/${category}`, { method: "PUT", body: items }),
  sources: () => request<Source[]>("/sources"),
  toggleSource: (id: string) => request<Source>(`/sources/${encodeURIComponent(id)}/toggle`, { method: "POST" }),
  
  // Institutions Management
  institutions: (p: { region?: string; type?: string; q?: string } = {}) =>
    request<Institution[]>(`/institutions${qs(p)}`),
  institution: (id: Id) => request<Institution>(`/institutions/${id}`),
  institutionOverview: () => request<InstitutionOverviewStats>("/institutions/overview/stats"),
  institutionStats: (id: Id) => request<any>(`/institutions/${id}/stats`),
  institutionApplications: (id: Id) => request<Application[]>(`/institutions/${id}/applications`),
  createInstitution: (body: any) => request<Institution>("/institutions", { method: "POST", body }),
  updateInstitution: (id: Id, body: any) => request<Institution>(`/institutions/${id}`, { method: "PATCH", body }),
  records: (institutionId: Id) => request<InstitutionalRecords>(`/institutions/${institutionId}/records`),

  // Cross Documentation Verification & Processing Summary
  crossVerification: (appId: Id) => request<CrossVerificationResult>(`/applications/${appId}/cross-verification`),
  processingSummary: (appId: Id) => request<ProcessingSummary>(`/applications/${appId}/processing-summary`),

  // Auth & Session Management
  refreshSession: () => request<{ accessToken: string; tokenType: string; user: User }>("/auth/refresh", { method: "POST" }),
  sessionStatus: () => request<{ authenticated: boolean; user: User; remainingSeconds: number; role: string }>("/auth/session"),
  changePassword: (oldPassword: string, newPassword: string) =>
    request<{ status: string; message: string }>("/auth/change-password", { method: "POST", body: { oldPassword, newPassword } }),

  // Reliability Health Probes
  healthLive: () => request<{ status: string; timestamp: string }>("/health/live"),
  healthReady: () => request<{ ready: boolean; version: string; checks: Record<string, string>; timestamp: string }>("/health/ready"),
  healthSystem: () => request<any>("/health/system"),
};

export async function downloadBlob(path: string, filename: string) {
  const blob = await requestBlob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = Array.from(filename.replace(/[\\/:*?"<>|]/g, "_"), (ch) => ch.charCodeAt(0) < 32 ? "_" : ch).join("");
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e ?? "Unknown error");
}
