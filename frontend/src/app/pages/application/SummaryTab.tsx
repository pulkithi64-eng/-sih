import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Award,
  Building,
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  FileCheck2,
  FileText,
  Gavel,
  History,
  Layers,
  Printer,
  Scale,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Users,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AdvisoryTag } from "@/components/common/AdvisoryNote";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { ScoreRing } from "@/components/common/ScoreBar";
import { RiskBandPill, SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { downloadBlob, errorMessage } from "@/lib/api";
import { useProcessingSummary } from "@/lib/hooks";
import { categoryLabel, REGION_LABEL } from "@/lib/labels";
import type { ApplicationDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { canDecide, isOfficerPlus, isReviewer, useAuth } from "../../auth";
import { Panel } from "../../components/Panel";
import { PageSkeleton } from "../../components/Skeletons";

export default function SummaryTab({
  app,
  onOpenDocument,
  onOpenDecision,
  onOpenRectification,
  onSelectTab,
}: {
  app: ApplicationDetail;
  onOpenDocument: (docId: string | number, page?: number | null) => void;
  onOpenDecision?: () => void;
  onOpenRectification?: () => void;
  onSelectTab?: (tab: string) => void;
}) {
  const { user } = useAuth();
  const q = useProcessingSummary(app.id);
  const [downloading, setDownloading] = useState(false);

  if (q.isLoading) return <PageSkeleton />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;

  const s = q.data;
  if (!s) return <EmptyState title="No processing summary available" />;

  const isLowRisk = s.scores.riskBand === "LOW";
  const isHighRisk = s.scores.riskBand === "HIGH";

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const fname = `${s.applicationNo.replace(/\//g, "_")}_scrutiny_summary.pdf`;
      await downloadBlob(`/applications/${s.applicationId}/report.pdf`, fname);
      toast.success("Validation report PDF downloaded");
    } catch (e) {
      toast.error("Download failed", { description: errorMessage(e) });
    } finally {
      setDownloading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6 print:space-y-4">
      {/* Executive Summary Header */}
      <Panel className="p-6 border-2 border-primary/20 bg-gradient-to-br from-card via-card to-primary/5">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm font-bold text-primary">{s.applicationNo}</span>
              <StatusBadge status={s.status} />
              <RiskBandPill band={s.scores.riskBand} />
              <Badge variant="outline" className="text-xs">
                AY {s.academicYear}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {categoryLabel(s.category)}
              </Badge>
            </div>

            <h2 className="text-xl font-bold text-foreground">
              {s.institution.name}
            </h2>

            <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-2">
              <span>Permanent ID: <strong>{s.institution.permanentId}</strong></span>
              <span>•</span>
              <span>Location: {s.institution.city}, {s.institution.state}</span>
              <span>•</span>
              <span>Region: {REGION_LABEL[s.region] ?? s.region}</span>
              {s.lastValidatedAt && (
                <>
                  <span>•</span>
                  <span>Validated: {new Date(s.lastValidatedAt).toLocaleString()}</span>
                </>
              )}
            </p>
          </div>

          <div className="flex items-center gap-6 self-start lg:self-center shrink-0">
            <div className="flex flex-col items-center">
              <ScoreRing value={s.scores.complianceScore} label={null} size={84} />
              <span className="text-2xs font-semibold uppercase text-muted-foreground mt-1">Compliance</span>
            </div>

            <div className="flex flex-col items-center">
              <ScoreRing value={s.scores.crossDocScore} label={null} size={84} />
              <span className="text-2xs font-semibold uppercase text-muted-foreground mt-1">Cross-Doc Score</span>
            </div>

            <div className="hidden sm:flex flex-col gap-2 print:hidden">
              <Button size="sm" onClick={handleDownloadPdf} disabled={downloading} className="gap-1.5 text-xs">
                <Download className="h-3.5 w-3.5" />
                <span>Export PDF</span>
              </Button>
              <Button size="sm" variant="outline" onClick={handlePrint} className="gap-1.5 text-xs">
                <Printer className="h-3.5 w-3.5" />
                <span>Print</span>
              </Button>
            </div>
          </div>
        </div>
      </Panel>

      {/* Advisory Decision Recommendation Banner */}
      <div
        className={cn(
          "rounded-lg border-2 p-4 transition-all",
          isLowRisk
            ? "border-emerald-500/40 bg-emerald-50/40 text-emerald-950"
            : isHighRisk
            ? "border-red-500/40 bg-red-50/40 text-red-950"
            : "border-amber-500/40 bg-amber-50/40 text-amber-950",
        )}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            {isLowRisk ? (
              <ShieldCheck className="h-6 w-6 text-emerald-600 shrink-0 mt-0.5" />
            ) : isHighRisk ? (
              <ShieldAlert className="h-6 w-6 text-red-600 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-amber-600 shrink-0 mt-0.5" />
            )}
            <div>
              <div className="flex items-center gap-2">
                <span className="text-2xs font-bold uppercase tracking-wider text-muted-foreground">
                  Scrutiny Recommendation Advisory
                </span>
                <Badge variant="outline" className="font-semibold text-2xs">
                  {s.advisoryRecommendation.recommendedAction}
                </Badge>
              </div>
              <h3 className="text-sm font-bold mt-0.5 text-foreground">{s.advisoryRecommendation.title}</h3>
              <p className="text-xs text-muted-foreground mt-0.5">{s.advisoryRecommendation.reason}</p>
            </div>
          </div>

          {/* Action trigger for officers */}
          {isOfficerPlus(user?.role) && (
            <div className="flex items-center gap-2 shrink-0 print:hidden">
              {onOpenRectification && s.findingsDigest.totalActive > 0 && (
                <Button size="sm" variant="outline" onClick={onOpenRectification} className="text-xs">
                  Request Rectification
                </Button>
              )}
              {onOpenDecision && canDecide(user?.role) && app.status !== "DECIDED" && (
                <Button size="sm" onClick={onOpenDecision} className="text-xs gap-1">
                  <Gavel className="h-3.5 w-3.5" />
                  <span>Record Decision</span>
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Verification Pipeline Funnel Metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div className="rounded-lg border p-3 bg-card shadow-sm">
          <div className="text-2xs font-semibold text-muted-foreground uppercase">Uploaded Docs</div>
          <div className="text-2xl font-bold text-foreground tabular mt-1">
            {s.processingMetrics.totalDocuments}
          </div>
          <div className="text-2xs text-muted-foreground mt-0.5">Checklist verified</div>
        </div>

        <div className="rounded-lg border p-3 bg-card shadow-sm">
          <div className="text-2xs font-semibold text-muted-foreground uppercase">OCR Recognition</div>
          <div className="text-2xl font-bold text-foreground tabular mt-1">
            {s.processingMetrics.ocrCompleted}/{s.processingMetrics.totalDocuments}
          </div>
          <div className="text-2xs text-muted-foreground mt-0.5">Text layer + OCR</div>
        </div>

        <div className="rounded-lg border p-3 bg-card shadow-sm">
          <div className="text-2xs font-semibold text-muted-foreground uppercase">Authority Verified</div>
          <div className="text-2xl font-bold text-emerald-700 tabular mt-1">
            {s.processingMetrics.verified}
          </div>
          <div className="text-2xs text-muted-foreground mt-0.5">
            {s.processingMetrics.mismatch > 0 ? `${s.processingMetrics.mismatch} mismatch(es)` : "No mismatches"}
          </div>
        </div>

        <div className="rounded-lg border p-3 bg-card shadow-sm">
          <div className="text-2xs font-semibold text-muted-foreground uppercase">Cross-Doc Score</div>
          <div className="text-2xl font-bold text-foreground tabular mt-1">
            {s.crossVerificationSummary.score}%
          </div>
          <div className="text-2xs text-muted-foreground mt-0.5">
            {s.crossVerificationSummary.discrepanciesCount} disparity flag(s)
          </div>
        </div>

        <div className="rounded-lg border p-3 bg-card shadow-sm">
          <div className="text-2xs font-semibold text-muted-foreground uppercase">Forensic Tampering</div>
          <div className="text-2xl font-bold tabular mt-1 text-foreground">
            {s.processingMetrics.forensicFlagsCount === 0 ? "Clean" : `${s.processingMetrics.forensicFlagsCount} flag(s)`}
          </div>
          <div className="text-2xs text-muted-foreground mt-0.5">ELA & metadata scan</div>
        </div>

        <div className="rounded-lg border p-3 bg-card shadow-sm">
          <div className="text-2xs font-semibold text-muted-foreground uppercase">Active Findings</div>
          <div
            className={cn(
              "text-2xl font-bold tabular mt-1",
              s.findingsDigest.critical.length > 0 ? "text-red-700" : "text-foreground",
            )}
          >
            {s.findingsDigest.totalActive}
          </div>
          <div className="text-2xs text-muted-foreground mt-0.5">
            {s.findingsDigest.critical.length} critical, {s.findingsDigest.major.length} major
          </div>
        </div>
      </div>

      {/* Document-by-Document Verification Summary Table */}
      <Panel className="overflow-hidden p-0 border">
        <div className="flex items-center justify-between bg-muted/40 px-4 py-3 border-b">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            <h4 className="font-bold text-xs uppercase tracking-wide text-foreground">
              Uploaded Document Authenticity Digest
            </h4>
          </div>
          <span className="text-2xs text-muted-foreground">
            {s.issuingAuthorityBreakdown.length} document(s) evaluated
          </span>
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-muted/10">
              <TableRow className="h-9">
                <TableHead className="text-xs font-semibold">Document Type</TableHead>
                <TableHead className="text-xs font-semibold">Filename</TableHead>
                <TableHead className="text-xs font-semibold">Issuing Authority</TableHead>
                <TableHead className="text-xs font-semibold">Verification Method</TableHead>
                <TableHead className="text-xs font-semibold text-center">Status</TableHead>
                <TableHead className="text-xs font-semibold text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {s.issuingAuthorityBreakdown.map((doc) => {
                const isDocVerified = doc.status === "VERIFIED";
                const isMismatch = doc.status === "MISMATCH_DETECTED";

                return (
                  <TableRow key={doc.documentId} className="h-10 hover:bg-muted/20">
                    <TableCell className="text-xs font-medium text-foreground py-2">
                      {doc.docType}
                    </TableCell>
                    <TableCell className="text-2xs font-mono text-muted-foreground py-2">
                      {doc.fileName}
                    </TableCell>
                    <TableCell className="text-xs text-foreground/80 py-2">
                      {doc.source}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground py-2">
                      {doc.method}
                    </TableCell>
                    <TableCell className="text-center py-2">
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-2xs font-semibold",
                          isDocVerified && "border-emerald-400 text-emerald-800 bg-emerald-50",
                          isMismatch && "border-red-400 text-red-800 bg-red-50",
                          !isDocVerified && !isMismatch && "border-amber-300 text-amber-800 bg-amber-50",
                        )}
                      >
                        {doc.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right py-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs px-2"
                        onClick={() => onOpenDocument(doc.documentId)}
                      >
                        View Document
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </Panel>

      {/* Critical Findings Checklist */}
      {s.findingsDigest.totalActive > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <span>Outstanding Findings Requiring Resolution ({s.findingsDigest.totalActive})</span>
            </h4>
            {onSelectTab && (
              <Button
                variant="link"
                size="sm"
                className="text-xs text-primary p-0 h-auto"
                onClick={() => onSelectTab("findings")}
              >
                View all findings in detail →
              </Button>
            )}
          </div>

          <div className="space-y-2">
            {[...s.findingsDigest.critical, ...s.findingsDigest.major, ...s.findingsDigest.minor].slice(0, 5).map((f) => (
              <div
                key={f.id}
                className={cn(
                  "rounded-lg border p-3 text-xs flex items-start justify-between gap-3 bg-card",
                  f.severity === "CRITICAL" && "border-red-200 bg-red-50/20",
                )}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={f.severity} />
                    <span className="font-semibold text-foreground">{f.title}</span>
                  </div>
                  <p className="text-muted-foreground text-xs">{f.reason}</p>
                </div>
                {f.documentId && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 text-2xs shrink-0"
                    onClick={() => onOpenDocument(f.documentId!)}
                  >
                    View Doc
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/30 p-4 text-center">
          <CheckCircle2 className="h-6 w-6 text-emerald-600 mx-auto mb-1" />
          <h4 className="text-sm font-semibold text-emerald-950">No Open Deficiencies</h4>
          <p className="text-xs text-emerald-800 mt-0.5">
            Application complies with all verified handbook rules and statutory requirements.
          </p>
        </div>
      )}
    </div>
  );
}
