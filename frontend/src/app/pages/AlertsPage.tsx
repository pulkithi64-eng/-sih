import { useState } from "react";
import { Link } from "react-router-dom";
import { Bell, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { SeverityBadge, severityDot } from "@/components/common/SeverityBadge";
import { useAlerts, useMarkAlertRead } from "@/lib/hooks";
import { fmtDateTime, fmtRelative } from "@/lib/format";
import { humanize, SEVERITY_ORDER } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

export default function AlertsPage() {
  const q = useAlerts();
  const mark = useMarkAlertRead();
  const [filter, setFilter] = useState<"all" | "unread">("unread");
  const [sev, setSev] = useState<string>("ALL");
  const all = [...(q.data ?? [])].sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt));
  const unread = all.filter((a) => !a.read);
  const shown = all.filter((a) => (filter === "all" || !a.read) && (sev === "ALL" || a.severity === sev));

  return (
    <div>
      <PageHeader
        title="Alerts"
        description="Notifications raised by validation, verification and workflow events."
        actions={
          (
            <Button size="sm" variant="outline" disabled={q.isLoading || unread.length === 0 || mark.isPending} onClick={() => unread.forEach((a) => mark.mutate(a.id))}>
              <CheckCheck className="mr-1.5 h-4 w-4" /> Mark all read
            </Button>
          )
        }
      />
      <div className="card-surface">
        <div className="flex flex-wrap items-center gap-3 border-b p-3">
          <ToggleGroup type="single" value={filter} onValueChange={(v) => v && setFilter(v as "all" | "unread")} className="rounded-md border p-0.5">
            <ToggleGroupItem value="unread" className="h-7 min-w-24 px-2.5 text-xs tabular-nums data-[state=on]:bg-navy data-[state=on]:text-white">
              Unread ({unread.length})
            </ToggleGroupItem>
            <ToggleGroupItem value="all" className="h-7 min-w-24 px-2.5 text-xs tabular-nums data-[state=on]:bg-navy data-[state=on]:text-white">
              All ({all.length})
            </ToggleGroupItem>
          </ToggleGroup>
          <ToggleGroup type="single" value={sev} onValueChange={(v) => v && setSev(v)} className="rounded-md border p-0.5" aria-label="Severity">
            {["ALL", ...SEVERITY_ORDER].map((s) => (
              <ToggleGroupItem key={s} value={s} className="h-7 px-2.5 text-xs data-[state=on]:bg-navy data-[state=on]:text-white">
                {s === "ALL" ? "Any severity" : humanize(s)}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
        {q.isLoading ? (
          <ul className="divide-y" aria-busy="true" aria-label="Loading alerts">
            {Array.from({ length: 6 }, (_, index) => (
              <li key={index} className="min-h-36 space-y-3 px-4 py-3 sm:min-h-28">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-36" />
              </li>
            ))}
          </ul>
        ) : q.isError ? (
          <ErrorState error={q.error} onRetry={() => q.refetch()} />
        ) : shown.length === 0 ? (
          <EmptyState icon={Bell} title={filter === "unread" ? "You're all caught up" : "No alerts"} />
        ) : (
          <ul className="divide-y">
            {shown.map((a) => (
              <li key={a.id} className={cn("flex min-h-36 items-start gap-3 px-4 py-3 sm:min-h-28", !a.read && "bg-navy-50/40")}>
                <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", severityDot(a.severity))} aria-hidden />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={a.severity} />
                    <span className="text-xs text-muted-foreground">{humanize(a.type)}</span>
                    <span className="ml-auto text-xs text-muted-foreground" title={fmtDateTime(a.createdAt)}>
                      {fmtRelative(a.createdAt)}
                    </span>
                  </div>
                  <p className={cn("mt-1 break-words text-sm", !a.read && "font-medium")}>{a.message}</p>
                  <div className="mt-1 flex items-center gap-3 text-xs">
                    <Link
                      to={`/portal/applications/${a.applicationId}`}
                      className="mono text-primary-600 hover:underline"
                      onClick={() => !a.read && mark.mutate(a.id)}
                    >
                      {a.applicationNo}
                    </Link>
                    {!a.read && (
                      <button type="button" className="text-muted-foreground hover:text-foreground" onClick={() => mark.mutate(a.id)}>
                        Mark read
                      </button>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
