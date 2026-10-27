import { useState } from "react";
import { CheckCircle2, CircleMinus, FileDown, Loader2, ScrollText, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AdvisoryNote } from "@/components/common/AdvisoryNote";
import { EmptyState } from "@/components/common/EmptyState";
import { ScoreRing } from "@/components/common/ScoreBar";
import { RiskBandPill, SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ApiError, downloadBlob, errorMessage } from "@/lib/api";
import { useReport, useValidate } from "@/lib/hooks";
import { fmtDateTime } from "@/lib/format";
import { categoryLabel, FINDING_KIND_LABEL, humanize, SEVERITY_ORDER } from "@/lib/labels";
import type { ApplicationDetail, Id } from "@/lib/types";
import { cn } from "@/lib/utils";
import { isOfficerPlus, useAuth } from "../../auth";
import { PageSkeleton } from "../../components/Skeletons";

export default function ReportTab({ app, onOpenDocument }: { app: ApplicationDetail; onOpenDocument: (id: Id) => void }) {
  const { user } = useAuth();
  const q = useReport(app.id);
  const validate = useValidate(app.id);
  const [busy, setBusy] = useState(false);
  const [ruleFilter, setRuleFilter] = useState<"ALL" | "FAIL">("FAIL");

  async function pdf() {
    setBusy(true);
    try {
      await downloadBlob(`/applications/${app.id}/report.pdf`, `VeriSense_${app.applicationNo}_report.pdf`);
    } catch (e) {
      toast.error("Could not download PDF", { description: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  if (q.isLoading) return <PageSkeleton />;
  if (q.isError && !(q.error instanceof ApiError && q.error.status === 404))
    return <EmptyState icon={ScrollText} title="Could not load report" description={errorMessage(q.error)}
      action={<Button onClick={() => q.refetch()} disabled={q.isFetching}>Retry</Button>} />;
  if (q.isError || !q.data)
    return (
      <EmptyState
        icon={ScrollText}
        title="No validation report yet"
        description="A report is generated each time validation runs."
        action={
          isOfficerPlus(user?.role) && app.status !== "DECIDED" ? (
            <Button size="sm" onClick={() => validate.mutate()} disabled={validate.isPending}>
              {validate.isPending && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />} Run validation
            </Button>
          ) : undefined
        }
      />
    );

  const r = q.data;
  const s = r.summary ?? ({} as typeof r.summary);
  const findings = [...(r.findings ?? [])].sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity));
  const rules = (r.rulesApplied ?? []).filter((x) => ruleFilter === "ALL" || x.result === "FAIL");
  const pass = (r.rulesApplied ?? []).filter((x) => x.result === "PASS").length;
  const fail = (r.rulesApplied ?? []).filter((x) => x.result === "FAIL").length;
  const skip = (r.rulesApplied ?? []).filter((x) => x.result === "SKIPPED").length;
  const docs = new Map((app.documents ?? []).map((d) => [String(d.id), d]));

  return (
    <div className="mx-auto max-w-5xl">
      <article className="card-surface overflow-hidden">
        <header className="flex flex-col gap-4 border-b bg-navy px-6 py-5 text-white sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-2xs font-semibold uppercase tracking-[0.18em] text-saffron">Validation report · advisory</p>
            <h2 className="mt-1 text-lg font-semibold">{app.institution?.name}</h2>
            <p className="mt-1 text-sm text-white/75">
              <span className="mono">{app.applicationNo}</span> · {categoryLabel(app.category)} · AY {app.academicYear}
            </p>
            <p className="mt-1 text-xs text-white/60">
              Generated {fmtDateTime(r.generatedAt)} · Ruleset v{String(r.rulesetVersion)}
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={pdf} disabled={busy} className="shrink-0">
            {busy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <FileDown className="mr-1.5 h-4 w-4" />}
            Download PDF
          </Button>
        </header>

        <div className="grid gap-4 border-b p-6 sm:grid-cols-2 lg:grid-cols-4">
          <ScoreRing value={s.complianceScore ?? 0} label="Compliance score" />
          <ScoreRing value={s.riskScore ?? 0} label="Risk score" invert />
          <div>
            <p className="kv-label">Risk band</p>
            <RiskBandPill band={s.riskBand} className="mt-1.5" />
          </div>
          <div>
            <p className="kv-label">Findings</p>
            <p className="mt-1 text-sm">
              <span className="font-semibold text-red-700">{s.critical ?? 0}</span> critical ·{" "}
              <span className="font-semibold text-orange-700">{s.major ?? 0}</span> major · <span className="font-semibold">{s.minor ?? 0}</span> minor
            </p>
          </div>
        </div>

        <div className="space-y-6 p-6">
          <AdvisoryNote>
            This report is produced by automated rules and document analysis. It supports, and does not replace, the judgement of the
            scrutiny committee.
          </AdvisoryNote>

          <ReportSection title="1. Document checklist">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Document</TableHead>
                  <TableHead>Mandatory</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(r.checklist ?? []).map((c) => (
                  <TableRow key={c.docType}>
                    <TableCell>
                      <span className="font-medium">{c.label}</span>
                      {c.clause && <span className="block text-xs text-muted-foreground">{c.clause}</span>}
                    </TableCell>
                    <TableCell className="text-sm">{c.mandatory ? "Yes" : "No"}</TableCell>
                    <TableCell>
                      <StatusBadge status={c.status ?? "MISSING"} kind="checklist" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ReportSection>

          <ReportSection title={`2. Findings (${findings.length})`}>
            {findings.length === 0 ? (
              <p className="text-sm text-muted-foreground">No findings.</p>
            ) : (
              <ol className="divide-y rounded-md border">
                {findings.map((f, i) => (
                  <li key={f.id} className="flex gap-3 px-3 py-2.5">
                    <span className="tabular w-6 shrink-0 text-xs text-muted-foreground">{i + 1}.</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <SeverityBadge severity={f.severity} />
                        <span className="text-xs text-muted-foreground">{FINDING_KIND_LABEL[f.kind] ?? humanize(f.kind)}</span>
                        <StatusBadge status={f.status} kind="finding" className="ml-auto" />
                      </div>
                      <p className="mt-1 text-sm font-medium">{f.title}</p>
                      <p className="text-sm text-foreground/80">{f.reason}</p>
                      {f.clause && <p className="mt-0.5 text-xs text-muted-foreground">{f.clause}</p>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </ReportSection>

          <ReportSection title="3. Source verification">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Document</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead className="hidden sm:table-cell">Source</TableHead>
                  <TableHead className="hidden md:table-cell">Checked</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(r.verifications ?? []).map((v) => (
                  <TableRow key={String(v.documentId)}>
                    <TableCell>
                      <button type="button" className="text-left font-medium hover:underline" onClick={() => onOpenDocument(v.documentId)}>
                        {docs.get(String(v.documentId))?.docTypeLabel ?? humanize(v.docType)}
                      </button>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={v.status} kind="verification" />
                    </TableCell>
                    <TableCell className="hidden text-sm sm:table-cell">{v.source || "—"}</TableCell>
                    <TableCell className="hidden text-xs text-muted-foreground md:table-cell">{fmtDateTime(v.checkedAt)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ReportSection>

          <ReportSection
            title="4. Rules applied"
            right={
              <div className="flex items-center gap-3 text-xs">
                <span className="text-green-700">{pass} pass</span>
                <span className="text-red-700">{fail} fail</span>
                <span className="text-muted-foreground">{skip} skipped</span>
                <button
                  type="button"
                  className="font-medium text-primary-600 hover:underline"
                  onClick={() => setRuleFilter((f) => (f === "ALL" ? "FAIL" : "ALL"))}
                >
                  {ruleFilter === "ALL" ? "Show failures only" : "Show all"}
                </button>
              </div>
            }
          >
            <ul className="divide-y rounded-md border">
              {rules.map((x, i) => (
                <li key={`${x.ruleId}-${i}`} className="flex items-start gap-2.5 px-3 py-2">
                  {x.result === "PASS" ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-700" aria-label="Pass" />
                  ) : x.result === "FAIL" ? (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-700" aria-label="Fail" />
                  ) : (
                    <CircleMinus className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-label="Skipped" />
                  )}
                  <div className="min-w-0">
                    <span className="mono text-xs font-medium">{x.ruleId}</span>
                    {x.detail && <p className={cn("text-sm", x.result === "SKIPPED" ? "text-muted-foreground" : "text-foreground/85")}>{x.detail}</p>}
                  </div>
                </li>
              ))}
              {rules.length === 0 && <li className="px-3 py-3 text-sm text-muted-foreground">No rules in this view.</li>}
            </ul>
          </ReportSection>
        </div>
        <footer className="border-t bg-slate-50 px-6 py-3 text-xs text-muted-foreground">
          Generated by VeriSense · Prototype built for AICTE · SIH 2026 · PS 26261. Clause references are illustrative and configurable.
        </footer>
      </article>
    </div>
  );
}

function ReportSection({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <section>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-navy">{title}</h3>
        {right}
      </div>
      <div className="overflow-hidden rounded-md">{children}</div>
    </section>
  );
}

