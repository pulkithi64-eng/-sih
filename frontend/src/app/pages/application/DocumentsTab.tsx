import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { FileImage, FileText, FolderOpen } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";
import { StatusBadge, getStatusDef, TONE_DOT } from "@/components/common/StatusBadge";
import { useVerifyDocument } from "@/lib/hooks";
import { humanize } from "@/lib/labels";
import type { ApplicationDetail, DocumentT } from "@/lib/types";
import { cn } from "@/lib/utils";
import { isOfficerPlus, useAuth } from "../../auth";
import DocumentAnalysis from "../../components/DocumentAnalysis";
import { DocumentViewer, type Box } from "../../components/DocumentViewer";

export function regionBoxesFor(doc: DocumentT, app?: ApplicationDetail): Box[] {
  const boxes: Box[] = [];
  const f = doc.forensics ?? ({} as DocumentT["forensics"]);
  (f.regions ?? []).forEach((r: any) => r?.bbox && boxes.push({ bbox: r.bbox, label: r.label ?? "ELA region", tone: "red" }));
  (f.flags ?? []).forEach((fl) => {
    const ev = fl.evidence;
    if (ev && typeof ev === "object") {
      if (Array.isArray(ev.bbox)) boxes.push({ bbox: ev.bbox, label: fl.code, tone: "red" });
      if (Array.isArray(ev.regions)) ev.regions.forEach((r: any) => boxes.push({ bbox: r.bbox ?? r, label: fl.code, tone: "red" }));
    }
  });
  (app?.findings ?? []).forEach((fi) =>
    fi.evidence?.forEach((e) => {
      if (e.type === "IMAGE_REGION" && e.bbox && String(e.documentId) === String(doc.id)) boxes.push({ bbox: e.bbox, label: e.label, tone: "amber" });
    }),
  );
  return boxes;
}

export default function DocumentsTab({ app }: { app: ApplicationDetail }) {
  const { user } = useAuth();
  const officer = isOfficerPlus(user?.role);
  const [sp, setSp] = useSearchParams();
  const docs = app.documents ?? [];
  const selId = sp.get("doc");
  const page = Number(sp.get("page")) || null;
  const idx = Math.max(0, docs.findIndex((d) => String(d.id) === selId));
  const doc = docs[idx];
  const verify = useVerifyDocument(app.id);

  useEffect(() => {
    if (docs.length && !selId) {
      const n = new URLSearchParams(sp);
      n.set("doc", String(docs[0].id));
      setSp(n, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs.length, selId]);

  const select = (d: DocumentT) => {
    const n = new URLSearchParams(sp);
    n.set("doc", String(d.id));
    n.delete("page");
    setSp(n, { replace: true });
  };

  if (!docs.length) return <EmptyState icon={FolderOpen} title="No documents uploaded" description="Documents uploaded by the institution appear here." />;

  const findingsByDoc = new Map<string, number>();
  (app.findings ?? []).forEach((f) => {
    if (f.documentId && (f.status === "OPEN" || f.status === "ESCALATED")) findingsByDoc.set(String(f.documentId), (findingsByDoc.get(String(f.documentId)) ?? 0) + 1);
  });

  return (
    <div className="space-y-4">
      {/* Document list (laptop & desktop screens) */}
      <nav aria-label="Documents" className="card-surface max-h-48 overflow-y-auto">
        <p className="border-b px-3 py-2 text-xs font-semibold text-muted-foreground">{docs.length} documents</p>
        <ul className="grid sm:grid-cols-2 xl:grid-cols-3">
          {docs.map((d) => {
            const def = getStatusDef(d.verification?.status ?? "VERIFICATION_PENDING", "verification");
            const n = findingsByDoc.get(String(d.id)) ?? 0;
            return (
              <li key={d.id}>
                <button
                  type="button"
                  onClick={() => select(d)}
                  aria-current={d.id === doc?.id ? "true" : undefined}
                  className={cn(
                    "flex w-full items-start gap-2 border-b border-l-2 px-3 py-2 text-left hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                    d.id === doc?.id ? "border-l-saffron bg-navy-50/70" : "border-l-transparent",
                  )}
                >
                  {d.mimeType?.startsWith("image/") ? (
                    <FileImage className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium" title={d.fileName}>{d.fileName}</span>
                    <span className="block truncate text-xs text-muted-foreground">{d.docTypeLabel || humanize(d.docType)}</span>
                    <span className="mt-0.5 flex items-center gap-1.5 text-2xs text-muted-foreground">
                      <span className={cn("h-1.5 w-1.5 rounded-full", TONE_DOT[def.tone])} aria-hidden />
                      {def.label}
                      {n > 0 && <span className="ml-auto rounded bg-red-100 px-1 font-semibold text-red-800">{n}</span>}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="min-w-0 space-y-3">
        {doc && (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold">{doc.docTypeLabel || humanize(doc.docType)}</h2>
              <StatusBadge status={doc.verification?.status ?? "VERIFICATION_PENDING"} kind="verification" />
              {page && <span className="text-xs text-muted-foreground">· showing page {page}</span>}
            </div>
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
              <DocumentViewer key={doc.id} doc={doc} page={page} canSeeEla={officer} regionBoxes={regionBoxesFor(doc, app)} />
              <DocumentAnalysis
                key={`a-${doc.id}`}
                doc={doc}
                onReverify={officer && app.status !== "DECIDED" ? () => verify.mutate(doc.id) : undefined}
                reverifying={verify.isPending}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
