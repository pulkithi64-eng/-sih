import { useState } from "react";
import { ExternalLink, FileWarning, Layers, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useBlobUrl } from "@/lib/hooks";
import type { DocumentT } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface Box {
  bbox: number[];
  label?: string;
  tone?: "red" | "blue" | "green" | "amber";
}

const TONE: Record<string, string> = {
  red: "border-red-600 bg-red-500/10",
  blue: "border-blue-600 bg-blue-500/10",
  green: "border-green-600 bg-green-500/10",
  amber: "border-amber-500 bg-amber-400/10",
};

/** Normalise a bbox to percentages. Accepts [x1,y1,x2,y2] in px or 0-1, or {x,y,w,h}. */
export function bboxToPct(b: any, natural: { w: number; h: number } | null): { left: number; top: number; width: number; height: number } | null {
  if (!b) return null;
  let x1: number, y1: number, x2: number, y2: number;
  if (Array.isArray(b) && b.length >= 4) {
    if (Array.isArray(b[0])) {
      // polygon [[x,y],...]
      const xs = b.map((p: number[]) => p[0]);
      const ys = b.map((p: number[]) => p[1]);
      [x1, y1, x2, y2] = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
    } else [x1, y1, x2, y2] = b.map(Number);
  } else if (typeof b === "object" && "x" in b) {
    x1 = b.x;
    y1 = b.y;
    x2 = b.x + (b.w ?? b.width);
    y2 = b.y + (b.h ?? b.height);
  } else return null;
  const normalised = Math.max(x1, y1, x2, y2) <= 1.0001;
  // Some producers send [x, y, w, h]; if x2 < x1 treat as width/height.
  if (x2 < x1 || y2 < y1) {
    x2 = x1 + x2;
    y2 = y1 + y2;
  }
  const W = normalised ? 1 : natural?.w;
  const H = normalised ? 1 : natural?.h;
  if (!W || !H) return null;
  return { left: (x1 / W) * 100, top: (y1 / H) * 100, width: ((x2 - x1) / W) * 100, height: ((y2 - y1) / H) * 100 };
}

