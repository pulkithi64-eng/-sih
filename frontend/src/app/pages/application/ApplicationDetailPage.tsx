import { lazy, Suspense, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  Building2,
  CalendarDays,
  ClipboardList,
  FileCheck2,
  FileDown,
  FileText,
  Gavel,
  History,
  ImageIcon,
  Loader2,
  MapPin,
  MessageSquarePlus,
  PenLine,
  RefreshCw,
  Scale,
  ScrollText,
  ShieldCheck,
  Undo2,
  AlertTriangle,
  Send,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { AdvisoryTag } from "@/components/common/AdvisoryNote";
import { ErrorState } from "@/components/common/EmptyState";
import { ScoreRing } from "@/components/common/ScoreBar";
import { RiskBandPill } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { downloadBlob, errorMessage } from "@/lib/api";
import { useApplication, useValidate } from "@/lib/hooks";
import { fmtDate, fmtDateTime } from "@/lib/format";
import { categoryLabel, DECISION_LABEL, REGION_LABEL } from "@/lib/labels";
import type { ApplicationDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EDITABLE_STATUSES, institutionNextAction } from "@/lib/journey";
import { canDecide, isInstitution, isOfficerPlus, isReviewer, useAuth } from "../../auth";
import { useSetCrumb } from "../../layout/crumbs";
import { PageSkeleton } from "../../components/Skeletons";
import { ContentBoundary } from "@/components/common/ContentBoundary";
import { DecisionDialog, ObservationDialog, RectificationDialog } from "./ActionDialogs";
const OverviewTab = lazy(() => import("./OverviewTab"));
const DocumentsTab = lazy(() => import("./DocumentsTab"));
const FindingsTab = lazy(() => import("./FindingsTab"));
const VerificationTab = lazy(() => import("./VerificationTab"));
const InfraTab = lazy(() => import("./InfraTab"));
const AuditTab = lazy(() => import("./AuditTab"));
const ReportTab = lazy(() => import("./ReportTab"));
const CrossVerificationTab = lazy(() => import("./CrossVerificationTab"));
const SummaryTab = lazy(() => import("./SummaryTab"));

const TABS = [
  { id: "overview", label: "Overview", icon: ClipboardList },
  { id: "summary", label: "Processing summary", icon: FileCheck2 },
  { id: "cross-verification", label: "Cross-record checks", icon: Scale },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "findings", label: "Findings", icon: AlertTriangle },
  { id: "verification", label: "Verification", icon: ShieldCheck },
  { id: "infrastructure", label: "Infrastructure", icon: ImageIcon },
  { id: "audit", label: "Audit trail", icon: History },
  { id: "report", label: "Report", icon: ScrollText },
] as const;

const PRIMARY_TABS = new Set(["overview", "documents", "findings", "report"]);

