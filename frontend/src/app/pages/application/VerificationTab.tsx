import { Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/common/EmptyState";
import { StatusBadge, VERIFICATION_CHART_COLOR } from "@/components/common/StatusBadge";
import { useVerifyDocument } from "@/lib/hooks";
import { fmtDateTime } from "@/lib/format";
import { humanize, METHOD_LABEL, VERIFICATION_DESCRIPTION, VERIFICATION_STATES } from "@/lib/labels";
import type { ApplicationDetail, Id, VerificationStatus } from "@/lib/types";
import { isOfficerPlus, useAuth } from "../../auth";
import { Panel } from "../../components/Panel";
import { StackedDistribution } from "../../components/charts";

export default function VerificationTab({ app, onOpenDocument }: { app: ApplicationDetail; onOpenDocument: (id: Id) => void }) {
  const { user } = useAuth();
  const officer = isOfficerPlus(user?.role);
  const verify = useVerifyDocument(app.id);
  const docs = app.documents ?? [];
  const counts = VERIFICATION_STATES.map((s) => ({
    key: s,
    label: humanize(s),
    value: docs.filter((d) => d.verification?.status === s).length,
    color: VERIFICATION_CHART_COLOR[s],
  }));
  const na = docs.filter((d) => d.verification?.status === "NOT_APPLICABLE").length;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <Panel
        title="Source verification by document"
        description="Each document is checked with its issuing authority (API, signed QR, DigiLocker or portal lookup)"
        flush
        actions={
          officer && docs.length > 0 ? (
            <Button
              size="sm"
              variant="outline"
              disabled={verify.isPending}
              onClick={async () => {
                for (const d of docs.filter((x) => x.verification?.status !== "VERIFIED" && x.verification?.status !== "NOT_APPLICABLE")) {
                  try {
                    await verify.mutateAsync(d.id);
                  } catch {
                    /* toast already shown */
                  }
                }
              }}
            >
              {verify.isPending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-1.5 h-4 w-4" />}
              Re-verify unresolved
            </Button>
          ) : undefined
        }
      >
        {docs.length === 0 ? (
          <EmptyState compact title="No documents" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Document</TableHead>
                <TableHead>State</TableHead>
                <TableHead className="hidden md:table-cell">Source</TableHead>
                <TableHead className="hidden lg:table-cell">Method</TableHead>
                <TableHead className="hidden md:table-cell">Checked</TableHead>
                {officer && <TableHead className="w-10"><span className="sr-only">Actions</span></TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {docs.map((d) => {
                const v = d.verification;
                const busy = verify.isPending && String(verify.variables) === String(d.id);
                return (
                  <TableRow key={d.id}>
                    <TableCell className="max-w-[260px]">
                      <button type="button" onClick={() => onOpenDocument(d.id)} className="block max-w-full text-left hover:underline">
                        <span className="block truncate font-medium">{d.docTypeLabel || humanize(d.docType)}</span>
                        <span className="mono block truncate text-xs text-muted-foreground">{d.referenceNo || d.fileName}</span>
                      </button>
                      {v?.reason && <span className="mt-0.5 line-clamp-1 block text-xs text-muted-foreground">{v.reason}</span>}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={v?.status ?? "VERIFICATION_PENDING"} kind="verification" />
                    </TableCell>
                    <TableCell className="hidden max-w-[200px] truncate text-sm md:table-cell">{v?.source || "—"}</TableCell>
                    <TableCell className="hidden text-sm lg:table-cell">{v?.method ? METHOD_LABEL[v.method] ?? v.method : "—"}</TableCell>
                    <TableCell className="hidden whitespace-nowrap text-xs text-muted-foreground md:table-cell">{fmtDateTime(v?.checkedAt)}</TableCell>
                    {officer && (
                      <TableCell>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          disabled={verify.isPending}
                          onClick={() => verify.mutate(d.id)}
                          aria-label={`Re-verify ${d.docTypeLabel}`}
                          title="Re-verify with source"
                        >
                          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Panel>

      <div className="space-y-4">
        <Panel title="Summary">
          <StackedDistribution data={counts} />
          {na > 0 && <p className="mt-3 text-xs text-muted-foreground">{na} document(s) not applicable for source verification.</p>}
        </Panel>
        <Panel title="What the states mean">
          <ul className="space-y-3">
            {(VERIFICATION_STATES as VerificationStatus[]).map((s) => (
              <li key={s}>
                <StatusBadge status={s} kind="verification" />
                <p className="mt-1 text-xs text-muted-foreground">{VERIFICATION_DESCRIPTION[s]}</p>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
