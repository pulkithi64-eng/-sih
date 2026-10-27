import { useState } from "react";
import { ArrowUpRight, Camera, Eye, EyeOff, ImageOff, Loader2, ScanEye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AdvisoryNote, AdvisoryTag } from "@/components/common/AdvisoryNote";
import { EmptyState } from "@/components/common/EmptyState";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { useBlobUrl } from "@/lib/hooks";
import { fmtDateTime, fmtNumber, fmtValue } from "@/lib/format";
import { humanize } from "@/lib/labels";
import type { ApplicationDetail, DocumentT, Finding, Id } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ImageWithBoxes } from "../../components/DocumentViewer";
import { ConfidenceMeter } from "../../components/DocumentAnalysis";

function flagText(f: any): { code: string; reason: string; severity?: string } {
  if (typeof f === "string") return { code: f, reason: humanize(f) };
  return { code: f.code ?? "", reason: f.reason ?? humanize(f.code), severity: f.severity };
}

export default function InfraTab({ app, onOpenDocument }: { app: ApplicationDetail; onOpenDocument: (id: Id) => void }) {
  const docs = (app.documents ?? []).filter((d) => d.infra || d.docType.startsWith("INFRA_PHOTO"));
  const infraFindings = (app.findings ?? []).filter((f) => f.kind === "INFRASTRUCTURE");
  const general = infraFindings.filter((f) => !f.documentId);
  const suggestInspection =
    infraFindings.some((f) => (f.severity === "CRITICAL" || f.severity === "MAJOR") && (f.status === "OPEN" || f.status === "ESCALATED")) ||
    docs.some((d) => (d.infra?.flags ?? []).length > 0);

  if (!docs.length)
    return (
      <EmptyState
        icon={Camera}
        title="No infrastructure evidence"
        description="Geo-tagged photographs of classrooms, laboratories, library and accessibility features appear here once uploaded."
      />
    );

  return (
    <div className="space-y-4">
      {suggestInspection && (
        <div className="flex items-start gap-3 rounded-lg border border-violet-200 bg-violet-50 px-4 py-3">
          <ScanEye className="mt-0.5 h-5 w-5 shrink-0 text-violet-700" aria-hidden />
          <div>
            <p className="text-sm font-semibold text-violet-900">Physical inspection suggested</p>
            <p className="mt-0.5 text-sm text-violet-900/80">
              Photographic evidence does not fully support the declared infrastructure (counts below norm, quality or metadata concerns). An
              expert-committee visit may be warranted.
            </p>
          </div>
          <AdvisoryTag className="ml-auto shrink-0" />
        </div>
      )}

      {general.length > 0 && (
        <div className="card-surface divide-y">
          {general.map((f) => (
            <InfraFindingRow key={f.id} f={f} />
          ))}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {docs.map((d) => (
          <InfraCard
            key={d.id}
            doc={d}
            findings={infraFindings.filter((f) => String(f.documentId) === String(d.id))}
            onOpen={() => onOpenDocument(d.id)}
          />
        ))}
      </div>
      <AdvisoryNote>Object detection counts are estimates from a single photograph and are not a substitute for physical verification.</AdvisoryNote>
    </div>
  );
}

function InfraFindingRow({ f }: { f: Finding }) {
  return (
    <div className="flex items-start gap-2 px-4 py-2.5">
      <SeverityBadge severity={f.severity} className="mt-0.5" />
      <div className="min-w-0">
        <p className="text-sm font-medium">{f.title}</p>
        <p className="text-xs text-muted-foreground">{f.reason}</p>
      </div>
    </div>
  );
}

function InfraCard({ doc, findings, onOpen }: { doc: DocumentT; findings: Finding[]; onOpen: () => void }) {
  const img = useBlobUrl(`/documents/${doc.id}/file`);
  const [boxes, setBoxes] = useState(true);
  const infra = doc.infra;
  const detections = infra?.detections ?? [];
  const counts = Object.entries(infra?.counts ?? {});
  const required: Record<string, any> = infra?.required ?? infra?.requirement ?? infra?.requirements ?? {};
  const quality = infra?.quality ?? {};
  const exif = infra?.exif ?? {};
  const flags = (infra?.flags ?? []).map(flagText);
  const isImage = (img.type || doc.mimeType || "").startsWith("image/");

  return (
    <article className="card-surface flex flex-col overflow-hidden">
      <div className="relative flex min-h-[200px] items-center justify-center bg-slate-100">
        {img.loading ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : img.url && isImage ? (
          <ImageWithBoxes
            src={img.url}
            alt={doc.docTypeLabel}
            imgClassName="max-h-72"
            boxes={boxes ? detections.map((d) => ({ bbox: d.bbox, label: `${d.label} ${Math.round((d.conf <= 1 ? d.conf * 100 : d.conf))}%`, tone: "blue" as const })) : []}
          />
        ) : (
          <div className="flex flex-col items-center text-xs text-muted-foreground">
            <ImageOff className="mb-1 h-5 w-5" /> {img.error ?? "Preview not available"}
          </div>
        )}
        {detections.length > 0 && (
          <Button
            size="sm"
            variant="secondary"
            className="absolute right-2 top-2 h-7 bg-white/90 px-2 text-xs shadow-card"
            onClick={() => setBoxes((b) => !b)}
            aria-pressed={boxes}
          >
            {boxes ? <EyeOff className="mr-1 h-3.5 w-3.5" /> : <Eye className="mr-1 h-3.5 w-3.5" />}
            {boxes ? "Hide" : "Show"} detections
          </Button>
        )}
      </div>
      <div className="flex-1 space-y-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold">{doc.docTypeLabel || humanize(doc.docType)}</h3>
            <p className="truncate text-xs text-muted-foreground">{humanize(infra?.evidenceType ?? doc.docType)}</p>
          </div>
          <button type="button" onClick={onOpen} className="inline-flex shrink-0 items-center gap-0.5 text-xs font-medium text-primary-600 hover:underline">
            Details <ArrowUpRight className="h-3 w-3" />
          </button>
        </div>

        {counts.length > 0 && (
          <div>
            <p className="kv-label mb-1">Detected objects</p>
            <ul className="divide-y rounded-md border text-sm">
              {counts.map(([k, v]) => {
                const req = Number(required?.[k] ?? required?.minCount?.[k] ?? NaN);
                const short = Number.isFinite(req) && Number(v) < req;
                return (
                  <li key={k} className={cn("flex items-center justify-between px-2.5 py-1.5", short && "bg-red-50/60")}>
                    <span>{humanize(k)}</span>
                    <span className="tabular">
                      <span className={cn("font-semibold", short && "text-red-700")}>{fmtNumber(v)}</span>
                      {Number.isFinite(req) && <span className="text-muted-foreground"> / {req} required</span>}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
          {quality.blurScore !== undefined && (
            <div>
              <dt className="kv-label">Sharpness</dt>
              <dd className="tabular mt-0.5">{fmtValue(quality.blurScore)}</dd>
            </div>
          )}
          {quality.brightness !== undefined && (
            <div>
              <dt className="kv-label">Brightness</dt>
              <dd className="tabular mt-0.5">{fmtValue(quality.brightness)}</dd>
            </div>
          )}
          <div>
            <dt className="kv-label">Taken</dt>
            <dd className="mt-0.5">{exif.takenAt ? fmtDateTime(exif.takenAt) : <span className="text-amber-700">No EXIF date</span>}</dd>
          </div>
          <div>
            <dt className="kv-label">GPS</dt>
            <dd className="mono mt-0.5">
              {exif.gps
                ? typeof exif.gps === "object"
                  ? `${Number(exif.gps.lat ?? exif.gps[0]).toFixed(4)}, ${Number(exif.gps.lng ?? exif.gps.lon ?? exif.gps[1]).toFixed(4)}`
                  : String(exif.gps)
                : <span className="font-sans text-amber-700">Not tagged</span>}
            </dd>
          </div>
          {exif.device && (
            <div className="col-span-2">
              <dt className="kv-label">Device</dt>
              <dd className="mt-0.5">{exif.device}</dd>
            </div>
          )}
        </dl>

        {detections.length > 0 && (
          <details className="text-xs">
            <summary className="cursor-pointer font-medium text-muted-foreground">{detections.length} detections</summary>
            <ul className="mt-1.5 space-y-1">
              {detections.slice(0, 30).map((d, i) => (
                <li key={i} className="flex items-center justify-between">
                  <span>{humanize(d.label)}</span>
                  <ConfidenceMeter value={d.conf} />
                </li>
              ))}
            </ul>
          </details>
        )}

        {(flags.length > 0 || findings.length > 0) && (
          <ul className="space-y-1.5">
            {flags.map((f, i) => (
              <li key={`f${i}`} className="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-900">
                <span className="mono mr-1 text-2xs">{f.code}</span>
                {f.reason}
              </li>
            ))}
            {findings.map((f) => (
              <li key={f.id} className="flex items-start gap-1.5 rounded-md border px-2.5 py-1.5 text-xs">
                <SeverityBadge severity={f.severity} />
                <span>{f.title}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  );
}
