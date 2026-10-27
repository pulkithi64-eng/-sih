import { useMemo, useState } from "react";
import { ScrollText, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { useAudit } from "@/lib/hooks";
import { humanize } from "@/lib/labels";
import { AuditTimeline, ChainVerifyButton } from "../components/AuditTimeline";
import { Panel } from "../components/Panel";
import { TableSkeleton } from "../components/Skeletons";

export default function AuditPage() {
  const [entityId, setEntityId] = useState("");
  const [applied, setApplied] = useState("");
  const [action, setAction] = useState("ALL");
  const [actor, setActor] = useState("");
  const [limit, setLimit] = useState(200);
  const q = useAudit({ entityId: applied || undefined, action: action === "ALL" ? undefined : action, limit });
  const all = q.data ?? [];
  const actions = useMemo(() => [...new Set(all.map((e) => e.action))].sort(), [all]);
  const events = all
    .filter((e) => !actor || `${e.actor} ${e.actorRole}`.toLowerCase().includes(actor.toLowerCase()))
    .sort((a, b) => +new Date(b.ts) - +new Date(a.ts));

  return (
    <div>
      <PageHeader
        title="Audit log"
        description="Every action in VeriSense is recorded in an append-only log. Each event includes the SHA-256 hash of the previous event, so any alteration breaks the chain."
        actions={<ChainVerifyButton />}
      />
      <Panel
        flush
        title={
          <span className="flex flex-wrap items-center gap-2">
            <form
              className="relative"
              onSubmit={(e) => {
                e.preventDefault();
                setApplied(entityId.trim());
              }}
            >
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
                onBlur={() => setApplied(entityId.trim())}
                placeholder="Entity ID"
                className="h-8 w-44 pl-8 font-normal"
                aria-label="Filter by entity ID"
              />
            </form>
            <Input value={actor} onChange={(e) => setActor(e.target.value)} placeholder="Actor" className="h-8 w-36 font-normal" aria-label="Filter by actor" />
            <Select value={action} onValueChange={setAction}>
              <SelectTrigger className="h-8 w-auto min-w-[180px] font-normal" aria-label="Filter by action">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All actions</SelectItem>
                {(action !== "ALL" && !actions.includes(action) ? [action, ...actions] : actions).map((a) => (
                  <SelectItem key={a} value={a}>
                    {humanize(a)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={String(limit)} onValueChange={(v) => setLimit(Number(v))}>
              <SelectTrigger className="h-8 w-auto font-normal" aria-label="Number of events">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[100, 200, 500, 1000].map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    Last {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </span>
        }
        actions={<span className="text-xs text-muted-foreground">{events.length} events</span>}
      >
        <div className="p-4">
          {q.isLoading ? (
            <TableSkeleton rows={8} cols={1} />
          ) : q.isError ? (
            <ErrorState error={q.error} onRetry={() => q.refetch()} />
          ) : events.length === 0 ? (
            <EmptyState icon={ScrollText} title="No events match" />
          ) : (
            <AuditTimeline events={events} showEntity />
          )}
        </div>
      </Panel>
    </div>
  );
}
