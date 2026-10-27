import { useId, useState } from "react";
import { CheckCircle2, ChevronDown, Fingerprint, Loader2, RefreshCw, ScanText, ShieldCheck, Tags, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AdvisoryTag } from "@/components/common/AdvisoryNote";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useDocText } from "@/lib/hooks";
import { confPct, fmtBytes, fmtDate, fmtDateTime, fmtValue, shortHash } from "@/lib/format";
import { humanize, METHOD_LABEL, VERIFICATION_DESCRIPTION } from "@/lib/labels";
import type { DocumentT } from "@/lib/types";
import { cn } from "@/lib/utils";
import { verificationNextStep } from "@/lib/journey";

function Section({
  icon: Icon,
  title,
  right,
  children,
  defaultOpen = true,
}: {
  icon: React.ElementType;
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();
  return (
    <section className="border-b last:border-0">
      <div className="flex items-center gap-2 px-4 py-2.5">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-expanded={open}
          aria-controls={contentId}
        >
          <Icon className="h-4 w-4 shrink-0 text-navy" aria-hidden />
          <h3 className="truncate text-sm font-semibold">{title}</h3>
          <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", !open && "-rotate-90")} />
        </button>
        {right}
      </div>
      {open && <div id={contentId} className="px-4 pb-4">{children}</div>}
    </section>
  );
}

export function ConfidenceMeter({ value, className }: { value: number; className?: string }) {
  const v = confPct(value);
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} title={`Confidence ${v}%`}>
      <span className="h-1.5 w-12 overflow-hidden rounded-full bg-slate-200">
        <span
          className={cn("block h-full rounded-full", v >= 85 ? "bg-green-600" : v >= 60 ? "bg-amber-500" : "bg-red-600")}
          style={{ width: `${v}%` }}
        />
      </span>
      <span className="tabular text-xs text-muted-foreground">{v}%</span>
    </span>
  );
}

