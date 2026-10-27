import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, BookOpen } from "lucide-react";
import { Container, PageHero } from "../components/Section";
import { docUrl, REPO_URL } from "../data/content";
import { DEMO_USERS, ROLE_GUIDES, DEMO_SCRIPT, REFERENCE_DOCS } from "../data/docs";

const TOC = [
  { id: "start", label: "Getting started" },
  { id: "accounts", label: "Demo accounts" },
  ...ROLE_GUIDES.map((g) => ({ id: g.id, label: g.role })),
  { id: "demo", label: "Seven-minute demo" },
  { id: "reference", label: "Reference documents" },
];

function H2({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className="scroll-mt-24 text-2xl font-semibold text-[#0B2E59]">
      {children}
    </h2>
  );
}

function Code({ children }: { children: string }) {
  return (
    <pre className="vs-mono mt-3 overflow-x-auto rounded-lg bg-[#0B2E59] p-4 text-[12.5px] leading-relaxed text-blue-50">
      {children}
    </pre>
  );
}

export default function DocsHub() {
  return (
    <>
      <PageHero
        eyebrow="Documentation"
        title="Run it, use it, demo it"
        intro="Setup instructions, a guide for each role, and the seven-minute demo script. Full technical references live in the repository's docs folder."
      />
      <Container className="grid gap-10 py-12 lg:grid-cols-[220px,1fr]">
        <aside className="hidden lg:block">
          <nav aria-label="Documentation" className="sticky top-24 space-y-1 text-sm">
            {TOC.map((t) => (
              <a key={t.id} href={`#${t.id}`} className="block rounded px-3 py-1.5 text-slate-600 hover:bg-[#F5F7FA] hover:text-[#0B2E59]">
                {t.label}
              </a>
            ))}
          </nav>
        </aside>

        <div className="min-w-0 space-y-16">
          <section>
            <H2 id="start">Getting started</H2>
            <p className="mt-3 text-slate-600">
              Requirements: Python 3.11 with <code className="vs-mono text-sm">uv</code>, and Node.js 18 or later. The
              backend seeds demo users, institutions and applications on first start.
            </p>
            <p className="mt-5 text-sm font-semibold text-slate-900">Backend (port 8001)</p>
            <Code>{`cd backend\nuv sync\nuv run uvicorn app.main:app --port 8001`}</Code>
            <p className="mt-5 text-sm font-semibold text-slate-900">Frontend (port 5176)</p>
            <Code>{`cd frontend\nnpm install\nnpm run dev\n# open http://localhost:5176`}</Code>
            <p className="mt-3 text-sm text-slate-600">
              The development server proxies <code className="vs-mono">/api</code> and{" "}
              <code className="vs-mono">/mock</code> to the backend. Interactive API docs are at{" "}
              <code className="vs-mono">http://localhost:8001/docs</code>.
            </p>
          </section>

          <section>
            <H2 id="accounts">Demo accounts</H2>
            <p className="mt-3 text-slate-600">
              All accounts use the password <code className="vs-mono rounded bg-slate-100 px-1.5 py-0.5 text-sm">Demo@2026</code>.
            </p>
            <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#F5F7FA] text-xs uppercase tracking-wider text-slate-500">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-semibold">Username</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Role</th>
                    <th scope="col" className="hidden px-4 py-3 font-semibold sm:table-cell">Scope</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {DEMO_USERS.map((u) => (
                    <tr key={u.username}>
                      <td className="vs-mono px-4 py-3 text-[13px] text-slate-900">{u.username}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {u.role}
                        <span className="mt-0.5 block text-xs text-slate-500 sm:hidden">{u.scope}</span>
                      </td>
                      <td className="hidden px-4 py-3 text-slate-600 sm:table-cell">{u.scope}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Link
              to="/portal/login"
              className="mt-5 inline-flex items-center gap-2 rounded-md bg-[#0B2E59] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1D4E89]"
            >
              Open the portal
            </Link>
          </section>

          {ROLE_GUIDES.map((g) => (
            <section key={g.id}>
              <H2 id={g.id}>{g.role}</H2>
              <p className="mt-3 text-slate-600">{g.intro}</p>
              <ol className="mt-5 space-y-3">
                {g.steps.map((s, i) => (
                  <li key={s.t} className="flex gap-4 rounded-lg border border-slate-200 p-4">
                    <span className="vs-mono inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#EEF3FA] text-xs font-semibold text-[#0B2E59]">
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium text-slate-900">{s.t}</p>
                      <p className="mt-1 text-sm leading-relaxed text-slate-600">{s.b}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          ))}

          <section>
            <H2 id="demo">Seven-minute demo</H2>
            <p className="mt-3 text-slate-600">
              A timed walkthrough for evaluators. The full version with talking points is in{" "}
              <a href={docUrl("DEMO_SCRIPT.md")} className="font-medium text-[#1D4E89] underline underline-offset-4" target="_blank" rel="noreferrer">
                docs/DEMO_SCRIPT.md
              </a>
              .
            </p>
            <ol className="mt-5 divide-y divide-slate-200 rounded-lg border border-slate-200">
              {DEMO_SCRIPT.map((d) => (
                <li key={d.time} className="grid gap-2 p-4 sm:grid-cols-[88px,1fr]">
                  <p className="vs-mono text-sm font-medium text-[#1D4E89]">{d.time}</p>
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900">
                      {d.title} <span className="vs-mono text-xs font-normal text-slate-500">· {d.user}</span>
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-600">{d.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section>
            <H2 id="reference">Reference documents</H2>
            <p className="mt-3 text-slate-600">Maintained in the repository alongside the code.</p>
            <ul className="mt-5 grid gap-3 sm:grid-cols-2">
              {REFERENCE_DOCS.map((r) => (
                <li key={r.file}>
                  <a
                    href={docUrl(r.file)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex h-full gap-3 rounded-lg border border-slate-200 p-4 hover:border-[#1D4E89]"
                  >
                    <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-[#1D4E89]" aria-hidden />
                    <span className="min-w-0">
                      <span className="flex items-center gap-1.5 font-medium text-slate-900">
                        {r.title} <ExternalLink className="h-3.5 w-3.5 text-slate-400" aria-hidden />
                      </span>
                      <span className="vs-mono block text-xs text-slate-500">docs/{r.file}</span>
                      <span className="mt-1 block text-sm text-slate-600">{r.body}</span>
                    </span>
                  </a>
                </li>
              ))}
            </ul>
            <p className="mt-6 text-sm text-slate-600">
              Source code:{" "}
              <a href={REPO_URL} className="font-medium text-[#1D4E89] underline underline-offset-4" target="_blank" rel="noreferrer">
                {REPO_URL.replace("https://", "")}
              </a>
            </p>
          </section>
        </div>
      </Container>
    </>
  );
}
