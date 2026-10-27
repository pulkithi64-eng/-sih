import { Link } from "react-router-dom";
import {
  ArrowRight,
  FileSearch,
  ShieldAlert,
  BadgeCheck,
  Building2,
  LayoutDashboard,
  UserCheck,
  KeyRound,
  Link2,
  Lightbulb,
  SlidersHorizontal,
  Lock,
  ChevronDown,
  PlayCircle,
} from "lucide-react";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Container, Section, Eyebrow, Card, AdvisoryMarker, Pill } from "../components/Section";
import { PipelineDiagram } from "../components/PipelineDiagram";
import { MODULES, SAFEGUARDS, VERIFICATION_STATES, TECH_STACK, FAQ, PIPELINE_STEPS } from "../data/content";
import { SCENARIOS } from "../data/scenarios";

const MODULE_ICONS = [FileSearch, ShieldAlert, BadgeCheck, Building2, LayoutDashboard];
const SAFEGUARD_ICONS = [UserCheck, KeyRound, Link2, Lightbulb, SlidersHorizontal, Lock];

function HeroPreview() {
  const rows = [
    { doc: "Fire NOC", status: "EXPIRED", note: "Valid upto 10/10/2026" },
    { doc: "TER payment receipt", status: "VERIFIED", note: "Gateway record matched" },
    { doc: "University affiliation", status: "MISMATCH_DETECTED", note: "Intake differs from source" },
    { doc: "Affidavit / undertaking", status: "MANUAL_REVIEW_REQUIRED", note: "No online source" },
  ] as const;
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-[0_12px_40px_-12px_rgba(11,46,89,0.25)]">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="min-w-0">
          <p className="vs-mono truncate text-[11px] text-slate-500">EOA/2026-27/WR/000142</p>
          <p className="truncate text-sm font-semibold text-slate-900">Extension of Approval · synthetic institute</p>
        </div>
        <span className="shrink-0 rounded border border-orange-200 bg-orange-50 px-2 py-0.5 text-[11px] font-semibold text-orange-800">
          RISK MEDIUM
        </span>
      </div>
      <div className="grid grid-cols-3 divide-x divide-slate-100 border-b border-slate-100 text-center">
        {[
          ["Checklist", "10 / 12"],
          ["Compliance", "71"],
          ["Open findings", "6"],
        ].map(([k, v]) => (
          <div key={k} className="px-2 py-3">
            <p className="text-lg font-semibold text-[#0B2E59]">{v}</p>
            <p className="text-[11px] text-slate-500">{k}</p>
          </div>
        ))}
      </div>
      <ul className="divide-y divide-slate-100">
        {rows.map((r) => (
          <li key={r.doc} className="flex flex-col items-start gap-1.5 px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-800">{r.doc}</p>
              <p className="truncate text-xs text-slate-500">{r.note}</p>
            </div>
            <div className="shrink-0">
              <StatusBadge status={r.status} kind="verification" />
            </div>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-5 py-3">
        <AdvisoryMarker />
        <span className="text-[11px] text-slate-500">Illustrative preview</span>
      </div>
    </div>
  );
}

export default function Landing() {
  return (
    <>
      {/* Hero */}
      <section className="vs-grid-bg relative border-b border-slate-200 bg-[#F5F7FA]">
        <Container className="grid grid-cols-1 items-center gap-12 py-16 sm:py-20 lg:grid-cols-[1.1fr,1fr] lg:py-24">
          <div>
            <Eyebrow>Smart India Hackathon 2026 · PS 26261 · Smart Automation</Eyebrow>
            <h1 className="mt-4 text-[2rem] font-semibold leading-[1.15] text-[#0B2E59] sm:text-5xl">
              Preliminary scrutiny in minutes, not weeks.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-700">
              Every flag backed by evidence, every decision left to AICTE officials. VeriSense reads an institution's
              approval application, checks each document against its checklist, the records AICTE already holds and the
              authority that issued it, and hands the scrutiny officer a report they can verify line by line.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/portal/login"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-[#0B2E59] px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4E89]"
              >
                Open the portal
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              <Link
                to="/how-it-works"
                className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-[#0B2E59] hover:border-[#1D4E89]"
              >
                See how it works
              </Link>
            </div>
            <dl className="mt-10 grid max-w-lg grid-cols-3 gap-4 border-t border-slate-200 pt-6">
              {[
                ["5", "integrated modules"],
                ["6", "verification states"],
                ["0", "automated final decisions"],
              ].map(([n, l]) => (
                <div key={l}>
                  <dt className="sr-only">{l}</dt>
                  <dd className="text-2xl font-semibold text-[#0B2E59]">{n}</dd>
                  <dd className="text-xs leading-snug text-slate-600">{l}</dd>
                </div>
              ))}
            </dl>
          </div>
          <HeroPreview />
        </Container>
      </section>

      {/* Problem */}
      <Section
        eyebrow="The problem"
        title="One application, many documents, many sources — checked by hand"
        intro="An approval application bundles certificates from municipal bodies, fire services, universities, registrars, accreditation bodies and banks, alongside data the institution has already filed with AICTE in earlier years. Today an officer reconciles these by reading each document and comparing it against the others."
      >
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          {[
            ["7", "application categories, each with its own checklist"],
            ["Up to 16", "documents required for a new institution in our configuration"],
            ["23", "document types from more than 15 kinds of issuer"],
            ["8", "record sets per institution to cross-check: approvals, intake, faculty, accreditation, land, TER, deficiencies, affidavits"],
          ].map(([n, l]) => (
            <Card key={l}>
              <p className="text-2xl font-semibold text-[#0B2E59] sm:text-3xl">{n}</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{l}</p>
            </Card>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-500">
          Figures describe the prototype's configurable catalogue and checklists, not official AICTE statistics.
        </p>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {[
            ["Missed expiries and gaps", "A Fire NOC that lapsed a fortnight before submission, or an affidavit from the previous year, is easy to overlook in a long bundle."],
            ["Inconsistencies across sources", "Declared intake, faculty strength or land area may not match the approved records or the documents themselves."],
            ["Altered or reused documents", "Edited scans, certificates reused across institutions and faculty listed at two colleges at once need forensic attention, not a quick glance."],
          ].map(([t, b]) => (
            <div key={t} className="border-l-2 border-[#E8772E] pl-4">
              <h3 className="font-semibold text-slate-900">{t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{b}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Modules */}
      <Section
        id="modules"
        tone="canvas"
        eyebrow="What VeriSense does"
        title="Five modules, one evidence trail"
        intro="Each module maps to a component of the problem statement. Together they turn an uploaded bundle into a structured, explainable preliminary scrutiny."
      >
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m, i) => {
            const Icon = MODULE_ICONS[i];
            return (
              <Card key={m.key} className="flex flex-col">
                <div className="flex items-center gap-3">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-[#EEF3FA] text-[#0B2E59]">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <span className="vs-mono text-xs text-slate-400">0{i + 1}</span>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-[#0B2E59]">{m.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{m.summary}</p>
                <ul className="mt-4 space-y-2 text-sm text-slate-700">
                  {m.points.map((p) => (
                    <li key={p} className="flex gap-2">
                      <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#E8772E]" aria-hidden />
                      {p}
                    </li>
                  ))}
                </ul>
              </Card>
            );
          })}
          <Card className="flex flex-col justify-between border-dashed bg-transparent shadow-none">
            <div>
              <h3 className="text-lg font-semibold text-[#0B2E59]">Mapped to the problem statement</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                Every objective, deliverable and safeguard of PS 26261, with where it lives in the product and whether
                it is built, simulated or designed.
              </p>
            </div>
            <Link to="/compliance" className="mt-6 inline-flex items-center gap-1 text-sm font-semibold text-[#1D4E89] hover:underline">
              View PS mapping <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </Card>
        </div>
      </Section>

      {/* Flow */}
      <Section
        id="flow"
        eyebrow="End to end"
        title="From application to decision"
        intro="Steps one to six run automatically when documents are uploaded and the application is submitted. Steps seven and eight belong to AICTE officials."
      >
        <PipelineDiagram />
        <ol className="mt-10 hidden gap-x-6 gap-y-5 lg:grid lg:grid-cols-4">
          {PIPELINE_STEPS.map((s, i) => (
            <li key={s.short} className="text-sm">
              <span className="vs-mono text-xs text-slate-400">{String(i + 1).padStart(2, "0")}</span>
              <p className="font-semibold text-slate-900">{s.label}</p>
              <p className="mt-1 text-slate-600">{s.detail}</p>
            </li>
          ))}
        </ol>
        <Link to="/how-it-works" className="mt-8 inline-flex items-center gap-1 text-sm font-semibold text-[#1D4E89] hover:underline">
          Walk through each step <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </Section>

      {/* Verification states */}
      <Section
        id="states"
        tone="canvas"
        eyebrow="Issuing-authority verification"
        title="Six outcomes, recorded with source and timestamp"
        intro="A document is never silently passed. Every check ends in one of six states, and anything inconclusive is routed to an officer for manual review."
      >
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {VERIFICATION_STATES.map((s) => (
            <Card key={s.id}>
              <StatusBadge status={s.id} kind="verification" size="md" />
              <p className="mt-3 text-sm font-medium text-slate-900">{s.meaning}</p>
              <dl className="mt-3 space-y-2 text-sm">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">When</dt>
                  <dd className="text-slate-600">{s.trigger}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">Then</dt>
                  <dd className="text-slate-600">{s.next}</dd>
                </div>
              </dl>
            </Card>
          ))}
        </div>
      </Section>

      {/* Safeguards */}
      <Section
        id="safeguards"
        tone="navy"
        eyebrow="Safeguards"
        title="Built to support officials, not to replace them"
        intro="The problem statement asks for configurability, authorised access, data protection, explainability and human authority over decisions. These are part of the design, not add-ons."
      >
        <div className="grid gap-px overflow-hidden rounded-lg bg-white/10 sm:grid-cols-2 lg:grid-cols-3">
          {SAFEGUARDS.map((s, i) => {
            const Icon = SAFEGUARD_ICONS[i];
            return (
              <div key={s.title} className="bg-[#0B2E59] p-6">
                <Icon className="h-5 w-5 text-[#F4A66F]" aria-hidden />
                <h3 className="mt-3 font-semibold text-white">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-blue-100">{s.body}</p>
              </div>
            );
          })}
        </div>
      </Section>

      {/* Demo scenarios */}
      <Section
        id="scenarios"
        eyebrow="Try it"
        title="Demo scenarios"
        intro="The portal is seeded with synthetic institutions and applications, each built to exercise a different part of the pipeline. Log in with any demo account (password Demo@2026)."
      >
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {SCENARIOS.map((s) => (
            <Card key={s.key} className="flex flex-col">
              <div className="flex flex-wrap gap-2">
                <Pill>{s.category}</Pill>
                <Pill className="vs-mono">{s.login}</Pill>
              </div>
              <h3 className="mt-3 font-semibold text-[#0B2E59]">{s.title}</h3>
              <p className="mt-0.5 text-xs text-slate-500">{s.institution}</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.description}</p>
              <ul className="mt-3 space-y-1.5 text-sm text-slate-700">
                {s.expect.map((e) => (
                  <li key={e} className="flex gap-2">
                    <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#1D4E89]" aria-hidden />
                    {e}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link
            to="/portal/login"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-[#0B2E59] px-5 py-3 text-sm font-semibold text-white hover:bg-[#1D4E89]"
          >
            Open the portal <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link
            to="/docs#demo"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-5 py-3 text-sm font-semibold text-[#0B2E59] hover:border-[#1D4E89]"
          >
            <PlayCircle className="h-4 w-4" aria-hidden /> Seven-minute demo script
          </Link>
        </div>
      </Section>

      {/* Tech stack */}
      <Section
        id="stack"
        tone="canvas"
        eyebrow="Technology"
        title="Open, auditable and deployable on government cloud"
        intro="Built entirely on open-source components that run on a single container host, with no dependency on external AI services. Document data stays inside the deployment."
      >
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-5">
          {TECH_STACK.map((g) => (
            <Card key={g.group}>
              <h3 className="text-sm font-semibold text-[#0B2E59]">{g.group}</h3>
              <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
                {g.items.map((it) => (
                  <li key={it}>{it}</li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </Section>

      {/* SIH strip */}
      <section className="border-y border-slate-200 bg-white">
        <Container className="flex flex-col gap-6 py-10 md:flex-row md:items-center md:justify-between">
          <div>
            <Eyebrow>Smart India Hackathon 2026</Eyebrow>
            <p className="mt-2 max-w-2xl text-lg font-semibold text-[#0B2E59]">
              Problem Statement 26261 — AI-powered application validation, document authentication and regulatory
              compliance verification
            </p>
            <p className="mt-1 text-sm text-slate-600">
              Organisation: AICTE, Regulation Bureau · Category: Software · Theme: Smart Automation
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Pill>Team VeriSense</Pill>
            <Pill>Open source · MIT</Pill>
            <Pill>Synthetic data only</Pill>
          </div>
        </Container>
      </section>

      {/* FAQ */}
      <Section id="faq" eyebrow="Questions" title="Frequently asked questions">
        <div className="max-w-3xl divide-y divide-slate-200 rounded-lg border border-slate-200">
          {FAQ.map((f) => (
            <details key={f.q} className="group px-5">
              <summary className="flex cursor-pointer items-center justify-between gap-4 py-4 text-left font-medium text-slate-900">
                {f.q}
                <ChevronDown className="vs-chevron h-4 w-4 shrink-0 text-slate-500 transition-transform" aria-hidden />
              </summary>
              <p className="pb-5 text-sm leading-relaxed text-slate-600">{f.a}</p>
            </details>
          ))}
        </div>
      </Section>
    </>
  );
}
