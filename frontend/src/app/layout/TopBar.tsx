import { useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  CheckCheck,
  Clock,
  Eye,
  EyeOff,
  LogOut,
  MapPin,
  Menu,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import { LogoMark } from "@/components/common/Logo";
import { severityDot } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useAlerts, useApplications, useMarkAlertRead } from "@/lib/hooks";
import { fmtRelative } from "@/lib/format";
import { REGION_LABEL, roleLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { useAuth } from "../auth";

export default function TopBar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const { user, logout, maskPii, toggleMaskPii, sessionExpiring, remainingMinutes, extendSession } = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const hasPageSearch = ["/portal/my-applications", "/portal/applications", "/portal/institutions"].includes(location.pathname);
  return (
    <header className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/85">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4 sm:px-6 lg:px-8">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onOpenMenu} aria-label="Open navigation">
          <Menu className="h-5 w-5" />
        </Button>
        <Link to="/portal" className="lg:hidden" aria-label="VeriSense home">
          <LogoMark className="h-7 w-7" />
        </Link>
        {hasPageSearch ? <span className="hidden text-sm font-medium text-muted-foreground sm:block">{roleLabel(user?.role)} workspace</span> : <GlobalSearch />}
        <div className="ml-auto flex items-center gap-2">
          {/* Session timeout warning */}
          {sessionExpiring && (
            <div className="flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-2xs font-semibold text-amber-900 animate-pulse">
              <Clock className="h-3 w-3 text-amber-700" />
              <span>Session: {remainingMinutes}m</span>
              <button
                type="button"
                onClick={extendSession}
                className="ml-1 underline font-bold hover:text-amber-950 focus:outline-none"
              >
                Extend
              </button>
            </div>
          )}

          {/* Mask PII Privacy Toggle */}
          <button
            type="button"
            onClick={toggleMaskPii}
            className={cn(
              "hidden sm:flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              maskPii
                ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                : "border-border bg-background text-muted-foreground hover:bg-accent",
            )}
            title={maskPii ? "Sensitive PII (PAN/Aadhaar) is masked. Click to reveal." : "Sensitive PII is unmasked. Click to conceal."}
          >
            {maskPii ? <EyeOff className="h-3.5 w-3.5 text-emerald-700" /> : <Eye className="h-3.5 w-3.5" />}
            <span className="text-2xs font-medium">{maskPii ? "PII Masked" : "PII Visible"}</span>
          </button>

          {user?.region && (
            <span className="hidden items-center gap-1 rounded-md border bg-background px-2 py-1 text-xs text-muted-foreground xl:inline-flex">
              <MapPin className="h-3.5 w-3.5" aria-hidden />
              {REGION_LABEL[user.region] ?? user.region}
            </span>
          )}
          <AlertsBell />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex items-center gap-2 rounded-md px-1.5 py-1 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Account menu"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-navy text-xs font-semibold text-white">
                  {initials(user?.fullName ?? user?.username ?? "")}
                </span>
                <span className="hidden min-w-0 text-left md:block">
                  <span className="block max-w-[160px] truncate text-sm font-medium leading-tight">{user?.fullName}</span>
                  <span className="block text-2xs leading-tight text-muted-foreground">{roleLabel(user?.role)}</span>
                </span>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              <DropdownMenuLabel className="font-normal">
                <p className="text-sm font-medium">{user?.fullName}</p>
                <p className="mono text-xs text-muted-foreground">{user?.username}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <span className="rounded bg-navy px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide text-white">
                    {roleLabel(user?.role)}
                  </span>
                  {user?.region && (
                    <span className="rounded border px-1.5 py-0.5 text-2xs font-medium text-muted-foreground">
                      {REGION_LABEL[user.region] ?? user.region}
                    </span>
                  )}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={() => {
                  logout();
                  nav("/portal/login", { replace: true });
                }}
              >
                <LogOut className="mr-2 h-4 w-4" /> Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}

