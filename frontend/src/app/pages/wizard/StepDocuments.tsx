import { useRef, useState } from "react";
import { CheckCircle2, CircleDashed, FileText, Loader2, Trash2, UploadCloud, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { AdvisoryTag } from "@/components/common/AdvisoryNote";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { api, errorMessage } from "@/lib/api";
import { useInvalidateApp, useMeta } from "@/lib/hooks";
import { confPct, fmtBytes } from "@/lib/format";
import { humanize } from "@/lib/labels";
import type { ApplicationDetail, ChecklistItem, DocumentT } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Panel } from "../../components/Panel";

interface UploadJob {
  key: string;
  file: File;
  docType?: string;
  state: "uploading" | "done" | "error";
  doc?: DocumentT;
  error?: string;
  stage: number;
}

const STAGES = ["Uploading", "Reading text (OCR)", "Classifying", "Extracting fields", "Forensic checks", "Verifying with issuer"];

function Dropzone({ onFiles, compact, label }: { onFiles: (f: File[]) => void; compact?: boolean; label?: string }) {
  const ref = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const files = Array.from(e.dataTransfer.files ?? []);
        if (files.length) onFiles(files);
      }}
      className={cn(
        "flex items-center justify-center rounded-md border-2 border-dashed text-center transition-colors",
        compact ? "gap-2 px-3 py-2" : "flex-col gap-2 px-6 py-8",
        over ? "border-primary-600 bg-navy-50" : "border-input bg-background hover:border-primary-600/50",
      )}
    >
      <UploadCloud className={cn("text-muted-foreground", compact ? "h-4 w-4" : "h-7 w-7")} aria-hidden />
      <p className={cn("text-muted-foreground", compact ? "text-xs" : "text-sm")}>
        {label ?? "Drag and drop files here, or"}{" "}
        <button type="button" onClick={() => ref.current?.click()} className="font-medium text-primary-600 hover:underline">
          browse
        </button>
      </p>
      {!compact && <p className="text-xs text-muted-foreground">PDF, JPG or PNG · up to 20 MB each</p>}
      <input
        ref={ref}
        type="file"
        className="sr-only"
        multiple={!compact}
        accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/png,image/jpeg"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) onFiles(files);
          e.target.value = "";
        }}
      />
    </div>
  );
}

export function evaluateChecklist(items: ChecklistItem[] | undefined, formData: Record<string, any>): ChecklistItem[] {
  return (items ?? []).filter((it: any) => {
    const cond = it.when;
    if (!cond) return true;
    const field = String(cond.field ?? "").replace(/^formData\./, "");
    const v = formData?.[field];
    if ("truthy" in cond) return !!v === !!cond.truthy;
    if ("equals" in cond) return v === cond.equals;
    return true;
  });
}

