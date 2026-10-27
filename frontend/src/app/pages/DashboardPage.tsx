import { Link } from "react-router-dom";
import { lazy, Suspense, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  ClipboardCheck,
  CloudOff,
  FileStack,
  Hourglass,
  ScanEye,
  Timer,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AdvisoryNote, AdvisoryTag } from "@/components/common/AdvisoryNote";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { KpiCard } from "@/components/common/KpiCard";
import { PageHeader } from "@/components/common/PageHeader";
import { ScoreBar } from "@/components/common/ScoreBar";
import { RiskBandPill, SEVERITY_CHART_COLOR, SeverityBadge, severityDot } from "@/components/common/SeverityBadge";
import { StatusBadge, VERIFICATION_CHART_COLOR, getStatusDef } from "@/components/common/StatusBadge";
import { useAlerts, useApplications, useDashboard } from "@/lib/hooks";
import { fmtNumber, fmtRelative } from "@/lib/format";
import { CATEGORY_SHORT, categoryLabel, REGION_LABEL, SEVERITY_ORDER, VERIFICATION_STATES } from "@/lib/labels";
import type { Application } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useAuth } from "../auth";
const HBarChart = lazy(() => import("../components/charts").then(module => ({ default: module.HBarChart })));
const StackedDistribution = lazy(() => import("../components/charts").then(module => ({ default: module.StackedDistribution })));
import { Panel } from "../components/Panel";
import { PageSkeleton, TableSkeleton } from "../components/Skeletons";

const INTERVENTION_STATUSES = new Set([
  "DEFICIENCIES_FLAGGED",
  "SOURCE_VERIFICATION_PENDING",
  "UNDER_REVIEW",
  "SUBMITTED",
  "UNDER_VALIDATION",
  "INSPECTION_ORDERED",
]);

function interventionScore(a: Application) {
  const c = a.counts ?? ({} as Application["counts"]);
  return (c.critical ?? 0) * 100 + (c.major ?? 0) * 10 + (a.riskScore ?? 0);
}

function fmtDuration(sec: number | null | undefined) {
  if (!sec && sec !== 0) return "—";
  if (sec < 60) return `${sec.toFixed(1)} s`;
  return `${(sec / 60).toFixed(1)} min`;
}

