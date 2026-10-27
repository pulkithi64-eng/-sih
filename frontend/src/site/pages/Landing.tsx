import { Link } from "react-router-dom";
import { ArrowRight, FileUp, ListChecks, UserCheck } from "lucide-react";
import { Container } from "../components/Section";
import { VERIFICATION_STATES } from "../data/content";

export default function Landing() {
  return <>
    <section className="border-b bg-slate-50">
      <Container className="grid gap-10 py-14 sm:py-20 lg:grid-cols-[1.2fr,1fr] lg:items-center">
        <div>
          <p className="text-sm font-medium text-slate-600">AICTE VeriSense · Document review prototype</p>
          <h1 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-[#0B2E59] sm:text-5xl">Upload documents.<br />See what needs attention.</h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-600">Prepare an application, check its supporting documents and follow the review. Officers see the evidence; authorised reviewers make the decisions.</p>
          <Link to="/portal/login" className="mt-7 inline-flex items-center gap-2 rounded-md bg-[#0B2E59] px-5 py-3 text-sm font-semibold text-white hover:bg-[#1D4E89] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1D4E89] focus-visible:ring-offset-2">Sign in to the portal<ArrowRight className="h-4 w-4" aria-hidden /></Link>
          <p className="mt-4 text-xs leading-relaxed text-slate-600">Unofficial prototype. All institutions and documents are synthetic. Issuer services are simulated, and handbook norms are illustrative.</p>
        </div>
        <ol className="divide-y rounded-lg border bg-white" aria-label="How to use VeriSense">
          {[
            { icon: FileUp, title: "1. Create and upload", text: "Choose an application category and upload the documents on its checklist." },
            { icon: ListChecks, title: "2. Check and correct", text: "Read verification results, see missing information and respond to findings." },
            { icon: UserCheck, title: "3. Follow the review", text: "An officer reviews the evidence. A regional director records the final decision." },
          ].map(({ icon: Icon, title, text }) => <li key={title} className="flex gap-4 p-5"><Icon className="mt-1 h-5 w-5 shrink-0 text-[#1D4E89]" aria-hidden /><div><h2 className="font-semibold text-slate-900">{title}</h2><p className="mt-1 text-sm leading-relaxed text-slate-600">{text}</p></div></li>)}
        </ol>
      </Container>
    </section>
    <Container className="py-10 sm:py-14">
      <h2 className="text-2xl font-semibold text-[#0B2E59]">Clear results, with the evidence behind them</h2>
      <p className="mt-3 max-w-3xl text-slate-600">A result tells you what matched, what needs correction and when a human must investigate. A source outage is not evidence of fraud. An integrity indicator is not proof of forgery.</p>
      <div className="mt-6 flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-[#1D4E89]">
        <Link className="underline underline-offset-4" to="/how-it-works">How the checks work</Link>
        <Link className="underline underline-offset-4" to="/compliance">Rules and limitations</Link>
        <Link className="underline underline-offset-4" to="/evaluation">Benchmarks and methodology</Link>
        <Link className="underline underline-offset-4" to="/help">Help and documentation</Link>
      </div>
      <details className="mt-8 rounded-lg border p-5">
        <summary className="cursor-pointer font-medium text-slate-900">Understand the six verification outcomes</summary>
        <dl className="mt-5 grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">{VERIFICATION_STATES.map(state => <div key={state.id}><dt className="font-semibold text-[#0B2E59]">{state.label}</dt><dd className="mt-1 text-sm leading-relaxed text-slate-600">{state.meaning}</dd></div>)}</dl>
      </details>
    </Container>
  </>;
}