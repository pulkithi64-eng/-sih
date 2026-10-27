type BoxProps = {
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  lines?: string[];
  tone?: "white" | "navy" | "tint" | "dashed";
};

function Box({ x, y, w, h, title, lines = [], tone = "white" }: BoxProps) {
  const fill = tone === "navy" ? "#0B2E59" : tone === "tint" ? "#EEF3FA" : "#FFFFFF";
  const stroke = tone === "navy" ? "#0B2E59" : "#1D4E89";
  const titleFill = tone === "navy" ? "#FFFFFF" : "#0B2E59";
  const lineFill = tone === "navy" ? "#C7D7EE" : "#475569";
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={8}
        fill={fill}
        stroke={stroke}
        strokeWidth={1.25}
        strokeDasharray={tone === "dashed" ? "5 4" : undefined}
      />
      <text x={x + 12} y={y + 22} fontSize="13" fontWeight={600} fill={titleFill}>
        {title}
      </text>
      {lines.map((l, i) => (
        <text key={i} x={x + 12} y={y + 40 + i * 15} fontSize="11" fill={lineFill}>
          {l}
        </text>
      ))}
    </g>
  );
}

function Arrow({ d, dashed, label, lx, ly }: { d: string; dashed?: boolean; label?: string; lx?: number; ly?: number }) {
  return (
    <g>
      <path
        d={d}
        fill="none"
        stroke={dashed ? "#E8772E" : "#1D4E89"}
        strokeWidth={1.4}
        strokeDasharray={dashed ? "5 4" : undefined}
        markerEnd={dashed ? "url(#arch-arrow-s)" : "url(#arch-arrow)"}
      />
      {label && (
        <text x={lx} y={ly} fontSize="10.5" fill="#475569" textAnchor="middle">
          {label}
        </text>
      )}
    </g>
  );
}

const LAYERS = [
  {
    name: "Users",
    items: ["Institution nodal officer", "Scrutiny officer", "Regional director", "Administrator"],
  },
  { name: "Web application", items: ["Public website", "Role-based portal (React, TypeScript)"] },
  {
    name: "VeriSense API (FastAPI)",
    items: [
      "Authentication and RBAC (JWT, role guards, scoping)",
      "Validation engine: rules loader, validator, PDF report",
      "Document AI pipeline: OCR, classification, extraction, forensics, QR and signatures, infrastructure CV",
      "Verification adapters, one per issuing authority",
      "Hash-chained audit log",
    ],
  },
  { name: "Data", items: ["Relational database", "Document storage", "Versioned YAML configuration and issuer public keys"] },
  {
    name: "External (prototype: simulated)",
    items: ["Issuing authorities: fire services, municipal bodies, NBA, NAAC, universities, DigiLocker-style pull", "AICTE portal: SSO, records API, webhooks (designed)"],
  },
];

