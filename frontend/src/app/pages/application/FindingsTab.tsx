import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  BookText,
  Check,
  CircleSlash,
  Database,
  FileSearch,
  FileText,
  Image as ImageIcon,
  Loader2,
  type LucideIcon,
  Radio,
  ShieldAlert,
  TriangleAlert,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { AdvisoryNote, AdvisoryTag } from "@/components/common/AdvisoryNote";
import { EmptyState } from "@/components/common/EmptyState";
import { SeverityBadge, severityDot } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useUpdateFinding } from "@/lib/hooks";
import { fmtDateTime, fmtValue } from "@/lib/format";
import { FINDING_KIND_LABEL, humanize, SEVERITY_ORDER } from "@/lib/labels";
import type { ApplicationDetail, Evidence, Finding, FindingStatus, Id } from "@/lib/types";
import { cn } from "@/lib/utils";
import { isInstitution, isReviewer, useAuth } from "../../auth";

const EVIDENCE_ICON: Record<string, LucideIcon> = {
  DOCUMENT: FileText,
  FIELD: FileSearch,
  RECORD: Database,
  SOURCE_RESPONSE: Radio,
  IMAGE_REGION: ImageIcon,
  METADATA: ShieldAlert,
  RULE: BookText,
};

const ACTIONS: { status: FindingStatus; label: string; icon: LucideIcon; officer: boolean; inst: boolean }[] = [
  { status: "ACKNOWLEDGED", label: "Acknowledge", icon: Check, officer: true, inst: true },
  { status: "RECTIFIED", label: "Confirm rectified", icon: Wrench, officer: true, inst: false },
  { status: "ESCALATED", label: "Escalate", icon: TriangleAlert, officer: true, inst: false },
  { status: "DISMISSED", label: "Dismiss", icon: CircleSlash, officer: true, inst: false },
];

type GroupBy = "severity" | "kind";

export default function FindingsTab({ app, onOpenDocument }: { app: ApplicationDetail; onOpenDocument: (id: Id, page?: number | null) => void }) {
  const [groupBy, setGroupBy] = useState<GroupBy>("severity");
  const [show, setShow] = useState<"active" | "all">("active");
  const [pending, setPending] = useState<{ f: Finding; status: FindingStatus } | null>(null);
  const findings = app.findings ?? [];
  const docs = new Map((app.documents ?? []).map((d) => [String(d.id), d]));

  const visible = findings.filter((f) => show === "all" || f.status === "OPEN" || f.status === "ESCALATED" || f.status === "ACKNOWLEDGED");
  const groups = useMemo(() => {
    const m = new Map<string, Finding[]>();
    const keys = groupBy === "severity" ? SEVERITY_ORDER : Object.keys(FINDING_KIND_LABEL);
    keys.forEach((k) => m.set(k, []));
    visible.forEach((f) => {
      const k = groupBy === "severity" ? f.severity : f.kind;
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(f);
    });
    m.forEach((list) => list.sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)));
    return [...m.entries()].filter(([, l]) => l.length > 0);
  }, [visible, groupBy]);

  const resolved = findings.length - findings.filter((f) => f.status === "OPEN" || f.status === "ESCALATED" || f.status === "ACKNOWLEDGED").length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <ToggleGroup type="single" value={groupBy} onValueChange={(v) => v && setGroupBy(v as GroupBy)} className="rounded-md border bg-card p-0.5" aria-label="Group findings by">
            <ToggleGroupItem value="severity" className="h-7 px-2.5 text-xs data-[state=on]:bg-navy data-[state=on]:text-white">
              By severity
            </ToggleGroupItem>
            <ToggleGroupItem value="kind" className="h-7 px-2.5 text-xs data-[state=on]:bg-navy data-[state=on]:text-white">
              By kind
            </ToggleGroupItem>
          </ToggleGroup>
          <ToggleGroup type="single" value={show} onValueChange={(v) => v && setShow(v as "active" | "all")} className="rounded-md border bg-card p-0.5" aria-label="Show findings">
            <ToggleGroupItem value="active" className="h-7 px-2.5 text-xs data-[state=on]:bg-navy data-[state=on]:text-white">
              Active
            </ToggleGroupItem>
            <ToggleGroupItem value="all" className="h-7 px-2.5 text-xs data-[state=on]:bg-navy data-[state=on]:text-white">
              All ({findings.length})
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
        <p className="text-xs text-muted-foreground">
          {findings.length} findings · {resolved} resolved or dismissed
        </p>
      </div>

      <AdvisoryNote>Each finding explains the rule applied and the evidence used. Confirm against the original documents before acting.</AdvisoryNote>

      {groups.length === 0 ? (
        <EmptyState
          icon={Check}
          title={findings.length ? "No active findings" : "No findings"}
          description={findings.length ? "All findings have been resolved or dismissed." : "Validation did not raise any findings for this application."}
        />
      ) : (
        groups.map(([key, list]) => (
          <section key={key} aria-labelledby={`grp-${key}`}>
            <h3 id={`grp-${key}`} className="mb-2 flex items-center gap-2 text-sm font-semibold">
              {groupBy === "severity" ? (
                <span className={cn("h-2.5 w-2.5 rounded-sm", severityDot(key))} aria-hidden />
              ) : null}
              {groupBy === "severity" ? humanize(key) : FINDING_KIND_LABEL[key] ?? humanize(key)}
              <span className="tabular rounded-full bg-muted px-1.5 text-2xs text-muted-foreground">{list.length}</span>
            </h3>
            <div className="space-y-3">
              {list.map((f) => (
                <FindingCard
                  key={f.id}
                  f={f}
                  docName={(id) => docs.get(String(id))?.docTypeLabel}
                  onOpenDocument={onOpenDocument}
                  onAction={app.status === "DECIDED" ? undefined : (status) => setPending({ f, status })}
                />
              ))}
            </div>
          </section>
        ))
      )}

      <FindingActionDialog appId={app.id} pending={pending} onClose={() => setPending(null)} />
    </div>
  );
}

