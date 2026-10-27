import { lazy, Suspense, useEffect } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import "./site.css";
import { SiteHeader } from "./components/SiteHeader";
import { SiteFooter } from "./components/SiteFooter";
import { Container } from "./components/Section";
import { ContentBoundary } from "@/components/common/ContentBoundary";
const Landing = lazy(() => import("./pages/Landing"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));
const Architecture = lazy(() => import("./pages/Architecture"));
const Compliance = lazy(() => import("./pages/Compliance"));
const Evaluation = lazy(() => import("./pages/Evaluation"));
const DocsHub = lazy(() => import("./pages/DocsHub"));

const TITLES: Record<string, string> = {
  "/": "AICTE VeriSense — AI-assisted application scrutiny",
  "/how-it-works": "How it works · AICTE VeriSense",
  "/architecture": "Architecture · AICTE VeriSense",
  "/compliance": "Problem statement mapping · AICTE VeriSense",
  "/evaluation": "Evaluation · AICTE VeriSense",
  "/help": "Documentation · AICTE VeriSense",
};

function ScrollManager() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    document.title = TITLES[pathname] ?? "AICTE VeriSense";
    if (hash) {
      const el = document.getElementById(decodeURIComponent(hash.slice(1)));
      if (el) {
        el.scrollIntoView();
        return;
      }
    }
    window.scrollTo(0, 0);
  }, [pathname, hash]);
  return null;
}

function NotFound() {
  return (
    <Container className="py-24 text-center">
      <p className="vs-mono text-sm text-slate-500">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-[#0B2E59]">Page not found</h1>
      <p className="mt-3 text-slate-600">The page you were looking for does not exist.</p>
      <Link to="/" className="mt-6 inline-block text-sm font-medium text-[#1D4E89] underline underline-offset-4">
        Back to overview
      </Link>
    </Container>
  );
}

export default function SiteApp() {
  return (
    <div className="vs-site flex min-h-screen flex-col">
      <ScrollManager />
      <SiteHeader />
      <main id="main" className="flex-1">
        <ContentBoundary><Suspense fallback={<div role="status" className="mx-auto min-h-[60vh] max-w-6xl px-6 py-16 text-slate-600">Loading page…</div>}>
        <Routes>
          <Route index element={<Landing />} />
          <Route path="how-it-works" element={<HowItWorks />} />
          <Route path="architecture" element={<Architecture />} />
          <Route path="compliance" element={<Compliance />} />
          <Route path="evaluation" element={<Evaluation />} />
          <Route path="help" element={<DocsHub />} />
          <Route path="docs" element={<DocsHub />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
        </Suspense></ContentBoundary>
      </main>
      <SiteFooter />
    </div>
  );
}
