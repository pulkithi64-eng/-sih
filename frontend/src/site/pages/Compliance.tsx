import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Section, PageHero } from "../components/Section";
import { PS_MAPPING, type MapStatus } from "../data/psMapping";
import { docUrl } from "../data/content";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<MapStatus, string> = {
  Built: "border-green-200 bg-green-50 text-green-800",
  "Prototype-simulated": "border-blue-200 bg-blue-50 text-blue-800",
  Designed: "border-slate-300 bg-slate-50 text-slate-700",
};

const STATUS_HELP: Record<MapStatus, string> = {
  Built: "Implemented and working in the prototype.",
  "Prototype-simulated": "Implemented end to end, against simulated external systems or seeded data.",
  Designed: "Specified in the architecture and docs; not implemented yet.",
};

function StatusTag({ s }: { s: MapStatus }) {
  return (
    <span className={cn("inline-flex whitespace-nowrap rounded border px-2 py-0.5 text-[11px] font-semibold", STATUS_STYLE[s])}>
      {s}
    </span>
  );
}

export default function Compliance() {
  const [filter, setFilter] = useState<MapStatus | "All">("All");
  const counts = useMemo(() => {
    const c: Record<string, number> = { Built: 0, "Prototype-simulated": 0, Designed: 0 };
    PS_MAPPING.forEach((g) => g.rows.forEach((r) => (c[r.status] += 1)));
    return c;
  }, []);
  const total = counts.Built + counts["Prototype-simulated"] + counts.Designed;

  return (
    <>
      <PageHero
        eyebrow="Problem statement mapping"
        title="Every requirement of PS 26261, and where it is answered"
        intro="This table lists each objective, functional requirement, deliverable, expected outcome and safeguard in the problem statement, the feature that addresses it, where to find it in the product, and an honest status."
      >
        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          {(Object.keys(STATUS_HELP) as MapStatus[]).map((s) => (
            <div key={s} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <StatusTag s={s} />
                <span className="text-xl font-semibold text-[#0B2E59]">
                  {counts[s]}
                  <span className="text-sm font-normal text-slate-400"> / {total}</span>
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">{STATUS_HELP[s]}</p>
            </div>
          ))}
        </div>
      </PageHero>

      <Section className="pt-10">
        <div className="mb-8 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by status">
          <span className="mr-1 text-sm text-slate-500">Show</span>
          {(["All", "Built", "Prototype-simulated", "Designed"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              aria-pressed={filter === f}
              className={cn(
                "rounded-full border px-3 py-1 text-sm font-medium",
                filter === f ? "border-[#0B2E59] bg-[#0B2E59] text-white" : "border-slate-300 text-slate-700 hover:border-[#1D4E89]",
              )}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="space-y-12">
          {PS_MAPPING.map((g) => {
            const rows = g.rows.filter((r) => filter === "All" || r.status === filter);
            if (!rows.length) return null;
            return (
              <div key={g.id} id={g.id} className="scroll-mt-24">
                <h2 className="text-xl font-semibold text-[#0B2E59]">{g.title}</h2>
                {/* Desktop table */}
                <div className="mt-4 hidden overflow-hidden rounded-lg border border-slate-200 md:block">
                  <table className="w-full table-fixed text-left text-sm">
                    <caption className="sr-only">{g.title}</caption>
                    <thead className="bg-[#F5F7FA] text-xs uppercase tracking-wider text-slate-500">
                      <tr>
                        <th scope="col" className="w-[26%] px-4 py-3 font-semibold">Requirement</th>
                        <th scope="col" className="w-[36%] px-4 py-3 font-semibold">Feature</th>
                        <th scope="col" className="w-[24%] px-4 py-3 font-semibold">Where in product</th>
                        <th scope="col" className="w-[14%] px-4 py-3 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 align-top">
                      {rows.map((r) => (
                        <tr key={r.requirement}>
                          <th scope="row" className="px-4 py-3 font-medium text-slate-900">{r.requirement}</th>
                          <td className="px-4 py-3 text-slate-600">
                            {r.feature}
                            {r.note && <p className="mt-1.5 text-xs text-slate-500">{r.note}</p>}
                          </td>
                          <td className="break-words px-4 py-3 text-slate-600">{r.where}</td>
                          <td className="px-4 py-3">
                            <StatusTag s={r.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Mobile cards */}
                <ul className="mt-4 space-y-3 md:hidden">
                  {rows.map((r) => (
                    <li key={r.requirement} className="rounded-lg border border-slate-200 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <p className="font-medium text-slate-900">{r.requirement}</p>
                        <StatusTag s={r.status} />
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{r.feature}</p>
                      {r.note && <p className="mt-1.5 text-xs text-slate-500">{r.note}</p>}
                      <p className="mt-2 break-words text-xs text-slate-500">
                        <span className="font-semibold text-slate-700">Where: </span>
                        {r.where}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>

        <p className="mt-12 text-sm text-slate-600">
          The same mapping is maintained in the repository as{" "}
          <a href={docUrl("PS_MAPPING.md")} className="font-medium text-[#1D4E89] underline underline-offset-4" target="_blank" rel="noreferrer">
            docs/PS_MAPPING.md
          </a>
          . Evaluation criteria are covered on the{" "}
          <Link to="/evaluation" className="font-medium text-[#1D4E89] underline underline-offset-4">
            evaluation page
          </Link>
          .
        </p>
      </Section>
    </>
  );
}
