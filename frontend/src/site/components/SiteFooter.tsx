import { Link } from "react-router-dom";
import { Logo } from "@/components/common/Logo";
import { NAV, REPO_URL } from "../data/content";
import { Container } from "./Section";

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-200 bg-[#F5F7FA]">
      <Container className="py-12">
        <div className="grid gap-10 md:grid-cols-[1.4fr,1fr,1fr]">
          <div>
            <Logo withTagline />
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-slate-600">
              Decision support for preliminary scrutiny of AICTE approval applications. Every flag is backed by
              evidence; every decision stays with AICTE officials.
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Explore</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link to="/" className="text-slate-700 hover:text-[#0B2E59]">
                  Overview
                </Link>
              </li>
              {NAV.map((n) => (
                <li key={n.to}>
                  <Link to={n.to} className="text-slate-700 hover:text-[#0B2E59]">
                    {n.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Prototype</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link to="/portal/login" className="text-slate-700 hover:text-[#0B2E59]">
                  Portal login
                </Link>
              </li>
              <li>
                <Link to="/docs#demo" className="text-slate-700 hover:text-[#0B2E59]">
                  Demo script
                </Link>
              </li>
              <li>
                <a href={REPO_URL} className="text-slate-700 hover:text-[#0B2E59]" rel="noreferrer" target="_blank">
                  Source code
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-10 flex flex-col gap-3 border-t border-slate-200 pt-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>Prototype built for AICTE · Smart India Hackathon 2026 · PS 26261</p>
          <p className="max-w-xl sm:text-right">
            Not an official AICTE system. All institutions, people and documents in the demo are synthetic.
          </p>
        </div>
      </Container>
    </footer>
  );
}
