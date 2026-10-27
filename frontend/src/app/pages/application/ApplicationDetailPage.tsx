import { useState } from "react";
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
import { canDecide, isInstitution, isOfficerPlus, isReviewer, useAuth } from "../../auth";
import { useSetCrumb } from "../../layout/crumbs";
import { PageSkeleton } from "../../components/Skeletons";
import { DecisionDialog, ObservationDialog, RectificationDialog } from "./ActionDialogs";
import OverviewTab from "./OverviewTab";
import DocumentsTab from "./DocumentsTab";
import FindingsTab from "./FindingsTab";
import VerificationTab from "./VerificationTab";
import InfraTab from "./InfraTab";
import AuditTab from "./AuditTab";
import ReportTab from "./ReportTab";
import CrossVerificationTab from "./CrossVerificationTab";
import SummaryTab from "./SummaryTab";

const TABS = [
  { id: "overview", label: "Overview", icon: ClipboardList },
  { id: "summary", label: "Processing Summary", icon: FileCheck2 },
  { id: "cross-verification", label: "Cross-Doc Verification", icon: Scale },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "findings", label: "Findings", icon: AlertTriangle },
  { id: "verification", label: "Verification", icon: ShieldCheck },
  { id: "infrastructure", label: "Infrastructure", icon: ImageIcon },
  { id: "audit", label: "Audit trail", icon: History },
  { id: "report", label: "Report", icon: ScrollText },
] as const;