const SEV_BORDER: Record<string, string> = {
  CRITICAL: "border-l-red-700",
  MAJOR: "border-l-orange-500",
  MINOR: "border-l-amber-400",
  INFO: "border-l-blue-500",
};

export function FindingCard({
  f,
  docName,
  onOpenDocument,
  onAction,
  compact,
}: {
  f: Finding;
  docName: (id: Id) => string | undefined;
  onOpenDocument: (id: Id, page?: number | null) => void;
  onAction?: (s: FindingStatus) => void;
  compact?: boolean;
}) {
  const { user } = useAuth();
  const officer = isReviewer(user?.role);
  const inst = isInstitution(user?.role);
  const actions = ACTIONS.filter((a) => a.status !== f.status && ((officer && a.officer) || (inst && a.inst && !["RECTIFIED", "DISMISSED"].includes(f.status))));
  const closed = f.status === "DISMISSED" || f.status === "RECTIFIED";
  return (
    <article className={cn("card-surface border-l-4", SEV_BORDER[f.severity] ?? "border-l-slate-300", closed && "opacity-75")}>
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={f.severity} />
          <span className="text-xs font-medium text-muted-foreground">{FINDING_KIND_LABEL[f.kind] ?? humanize(f.kind)}</span>
          <span className="ml-auto flex items-center gap-2">
            {f.advisory !== false && <AdvisoryTag />}
            <StatusBadge status={f.status} kind="finding" />
          </span>
        </div>
        <h4 className="mt-2 text-sm font-semibold leading-snug">{f.title}</h4>
        <p className="mt-1 text-sm text-foreground/85">{f.reason}</p>
        {(f.ruleId || f.clause) && (
          <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {f.ruleId && (
              <span>
                Rule <span className="mono text-foreground">{f.ruleId}</span>
              </span>
            )}
            {f.clause && (
              <span className="inline-flex items-center gap-1">
                <BookText className="h-3 w-3" /> {f.clause}
              </span>
            )}
          </p>
        )}

        {!compact && f.evidence?.length > 0 && (
          <div className="mt-3">
            <p className="kv-label mb-1.5">Evidence</p>
            <ul className="divide-y rounded-md border">
              {f.evidence.map((e, i) => (
                <EvidenceRow key={i} e={e} docName={docName} onOpenDocument={onOpenDocument} />
              ))}
            </ul>
          </div>
        )}

        {f.reviewerNote && (
          <p className="mt-3 rounded-md bg-muted/60 px-3 py-2 text-xs">
            <span className="font-semibold">Reviewer note:</span> {f.reviewerNote}
          </p>
        )}
      </div>
      {onAction && actions.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-t bg-slate-50/60 px-4 py-2">
          <span className="mr-auto text-2xs text-muted-foreground">Updated {fmtDateTime(f.updatedAt)}</span>
          {actions.map((a) => (
            <Button key={a.status} size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => onAction(a.status)}>
              <a.icon className="mr-1 h-3.5 w-3.5" /> {a.label}
            </Button>
          ))}
        </div>
      )}
    </article>
  );
}

