import { KeyRound, Webhook, Server, Boxes, ShieldCheck, FileLock2, ScrollText, Network } from "lucide-react";
import { Section, PageHero, Card } from "../components/Section";
import { ArchitectureDiagram } from "../components/ArchitectureDiagram";

const COMPONENTS = [
  { name: "Web application", path: "frontend/", body: "React and TypeScript. Public website plus the role-based portal: dashboards, application workspace, document viewer with extracted fields and ELA overlay, findings, admin console." },
  { name: "API and access control", path: "backend/app/routers, security.py", body: "FastAPI service under /api. JWT authentication, role guards and server-side scoping by institution and region on every endpoint." },
  { name: "Document AI pipeline", path: "backend/app/pipeline", body: "Pure functions with no database access: OCR, classification, extraction, forensics, hashing, QR decoding, signature verification, infrastructure CV. Independently testable." },
  { name: "Verification adapters", path: "backend/app/adapters", body: "One adapter per issuing authority behind a common interface. Each returns a normalised six-state result with source, method, timestamp and comparisons." },
  { name: "Rule engine", path: "backend/app/engine", body: "Loads versioned rules and checklists, runs validation, writes findings and alerts, computes scores and renders the PDF report." },
  { name: "Audit log", path: "backend/app/audit.py", body: "Append-only event log in which each entry includes the hash of the previous one. Chain verification endpoint for administrators." },
  { name: "Configuration", path: "backend/config", body: "rules.yaml, checklists.yaml, doc_types.yaml and issuer public keys. Edited through the admin console; every change versioned and audited." },
  { name: "Simulated authorities", path: "backend/app/mock_authorities", body: "Stand-ins for issuing authorities, mounted at /mock/*, with their own records and Ed25519 signing keys, used only for the prototype." },
];

const FLOW = [
  ["Upload", "Institution uploads a file. It is stored, hashed (SHA-256, perceptual hash) and recorded in the audit log."],
  ["Read", "OCR, classification and extraction produce text, a document type and fields with confidence and source text."],
  ["Inspect", "Forensics computes ELA and inspects metadata; QR payloads are decoded and signatures checked."],
  ["Verify", "The adapter for the document type queries its source; the result, response and timestamp are stored."],
  ["Validate", "On submission the rule engine evaluates the category's rules against documents, form data and institutional records."],
  ["Report", "Findings, alerts, scores and a versioned validation report are written; the institution and officer are notified."],
  ["Review", "Officers act on findings; the Regional Director records the decision. Every step is chained in the audit log."],
];

const INTEGRATION = [
  { Icon: KeyRound, t: "Single sign-on", b: "Officials authenticate with the AICTE identity provider (OIDC/SAML); VeriSense maps their role and region from token claims instead of keeping its own passwords." },
  { Icon: Network, t: "Records API", b: "Institutional records are read through one interface. In the prototype it is backed by seeded data; in production it calls the AICTE portal's existing databases." },
  { Icon: Webhook, t: "Webhooks", b: "The AICTE portal notifies VeriSense when an application is submitted; VeriSense posts back the validation summary and, once recorded, the official's decision." },
  { Icon: ScrollText, t: "OpenAPI contract", b: "Every endpoint is described in the generated OpenAPI schema, so the portal team can integrate against a stable, typed contract." },
];

const DEPLOY = [
  { Icon: Boxes, t: "Containerised", b: "Backend and frontend build into standard container images with no GPU or external AI service required. OCR and CV models run on CPU." },
  { Icon: Server, t: "Government cloud ready", b: "Designed to run on NIC / MeghRaj infrastructure: PostgreSQL in place of SQLite, an object store for documents, secrets from the environment." },
  { Icon: ShieldCheck, t: "Stateless API", b: "JWT sessions and no in-process state allow the API to scale horizontally behind a load balancer; validation can move to a worker queue for large batches." },
];