export function ArchitectureDiagram() {
  return (
    <figure className="w-full">
      <svg viewBox="0 0 1000 600" className="hidden w-full md:block" role="img" aria-labelledby="arch-title arch-desc">
        <title id="arch-title">VeriSense system architecture</title>
        <desc id="arch-desc">
          Users reach a React web application, which calls the FastAPI service. The service contains authentication
          and role-based access, the validation engine, the document AI pipeline, verification adapters and a
          hash-chained audit log, backed by a database, document storage and YAML configuration. Adapters call
          issuing authorities, which are simulated in the prototype. Integration with the AICTE portal is designed.
        </desc>
        <defs>
          <marker id="arch-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#1D4E89" />
          </marker>
          <marker id="arch-arrow-s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#E8772E" />
          </marker>
        </defs>

        {/* Users */}
        <text x={20} y={18} fontSize="11" fontWeight={600} fill="#475569" letterSpacing="0.08em">
          USERS
        </text>
        {["Institution", "Scrutiny officer", "Regional director", "Administrator"].map((u, i) => (
          <Box key={u} x={20 + i * 170} y={28} w={154} h={36} title={u} tone="tint" />
        ))}

        {/* Web app */}
        <Box x={20} y={98} w={664} h={58} title="React web application" lines={["Public website  ·  Role-based portal: dashboards, application workspace, findings, admin console"]} />
        <Arrow d="M 352 64 V 96" />

        {/* API */}
        <rect x={20} y={190} width={664} height={250} rx={10} fill="#F5F7FA" stroke="#0B2E59" strokeWidth={1.5} />
        <text x={34} y={212} fontSize="13" fontWeight={700} fill="#0B2E59">
          VeriSense API  ·  FastAPI, /api, JSON over HTTPS
        </text>
        <Arrow d="M 352 156 V 188" label="REST + JWT" lx={400} ly={177} />
        <Box x={34} y={224} w={200} h={88} title="Auth & RBAC" lines={["JWT sessions", "Role guards", "Institution / region scoping"]} tone="navy" />
        <Box x={246} y={224} w={210} h={88} title="Validation engine" lines={["Rules loader (versioned)", "Validator & scoring", "Report PDF"]} />
        <Box x={468} y={224} w={202} h={88} title="Audit log" lines={["Every mutating action", "SHA-256 hash chain", "Chain verification"]} />
        <Box
          x={34}
          y={324}
          w={422}
          h={102}
          title="Document AI pipeline (pure functions)"
          lines={[
            "OCR (PDF text layer, RapidOCR)  ·  classify  ·  extract fields",
            "Forensics: ELA, PDF/EXIF metadata, fonts  ·  SHA-256 + pHash",
            "QR decode + Ed25519 signature check  ·  infrastructure CV",
          ]}
        />
        <Box x={468} y={324} w={202} h={102} title="Verification adapters" lines={["One adapter per source", "Common interface", "Six-state outcome", "Timeout -> unavailable"]} />

        {/* Data */}
        <text x={20} y={478} fontSize="11" fontWeight={600} fill="#475569" letterSpacing="0.08em">
          DATA
        </text>
        <Box x={20} y={488} w={210} h={74} title="Database" lines={["SQLite (prototype)", "PostgreSQL (production)"]} tone="tint" />
        <Box x={247} y={488} w={210} h={74} title="Document storage" lines={["Original files, ELA heatmaps", "Object store in production"]} tone="tint" />
        <Box x={474} y={488} w={210} h={74} title="Configuration" lines={["rules / checklists / doc types", "Issuer public keys"]} tone="tint" />
        <Arrow d="M 125 440 V 486" />
        <Arrow d="M 352 440 V 486" />
        <Arrow d="M 579 440 V 486" />

        {/* External */}
        <text x={730} y={18} fontSize="11" fontWeight={600} fill="#475569" letterSpacing="0.08em">
          EXTERNAL SYSTEMS
        </text>
        <Box
          x={730}
          y={300}
          w={250}
          h={150}
          title="Issuing authorities"
          lines={["Fire services, municipal bodies", "NBA, NAAC, universities", "State government NOCs", "DigiLocker-style document pull", "", "Prototype: simulated at /mock/*"]}
          tone="dashed"
        />
        <Arrow d="M 670 375 H 728" dashed />
        <Box
          x={730}
          y={98}
          w={250}
          h={150}
          title="AICTE portal (designed)"
          lines={["Single sign-on for officials", "Institutional records API", "Webhooks: submission, decision", "Deployment: NIC / MeghRaj cloud,", "containerised"]}
          tone="dashed"
        />
        <Arrow d="M 728 173 H 686" dashed />
        <Arrow d="M 728 210 C 700 210 700 230 686 236" dashed />
      </svg>

      {/* Narrow layout: stacked layers */}
      <ol className="space-y-3 md:hidden" aria-label="VeriSense system architecture, top to bottom">
        {LAYERS.map((l, i) => (
          <li key={l.name}>
            <div
              className={
                i === 2
                  ? "rounded-lg border border-[#0B2E59] bg-[#F5F7FA] p-4"
                  : i === 4
                    ? "rounded-lg border border-dashed border-[#1D4E89] bg-white p-4"
                    : "rounded-lg border border-slate-200 bg-white p-4"
              }
            >
              <p className="text-sm font-semibold text-[#0B2E59]">{l.name}</p>
              <ul className="mt-2 space-y-1 text-sm text-slate-600">
                {l.items.map((it) => (
                  <li key={it} className="flex gap-2">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-[#1D4E89]" aria-hidden />
                    {it}
                  </li>
                ))}
              </ul>
            </div>
            {i < LAYERS.length - 1 && <div className="mx-auto h-3 w-px bg-[#1D4E89]" aria-hidden />}
          </li>
        ))}
      </ol>
    </figure>
  );
}
