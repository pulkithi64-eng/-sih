import { History } from "lucide-react";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { useAudit } from "@/lib/hooks";
import type { ApplicationDetail } from "@/lib/types";
import { isOfficerPlus, useAuth } from "../../auth";
import { AuditTimeline, ChainVerifyButton } from "../../components/AuditTimeline";
import { Panel } from "../../components/Panel";
import { TableSkeleton } from "../../components/Skeletons";

export default function AuditTab({ app }: { app: ApplicationDetail }) {
  const { user } = useAuth();
  const officer = isOfficerPlus(user?.role);
  const q = useAudit({ entityId: String(app.id), limit: 500 }, officer);

  if (!officer)
    return (
      <EmptyState
        icon={History}
        title="Audit trail is visible to AICTE officials"
        description="Every action on your application is recorded in a tamper-evident log reviewed by AICTE."
      />
    );

  const events = [...(q.data ?? [])].sort((a, b) => +new Date(b.ts) - +new Date(a.ts));
  return (
    <Panel
      title="Audit trail"
      description="Hash-chained record of every action on this application. Each event stores the hash of the previous one."
      actions={<ChainVerifyButton />}
    >
      {q.isLoading ? (
        <TableSkeleton rows={5} cols={1} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} />
      ) : events.length === 0 ? (
        <EmptyState compact icon={History} title="No events recorded" />
      ) : (
        <AuditTimeline events={events} />
      )}
    </Panel>
  );
}
