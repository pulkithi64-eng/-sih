import { CloudOff, Radio, RadioTower } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { useMeta, useSources, useToggleSource } from "@/lib/hooks";
import { fmtNumber } from "@/lib/format";
import { humanize, METHOD_LABEL } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { isAdmin, useAuth } from "../auth";
import { CardSkeleton } from "../components/Skeletons";

export default function SourcesPage() {
  const { user } = useAuth();
  const admin = isAdmin(user?.role);
  const q = useSources();
  const meta = useMeta();
  const toggle = useToggleSource();
  const label = (id: string) => meta.data?.docTypes?.find((d) => d.id === id)?.label ?? humanize(id);
  const sources = q.data ?? [];
  const online = sources.filter((s) => s.online).length;

  return (
    <div>
      <PageHeader
        title="Verification sources"
        description="Issuing-authority services used to verify documents at source. In this prototype they are simulated services; administrators can simulate an outage to demonstrate graceful degradation."
        actions={
          sources.length > 0 && (
            <span className="rounded-md border bg-card px-2.5 py-1 text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">{online}</span> of {sources.length} online
            </span>
          )
        }
      />
      {q.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} />
      ) : sources.length === 0 ? (
        <EmptyState icon={RadioTower} title="No sources configured" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sources.map((s) => (
            <article key={s.id} className={cn("card-surface flex flex-col", !s.online && "border-slate-300 bg-slate-50")}>
              <div className="flex items-start gap-3 p-4">
                <span
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-md",
                    s.online ? "bg-green-50 text-green-700" : "bg-slate-200 text-slate-600",
                  )}
                >
                  {s.online ? <Radio className="h-4 w-4" /> : <CloudOff className="h-4 w-4" />}
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="text-sm font-semibold leading-snug">{s.name}</h2>
                  <p className="text-xs text-muted-foreground">{s.issuer}</p>
                </div>
                <span
                  className={cn(
                    "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
                    s.online ? "border-green-200 bg-green-50 text-green-800" : "border-slate-300 bg-slate-100 text-slate-700",
                  )}
                >
                  <span className={cn("h-1.5 w-1.5 rounded-full", s.online ? "bg-green-600" : "bg-slate-500")} />
                  {s.online ? "Online" : "Offline"}
                </span>
              </div>
              <dl className="grid grid-cols-3 gap-2 border-t px-4 py-3 text-xs">
                <div>
                  <dt className="kv-label">Method</dt>
                  <dd className="mt-0.5 font-medium">{METHOD_LABEL[s.method] ?? s.method}</dd>
                </div>
                <div>
                  <dt className="kv-label">Latency</dt>
                  <dd className="tabular mt-0.5 font-medium">{s.lastLatencyMs !== null && s.lastLatencyMs !== undefined ? `${fmtNumber(s.lastLatencyMs)} ms` : "—"}</dd>
                </div>
                <div>
                  <dt className="kv-label">Success</dt>
                  <dd className="tabular mt-0.5 font-medium">
                    {s.successRate !== null && s.successRate !== undefined ? `${Math.round(s.successRate <= 1 ? s.successRate * 100 : s.successRate)}%` : "—"}
                  </dd>
                </div>
              </dl>
              <div className="flex-1 border-t px-4 py-3">
                <p className="kv-label mb-1.5">Document types</p>
                <div className="flex flex-wrap gap-1">
                  {s.docTypes.map((d) => (
                    <span key={d} className="rounded border bg-background px-1.5 py-0.5 text-2xs text-muted-foreground">
                      {label(d)}
                    </span>
                  ))}
                </div>
              </div>
              {admin && (
                <label className="flex items-center justify-between gap-3 border-t bg-slate-50/70 px-4 py-2.5 text-sm">
                  <span>
                    <span className="block font-medium">Service available</span>
                    <span className="block text-xs text-muted-foreground">Turn off to simulate an outage</span>
                  </span>
                  <Switch checked={s.online} disabled={toggle.isPending} onCheckedChange={() => toggle.mutate(s.id)} aria-label={`Toggle ${s.name}`} />
                </label>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
