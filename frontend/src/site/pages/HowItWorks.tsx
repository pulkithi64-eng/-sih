import { Link } from "react-router-dom";
import { ArrowRight, QrCode, Database, Cloud, UserSearch, RefreshCcw } from "lucide-react";
import { Container, Section, PageHero, Card, AdvisoryMarker } from "../components/Section";
import { FindingCard, EXAMPLE_FINDINGS } from "../components/FindingCard";
import { HOW_STEPS, RULE_EXAMPLE, SCORING } from "../data/howItWorks";

function StepNav() {
  return (
    <nav aria-label="Steps" className="sticky top-16 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <Container className="flex gap-1 overflow-x-auto py-2 text-sm [scrollbar-width:none]">
        {HOW_STEPS.map((s, i) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            className="shrink-0 rounded px-3 py-1.5 font-medium text-slate-600 hover:bg-[#F5F7FA] hover:text-[#0B2E59]"
          >
            <span className="vs-mono mr-1.5 text-xs text-slate-400">{i + 1}</span>
            {s.nav}
          </a>
        ))}
        <a href="#findings" className="shrink-0 rounded px-3 py-1.5 font-medium text-slate-600 hover:bg-[#F5F7FA] hover:text-[#0B2E59]">
          Findings
        </a>
      </Container>
    </nav>
  );
}

export default function HowItWorks() {
  return (
    <>
      <PageHero
        eyebrow="How it works"
        title="What happens to an application, step by step"
        intro="Each uploaded document passes through a fixed pipeline of pure, testable functions. The application-level rule engine then combines those results with the checklist and the records AICTE already holds, and writes findings that an officer can trace back to their evidence."
      />
      <StepNav />

      {HOW_STEPS.map((s, i) => (
        <Section key={s.id} id={s.id} tone={i % 2 ? "canvas" : "white"} className="py-14 sm:py-16">
          <div className="grid gap-10 lg:grid-cols-[1fr,1.1fr]">
            <div>
              <p className="vs-mono text-xs text-slate-400">STEP {String(i + 1).padStart(2, "0")}</p>
              <h2 className="mt-2 text-2xl font-semibold text-[#0B2E59]">{s.title}</h2>
              <p className="mt-3 leading-relaxed text-slate-600">{s.body}</p>
              {s.output && (
                <p className="mt-4 rounded-md border-l-2 border-[#E8772E] bg-white px-4 py-3 text-sm text-slate-700">
                  <span className="font-semibold text-slate-900">Output: </span>
                  {s.output}
                </p>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">What is checked</p>
              <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
                {s.checks.map((c) => (
                  <li key={c.name} className="px-4 py-3">
                    <p className="text-sm font-medium text-slate-900">{c.name}</p>
                    <p className="mt-0.5 text-sm text-slate-600">{c.detail}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {s.id === "verification" && (
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                {
                  Icon: QrCode,
                  t: "Signed QR payloads",
                  b: "The issuer embeds a JSON payload signed with Ed25519. VeriSense decodes the QR, verifies the signature with the issuer's public key and compares each claim with the printed, extracted values.",
                },
                {
                  Icon: Database,
                  t: "Registry lookups",
                  b: "For sources with a lookup API, the adapter queries by reference number and compares status, holder, dates and amounts field by field.",
                },
                {
                  Icon: Cloud,
                  t: "DigiLocker-style pull",
                  b: "Designed for consent-based retrieval of issued documents from the issuer's repository, so the original rather than a scan is compared. Simulated in the prototype.",
                },
                {
                  Icon: UserSearch,
                  t: "Fallback to manual",
                  b: "No source, no reference number, a timeout or conflicting signals: the document is marked Source unavailable or Manual review required and placed in the officer's queue.",
                },
              ].map(({ Icon, t, b }) => (
                <Card key={t}>
                  <Icon className="h-5 w-5 text-[#1D4E89]" aria-hidden />
                  <h3 className="mt-3 text-sm font-semibold text-slate-900">{t}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{b}</p>
                </Card>
              ))}
              <p className="text-xs text-slate-500 sm:col-span-2 lg:col-span-4">
                In this prototype all issuing authorities are simulated services with their own keys and records. Real
                integrations require authorisation from each authority and plug into the same adapter interface.
              </p>
            </div>
          )}

          {s.id === "rules" && (
            <div className="mt-10 grid gap-6 lg:grid-cols-2">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">A rule, as configured</p>
                <pre className="vs-mono mt-3 overflow-x-auto rounded-lg bg-[#0B2E59] p-4 text-[12.5px] leading-relaxed text-blue-50">
                  {RULE_EXAMPLE}
                </pre>
                <p className="mt-2 text-xs text-slate-500">
                  Administrators can enable or disable a rule and change its parameters and severity from the console.
                  Each change bumps the ruleset version and is written to the audit log.
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Scores</p>
                <div className="mt-3 space-y-3">
                  {SCORING.map((sc) => (
                    <Card key={sc.name}>
                      <p className="text-sm font-semibold text-slate-900">{sc.name}</p>
                      <p className="vs-mono mt-2 break-words text-[12.5px] text-[#1D4E89]">{sc.formula}</p>
                      <p className="mt-2 text-sm text-slate-600">{sc.note}</p>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          )}

          {s.id === "review" && (
            <div className="mt-10 rounded-lg border border-slate-200 bg-white p-6">
              <div className="flex items-center gap-2">
                <RefreshCcw className="h-5 w-5 text-[#E8772E]" aria-hidden />
                <h3 className="font-semibold text-slate-900">The rectification loop</h3>
              </div>
              <ol className="mt-4 grid gap-4 text-sm md:grid-cols-4">
                {[
                  ["Officer selects findings", "and requests rectification with a note. Status becomes Rectification requested; the institution is alerted."],
                  ["Institution responds", "by uploading corrected documents and marking findings rectified, with its own note."],
                  ["Pipeline runs again", "on the new uploads; the officer re-runs validation against the current ruleset."],
                  ["Officer closes or escalates", "each finding. The full exchange stays in the audit trail."],
                ].map(([a, b], i) => (
                  <li key={a} className="rounded-md bg-[#F5F7FA] p-4">
                    <span className="vs-mono text-xs text-slate-400">{i + 1}</span>
                    <p className="font-semibold text-slate-900">{a}</p>
                    <p className="mt-1 text-slate-600">{b}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </Section>
      ))}

      <Section
        id="findings"
        eyebrow="Output"
        title="What a finding looks like"
        intro="A finding states what was found, why it matters and exactly where the evidence is. Officers can open the document at the cited page, compare submitted and source values, and dismiss, escalate or request rectification."
      >
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {EXAMPLE_FINDINGS.map((f) => (
            <FindingCard key={f.ruleId} f={f} />
          ))}
        </div>
        <div className="mt-8 flex flex-col gap-4 rounded-lg border border-amber-200 bg-amber-50 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <AdvisoryMarker />
            <p className="mt-2 max-w-2xl text-sm text-amber-900">
              Forensic and infrastructure findings are preliminary indicators. They point the officer to where a closer
              look is needed; they are not conclusions about authenticity or compliance.
            </p>
          </div>
          <Link
            to="/portal/login"
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md bg-[#0B2E59] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1D4E89]"
          >
            See real findings in the portal <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
      </Section>
    </>
  );
}
