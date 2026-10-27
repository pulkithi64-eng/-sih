import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { Menu, X, LogIn } from "lucide-react";
import { Logo } from "@/components/common/Logo";
import { NAV } from "../data/content";
import { Container } from "./Section";
import { cn } from "@/lib/utils";

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => setOpen(false), [pathname]);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/85">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:shadow"
      >
        Skip to content
      </a>
      <Container className="flex h-16 items-center justify-between gap-4">
        <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="AICTE VeriSense home">
          <Logo />
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
          {NAV.filter((item) => !["/architecture", "/help"].includes(item.to)).map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                cn(
                  "relative rounded px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "text-[#0B2E59]" : "text-slate-600 hover:text-[#0B2E59]",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {n.label}
                  {isActive && <span className="absolute inset-x-3 -bottom-[13px] h-[2px] bg-[#E8772E]" aria-hidden />}
                </>
              )}
            </NavLink>
          ))}
          <details className="relative text-sm"><summary className="cursor-pointer rounded px-3 py-2 font-medium text-slate-600">More</summary><div className="absolute right-0 top-full mt-2 w-48 rounded-md border bg-white p-2 shadow-sm">{NAV.filter((item) => ["/architecture", "/help"].includes(item.to)).map((item) => <Link key={item.to} to={item.to} className="block rounded px-3 py-2 text-slate-700 hover:bg-slate-50">{item.label}</Link>)}</div></details>
        </nav>

        <div className="flex items-center gap-2">
          <Link
            to="/portal/login"
            className="hidden items-center gap-2 rounded-md bg-[#0B2E59] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#1D4E89] sm:inline-flex"
          >
            <LogIn className="h-4 w-4" aria-hidden />
            Sign in
          </Link>
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-700 hover:bg-slate-100 lg:hidden"
            aria-expanded={open}
            aria-controls="site-mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </Container>

      {open && (
        <div id="site-mobile-nav" className="border-t border-slate-200 bg-white lg:hidden">
          <Container className="py-3">
            <nav aria-label="Mobile" className="flex flex-col">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  cn("rounded px-3 py-3 text-[15px] font-medium", isActive ? "bg-[#F5F7FA] text-[#0B2E59]" : "text-slate-700")
                }
              >
                Overview
              </NavLink>
              {NAV.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  className={({ isActive }) =>
                    cn("rounded px-3 py-3 text-[15px] font-medium", isActive ? "bg-[#F5F7FA] text-[#0B2E59]" : "text-slate-700")
                  }
                >
                  {n.label}
                </NavLink>
              ))}
              <Link
                to="/portal/login"
                className="mt-2 inline-flex items-center justify-center gap-2 rounded-md bg-[#0B2E59] px-4 py-3 text-sm font-medium text-white"
              >
                <LogIn className="h-4 w-4" aria-hidden />
                Sign in
              </Link>
            </nav>
          </Container>
        </div>
      )}
    </header>
  );
}