function EvidenceRow({ e, docName, onOpenDocument }: { e: Evidence; docName: (id: Id) => string | undefined; onOpenDocument: (id: Id, page?: number | null) => void }) {
  const Icon = EVIDENCE_ICON[e.type] ?? FileText;
  const jump = e.documentId !== undefined && e.documentId !== null;
  const content = (
    <>
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden />
      <span className="min-w-0 flex-1">
        <span className="block text-xs font-medium">
          {e.label}
          <span className="ml-1.5 font-normal text-muted-foreground">
            {humanize(e.type)}
            {jump && docName(e.documentId!) ? ` · ${docName(e.documentId!)}` : ""}
            {e.page ? ` · p. ${e.page}` : ""}
          </span>
        </span>
        {e.excerpt && <span className="mt-0.5 line-clamp-2 block text-xs italic text-muted-foreground">“{e.excerpt}”</span>}
        {(e.submitted !== undefined && e.submitted !== null) || (e.reference !== undefined && e.reference !== null) ? (
          <span className="mt-1 grid grid-cols-2 gap-2 text-xs">
            <span>
              <span className="text-muted-foreground">Submitted: </span>
              <span className="font-medium">{fmtValue(e.submitted)}</span>
            </span>
            <span>
              <span className="text-muted-foreground">Reference: </span>
              <span className="font-medium">{fmtValue(e.reference)}</span>
            </span>
          </span>
        ) : null}
      </span>
      {jump && <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary-600" aria-hidden />}
    </>
  );
  return (
    <li>
      {jump ? (
        <button
          type="button"
          onClick={() => onOpenDocument(e.documentId!, e.page)}
          className="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-navy-50/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
          title="Open document"
        >
          {content}
        </button>
      ) : (
        <div className="flex items-start gap-2 px-3 py-2">{content}</div>
      )}
    </li>
  );
}

function FindingActionDialog({ appId, pending, onClose }: { appId: Id; pending: { f: Finding; status: FindingStatus } | null; onClose: () => void }) {
  const [note, setNote] = useState("");
  const m = useUpdateFinding(appId);
  const label = pending ? ACTIONS.find((a) => a.status === pending.status)?.label : "";
  const needsLong = pending?.status === "DISMISSED" || pending?.status === "ESCALATED";
  const valid = note.trim().length >= (needsLong ? 10 : 3);
  return (
    <Dialog
      open={!!pending}
      onOpenChange={(o) => {
        if (!o) {
          onClose();
          setNote("");
        }
      }}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{label}</DialogTitle>
          <DialogDescription className="line-clamp-2">{pending?.f.title}</DialogDescription>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label htmlFor="finding-note">
            Note <span className="text-red-700">*</span>
          </Label>
          <Textarea
            id="finding-note"
            rows={4}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              pending?.status === "DISMISSED"
                ? "Why is this finding not applicable? (e.g. verified original during hearing)"
                : pending?.status === "RECTIFIED"
                  ? "What was corrected? Reference the re-uploaded document."
                  : "Add context for the record."
            }
          />
          <p className="text-xs text-muted-foreground">Status changes and notes are written to the audit trail.</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={!valid || m.isPending}
            onClick={() =>
              pending &&
              m.mutate(
                { id: pending.f.id, status: pending.status, note: note.trim() },
                {
                  onSuccess: () => {
                    setNote("");
                    onClose();
                  },
                },
              )
            }
          >
            {m.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Confirm
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
