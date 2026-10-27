import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpDown, ArrowRight, FilePlus2, FileStack, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { ProgressFraction, ScoreBar } from "@/components/common/ScoreBar";
import { RiskBandPill } from "@/components/common/SeverityBadge";
import { StatusBadge, getStatusDef } from "@/components/common/StatusBadge";
import { useApplications, useMeta } from "@/lib/hooks";
import { fmtDate } from "@/lib/format";
import { CATEGORY_LABEL, CATEGORY_SHORT, categoryLabel, REGION_LABEL } from "@/lib/labels";
import type { Application, ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { applicationStage, institutionNextAction } from "@/lib/journey";
import { isInstitution, useAuth } from "../auth";
import { TableSkeleton } from "../components/Skeletons";

const STATUSES: ApplicationStatus[] = [
  "DRAFT",
  "SUBMITTED",
  "UNDER_VALIDATION",
  "DEFICIENCIES_FLAGGED",
  "RECTIFICATION_REQUESTED",
  "SOURCE_VERIFICATION_PENDING",
  "UNDER_REVIEW",
  "INSPECTION_ORDERED",
  "RECOMMENDED",
  "DECIDED",
];

type SortKey = "applicationNo" | "institution" | "status" | "complianceScore" | "riskScore" | "critical" | "updatedAt";

function sortVal(a: Application, k: SortKey): string | number {
  switch (k) {
    case "institution":
      return a.institution?.name ?? "";
    case "critical":
      return (a.counts?.critical ?? 0) * 1000 + (a.counts?.major ?? 0);
    case "updatedAt":
      return +new Date(a.updatedAt);
    case "status":
      return STATUSES.indexOf(a.status);
    default:
      return (a as any)[k] ?? 0;
  }
}

export default function ApplicationsPage({ mine = false }: { mine?: boolean }) {
  const { user } = useAuth();
  const inst = isInstitution(user?.role);
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const filters = {
    status: sp.get("status") ?? undefined,
    category: sp.get("category") ?? undefined,
    region: sp.get("region") ?? undefined,
    riskBand: sp.get("riskBand") ?? undefined,
    q: sp.get("q") ?? undefined,
  };
  const [qDraft, setQDraft] = useState(filters.q ?? "");
  useEffect(() => setQDraft(filters.q ?? ""), [filters.q]);
  const [sort, setSort] = useState<{ k: SortKey; dir: 1 | -1 }>({ k: inst ? "updatedAt" : "riskScore", dir: -1 });
  const meta = useMeta();
  const apps = useApplications(filters);

  const rows = useMemo(() => {
    const list = [...(apps.data ?? [])];
    list.sort((a, b) => {
      const va = sortVal(a, sort.k);
      const vb = sortVal(b, sort.k);
      return (va < vb ? -1 : va > vb ? 1 : 0) * sort.dir;
    });
    return list;
  }, [apps.data, sort]);

  function setFilter(k: string, v: string | undefined) {
    const next = new URLSearchParams(sp);
    if (!v || v === "ALL") next.delete(k);
    else next.set(k, v);
    setSp(next, { replace: true });
  }

  const hasFilters = Object.values(filters).some(Boolean);
  const categories = meta.data?.categories?.length
    ? meta.data.categories
    : (Object.keys(CATEGORY_LABEL) as (keyof typeof CATEGORY_LABEL)[]).map((id) => ({ id, label: CATEGORY_LABEL[id] }));

  const header = (k: SortKey, label: string, cls?: string) => (
    <TableHead className={cls} aria-sort={sort.k === k ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
      <button
        type="button"
        className="inline-flex items-center gap-1 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        onClick={() => setSort((s) => ({ k, dir: s.k === k ? ((-s.dir) as 1 | -1) : -1 }))}
      >
        {label}
        {sort.k === k ? sort.dir === 1 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" /> : <ArrowUpDown className="h-3 w-3 opacity-40" />}
      </button>
    </TableHead>
  );

  return (
    <div>
      <PageHeader
        title={inst ? "My applications" : user?.role === "REGIONAL_DIRECTOR" ? "Decision queue" : user?.role === "SCRUTINY_OFFICER" ? "Review queue" : "Applications"}
        description={
          inst
            ? "Create an application, upload its documents and follow the review."
            : user?.role === "REGIONAL_DIRECTOR" ? "Review recommendations and record a reasoned final decision." : "Review the important findings and evidence for applications in your region."
        }
        actions={
          inst && (
            <Button asChild size="sm">
              <Link to="/portal/applications/new">
                <FilePlus2 className="mr-1.5 h-4 w-4" /> New application
              </Link>
            </Button>
          )
        }
      />

      {inst && <div className="mb-5 rounded-lg border bg-card px-4 py-3 text-sm text-muted-foreground">
        <p className="font-medium text-foreground">How to submit an application</p>
        <ol className="mt-2 flex flex-wrap gap-x-6 gap-y-2" aria-label="Application steps">
          <li>1. Create application</li><li>2. Upload documents</li><li>3. Check and correct</li><li>4. Submit for review</li>
        </ol>
      </div>}

      <div className="card-surface">
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <form
            className="relative min-w-[220px] flex-1"
            onSubmit={(e) => {
              e.preventDefault();
              setFilter("q", qDraft.trim() || undefined);
            }}
          >
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              value={qDraft}
              onChange={(e) => setQDraft(e.target.value)}
              onBlur={() => qDraft.trim() !== (filters.q ?? "") && setFilter("q", qDraft.trim() || undefined)}
              placeholder="Application no., institution name, permanent ID"
              className="h-9 pl-8"
              aria-label="Search applications"
            />
          </form>
          <FilterSelect label="Status" value={filters.status} onChange={(v) => setFilter("status", v)}
            options={STATUSES.map((s) => ({ value: s, label: getStatusDef(s, "application").label }))} />
          <FilterSelect label="Category" value={filters.category} onChange={(v) => setFilter("category", v)}
            options={categories.map((c) => ({ value: c.id, label: c.label }))} />
          {user?.role === "ADMIN" && (
            <FilterSelect label="Region" value={filters.region} onChange={(v) => setFilter("region", v)}
              options={Object.entries(REGION_LABEL).map(([k, v]) => ({ value: k, label: `${k} · ${v}` }))} />
          )}
          {!inst && <FilterSelect label="Risk band" value={filters.riskBand} onChange={(v) => setFilter("riskBand", v)}
            options={["HIGH", "MEDIUM", "LOW"].map((r) => ({ value: r, label: r.charAt(0) + r.slice(1).toLowerCase() }))} />
          }
          {hasFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setQDraft("");
                setSp(new URLSearchParams(), { replace: true });
              }}
            >
              <X className="mr-1 h-4 w-4" /> Clear
            </Button>
          )}
        </div>

        {apps.isLoading ? (
          <TableSkeleton rows={8} cols={7} />
        ) : apps.isError ? (
          <ErrorState error={apps.error} onRetry={() => apps.refetch()} />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={FileStack}
            title={hasFilters ? "No applications match these filters" : "No applications yet"}
            description={inst && !hasFilters ? "Start a new application to upload documents and run a pre-submission check." : undefined}
            action={
              inst && !hasFilters ? (
                <Button asChild size="sm">
                  <Link to="/portal/applications/new">New application</Link>
                </Button>
              ) : undefined
            }
          />
        ) : inst ? (
          <ul className="divide-y" aria-label="My applications">
            {rows.map((application) => {
              const next = institutionNextAction(application);
              const stage = applicationStage(application);
              return <li key={application.id} className="p-4 sm:p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2"><StatusBadge status={application.status} kind="application" /><span className="text-xs text-muted-foreground">AY {application.academicYear}</span></div>
                    <h2 className="mt-2 text-base font-semibold">{categoryLabel(application.category)}</h2>
                    <Link to={`/portal/applications/${application.id}`} className="mono mt-1 inline-block break-all text-xs text-primary-600 hover:underline">{application.applicationNo}</Link>
                    <p className="mt-2 max-w-xl text-sm text-muted-foreground">{next.description}</p>
                  </div>
                  <Button asChild size="sm" className="shrink-0 self-start"><Link to={next.to}>{next.label}<ArrowRight className="ml-2 h-4 w-4" /></Link></Button>
                </div>
                <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
                  <span>{application.counts?.documents ?? 0} documents uploaded</span>
                  <span>{application.counts?.findingsOpen ?? 0} unresolved findings</span>
                  <span>Updated {fmtDate(application.updatedAt)}</span>
                </div>
                <ol className="mt-3 grid grid-cols-5 gap-1 text-[10px] sm:text-xs" aria-label="Application progress">
                  {["Details", "Documents", "Review", "Decision", "Complete"].map((label, index) => <li key={label} aria-current={index === stage ? "step" : undefined} className={cn("border-t-2 pt-2", index <= stage ? "border-primary text-foreground" : "border-border text-muted-foreground")}>{index + 1}. {label}</li>)}
                </ol>
              </li>;
            })}
          </ul>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  {header("applicationNo", "Application")}
                  {header("institution", "Institution", "hidden min-w-[220px] md:table-cell")}
                  {header("status", "Status")}
                  {header("complianceScore", "Compliance", "hidden w-36 xl:table-cell")}
                  {header("riskScore", "Risk")}
                  {header("critical", "Critical / Major", "hidden text-right sm:table-cell")}
                  <TableHead className="hidden w-32 xl:table-cell">Verified docs</TableHead>
                  {header("updatedAt", "Updated", "hidden lg:table-cell")}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((a) => (
                  <TableRow
                    key={a.id}
                    className="cursor-pointer"
                    onClick={() => nav(`/portal/applications/${a.id}`)}
                  >
                    <TableCell>
                      <Link
                        to={`/portal/applications/${a.id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="mono font-medium text-primary-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {a.applicationNo}
                      </Link>
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {CATEGORY_SHORT[a.category] ?? categoryLabel(a.category)} · AY {a.academicYear}
                      </div>
                      <div className="mt-0.5 truncate text-xs text-foreground md:hidden">{a.institution?.name}</div>
                    </TableCell>
                    <TableCell className="hidden max-w-[320px] md:table-cell">
                      <div className="truncate font-medium">{a.institution?.name}</div>
                      <div className="truncate text-xs text-muted-foreground">
                        {a.institution?.city}, {a.institution?.state} · {a.region}
                      </div>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={a.status} kind="application" />
                    </TableCell>
                    <TableCell className="hidden xl:table-cell">
                      {a.status === "DRAFT" && !a.lastValidatedAt ? (
                        <span className="text-xs text-muted-foreground">Not validated</span>
                      ) : (
                        <ScoreBar value={a.complianceScore} />
                      )}
                    </TableCell>
                    <TableCell>
                      <RiskBandPill band={a.riskBand} score={a.riskScore} />
                    </TableCell>
                    <TableCell className="tabular hidden text-right sm:table-cell">
                      <span className={cn("font-semibold", (a.counts?.critical ?? 0) > 0 ? "text-red-700" : "text-muted-foreground")}>
                        {a.counts?.critical ?? 0}
                      </span>
                      <span className="text-muted-foreground"> / </span>
                      <span className={cn((a.counts?.major ?? 0) > 0 ? "font-medium text-orange-700" : "text-muted-foreground")}>
                        {a.counts?.major ?? 0}
                      </span>
                    </TableCell>
                    <TableCell className="hidden xl:table-cell">
                      <ProgressFraction done={a.counts?.verified ?? 0} total={a.counts?.documents ?? 0} />
                    </TableCell>
                    <TableCell className="hidden whitespace-nowrap text-xs text-muted-foreground lg:table-cell">{fmtDate(a.updatedAt)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="border-t px-4 py-2.5 text-xs text-muted-foreground">
              {rows.length} application{rows.length === 1 ? "" : "s"}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value?: string;
  onChange: (v: string | undefined) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <Select value={value ?? "ALL"} onValueChange={(v) => onChange(v === "ALL" ? undefined : v)}>
      <SelectTrigger className={cn("h-9 w-auto min-w-[140px] gap-2 text-sm", value && "border-primary-600/50 bg-navy-50")} aria-label={label}>
        <span className="text-muted-foreground">{label}:</span>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="ALL">All</SelectItem>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
