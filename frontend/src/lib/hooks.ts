import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errorMessage, requestBlob, type ApplicationFilters } from "./api";
import type { ChecklistItem, FindingStatus, Id } from "./types";

export const qk = {
  meta: ["meta"] as const,
  dashboard: ["dashboard"] as const,
  applications: (f: ApplicationFilters = {}) => ["applications", f] as const,
  application: (id: Id) => ["application", String(id)] as const,
  report: (id: Id) => ["report", String(id)] as const,
  crossVerification: (id: Id) => ["cross-verification", String(id)] as const,
  processingSummary: (id: Id) => ["processing-summary", String(id)] as const,
  institutions: (p: object = {}) => ["institutions", p] as const,
  institution: (id: Id) => ["institution", String(id)] as const,
  institutionOverview: ["institution-overview"] as const,
  institutionStats: (id: Id) => ["institution-stats", String(id)] as const,
  alerts: ["alerts"] as const,
  audit: (p: object) => ["audit", p] as const,
  rules: ["rules"] as const,
  checklists: ["checklists"] as const,
  sources: ["sources"] as const,
  text: (id: Id) => ["doc-text", String(id)] as const,
};

export const useMeta = () => useQuery({ queryKey: qk.meta, queryFn: api.meta, staleTime: 10 * 60_000 });
export const useDashboard = () => useQuery({ queryKey: qk.dashboard, queryFn: api.dashboard });
export const useApplications = (f: ApplicationFilters = {}, enabled = true) =>
  useQuery({ queryKey: qk.applications(f), queryFn: ({ signal }) => api.applications(f, signal), enabled });
export const useApplication = (id: Id | undefined) =>
  useQuery({ queryKey: qk.application(id ?? ""), queryFn: ({ signal }) => api.application(id!, signal), enabled: !!id });
export const useReport = (id: Id | undefined, enabled = true) =>
  useQuery({ queryKey: qk.report(id ?? ""), queryFn: ({ signal }) => api.report(id!, signal), enabled: !!id && enabled, retry: false });
export const useAlerts = (enabled = true) =>
  useQuery({ queryKey: qk.alerts, queryFn: () => api.alerts(), staleTime: 30_000, refetchInterval: 30_000, enabled });
export const useAudit = (p: { entityId?: string; action?: string; limit?: number }, enabled = true) =>
  useQuery({ queryKey: qk.audit(p), queryFn: () => api.audit(p), enabled });
export const useRules = () => useQuery({ queryKey: qk.rules, queryFn: api.rules });
export const useChecklists = () => useQuery({ queryKey: qk.checklists, queryFn: api.checklists, staleTime: 5 * 60_000 });
export const useSources = (enabled = true) => useQuery({ queryKey: qk.sources, queryFn: api.sources, enabled });
export const useDocText = (id: Id | undefined, enabled: boolean) =>
  useQuery({ queryKey: qk.text(id ?? ""), queryFn: () => api.documentText(id!), enabled: !!id && enabled });

export const useInstitutions = (p: { region?: string; type?: string; q?: string } = {}) =>
  useQuery({ queryKey: qk.institutions(p), queryFn: () => api.institutions(p) });
export const useInstitution = (id: Id | undefined) =>
  useQuery({ queryKey: qk.institution(id ?? ""), queryFn: () => api.institution(id!), enabled: !!id });
export const useInstitutionOverview = () =>
  useQuery({ queryKey: qk.institutionOverview, queryFn: api.institutionOverview });
export const useInstitutionStats = (id: Id | undefined) =>
  useQuery({ queryKey: qk.institutionStats(id ?? ""), queryFn: () => api.institutionStats(id!), enabled: !!id });

export const useCrossVerification = (appId: Id | undefined) =>
  useQuery({ queryKey: qk.crossVerification(appId ?? ""), queryFn: () => api.crossVerification(appId!), enabled: !!appId });
export const useProcessingSummary = (appId: Id | undefined) =>
  useQuery({ queryKey: qk.processingSummary(appId ?? ""), queryFn: () => api.processingSummary(appId!), enabled: !!appId });

export function useCreateInstitution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: any) => api.createInstitution(body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["institutions"] });
      qc.invalidateQueries({ queryKey: qk.institutionOverview });
      toast.success("Institution registered successfully", { description: `${data.name} (${data.permanentId})` });
    },
    onError: onErr("Could not create institution"),
  });
}

export function useUpdateInstitution(id: Id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: any) => api.updateInstitution(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["institutions"] });
      qc.invalidateQueries({ queryKey: qk.institution(id) });
      toast.success("Institution profile updated");
    },
    onError: onErr("Could not update institution"),
  });
}