function initials(name: string) {
  return (
    name
      .split(/[\s.]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((s) => s[0]?.toUpperCase())
      .join("") || "U"
  );
}

function GlobalSearch() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const apps = useApplications({}, q.trim().length > 0);
  const results = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return [];
    return (apps.data ?? [])
      .filter(
        (a) =>
          a.applicationNo?.toLowerCase().includes(s) ||
          a.institution?.name?.toLowerCase().includes(s) ||
          a.institution?.permanentId?.toLowerCase().includes(s) ||
          a.institution?.city?.toLowerCase().includes(s),
      )
      .slice(0, 7);
  }, [q, apps.data]);

  function go(id: string | number) {
    setOpen(false);
    setQ("");
    nav(`/portal/applications/${id}`);
  }

  return (
    <Popover open={open && q.trim().length > 0} onOpenChange={setOpen}>
      <PopoverAnchor asChild>
        <form
          role="search"
          className="relative min-w-0 w-full max-w-md"
          onSubmit={(e) => {
            e.preventDefault();
            if (results[active]) go(results[active].id);
            else if (q.trim()) {
              setOpen(false);
              nav(`/portal/applications?q=${encodeURIComponent(q.trim())}`);
            }
          }}
        >
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setActive(0);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((a) => Math.min(a + 1, results.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((a) => Math.max(a - 1, 0));
              } else if (e.key === "Escape") setOpen(false);
            }}
            placeholder="Search application no., institution, permanent ID"
            aria-label="Search applications"
            className="h-9 w-full rounded-md border border-input bg-background pl-8 pr-3 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </form>
      </PopoverAnchor>
      <PopoverContent
        align="start"
        className="w-[var(--radix-popover-trigger-width)] min-w-[320px] p-1"
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        {results.length === 0 ? (
          <p className="px-3 py-4 text-center text-sm text-muted-foreground">
            {apps.isLoading ? "Searching…" : "No matching applications. Press Enter to search all."}
          </p>
        ) : (
          <ul role="listbox" aria-label="Search results">
            {results.map((a, i) => (
              <li key={a.id} role="option" aria-selected={i === active}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onClick={() => go(a.id)}
                  className={cn("flex w-full items-center gap-3 rounded px-2.5 py-2 text-left", i === active && "bg-accent")}
                >
                  <span className="min-w-0 flex-1">
                    <span className="mono block truncate text-xs text-muted-foreground">{a.applicationNo}</span>
                    <span className="block truncate text-sm font-medium">{a.institution?.name}</span>
                  </span>
                  <StatusBadge status={a.status} kind="application" showIcon={false} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}

function AlertsBell() {
  const { data } = useAlerts();
  const mark = useMarkAlertRead();
  const nav = useNavigate();
  const alerts = data ?? [];
  const unread = alerts.filter((a) => !a.read);
  const shown = [...alerts].sort((a, b) => Number(a.read) - Number(b.read) || +new Date(b.createdAt) - +new Date(a.createdAt)).slice(0, 6);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label={`Alerts, ${unread.length} unread`}>
          <Bell className="h-5 w-5" />
          {unread.length > 0 && (
            <span className="tabular absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-saffron px-1 text-[10px] font-semibold leading-none text-white">
              {unread.length > 9 ? "9+" : unread.length}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[360px] p-0">
        <div className="flex items-center justify-between border-b px-3 py-2.5">
          <p className="text-sm font-semibold">Alerts</p>
          <span className="text-xs text-muted-foreground">{unread.length} unread</span>
        </div>
        {shown.length === 0 ? (
          <p className="px-3 py-6 text-center text-sm text-muted-foreground">No alerts.</p>
        ) : (
          <div className="max-h-[360px] overflow-y-auto">
            {shown.map((a) => (
              <DropdownMenuItem
                key={a.id}
                className="flex cursor-pointer items-start gap-2.5 rounded-none border-b px-3 py-2.5 last:border-0"
                onSelect={() => {
                  if (!a.read) mark.mutate(a.id);
                  nav(`/portal/applications/${a.applicationId}`);
                }}
              >
                <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", severityDot(a.severity))} aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className={cn("block text-sm leading-snug", !a.read ? "font-medium" : "text-muted-foreground")}>{a.message}</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    <span className="mono">{a.applicationNo}</span> · {fmtRelative(a.createdAt)}
                  </span>
                </span>
                {!a.read && <span className="mt-1 h-1.5 w-1.5 rounded-full bg-info" aria-label="Unread" />}
              </DropdownMenuItem>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between border-t px-3 py-2">
          <Link to="/portal/alerts" className="text-sm font-medium text-primary-600 hover:underline">
            View all alerts
          </Link>
          {unread.length > 0 && (
            <button
              type="button"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => unread.forEach((a) => mark.mutate(a.id))}
            >
              <CheckCheck className="h-3.5 w-3.5" /> Mark all read
            </button>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