export default function DashboardPage() {
  const [metricsOpen, setMetricsOpen] = useState(false);
  const { user } = useAuth();
  const dash = useDashboard();
  const apps = useApplications({});
  const alerts = useAlerts();

  if (dash.isLoading) return <PageSkeleton />;
  if (dash.isError) return <ErrorState error={dash.error} onRetry={() => dash.refetch()} />;
  const d = dash.data!;
  const t = d.totals ?? ({} as typeof d.totals);

  const verData = VERIFICATION_STATES.map((s) => ({
    key: s,
    label: getStatusDef(s, "verification").label,
    value: d.byVerification?.[s] ?? 0,
    color: VERIFICATION_CHART_COLOR[s],
  }));
  const sevData = SEVERITY_ORDER.map((s) => ({
    key: s,
    label: s.charAt(0) + s.slice(1).toLowerCase(),
    value: d.findingsBySeverity?.[s] ?? 0,
    color: SEVERITY_CHART_COLOR[s],
  }));
  const catData = Object.entries(d.byCategory ?? {})
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ key: k, label: CATEGORY_SHORT[k as keyof typeof CATEGORY_SHORT] ?? categoryLabel(k), value: v }))
    .sort((a, b) => b.value - a.value);
  const statusData = Object.entries(d.byStatus ?? {})
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ key: k, label: getStatusDef(k, "application").label, value: v }))
    .sort((a, b) => b.value - a.value);

  const queue = (apps.data ?? [])
    .filter((a) => INTERVENTION_STATUSES.has(a.status) && ((a.counts?.critical ?? 0) > 0 || (a.counts?.major ?? 0) > 0 || a.riskBand === "HIGH" || a.status === "SOURCE_VERIFICATION_PENDING"))
    .sort((a, b) => interventionScore(b) - interventionScore(a))
    .slice(0, 8);

  const recentAlerts = [...(alerts.data ?? [])].sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt)).slice(0, 6);

  return (
    <div>
      <PageHeader
        eyebrow={user?.region ? REGION_LABEL[user.region] ?? user.region : "All regions"}
        title="Review overview"
        description="A summary of applications in your region. Open the review queue to work on a case."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/portal/applications">
              All applications <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <KpiCard label="Applications" value={fmtNumber(t.applications)} icon={FileStack} to="/portal/applications" />
        <KpiCard label="Pending validation" value={fmtNumber(t.pendingValidation)} icon={Hourglass} tone="info" to="/portal/applications?status=SUBMITTED" />
        <KpiCard label="Deficiencies flagged" value={fmtNumber(t.deficiencies)} icon={AlertTriangle} tone="danger" to="/portal/applications?status=DEFICIENCIES_FLAGGED" />
        <KpiCard
          label="Source verification pending"
          value={fmtNumber(t.sourcePending)}
          icon={CloudOff}
          tone="warning"
          to="/portal/applications?status=SOURCE_VERIFICATION_PENDING"
        />
        <KpiCard label="Inspection ordered" value={fmtNumber(t.inspection)} icon={ScanEye} to="/portal/applications?status=INSPECTION_ORDERED" />
        <KpiCard label="Manual effort saved" value={`${fmtNumber(d.manualEffortSavedHours, 1)} h`} icon={ClipboardCheck} tone="success" hint="Estimated, vs manual scrutiny" />
        <KpiCard label="Avg. validation time" value={fmtDuration(d.avgValidationSeconds)} icon={Timer} hint="Per application run" />
      </div>

      <details className="mt-6 rounded-lg border bg-card p-4" onToggle={(event) => setMetricsOpen(event.currentTarget.open)}>
        <summary className="cursor-pointer text-sm font-medium">Detailed metrics and distributions</summary>
      {metricsOpen && <Suspense fallback={<PageSkeleton />}><div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel
          title="Document verification status"
          description="Documents grouped by their recorded verification outcome"
          actions={<span className="text-xs text-muted-foreground">{verData.reduce((s, x) => s + x.value, 0)} documents</span>}
        >
          <StackedDistribution data={verData} />
        </Panel>
        <Panel title="Findings by severity" description="Automated findings across applications (advisory)">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {sevData.map((s) => (
              <div key={s.key} className="rounded-md border px-3 py-2.5">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="h-2 w-2 rounded-sm" style={{ background: s.color }} aria-hidden /> {s.label}
                </div>
                <div className="tabular mt-1 text-xl font-semibold">{s.value}</div>
              </div>
            ))}
          </div>
          <div className="mt-4">
            <HBarChart data={sevData} height={150} />
          </div>
        </Panel>
        <Panel title="Applications by category">
          {catData.length ? <HBarChart data={catData} /> : <EmptyState compact title="No applications yet" />}
        </Panel>
        <Panel title="Applications by status">
          {statusData.length ? <HBarChart data={statusData} color="#0B2E59" /> : <EmptyState compact title="No applications yet" />}
        </Panel>
      </div>

      </Suspense>}
      </details>
      <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Panel
          title="Needs official intervention"
          description="Prioritised by critical and major findings, then risk score"
          flush
          actions={<AdvisoryTag />}
        >
          {apps.isLoading ? (
            <TableSkeleton rows={5} cols={5} />
          ) : apps.isError ? (
            <ErrorState error={apps.error} onRetry={() => apps.refetch()} />
          ) : queue.length === 0 ? (
            <EmptyState compact title="Nothing waiting" description="No applications currently need intervention." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Application</TableHead>
                  <TableHead className="hidden md:table-cell">Status</TableHead>
                  <TableHead className="w-32">Compliance</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead className="text-right">Crit / Major</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {queue.map((a) => (
                  <TableRow key={a.id} className="cursor-pointer">
                    <TableCell className="max-w-[280px]">
                      <Link to={`/portal/applications/${a.id}`} className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        <span className="block truncate font-medium text-foreground hover:underline">{a.institution?.name}</span>
                        <span className="mono block truncate text-xs text-muted-foreground">
                          {a.applicationNo} · {CATEGORY_SHORT[a.category] ?? a.category}
                        </span>
                      </Link>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <StatusBadge status={a.status} kind="application" />
                    </TableCell>
                    <TableCell>
                      <ScoreBar value={a.complianceScore} />
                    </TableCell>
                    <TableCell>
                      <RiskBandPill band={a.riskBand} />
                    </TableCell>
                    <TableCell className="tabular text-right">
                      <span className={cn("font-semibold", (a.counts?.critical ?? 0) > 0 ? "text-red-700" : "text-muted-foreground")}>
                        {a.counts?.critical ?? 0}
                      </span>
                      <span className="text-muted-foreground"> / </span>
                      <span className={cn((a.counts?.major ?? 0) > 0 ? "text-orange-700" : "text-muted-foreground")}>{a.counts?.major ?? 0}</span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Panel>

        <Panel
          title="Recent alerts"
          flush
          actions={
            <Link to="/portal/alerts" className="text-xs font-medium text-primary-600 hover:underline">
              View all
            </Link>
          }
        >
          {alerts.isLoading ? (
            <TableSkeleton rows={4} cols={1} />
          ) : alerts.isError ? (
            <ErrorState error={alerts.error} onRetry={() => alerts.refetch()} />
          ) : recentAlerts.length === 0 ? (
            <EmptyState compact title="No alerts" />
          ) : (
            <ul className="divide-y">
              {recentAlerts.map((a) => (
                <li key={a.id}>
                  <Link to={`/portal/applications/${a.applicationId}`} className="flex gap-2.5 px-4 py-3 hover:bg-muted/50">
                    <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", severityDot(a.severity))} aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className={cn("block text-sm leading-snug", !a.read && "font-medium")}>{a.message}</span>
                      <span className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <SeverityBadge severity={a.severity} />
                        <span className="mono truncate">{a.applicationNo}</span>
                        <span className="ml-auto whitespace-nowrap">{fmtRelative(a.createdAt)}</span>
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <AdvisoryNote className="mt-6">
        Scores, risk bands and findings are generated by configurable rules and document analysis. They prioritise work; final decisions
        rest with the competent authority.
      </AdvisoryNote>
    </div>
  );
}