/** Invalidate everything that depends on an application's state. */
export function useInvalidateApp() {
  const qc = useQueryClient();
  return (id?: Id) => {
    if (id !== undefined) {
      qc.invalidateQueries({ queryKey: qk.application(id) });
      qc.invalidateQueries({ queryKey: qk.report(id) });
      qc.invalidateQueries({ queryKey: qk.processingSummary(id) });
      qc.invalidateQueries({ queryKey: qk.crossVerification(id) });
    }
    qc.invalidateQueries({ queryKey: ["applications"] });
    qc.invalidateQueries({ queryKey: qk.dashboard });
    qc.invalidateQueries({ queryKey: qk.alerts });
    qc.invalidateQueries({ queryKey: ["audit"] });
    qc.invalidateQueries({ queryKey: ["institutions"] });
    qc.invalidateQueries({ queryKey: qk.institutionOverview });
  };
}

function onErr(prefix: string) {
  return (e: unknown) => toast.error(prefix, { description: errorMessage(e) });
}

export function useValidate(id: Id) {
  const inv = useInvalidateApp();
  return useMutation({
    mutationFn: () => api.validate(id),
    onSuccess: (r) => {
      inv(id);
      toast.success("Validation completed", {
        description: `Compliance score ${Math.round(r?.summary?.complianceScore ?? 0)} · ${r?.findings?.length ?? 0} findings`,
      });
    },
    onError: onErr("Validation failed"),
  });
}

export function useUpdateFinding(appId: Id) {
  const inv = useInvalidateApp();
  return useMutation({
    mutationFn: (v: { id: Id; status: FindingStatus; note: string }) => api.updateFinding(v.id, v.status, v.note),
    onSuccess: (f) => {
      inv(appId);
      toast.success(`Finding marked ${String(f?.status ?? "").toLowerCase()}`);
    },
    onError: onErr("Could not update finding"),
  });
}

export function useVerifyDocument(appId: Id) {
  const inv = useInvalidateApp();
  return useMutation({
    mutationFn: (docId: Id) => api.verifyDocument(docId),
    onSuccess: (d) => {
      inv(appId);
      toast.success("Source verification re-run", { description: `${d?.docTypeLabel ?? "Document"}: ${d?.verification?.status ?? ""}` });
    },
    onError: onErr("Verification failed"),
  });
}

export function useObservation(appId: Id) {
  const inv = useInvalidateApp();
  return useMutation({
    mutationFn: (note: string) => api.addObservation(appId, note),
    onSuccess: () => {
      inv(appId);
      toast.success("Observation recorded in audit trail");
    },
    onError: onErr("Could not add observation"),
  });
}

export function useRectification(appId: Id) {
  const inv = useInvalidateApp();
  return useMutation({
    mutationFn: (v: { note: string; findingIds: Id[] }) => api.requestRectification(appId, v.note, v.findingIds),
    onSuccess: () => {
      inv(appId);
      toast.success("Rectification requested from institution");
    },
    onError: onErr("Could not request rectification"),
  });
}

export function useDecision(appId: Id) {
  const inv = useInvalidateApp();
  return useMutation({
    mutationFn: (v: { action: string; note: string }) => api.decide(appId, v.action, v.note),
    onSuccess: () => {
      inv(appId);
      toast.success("Decision recorded");
    },
    onError: onErr("Could not record decision"),
  });
}

export function useMarkAlertRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: Id) => api.readAlert(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.alerts }),
  });
}

export function useUpdateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; body: { enabled?: boolean; params?: Record<string, unknown>; severity?: string } }) =>
      api.updateRule(v.id, v.body),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: qk.rules });
      toast.success("Rule updated", { description: `${r?.id ?? ""} · ruleset version bumped` });
    },
    onError: onErr("Could not update rule"),
  });
}

export function useUpdateChecklist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { category: string; items: ChecklistItem[] }) => api.updateChecklist(v.category, v.items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.checklists });
      toast.success("Checklist saved");
    },
    onError: onErr("Could not save checklist"),
  });
}

export function useToggleSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.toggleSource(id),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: qk.sources });
      toast.success(`${s?.name ?? "Source"} is now ${s?.online ? "online" : "offline (simulated outage)"}`);
    },
    onError: onErr("Could not toggle source"),
  });
}

/** Fetch an authenticated binary endpoint and expose it as an object URL. */
export function useBlobUrl(path: string | null) {
  const [state, setState] = useState<{ url: string | null; loading: boolean; error: string | null; type: string | null }>({
    url: null,
    loading: !!path,
    error: null,
    type: null,
  });
  useEffect(() => {
    if (!path) {
      setState({ url: null, loading: false, error: null, type: null });
      return;
    }
    const ctrl = new AbortController();
    let url: string | null = null;
    setState({ url: null, loading: true, error: null, type: null });
    requestBlob(path, ctrl.signal)
      .then((b) => {
        url = URL.createObjectURL(b);
        setState({ url, loading: false, error: null, type: b.type });
      })
      .catch((e) => {
        if ((e as Error)?.name === "AbortError") return;
        setState({ url: null, loading: false, error: errorMessage(e), type: null });
      });
    return () => {
      ctrl.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [path]);
  return state;
}