export default function ApplicationDetailPage() {
  const { id } = useParams();
  const q = useApplication(id);
  useSetCrumb(q.data?.applicationNo);
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("tab") ?? "overview";

  if (q.isLoading) return <PageSkeleton />;
  if (q.isError || !q.data) return <ErrorState error={q.error ?? "Application not found"} onRetry={() => q.refetch()} />;
  const app = q.data;

  const setTab = (t: string) => {
    const n = new URLSearchParams(sp);
    n.set("tab", t);
    if (t !== "documents") {
      n.delete("doc");
      n.delete("page");
    }
    setSp(n, { replace: true });
  };

  /** Jump to a document (optionally a page) from anywhere in the page. */
  const openDocument = (docId: string | number, page?: number | null) => {
    const n = new URLSearchParams(sp);
    n.set("tab", "documents");
    n.set("doc", String(docId));
    if (page) n.set("page", String(page));
    else n.delete("page");
    setSp(n);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const openFindings = (app.findings ?? []).filter((f) => ["OPEN", "ACKNOWLEDGED", "ESCALATED"].includes(f.status)).length;
  const infraCount = (app.documents ?? []).filter((d) => d.infra || d.docType.startsWith("INFRA_PHOTO")).length;

  return (
    <div>
      <Header app={app} />

      <Tabs value={tab} onValueChange={setTab} className="mt-5">
        <div className="-mx-4 flex items-start gap-2 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <TabsList className="h-auto w-max justify-start gap-1 rounded-none border-b bg-transparent p-0">
            {TABS.filter((t) => PRIMARY_TABS.has(t.id) || t.id === tab).map((t) => (
              <TabsTrigger
                key={t.id}
                value={t.id}
                className={cn(
                  "relative gap-1.5 rounded-none border-b-2 border-transparent px-3 pb-2.5 pt-2 text-sm font-medium text-muted-foreground",
                  "data-[state=active]:border-saffron data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none",
                )}
              >
                <t.icon className="h-4 w-4" aria-hidden />
                {t.label}
                {t.id === "findings" && openFindings > 0 && (
                  <span className="tabular rounded-full bg-red-100 px-1.5 text-2xs font-semibold leading-4 text-red-800">{openFindings}</span>
                )}
                {t.id === "documents" && (
                  <span className="tabular rounded-full bg-muted px-1.5 text-2xs font-semibold leading-4 text-muted-foreground">
                    {app.documents?.length ?? 0}
                  </span>
                )}
                {t.id === "infrastructure" && infraCount > 0 && (
                  <span className="tabular rounded-full bg-muted px-1.5 text-2xs font-semibold leading-4 text-muted-foreground">{infraCount}</span>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button size="sm" variant="ghost" className="shrink-0">More details</Button></DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Evidence and history</DropdownMenuLabel>
              {TABS.filter((item) => !PRIMARY_TABS.has(item.id)).map((item) => <DropdownMenuItem key={item.id} onSelect={() => setTab(item.id)}><item.icon className="mr-2 h-4 w-4" />{item.label}</DropdownMenuItem>)}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="mt-5">
          <ContentBoundary key={tab}><Suspense fallback={<PageSkeleton />}>
          <TabsContent value="overview" className="mt-0">
            <OverviewTab app={app} onOpenDocument={openDocument} />
          </TabsContent>
          <TabsContent value="summary" className="mt-0">
            <SummaryTab
              app={app}
              onOpenDocument={openDocument}
              onSelectTab={setTab}
            />
          </TabsContent>
          <TabsContent value="cross-verification" className="mt-0">
            <CrossVerificationTab app={app} onOpenDocument={openDocument} />
          </TabsContent>
          <TabsContent value="documents" className="mt-0">
            <DocumentsTab app={app} />
          </TabsContent>
          <TabsContent value="findings" className="mt-0">
            <FindingsTab app={app} onOpenDocument={openDocument} />
          </TabsContent>
          <TabsContent value="verification" className="mt-0">
            <VerificationTab app={app} onOpenDocument={openDocument} />
          </TabsContent>
          <TabsContent value="infrastructure" className="mt-0">
            <InfraTab app={app} onOpenDocument={openDocument} />
          </TabsContent>
          <TabsContent value="audit" className="mt-0">
            <AuditTab app={app} />
          </TabsContent>
          <TabsContent value="report" className="mt-0">
            <ReportTab app={app} onOpenDocument={openDocument} />
          </TabsContent>
          </Suspense></ContentBoundary>
        </div>
      </Tabs>
    </div>
  );
}

function Header({ app }: { app: ApplicationDetail }) {
  const { user } = useAuth();
  const role = user?.role;
  const validate = useValidate(app.id);
  const [dlg, setDlg] = useState<null | "obs" | "rect" | "decide" | "recommend">(null);
  const decided = app.status === "DECIDED";
  const canReview = !decided && app.status !== "DRAFT" && !!app.lastValidatedAt;
  const next = institutionNextAction(app);
  const unresolvedCritical = app.findings.filter((finding) => finding.severity === "CRITICAL" && !["RECTIFIED", "DISMISSED"].includes(finding.status)).length;

  return (
    <section className="card-surface overflow-hidden">
      <div className="p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="mono break-all text-xs text-muted-foreground">{app.applicationNo}</span>
          <StatusBadge status={app.status} kind="application" />
        </div>
        <h1 className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">{app.institution?.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{categoryLabel(app.category)} · {app.academicYear}</p>
        <dl className="mt-4 grid grid-cols-3 gap-3 border-y py-3 text-sm">
          <div><dt className="text-xs text-muted-foreground">Compliance</dt><dd className="mt-1 font-semibold">{app.lastValidatedAt ? `${Math.round(app.complianceScore)} / 100` : "Not checked"}</dd></div>
          <div><dt className="text-xs text-muted-foreground">Risk</dt><dd className="mt-1">{app.lastValidatedAt ? <RiskBandPill band={app.riskBand} /> : "Not checked"}</dd></div>
          <div><dt className="text-xs text-muted-foreground">Unresolved findings</dt><dd className="mt-1 font-semibold">{app.counts?.findingsOpen ?? 0}</dd></div>
        </dl>
        {unresolvedCritical > 0 && <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{unresolvedCritical} unresolved critical finding{unresolvedCritical === 1 ? "" : "s"}. Approval is blocked until a reviewer confirms resolution or dismisses each with a reason. <Link className="font-semibold underline" to={`?tab=findings`}>Review findings</Link></p>}
        {app.decision && <div className="mt-3 rounded-md border bg-muted/40 p-3 text-sm"><p className="font-semibold">{DECISION_LABEL[app.decision.action] ?? app.decision.action}</p><p className="mt-1">{app.decision.note}</p><p className="mt-1 text-xs text-muted-foreground">{app.decision.decidedBy} · {fmtDateTime(app.decision.decidedAt)}</p></div>}
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Application details</summary>
          <dl className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2"><div><dt className="inline font-medium">Permanent ID: </dt><dd className="inline">{app.institution?.permanentId}</dd></div><div><dt className="inline font-medium">Region: </dt><dd className="inline">{REGION_LABEL[app.region] ?? app.region}</dd></div><div><dt className="inline font-medium">Last checked: </dt><dd className="inline">{app.lastValidatedAt ? fmtDateTime(app.lastValidatedAt) : "Not checked"}</dd></div><div><dt className="inline font-medium">Assigned officer: </dt><dd className="inline">{app.assignedOfficer || "Not assigned"}</dd></div>{app.submittedAt && <div><dt className="inline font-medium">Submitted: </dt><dd className="inline">{fmtDate(app.submittedAt)}</dd></div>}</dl>
        </details>
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t px-4 py-3 sm:px-5">
        {isInstitution(role) && EDITABLE_STATUSES.has(app.status) && <Button asChild size="sm"><Link to={next.to}><FileText className="mr-2 h-4 w-4" />{next.label === "Continue application" ? "Upload documents" : next.label}</Link></Button>}
        {role === "SCRUTINY_OFFICER" && !decided && <Button size="sm" onClick={() => setDlg("recommend")} disabled={!canReview}><Gavel className="mr-2 h-4 w-4" />Record recommendation</Button>}
        {canDecide(role) && !decided && <Button size="sm" onClick={() => setDlg("decide")} disabled={!canReview}><Gavel className="mr-2 h-4 w-4" />Record decision</Button>}
        {app.lastValidatedAt && <Button asChild size="sm" variant="outline"><Link to="?tab=report">View report</Link></Button>}
        {(isReviewer(role) || isOfficerPlus(role) || (isInstitution(role) && EDITABLE_STATUSES.has(app.status))) && <DropdownMenu>
          <DropdownMenuTrigger asChild><Button size="sm" variant="ghost">More actions</Button></DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            {isInstitution(role) && EDITABLE_STATUSES.has(app.status) && <DropdownMenuItem asChild><Link to={`/portal/applications/${app.id}/edit?step=details`}>Edit application details</Link></DropdownMenuItem>}
            {isReviewer(role) && <><DropdownMenuItem disabled={decided || app.status === "DRAFT"} onSelect={() => setDlg("rect")}>Request corrections</DropdownMenuItem><DropdownMenuItem onSelect={() => setDlg("obs")}>Add review note</DropdownMenuItem></>}
            {isOfficerPlus(role) && <DropdownMenuItem disabled={validate.isPending || decided} onSelect={() => validate.mutate()}>{validate.isPending ? "Checking…" : "Run checks again"}</DropdownMenuItem>}
          </DropdownMenuContent>
        </DropdownMenu>}
        {!canReview && isReviewer(role) && !decided && <span className="text-xs text-muted-foreground">A submitted, checked application is required before review.</span>}
        <p className="w-full pt-1 text-xs text-muted-foreground">Decision support only. Issuer services and records in this prototype are simulated.</p>
      </div>
      {isReviewer(role) && <>
        <ObservationDialog app={app} open={dlg === "obs"} onOpenChange={(open) => setDlg(open ? "obs" : null)} />
        <RectificationDialog app={app} open={dlg === "rect"} onOpenChange={(open) => setDlg(open ? "rect" : null)} />
        <DecisionDialog app={app} mode={canDecide(role) ? "decide" : "recommend"} open={dlg === "decide" || dlg === "recommend"} onOpenChange={(open) => setDlg(open ? (canDecide(role) ? "decide" : "recommend") : null)} />
      </>}
    </section>
  );
}
