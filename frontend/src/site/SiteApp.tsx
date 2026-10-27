import { useEffect } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import "./site.css";
import { SiteHeader } from "./components/SiteHeader";
import { SiteFooter } from "./components/SiteFooter";
import { Container } from "./components/Section";
import Landing from "./pages/Landing";
import HowItWorks from "./pages/HowItWorks";
import Architecture from "./pages/Architecture";
import Compliance from "./pages/Compliance";
import Evaluation from "./pages/Evaluation";
import DocsHub from "./pages/DocsHub";

const TITLES: Record<string, string> = {
  "/": "AICTE VeriSense — AI-assisted application scrutiny",
  "/how-it-works": "How it works · AICTE VeriSense",
  "/architecture": "Architecture · AICTE VeriSense",
  "/compliance": "Problem statement mapping · AICTE VeriSense",
  "/evaluation": "Evaluation · AICTE VeriSense",
  "/docs": "Documentation · AICTE VeriSense",
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
        <Routes>
          <Route index element={<Landing />} />
          <Route path="how-it-works" element={<HowItWorks />} />
          <Route path="architecture" element={<Architecture />} />
          <Route path="compliance" element={<Compliance />} />
          <Route path="evaluation" element={<Evaluation />} />
          <Route path="docs" element={<DocsHub />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <SiteFooter />
    </div>
  );
}