export default function StepDocuments({ app, checklist }: { app: ApplicationDetail; checklist: ChecklistItem[] }) {
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const inv = useInvalidateApp();
  const meta = useMeta();
  const docs = app.documents ?? [];

  async function upload(files: File[], docType?: string) {
    for (const file of files) {
      const key = `${Date.now()}-${Math.random()}`;
      const job: UploadJob = { key, file, docType, state: "uploading", stage: 0 };
      setJobs((j) => [job, ...j]);
      const timer = setInterval(() => setJobs((js) => js.map((x) => (x.key === key && x.stage < STAGES.length - 1 ? { ...x, stage: x.stage + 1 } : x))), 700);
      try {
        const doc = await api.uploadDocument(app.id, file, docType);
        setJobs((js) => js.map((x) => (x.key === key ? { ...x, state: "done", doc } : x)));
        inv(app.id);
      } catch (e) {
        setJobs((js) => js.map((x) => (x.key === key ? { ...x, state: "error", error: errorMessage(e) } : x)));
        toast.error(`Upload failed: ${file.name}`, { description: errorMessage(e) });
      } finally {
        clearInterval(timer);
      }
    }
  }

  async function remove(d: DocumentT) {
    try {
      await api.deleteDocument(d.id);
      setJobs((js) => js.filter((j) => j.doc?.id !== d.id));
      inv(app.id);
      toast.success("Document removed");
    } catch (e) {
      toast.error("Could not remove document", { description: errorMessage(e) });
    }
  }

  const byType = new Map<string, DocumentT[]>();
  docs.forEach((d) => byType.set(d.docType, [...(byType.get(d.docType) ?? []), d]));
  const checklistTypes = new Set(checklist.map((c) => c.docType));
  const others = docs.filter((d) => !checklistTypes.has(d.docType));
  const mandatoryDone = checklist.filter((c) => c.mandatory && byType.has(c.docType)).length;
  const mandatoryTotal = checklist.filter((c) => c.mandatory).length;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="space-y-4">
        <Panel
          title="Required documents"
          description={`${mandatoryDone} of ${mandatoryTotal} mandatory documents uploaded`}
          flush
        >
          <ul className="divide-y">
            {checklist.map((c) => {
              const have = byType.get(c.docType) ?? [];
              return (
                <li key={c.docType} className="px-4 py-3">
                  <div className="flex flex-wrap items-start gap-3">
                    {have.length ? (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-700" aria-label="Uploaded" />
                    ) : (
                      <CircleDashed className={cn("mt-0.5 h-4 w-4 shrink-0", c.mandatory ? "text-red-600" : "text-slate-400")} aria-label="Not uploaded" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">
                        {c.label || humanize(c.docType)}
                        {!c.mandatory && <span className="ml-1.5 rounded bg-muted px-1 text-2xs font-normal text-muted-foreground">Optional</span>}
                      </p>
                      {c.clause && <p className="text-xs text-muted-foreground">{c.clause}</p>}
                      {have.map((d) => (
                        <DocLine key={d.id} d={d} onRemove={() => remove(d)} />
                      ))}
                    </div>
                    <div className="w-full sm:w-56">
                      <Dropzone compact label={have.length ? "Replace or add:" : "Drop file or"} onFiles={(f) => upload(f.slice(0, 1), c.docType)} />
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </Panel>

        <Panel title="Other documents" description="Upload anything else; VeriSense will classify it automatically.">
          <Dropzone onFiles={(f) => upload(f)} />
          {others.length > 0 && (
            <div className="mt-3 space-y-1">
              {others.map((d) => (
                <DocLine key={d.id} d={d} onRemove={() => remove(d)} />
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Live processing results" description="Each file is analysed as soon as it is uploaded" actions={<AdvisoryTag />} className="xl:sticky xl:top-20 xl:self-start">
        {jobs.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">Upload a document to see classification, verification and integrity checks.</p>
        ) : (
          <ul className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
            {jobs.map((j) => (
              <JobCard key={j.key} job={j} docTypeLabel={(id) => meta.data?.docTypes?.find((t) => t.id === id)?.label ?? humanize(id)} />
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function DocLine({ d, onRemove }: { d: DocumentT; onRemove: () => void }) {
  return (
    <div className="mt-1.5 flex items-center gap-2 rounded border bg-slate-50 px-2 py-1">
      <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1 truncate text-xs">{d.fileName}</span>
      <StatusBadge status={d.verification?.status ?? "VERIFICATION_PENDING"} kind="verification" className="hidden sm:inline-flex" />
      {(d.forensics?.flags?.length ?? 0) > 0 && <span className="rounded bg-red-50 px-1 text-2xs font-medium text-red-800">{d.forensics.flags.length} flag(s)</span>}
      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onRemove} aria-label={`Remove ${d.fileName}`}>
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function JobCard({ job, docTypeLabel }: { job: UploadJob; docTypeLabel: (id: string) => string }) {
  const d = job.doc;
  return (
    <li className="rounded-md border p-3">
      <div className="flex items-start gap-2">
        {job.state === "uploading" ? (
          <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary-600" />
        ) : job.state === "done" ? (
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-700" />
        ) : (
          <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-700" />
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{job.file.name}</p>
          <p className="text-xs text-muted-foreground">{fmtBytes(job.file.size)}</p>
        </div>
      </div>
      {job.state === "uploading" && (
        <ol className="mt-2 space-y-0.5 pl-6 text-xs">
          {STAGES.map((s, i) => (
            <li key={s} className={cn(i < job.stage ? "text-green-700" : i === job.stage ? "font-medium text-foreground" : "text-muted-foreground/60")}>
              {i < job.stage ? "✓ " : i === job.stage ? "› " : "  "}
              {s}
            </li>
          ))}
        </ol>
      )}
      {job.state === "error" && <p className="mt-2 pl-6 text-xs text-red-700">{job.error}</p>}
      {d && (
        <div className="mt-2 space-y-2 pl-6">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            <span className="text-muted-foreground">Classified as</span>
            <span className="font-medium">{docTypeLabel(d.classification?.docType ?? d.docType)}</span>
            <span className="tabular text-muted-foreground">({confPct(d.classification?.confidence)}%)</span>
            {job.docType && d.classification?.docType && d.classification.docType !== job.docType && (
              <span className="rounded bg-amber-50 px-1 text-amber-800">differs from slot: {docTypeLabel(job.docType)}</span>
            )}
          </div>
          <StatusBadge status={d.verification?.status ?? "VERIFICATION_PENDING"} kind="verification" />
          {d.verification?.reason && <p className="text-xs text-muted-foreground">{d.verification.reason}</p>}
          {(d.forensics?.flags ?? []).map((f, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs">
              <SeverityBadge severity={String(f.severity)} />
              <span>{f.reason}</span>
            </div>
          ))}
          {Object.keys(d.extractedFields ?? {}).length > 0 && (
            <p className="text-xs text-muted-foreground">
              Extracted: {Object.keys(d.extractedFields).slice(0, 5).map(humanize).join(", ")}
              {Object.keys(d.extractedFields).length > 5 ? "…" : ""}
            </p>
          )}
        </div>
      )}
    </li>
  );
}

