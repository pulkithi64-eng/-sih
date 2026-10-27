import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileCheck2,
  FileSearch,
  FileText,
  Info,
  Scale,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AdvisoryTag } from "@/components/common/AdvisoryNote";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { ScoreRing } from "@/components/common/ScoreBar";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { useCrossVerification } from "@/lib/hooks";
import type { ApplicationDetail, CrossVerificationDiscrepancy, CrossVerificationField } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Panel } from "../../components/Panel";
import { PageSkeleton } from "../../components/Skeletons";

export default function CrossVerificationTab({
  app,
  onOpenDocument,
}: {
  app: ApplicationDetail;
  onOpenDocument: (docId: string | number, page?: number | null) => void;
}) {
  const q = useCrossVerification(app.id);

  if (q.isLoading) return <PageSkeleton />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;

  const result = q.data;
  if (!result || result.totalDocumentsAnalyzed === 0) {
    return (
      <EmptyState
        icon={Scale}
        title="No documents available for cross-verification"
        description="Upload statutory documents (Affidavit, Land Deed, Fire NOC, Occupancy Cert) to run automated cross-consistency analysis."
      />
    );
  }

  const isConsistent = result.status === "CONSISTENT";
  const isCritical = result.status === "CRITICAL_CONFLICT";

  return (
    <div className="space-y-6">
      {/* Overview & Score Card */}
      <Panel className="p-5">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-5">
            <div className="flex flex-col items-center">
              <ScoreRing value={result.overallScore} label={null} size={92} />
              <span className="text-2xs font-semibold uppercase text-muted-foreground mt-1">Consistency</span>
            </div>

            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-bold text-foreground">Cross-Documentation Verification</h3>
                <Badge
                  variant={isConsistent ? "default" : isCritical ? "destructive" : "secondary"}
                  className={cn(
                    "font-semibold text-xs",
                    isConsistent && "bg-emerald-600 hover:bg-emerald-700 text-white",
                    !isConsistent && !isCritical && "bg-amber-100 text-amber-900 border-amber-300",
                  )}
                >
                  {isConsistent ? (
                    <span className="flex items-center gap-1">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      Consistent Cross-Reference
                    </span>
                  ) : isCritical ? (
                    <span className="flex items-center gap-1">
                      <ShieldAlert className="h-3.5 w-3.5" />
                      Critical Conflict Detected
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Discrepancies Flagged
                    </span>
                  )}
                </Badge>
              </div>

              <p className="text-xs text-muted-foreground max-w-2xl leading-relaxed">
                Automated multi-document correlation analyzes extracted textual particulars, area measurements, and
                statutory validity periods across certificates, deeds, affidavits, and application declarations to detect
                contradictions or forged alterations.
              </p>

              <div className="flex flex-wrap gap-4 pt-2 text-xs">
                <div>
                  <span className="text-muted-foreground">Documents analyzed:</span>{" "}
                  <strong className="text-foreground tabular">{result.totalDocumentsAnalyzed}</strong>
                </div>
                <div>
                  <span className="text-muted-foreground">Parameters cross-checked:</span>{" "}
                  <strong className="text-foreground tabular">{result.fieldsChecked.length}</strong>
                </div>
                <div>
                  <span className="text-muted-foreground">Discrepancies:</span>{" "}
                  <strong className={cn("tabular", result.discrepanciesCount > 0 ? "text-red-700 font-bold" : "text-emerald-700 font-medium")}>
                    {result.discrepanciesCount}
                  </strong>
                </div>
              </div>
            </div>
          </div>

          <div className="flex md:flex-col justify-end gap-2 shrink-0">
            <AdvisoryTag />
          </div>
        </div>
      </Panel>

      {/* Flagged Discrepancy Cards */}
      {result.discrepancies.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <span>Flagged Multi-Document Inconsistencies ({result.discrepancies.length})</span>
            </h4>
            <span className="text-2xs text-muted-foreground">Sorted by regulatory severity</span>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {result.discrepancies.map((disc) => (
              <DiscrepancyCard key={disc.id} disc={disc} onOpenDocument={onOpenDocument} />
            ))}
          </div>
        </div>
      )}

      {/* Parameter Comparison Matrix */}
      <div className="space-y-3">
        <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
          <FileCheck2 className="h-4 w-4 text-primary" />
          <span>Cross-Document Correlation Matrix</span>
        </h4>

        <div className="space-y-4">
          {result.fieldsChecked.map((f) => (
            <FieldMatrixPanel key={f.field} field={f} onOpenDocument={onOpenDocument} />
          ))}
        </div>
      </div>
    </div>
  );
}