export function ImageWithBoxes({
  src,
  alt,
  boxes = [],
  overlaySrc,
  overlayOpacity = 0.6,
  className,
  imgClassName,
}: {
  src: string;
  alt: string;
  boxes?: Box[];
  overlaySrc?: string | null;
  overlayOpacity?: number;
  className?: string;
  imgClassName?: string;
}) {
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  return (
    <div className={cn("relative inline-block max-w-full", className)}>
      <img
        src={src}
        alt={alt}
        className={cn("block max-h-[70vh] max-w-full", imgClassName)}
        onLoad={(e) => setNatural({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
      />
      {overlaySrc && (
        <img
          src={overlaySrc}
          alt="Error level analysis heatmap"
          className="pointer-events-none absolute inset-0 h-full w-full mix-blend-multiply"
          style={{ opacity: overlayOpacity }}
        />
      )}
      {boxes.map((b, i) => {
        const p = bboxToPct(b.bbox, natural);
        if (!p) return null;
        return (
          <div
            key={i}
            className={cn("pointer-events-none absolute border-2", TONE[b.tone ?? "red"])}
            style={{ left: `${p.left}%`, top: `${p.top}%`, width: `${p.width}%`, height: `${p.height}%` }}
          >
            {b.label && (
              <span
                className={cn(
                  "absolute -top-5 left-[-2px] whitespace-nowrap rounded-sm px-1 text-[10px] font-medium leading-4 text-white",
                  b.tone === "blue" ? "bg-blue-600" : b.tone === "green" ? "bg-green-600" : b.tone === "amber" ? "bg-amber-500" : "bg-red-600",
                )}
              >
                {b.label}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function DocumentViewer({
  doc,
  page,
  canSeeEla,
  regionBoxes = [],
}: {
  doc: DocumentT;
  page?: number | null;
  canSeeEla: boolean;
  regionBoxes?: Box[];
}) {
  const file = useBlobUrl(`/documents/${doc.id}/file`);
  const [ela, setEla] = useState(false);
  const [opacity, setOpacity] = useState(60);
  const elaAvailable = canSeeEla && doc.forensics?.hasElaHeatmap;
  const elaBlob = useBlobUrl(ela && elaAvailable ? `/documents/${doc.id}/ela` : null);
  const mime = file.type || doc.mimeType || "";
  const isPdf = mime.includes("pdf") || doc.fileName.toLowerCase().endsWith(".pdf");
  const isImage = mime.startsWith("image/") || /\.(png|jpe?g|webp|gif|bmp|tiff?)$/i.test(doc.fileName);

  return (
    <div className="card-surface flex min-h-[420px] flex-col overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b px-3 py-2">
        <p className="min-w-0 flex-1 truncate text-sm font-medium" title={doc.fileName}>
          {doc.fileName}
        </p>
        {elaAvailable && (
          <div className="flex items-center gap-2">
            <Switch id={`ela-${doc.id}`} checked={ela} onCheckedChange={setEla} />
            <Label htmlFor={`ela-${doc.id}`} className="flex cursor-pointer items-center gap-1 text-xs font-medium">
              <Layers className="h-3.5 w-3.5" /> ELA heatmap
            </Label>
            {ela && isImage && (
              <Slider
                value={[opacity]}
                onValueChange={(v) => setOpacity(v[0])}
                min={10}
                max={100}
                step={5}
                className="w-20"
                aria-label="Heatmap opacity"
              />
            )}
          </div>
        )}
        {file.url && (
          <Button asChild variant="ghost" size="sm" className="h-7 px-2">
            <a href={file.url} target="_blank" rel="noreferrer">
              <ExternalLink className="mr-1 h-3.5 w-3.5" /> Open
            </a>
          </Button>
        )}
      </div>
      <div className="relative flex flex-1 items-start justify-center overflow-auto bg-slate-100 p-3">
        {file.loading ? (
          <div className="flex h-80 items-center justify-center text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading original file…
          </div>
        ) : file.error ? (
          <div className="flex h-80 flex-col items-center justify-center text-center text-sm text-muted-foreground">
            <FileWarning className="mb-2 h-6 w-6" />
            Could not load the original file.
            <span className="mt-1 text-xs">{file.error}</span>
          </div>
        ) : ela && isPdf ? (
          elaBlob.loading ? (
            <div className="flex h-80 items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Rendering heatmap…
            </div>
          ) : elaBlob.url ? (
            <div className="text-center">
              <ImageWithBoxes src={elaBlob.url} alt="ELA heatmap of first page" boxes={regionBoxes} className="bg-white shadow-card" />
              <p className="mt-2 text-xs text-muted-foreground">ELA heatmap of the rasterised first page. Bright areas recompress differently.</p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{elaBlob.error ?? "Heatmap unavailable."}</p>
          )
        ) : isPdf && file.url ? (
          <iframe
            key={`${file.url}-${page ?? 1}`}
            src={`${file.url}#page=${page ?? 1}&view=FitH`}
            title={`Original document: ${doc.fileName}`}
            className="h-[72vh] min-h-[420px] w-full rounded bg-white shadow-card"
          />
        ) : isImage && file.url ? (
          <ImageWithBoxes
            src={file.url}
            alt={doc.fileName}
            boxes={ela ? regionBoxes : []}
            overlaySrc={ela ? elaBlob.url : null}
            overlayOpacity={opacity / 100}
            className="bg-white shadow-card"
          />
        ) : (
          <div className="flex h-80 flex-col items-center justify-center text-sm text-muted-foreground">
            Preview not available for this file type.
            {file.url && (
              <a href={file.url} download={doc.fileName} className="mt-2 text-primary-600 hover:underline">
                Download file
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