const SECURITY = [
  ["Authentication", "JWT (HS256) with expiry; passwords hashed; designed to move to AICTE SSO."],
  ["Authorisation", "Four roles with explicit guards; institution and region scoping on every query, including file downloads."],
  ["Least privilege", "Only administrators change rules, checklists and sources; only Regional Directors record final decisions."],
  ["Audit", "Every mutating action and every verification response is written to the hash-chained log."],
  ["Data minimisation", "PAN masked in all views; full text available only to users who can see the application."],
  ["Transport and storage", "HTTPS terminated at the gateway in deployment; storage encryption provided by the hosting platform."],
];

export default function Architecture() {
  return (
    <>
      <PageHero
        eyebrow="Architecture"
        title="A small, auditable system designed to sit beside the AICTE portal"
        intro="VeriSense is a single API service with a web front end. The document AI pipeline is a set of pure functions, issuing authorities sit behind adapters, and rules live in versioned configuration — so each part can be tested, replaced or integrated on its own."
      />

      <Section eyebrow="Overview" title="System architecture">
        <ArchitectureDiagram />
        <p className="mt-4 text-sm text-slate-500">
          Dashed boxes are external systems. In the prototype the issuing authorities are simulated; AICTE portal
          integration is designed and documented but not connected.
        </p>
      </Section>

      <Section tone="canvas" eyebrow="Components" title="What each part does">
        <div className="grid gap-4 md:grid-cols-2">
          {COMPONENTS.map((c) => (
            <Card key={c.name}>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-semibold text-[#0B2E59]">{c.name}</h3>
                <code className="vs-mono break-all text-[11.5px] text-slate-500">{c.path}</code>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{c.body}</p>
            </Card>
          ))}
        </div>
      </Section>

      <Section eyebrow="Data flow" title="From upload to decision">
        <ol className="relative space-y-0 border-l-2 border-slate-200 pl-6">
          {FLOW.map(([t, b], i) => (
            <li key={t} className="relative pb-7 last:pb-0">
              <span className="absolute -left-[34px] top-0 inline-flex h-6 w-6 items-center justify-center rounded-full bg-[#0B2E59] text-[11px] font-semibold text-white">
                {i + 1}
              </span>
              <p className="font-semibold text-slate-900">{t}</p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-slate-600">{b}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        tone="canvas"
        eyebrow="Integration"
        title="Designed for integration with the AICTE portal"
        intro="VeriSense does not replace the existing approval portal. It is meant to be called by it, with officials signing in through the same identity provider."
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {INTEGRATION.map(({ Icon, t, b }) => (
            <Card key={t}>
              <Icon className="h-5 w-5 text-[#1D4E89]" aria-hidden />
              <h3 className="mt-3 text-sm font-semibold text-slate-900">{t}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{b}</p>
            </Card>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-500">Status: designed. The REST API and OpenAPI schema exist today; SSO and webhooks are not yet implemented.</p>
      </Section>

      <Section eyebrow="Deployment" title="Runs on modest, sovereign infrastructure">
        <div className="grid gap-4 md:grid-cols-3">
          {DEPLOY.map(({ Icon, t, b }) => (
            <Card key={t}>
              <Icon className="h-5 w-5 text-[#1D4E89]" aria-hidden />
              <h3 className="mt-3 text-sm font-semibold text-slate-900">{t}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{b}</p>
            </Card>
          ))}
        </div>
      </Section>

      <Section tone="navy" eyebrow="Security model" title="Access is enforced on the server, and every action leaves a trace">
        <div className="grid gap-px overflow-hidden rounded-lg bg-white/10 sm:grid-cols-2 lg:grid-cols-3">
          {SECURITY.map(([t, b]) => (
            <div key={t} className="bg-[#0B2E59] p-5">
              <FileLock2 className="h-4 w-4 text-[#F4A66F]" aria-hidden />
              <h3 className="mt-2 font-semibold text-white">{t}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-blue-100">{b}</p>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