function DiscrepancyCard({
  disc,
  onOpenDocument,
}: {
  disc: CrossVerificationDiscrepancy;
  onOpenDocument: (docId: string | number, page?: number | null) => void;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4 bg-card shadow-sm transition-all",
        disc.severity === "CRITICAL"
          ? "border-red-300 bg-red-50/20"
          : "border-amber-300 bg-amber-50/20",
      )}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1.5 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={disc.severity} />
            <span className="font-semibold text-sm text-foreground">{disc.fieldLabel}</span>
            <Badge variant="outline" className="font-mono text-2xs">
              {disc.id}
            </Badge>
          </div>

          <p className="text-xs text-foreground/90 font-medium">{disc.description}</p>

          {disc.clause && (
            <p className="text-2xs text-muted-foreground italic">
              Clause: {disc.clause}
            </p>
          )}

          {/* Side by side comparison pills */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2 max-w-2xl">
            <div className="rounded border bg-background/90 p-2 text-xs">
              <div className="text-2xs font-semibold text-muted-foreground uppercase flex items-center justify-between">
                <span>{disc.docA.type}</span>
                <span className="truncate max-w-[150px]">{disc.docA.fileName}</span>
              </div>
              <div className="mt-1 font-mono font-medium text-foreground text-xs break-words">
                {disc.docA.value}
              </div>
            </div>

            <div className="rounded border bg-background/90 p-2 text-xs">
              <div className="text-2xs font-semibold text-muted-foreground uppercase flex items-center justify-between">
                <span>{disc.docB.type}</span>
                <span className="truncate max-w-[150px]">{disc.docB.fileName}</span>
              </div>
              <div className="mt-1 font-mono font-medium text-foreground text-xs break-words">
                {disc.docB.value}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-row md:flex-col gap-2 shrink-0 pt-2 md:pt-0">
          {Number(disc.docA.id) > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-2xs gap-1"
              onClick={() => onOpenDocument(disc.docA.id)}
            >
              <FileSearch className="h-3 w-3" />
              <span>Inspect {disc.docA.type}</span>
            </Button>
          )}
          {Number(disc.docB.id) > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-2xs gap-1"
              onClick={() => onOpenDocument(disc.docB.id)}
            >
              <FileSearch className="h-3 w-3" />
              <span>Inspect {disc.docB.type}</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function FieldMatrixPanel({
  field,
  onOpenDocument,
}: {
  field: CrossVerificationField;
  onOpenDocument: (docId: string | number, page?: number | null) => void;
}) {
  const isMatch = field.status === "MATCH";
  const isPartial = field.status === "PARTIAL_MATCH";

  return (
    <Panel className="overflow-hidden p-0 border">
      <div className="flex items-center justify-between bg-muted/40 px-4 py-2.5 border-b">
        <div className="flex items-center gap-2.5">
          {isMatch ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          ) : isPartial ? (
            <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
          ) : (
            <XCircle className="h-4 w-4 text-red-600 shrink-0" />
          )}
          <span className="font-semibold text-xs text-foreground">{field.label}</span>
          <span className="text-2xs text-muted-foreground">
            (Reference: <strong className="text-foreground">{field.referenceValue}</strong>)
          </span>
        </div>

        <Badge
          variant="outline"
          className={cn(
            "text-2xs font-semibold",
            isMatch && "border-emerald-300 text-emerald-800 bg-emerald-50",
            isPartial && "border-amber-300 text-amber-800 bg-amber-50",
            !isMatch && !isPartial && "border-red-300 text-red-800 bg-red-50",
          )}
        >
          {isMatch ? "100% Match" : isPartial ? "Fuzzy Match" : "Mismatch"}
        </Badge>
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader className="bg-muted/10">
            <TableRow className="h-8">
              <TableHead className="text-2xs font-semibold">Document Type</TableHead>
              <TableHead className="text-2xs font-semibold">File Name</TableHead>
              <TableHead className="text-2xs font-semibold">Extracted Value</TableHead>
              <TableHead className="text-2xs font-semibold text-center">Status</TableHead>
              <TableHead className="text-2xs font-semibold text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {field.documents.map((d) => (
              <TableRow key={`${d.docId}-${d.docType}`} className="h-9 hover:bg-muted/20">
                <TableCell className="text-xs font-medium text-foreground py-1.5">
                  {d.docTypeLabel || d.docType}
                </TableCell>
                <TableCell className="text-2xs font-mono text-muted-foreground py-1.5">
                  {d.fileName}
                </TableCell>
                <TableCell className="text-xs font-mono py-1.5">
                  <span className="font-medium text-foreground">{String(d.value)}</span>
                  {d.similarity !== undefined && (
                    <span className="text-2xs text-muted-foreground ml-1.5">
                      ({Math.round(d.similarity * 100)}% sim)
                    </span>
                  )}
                  {d.diffPct !== undefined && d.diffPct > 0 && (
                    <span className="text-2xs text-amber-700 ml-1.5">
                      (Δ {d.diffPct}%)
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-center py-1.5">
                  {d.status === "MATCH" ? (
                    <span className="inline-flex items-center gap-1 text-2xs font-semibold text-emerald-700">
                      <CheckCircle2 className="h-3 w-3" />
                      Match
                    </span>
                  ) : d.status === "PARTIAL_MATCH" ? (
                    <span className="inline-flex items-center gap-1 text-2xs font-semibold text-amber-700">
                      <AlertTriangle className="h-3 w-3" />
                      Partial
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-2xs font-semibold text-red-700">
                      <XCircle className="h-3 w-3" />
                      Mismatch
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right py-1.5">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-2xs px-2"
                    onClick={() => onOpenDocument(d.docId, d.page)}
                  >
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Panel>
  );
}