const EDITABLE = new Set(["DRAFT", "RECTIFICATION_REQUESTED"]);

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

  const openFindings = (app.findings ?? []).filter((f) => f.status === "OPEN" || f.status === "ESCALATED").length;
  const infraCount = (app.documents ?? []).filter((d) => d.infra || d.docType.startsWith("INFRA_PHOTO")).length;

  return (
    <div>
      <Header app={app} />

      <Tabs value={tab} onValueChange={setTab} className="mt-5">
        <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <TabsList className="h-auto w-max justify-start gap-1 rounded-none border-b bg-transparent p-0">
            {TABS.map((t) => (
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
        </div>
        <div className="mt-5">
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
  const [pdfBusy, setPdfBusy] = useState(false);
  const inst = app.institution;
  const decided = app.status === "DECIDED";
  const counts = app.counts ?? ({} as ApplicationDetail["counts"]);

  async function downloadPdf() {
    setPdfBusy(true);
    try {
      await downloadBlob(`/applications/${app.id}/report.pdf`, `VeriSense_${app.applicationNo}_report.pdf`);
    } catch (e) {
      toast.error("Could not download report", { description: errorMessage(e) });
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <section className="card-surface overflow-hidden">
      <div className="h-1 bg-navy" aria-hidden />
      <div className="flex flex-col gap-5 p-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="mono rounded bg-navy-50 px-1.5 py-0.5 text-xs font-medium text-navy">{app.applicationNo}</span>
            <StatusBadge status={app.status} kind="application" />
            <RiskBandPill band={app.riskBand} />
          </div>
          <h1 className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">{inst?.name}</h1>
          <dl className="mt-2 flex flex-wrap gap-x-5 gap-y-1.5 text-sm text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Building2 className="h-4 w-4" aria-hidden />
              <dt className="sr-only">Permanent ID</dt>
              <dd>
                Permanent ID <span className="mono text-foreground">{inst?.permanentId}</span>
              </dd>
            </div>
            <div className="flex items-center gap-1.5">
              <ClipboardList className="h-4 w-4" aria-hidden />
              <dt className="sr-only">Category</dt>
              <dd className="text-foreground">{categoryLabel(app.category)}</dd>
            </div>
            <div className="flex items-center gap-1.5">
              <CalendarDays className="h-4 w-4" aria-hidden />
              <dt className="sr-only">Academic year</dt>
              <dd>
                AY <span className="text-foreground">{app.academicYear}</span>
              </dd>
            </div>
            <div className="flex items-center gap-1.5">
              <MapPin className="h-4 w-4" aria-hidden />
              <dt className="sr-only">Location</dt>
              <dd>
                {inst?.city}, {inst?.state} · {REGION_LABEL[app.region] ?? app.region}
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-xs text-muted-foreground">
            {app.submittedAt ? <>Submitted {fmtDate(app.submittedAt)} · </> : null}
            Last validated {app.lastValidatedAt ? fmtDateTime(app.lastValidatedAt) : "never"}
            {app.assignedOfficer ? <> · Assigned to {app.assignedOfficer}</> : null}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <ScoreRing value={app.complianceScore ?? 0} label={<>Compliance<br />score</>} />
          <ScoreRing value={app.riskScore ?? 0} label={<>Risk<br />score</>} invert />
          <div className="grid grid-cols-3 gap-2 text-center">
            <Count n={counts.critical} label="Critical" tone="text-red-700" />
            <Count n={counts.major} label="Major" tone="text-orange-700" />
            <Count n={counts.minor} label="Minor" tone="text-amber-700" />
          </div>
          <AdvisoryTag className="self-start" />
        </div>
      </div>

      {app.decision && (
        <div className="border-t bg-navy-50/60 px-5 py-3 text-sm">
          <span className="font-semibold text-navy">{DECISION_LABEL[app.decision.action] ?? app.decision.action}</span>
          <span className="text-muted-foreground">
            {" "}
            · by {app.decision.decidedBy} on {fmtDateTime(app.decision.decidedAt)}
          </span>
          <p className="mt-1 text-foreground/90">“{app.decision.note}”</p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 border-t bg-slate-50/70 px-5 py-3">
        {isOfficerPlus(role) && (
          <Button size="sm" variant="outline" onClick={() => validate.mutate()} disabled={validate.isPending || decided}>
            {validate.isPending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-1.5 h-4 w-4" />}
            Re-run validation
          </Button>
        )}
        {isReviewer(role) && (
          <>
            <Button size="sm" variant="outline" onClick={() => setDlg("rect")} disabled={decided}>
              <Undo2 className="mr-1.5 h-4 w-4" /> Request rectification
            </Button>
            <Button size="sm" variant="outline" onClick={() => setDlg("obs")}>
              <MessageSquarePlus className="mr-1.5 h-4 w-4" /> Add observation
            </Button>
          </>
        )}
        {isInstitution(role) && EDITABLE.has(app.status) && (
          <Button size="sm" asChild>
            <Link to={`/portal/applications/${app.id}/edit`}>
              {app.status === "DRAFT" ? <PenLine className="mr-1.5 h-4 w-4" /> : <Send className="mr-1.5 h-4 w-4" />}
              {app.status === "DRAFT" ? "Continue application" : "Respond & resubmit"}
            </Link>
          </Button>
        )}
        <Button size="sm" variant="outline" asChild className="gap-1 text-xs">
          <Link to={`/portal/applications/${app.id}?tab=summary`}>
            <FileCheck2 className="h-3.5 w-3.5" />
            <span>Summary Digest</span>
          </Link>
        </Button>
        <Button size="sm" variant="ghost" onClick={downloadPdf} disabled={pdfBusy}>
          {pdfBusy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <FileDown className="mr-1.5 h-4 w-4" />}
          Report PDF
        </Button>
        <div className="ml-auto flex gap-2">
          {role === "SCRUTINY_OFFICER" && (
            <Button size="sm" onClick={() => setDlg("recommend")} disabled={decided}>
              <Gavel className="mr-1.5 h-4 w-4" /> Recommend
            </Button>
          )}
          {canDecide(role) && (
            <Button size="sm" onClick={() => setDlg("decide")} disabled={decided}>
              <Gavel className="mr-1.5 h-4 w-4" /> Decide
            </Button>
          )}
        </div>
      </div>

      {isReviewer(role) && (
        <>
          <ObservationDialog app={app} open={dlg === "obs"} onOpenChange={(o) => setDlg(o ? "obs" : null)} />
          <RectificationDialog app={app} open={dlg === "rect"} onOpenChange={(o) => setDlg(o ? "rect" : null)} />
          <DecisionDialog
            app={app}
            mode={canDecide(role) ? "decide" : "recommend"}
            open={dlg === "decide" || dlg === "recommend"}
            onOpenChange={(o) => setDlg(o ? (canDecide(role) ? "decide" : "recommend") : null)}
          />
        </>
      )}
    </section>
  );
}

function Count({ n, label, tone }: { n?: number; label: string; tone: string }) {
  return (
    <div className="min-w-[56px] rounded-md border bg-card px-2 py-1.5">
      <div className={cn("tabular text-lg font-semibold leading-none", (n ?? 0) > 0 ? tone : "text-muted-foreground")}>{n ?? 0}</div>
      <div className="mt-1 text-2xs text-muted-foreground">{label}</div>
    </div>
  );
}