export function VerificationCard({ doc, onReverify, reverifying }: { doc: DocumentT; onReverify?: () => void; reverifying?: boolean }) {
  const v = doc.verification ?? ({ status: "VERIFICATION_PENDING" } as DocumentT["verification"]);
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge status={v.status} kind="verification" size="md" />
        {onReverify && (
          <Button size="sm" variant="outline" className="h-7" onClick={onReverify} disabled={reverifying}>
            {reverifying ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="mr-1 h-3.5 w-3.5" />}
            Re-verify
          </Button>
        )}
      </div>
      <p className="mt-2 text-sm">{verificationNextStep(v.status)}</p>
      <p className="mt-2 text-xs text-muted-foreground"><span className="font-medium">Source: </span>{v.source || "No issuer source available"}</p>
      <details className="mt-3" open={v.status === "MISMATCH_DETECTED"}>
      <summary className="cursor-pointer text-xs font-medium text-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Verification evidence</summary>
      <p className="mt-2 text-xs text-muted-foreground">{VERIFICATION_DESCRIPTION[v.status]}</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div>
          <dt className="kv-label">Source</dt>
          <dd className="mt-0.5">{v.source || "—"}</dd>
        </div>
        <div>
          <dt className="kv-label">Method</dt>
          <dd className="mt-0.5">{v.method ? METHOD_LABEL[v.method] ?? v.method : "—"}</dd>
        </div>
        <div>
          <dt className="kv-label">Checked</dt>
          <dd className="mt-0.5">{fmtDateTime(v.checkedAt)}</dd>
        </div>
        <div>
          <dt className="kv-label">Reference no.</dt>
          <dd className="mono mt-0.5 break-all">{doc.referenceNo || "—"}</dd>
        </div>
      </dl>
      {(v.reason || v.responseSummary) && (
        <div className="mt-3 rounded-md bg-muted/60 px-3 py-2 text-xs">
          {v.reason && <p className="text-foreground">{v.reason}</p>}
          {v.responseSummary && <p className="mt-1 text-muted-foreground">Source response: {v.responseSummary}</p>}
        </div>
      )}
      {v.comparisons && v.comparisons.length > 0 && (
        <div className="mt-3 overflow-hidden rounded-md border">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-muted-foreground">
              <tr>
                <th className="px-2.5 py-1.5 text-left font-semibold">Field</th>
                <th className="px-2.5 py-1.5 text-left font-semibold">Submitted</th>
                <th className="px-2.5 py-1.5 text-left font-semibold">Source</th>
                <th className="w-6 px-2 py-1.5" aria-label="Match" />
              </tr>
            </thead>
            <tbody>
              {v.comparisons.map((c, i) => (
                <tr key={i} className={cn("border-t", !c.match && "bg-red-50/60")}>
                  <td className="px-2.5 py-1.5 font-medium">{humanize(c.field)}</td>
                  <td className="break-all px-2.5 py-1.5">{fmtValue(c.submitted)}</td>
                  <td className="break-all px-2.5 py-1.5">{fmtValue(c.source)}</td>
                  <td className="px-2 py-1.5">
                    {c.match ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-700" aria-label="Match" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-red-700" aria-label="Mismatch" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      </details>
    </div>
  );
}

export function ForensicsCard({ doc }: { doc: DocumentT }) {
  const f = doc.forensics ?? ({ flags: [], metadata: {}, hasElaHeatmap: false } as DocumentT["forensics"]);
  const ela = f.elaScore;
  const elaPct = ela === null || ela === undefined ? null : ela <= 1 ? ela * 100 : ela;
  const meta = Object.entries(f.metadata ?? {}).filter(([, v]) => v !== null && v !== undefined && v !== "");
  return (
    <div>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-md border px-3 py-2">
          <p className="kv-label">ELA score</p>
          <p className="tabular mt-0.5 text-lg font-semibold">{elaPct === null ? "—" : elaPct.toFixed(1)}</p>
          <p className="text-2xs text-muted-foreground">Higher = more uneven recompression</p>
        </div>
        <div className="rounded-md border px-3 py-2">
          <p className="kv-label">Forensic flags</p>
          <p className={cn("tabular mt-0.5 text-lg font-semibold", f.flags?.length ? "text-red-700" : "text-green-700")}>{f.flags?.length ?? 0}</p>
          <p className="text-2xs text-muted-foreground">{f.hasElaHeatmap ? "Heatmap available" : "No heatmap"}</p>
        </div>
      </div>
      {f.flags?.length > 0 && (
        <ul className="mt-3 space-y-2">
          {f.flags.map((fl, i) => (
            <li key={i} className="rounded-md border border-l-4 border-l-red-600 px-3 py-2">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={String(fl.severity)} />
                <span className="mono text-xs text-muted-foreground">{fl.code}</span>
              </div>
              <p className="mt-1 text-sm">{fl.reason}</p>
              {fl.evidence && typeof fl.evidence !== "object" && <p className="mt-0.5 text-xs text-muted-foreground">{String(fl.evidence)}</p>}
              {fl.evidence && typeof fl.evidence === "object" && (
                <p className="mono mt-0.5 break-all text-2xs text-muted-foreground">
                  {Object.entries(fl.evidence)
                    .filter(([k]) => k !== "bbox" && k !== "regions")
                    .map(([k, v]) => `${k}: ${fmtValue(v)}`)
                    .join(" · ")}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      {meta.length > 0 && (
        <dl className="mt-3 divide-y rounded-md border text-xs">
          {meta.map(([k, v]) => (
            <div key={k} className="grid grid-cols-[120px_minmax(0,1fr)] gap-2 px-2.5 py-1.5">
              <dt className="text-muted-foreground">{humanize(k)}</dt>
              <dd className="mono break-all">{fmtValue(v)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

export function ExtractedFieldsTable({ doc }: { doc: DocumentT }) {
  const fields = Object.entries(doc.extractedFields ?? {});
  if (!fields.length) return <p className="text-sm text-muted-foreground">No fields extracted.</p>;
  return (
    <div className="overflow-hidden rounded-md border">
      <table className="w-full text-xs">
        <thead className="bg-slate-50 text-muted-foreground">
          <tr>
            <th className="px-2.5 py-1.5 text-left font-semibold">Field</th>
            <th className="px-2.5 py-1.5 text-left font-semibold">Value</th>
            <th className="px-2.5 py-1.5 text-left font-semibold">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {fields.map(([k, f]) => {
            const fv = f && typeof f === "object" && "value" in f ? f : { value: f, confidence: 0 };
            return (
              <tr key={k} className="border-t align-top">
                <td className="px-2.5 py-1.5 font-medium">
                  {humanize(k)}
                  {fv.page ? <span className="block text-2xs font-normal text-muted-foreground">p. {fv.page}</span> : null}
                </td>
                <td className="px-2.5 py-1.5">
                  <span className="break-words">{fmtValue(fv.value)}</span>
                  {fv.sourceText && fv.sourceText !== String(fv.value) && <details className="mt-1 text-2xs text-muted-foreground"><summary className="cursor-pointer">Source text</summary><p className="mt-1 whitespace-pre-wrap break-words">{fv.sourceText}</p></details>}
                </td>
                <td className="whitespace-nowrap px-2.5 py-1.5">{fv.confidence ? <ConfidenceMeter value={fv.confidence} /> : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function OcrPreview({ doc }: { doc: DocumentT }) {
  const [full, setFull] = useState(false);
  const text = useDocText(doc.id, full);
  const body = full ? text.data?.text ?? "" : doc.ocr?.textPreview ?? "";
  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span>
          Method <span className="font-medium text-foreground">{doc.ocr?.method ?? "—"}</span>
        </span>
        <span>
          Pages <span className="font-medium text-foreground">{doc.ocr?.pageCount ?? "—"}</span>
        </span>
        {doc.ocr?.confidence ? (
          <span className="inline-flex items-center gap-1">
            Confidence <ConfidenceMeter value={doc.ocr.confidence} />
          </span>
        ) : null}
      </div>
      {full && text.isError && <div role="alert" className="mb-2 text-sm text-destructive">Could not load recognised text. <button type="button" className="underline" onClick={() => text.refetch()}>Retry</button></div>}
      <pre className="mono max-h-64 overflow-auto whitespace-pre-wrap rounded-md border bg-slate-50 p-2.5 text-[11px] leading-relaxed text-foreground/90">
        {full && text.isLoading ? "Loading full text…" : body || "No text recognised."}
      </pre>
      {!full && (
        <button type="button" onClick={() => setFull(true)} className="mt-1.5 text-xs font-medium text-primary-600 hover:underline">
          Show full text
        </button>
      )}
    </div>
  );
}

export default function DocumentAnalysis({
  doc,
  onReverify,
  reverifying,
}: {
  doc: DocumentT;
  onReverify?: () => void;
  reverifying?: boolean;
}) {
  const cls = doc.classification ?? ({ docType: doc.docType, confidence: 0, signals: [] } as DocumentT["classification"]);
  const disagrees = cls.docType && cls.docType !== doc.docType;
  return (
    <div className="card-surface overflow-hidden">
      <div className="flex items-start justify-between gap-2 border-b bg-slate-50/70 px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{doc.docTypeLabel || humanize(doc.docType)}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {fmtBytes(doc.sizeBytes)} · uploaded {fmtDate(doc.uploadedAt)}
            {doc.issuer ? ` · ${doc.issuer}` : ""}
          </p>
        </div>
        <AdvisoryTag />
      </div>

      <Section icon={ShieldCheck} title="Source verification">
        <VerificationCard doc={doc} onReverify={onReverify} reverifying={reverifying} />
      </Section>

      {doc.pipelineErrors?.length > 0 && <p role="alert" className="border-b bg-amber-50 p-3 text-sm text-amber-900">Some checks could not finish. A reviewer should inspect this document. Details remain in the processing summary.</p>}
      <Section icon={Tags} title="Classification & dates" defaultOpen={false} right={<ConfidenceMeter value={cls.confidence} />}>
        <p className="mono mb-3 break-all text-xs text-muted-foreground">SHA-256 {doc.sha256}</p>
        <p className="text-sm">
          Predicted <span className="font-medium">{humanize(cls.docType)}</span>
          {disagrees && (
            <span className="ml-1 rounded bg-amber-50 px-1 text-xs text-amber-800">differs from declared {humanize(doc.docType)}</span>
          )}
        </p>
        {cls.signals?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {cls.signals.map((s, i) => (
              <span key={i} className="rounded border bg-background px-1.5 py-0.5 text-2xs text-muted-foreground">
                {s}
              </span>
            ))}
          </div>
        )}
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="kv-label">Issue date</dt>
            <dd className="mt-0.5">{fmtDate(doc.issueDate)}</dd>
          </div>
          <div>
            <dt className="kv-label">Expiry date</dt>
            <dd className="mt-0.5">{fmtDate(doc.expiryDate)}</dd>
          </div>
        </dl>
      </Section>

      <Section icon={ScanText} title="Document fields">
        <ExtractedFieldsTable doc={doc} />
      </Section>

      <Section icon={Fingerprint} title="Integrity indicators" defaultOpen={(doc.forensics?.flags?.length ?? 0) > 0}>
        <p className="mb-3 text-xs text-muted-foreground">These are preliminary indicators, not proof of forgery. Confirm them against the original.</p>
        <ForensicsCard doc={doc} />
      </Section>

      <Section icon={ScanText} title="Recognised text" defaultOpen={false}>
        <OcrPreview doc={doc} />
      </Section>
    </div>
  );
}
