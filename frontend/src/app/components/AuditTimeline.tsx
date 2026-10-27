import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Link2, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api, errorMessage } from "@/lib/api";
import { fmtDateTime, fmtValue, shortHash } from "@/lib/format";
import { humanize, roleLabel } from "@/lib/labels";
import type { AuditEvent, AuditVerifyResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const ACTION_TONE: Array<[RegExp, string]> = [
  [/DECISION|DECIDE|RECOMMEND/i, "bg-navy"],
  [/REJECT|ESCALAT|MISMATCH|FAIL/i, "bg-red-600"],
  [/RECTIF/i, "bg-amber-500"],
  [/VALIDAT|VERIFY|VERIFIED/i, "bg-green-600"],
  [/UPLOAD|CREATE|SUBMIT/i, "bg-blue-600"],
  [/LOGIN/i, "bg-slate-400"],
];

function dotFor(action: string) {
  return ACTION_TONE.find(([re]) => re.test(action))?.[1] ?? "bg-slate-400";
}

function detailsSummary(d: any): string | null {
  if (d === null || d === undefined) return null;
  if (typeof d !== "object") return String(d);
  const entries = Object.entries(d).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (!entries.length) return null;
  return entries
    .slice(0, 6)
    .map(([k, v]) => `${humanize(k)}: ${typeof v === "object" ? JSON.stringify(v).slice(0, 80) : fmtValue(v)}`)
    .join(" · ");
}

export function ChainVerifyButton({ size = "sm" }: { size?: "sm" | "default" }) {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<AuditVerifyResult | null>(null);
  return (
    <div className="flex flex-wrap items-center gap-2">
      {res && (
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
            res.valid ? "border-green-200 bg-green-50 text-green-800" : "border-red-200 bg-red-50 text-red-800",
          )}
          role="status"
        >
          {res.valid ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
          {res.valid ? `Chain intact · ${res.checked} events checked` : `Chain broken at event ${res.brokenAt}`}
        </span>
      )}
      <Button
        size={size}
        variant="outline"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            const r = await api.verifyAudit();
            setRes(r);
            if (r.valid) toast.success("Audit chain verified", { description: `${r.checked} events, no tampering detected` });
            else toast.error("Audit chain integrity failure", { description: `Hash mismatch at event ${r.brokenAt}` });
          } catch (e) {
            toast.error("Could not verify chain", { description: errorMessage(e) });
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Link2 className="mr-1.5 h-4 w-4" />}
        Verify chain integrity
      </Button>
    </div>
  );
}

export function AuditTimeline({ events, showEntity = false }: { events: AuditEvent[]; showEntity?: boolean }) {
  return (
    <ol className="relative">
      {events.map((e, i) => {
        const summary = detailsSummary(e.details);
        const appId = e.entityType?.toLowerCase() === "application" ? e.entityId : e.details?.applicationId;
        return (
          <li key={e.id} className="relative flex gap-3 pb-5 last:pb-0">
            {i < events.length - 1 && <span className="absolute left-[7px] top-4 h-full w-px bg-border" aria-hidden />}
            <span className={cn("relative mt-1 h-[15px] w-[15px] shrink-0 rounded-full border-[3px] border-card ring-1 ring-border", dotFor(e.action))} aria-hidden />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span className="text-sm font-semibold">{humanize(e.action)}</span>
                <span className="text-xs text-muted-foreground">
                  by <span className="font-medium text-foreground">{e.actor}</span>
                  {e.actorRole ? ` (${roleLabel(e.actorRole)})` : ""}
                </span>
                <time className="ml-auto whitespace-nowrap text-xs text-muted-foreground" dateTime={e.ts}>
                  {fmtDateTime(e.ts)}
                </time>
              </div>
              {showEntity && (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {humanize(e.entityType)}{" "}
                  {appId ? (
                    <Link to={`/portal/applications/${appId}`} className="mono text-primary-600 hover:underline">
                      {e.entityId}
                    </Link>
                  ) : (
                    <span className="mono">{e.entityId}</span>
                  )}
                </p>
              )}
              {summary && <p className="mt-1 break-words text-sm text-foreground/85">{summary}</p>}
              <p className="mono mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-2xs text-muted-foreground">
                <span title={e.hash}>
                  <CheckCircle2 className="mr-0.5 inline h-3 w-3 align-[-2px] text-green-700" />
                  hash {shortHash(e.hash, 12)}
                </span>
                <span title={e.prevHash}>prev {shortHash(e.prevHash, 12)}</span>
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
