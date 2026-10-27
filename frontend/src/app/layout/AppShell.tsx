import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ChevronRight, ChevronsLeft, ChevronsRight, Home } from "lucide-react";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Logo } from "@/components/common/Logo";
import { useAlerts } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { useAuth } from "../auth";
import { CrumbProvider, useCrumbLabel } from "./crumbs";
import { CRUMB_LABEL, NAV_SECTIONS } from "./nav";
import TopBar from "./TopBar";

const COLLAPSE_KEY = "verisense.sidebar.collapsed";

export default function AppShell() {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const loc = useLocation();

  useEffect(() => setMobileOpen(false), [loc.pathname]);
  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  return (
    <CrumbProvider>
      <div className="flex min-h-screen bg-background">
        <a
          href="#main"
          className="sr-only z-50 rounded bg-primary px-3 py-2 text-primary-foreground focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
        >
          Skip to content
        </a>
        <aside
          className={cn(
            "sticky top-0 hidden h-screen shrink-0 flex-col bg-sidebar text-sidebar-foreground transition-[width] duration-200 lg:flex",
            collapsed ? "w-[68px]" : "w-60",
          )}
        >
          <SidebarBody collapsed={collapsed} />
          <button
            type="button"
            onClick={() => setCollapsed((c) => !c)}
            className="flex h-10 items-center gap-2 border-t border-sidebar-border px-5 text-xs text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sidebar-ring"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
            {!collapsed && "Collapse"}
          </button>
        </aside>

        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetContent side="left" className="w-64 border-0 bg-sidebar p-0 text-sidebar-foreground">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <SidebarBody collapsed={false} />
          </SheetContent>
        </Sheet>

        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar onOpenMenu={() => setMobileOpen(true)} />
          <main id="main" className="mx-auto min-h-[calc(100svh-3.5rem)] w-full max-w-[1440px] flex-1 px-4 pb-10 pt-4 sm:px-6 lg:px-8">
            <Breadcrumbs />
            <Outlet />
          </main>
          <footer className="border-t bg-card">
            <div className="mx-auto flex max-w-[1440px] flex-col gap-1 px-4 py-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
              <span>Prototype built for AICTE · SIH 2026 · PS 26261</span>
              <span>Synthetic data. AI outputs are advisory and require officer review.</span>
            </div>
          </footer>
        </div>
      </div>
    </CrumbProvider>
  );
}

function SidebarBody({ collapsed }: { collapsed: boolean }) {
  const { user } = useAuth();
  const alerts = useAlerts(!!user);
  const unread = (alerts.data ?? []).filter((a) => !a.read).length;
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Link
        to="/portal"
        className={cn("flex h-14 items-center border-b border-sidebar-border", collapsed ? "justify-center px-0" : "px-5")}
        aria-label="VeriSense home"
      >
        <Logo inverted compact={collapsed} />
      </Link>
      <nav className="scrollbar-thin flex-1 overflow-y-auto py-4" aria-label="Main">
        {NAV_SECTIONS.map((sec) => {
          const items = sec.items.filter((i) => user && i.roles.includes(user.role));
          if (!items.length) return null;
          return (
            <div key={sec.title} className="mb-5">
              {!collapsed && (
                <p className="mb-1.5 px-5 text-2xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">{sec.title}</p>
              )}
              <ul className="space-y-0.5 px-2.5">
                {items.map((item) => {
                  const link = (
                    <NavLink
                      to={item.to}
                      end={item.to === "/portal/applications" || item.to.endsWith("/new")}
                      className={({ isActive }) =>
                        cn(
                          "relative flex h-9 items-center gap-3 rounded-md text-sm font-medium transition-colors",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                          collapsed ? "justify-center px-0" : "px-2.5",
                          isActive
                            ? "bg-sidebar-accent text-white before:absolute before:inset-y-1.5 before:left-0 before:w-[3px] before:rounded-full before:bg-saffron"
                            : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-white",
                        )
                      }
                    >
                      <item.icon className="h-4 w-4 shrink-0" aria-hidden />
                      {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                      {item.badge === "alerts" && unread > 0 && (
                        <span
                          className={cn(
                            "tabular rounded-full bg-saffron px-1.5 text-2xs font-semibold leading-5 text-white",
                            collapsed && "absolute right-1 top-0.5 px-1 leading-4",
                          )}
                          aria-label={`${unread} unread`}
                        >
                          {unread > 99 ? "99+" : unread}
                        </span>
                      )}
                    </NavLink>
                  );
                  return (
                    <li key={item.to}>
                      {collapsed ? (
                        <Tooltip>
                          <TooltipTrigger asChild>{link}</TooltipTrigger>
                          <TooltipContent side="right">{item.label}</TooltipContent>
                        </Tooltip>
                      ) : (
                        link
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>
      {!collapsed && (
        <div className="border-t border-sidebar-border px-5 py-3 text-2xs leading-relaxed text-sidebar-foreground/50">
          Decision-support prototype.
          <br />
          Not an official AICTE system.
        </div>
      )}
    </div>
  );
}

function Breadcrumbs() {
  const loc = useLocation();
  const label = useCrumbLabel();
  const parts = loc.pathname.replace(/^\/portal\/?/, "").split("/").filter(Boolean);
  if (parts.length === 0) return null;
  const crumbs = parts.map((p, i) => {
    const to = "/portal/" + parts.slice(0, i + 1).join("/");
    const isLast = i === parts.length - 1;
    let text = CRUMB_LABEL[p] ?? (label && (isLast || parts[i + 1] === "edit") ? label : decodeURIComponent(p));
    if (p === "applications" && parts.length > 1 && parts[1] !== "new") text = "Applications";
    return { to, text, isLast };
  });
  return (
    <nav aria-label="Breadcrumb" className="mb-4">
      <ol className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
        <li>
          <Link to="/portal" className="inline-flex items-center hover:text-foreground" aria-label="Portal home">
            <Home className="h-3.5 w-3.5" />
          </Link>
        </li>
        {crumbs.map((c) => (
          <li key={c.to} className="inline-flex items-center gap-1">
            <ChevronRight className="h-3 w-3" aria-hidden />
            {c.isLast ? (
              <span aria-current="page" className="font-medium text-foreground">
                {c.text}
              </span>
            ) : (
              <Link to={c.to} className="hover:text-foreground">
                {c.text}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
