import { PIPELINE_STEPS } from "../data/content";

// Phase of each step: automated (navy outline) vs human (navy fill).
const HUMAN = new Set([6, 7]);

// Hand-broken labels for the wide layout (box width fits ~14 characters per line).
const WIDE_LINES: string[][] = [
  ["Application"],
  ["Checklist"],
  ["OCR, classify", "& extract"],
  ["Forensics"],
  ["Issuer", "verification"],
  ["Rule engine"],
  ["Officer", "review"],
  ["Decision by", "authority"],
];

/** End-to-end pipeline. Horizontal on wide screens, vertical on narrow screens. */
export function PipelineDiagram() {
  const W = 128;
  const H = 96;
  const GAP = 22;
  const total = PIPELINE_STEPS.length * W + (PIPELINE_STEPS.length - 1) * GAP;

  return (
    <figure className="w-full">
      {/* Wide layout */}
      <svg
        viewBox={`0 0 ${total + 4} 172`}
        className="hidden w-full lg:block"
        role="img"
        aria-labelledby="pipe-title pipe-desc"
      >
        <title id="pipe-title">VeriSense end-to-end pipeline</title>
        <desc id="pipe-desc">
          Eight steps from application to decision: application, checklist, OCR classification and extraction,
          forensics, issuing-authority verification, rule engine, officer review, and decision by the competent authority.
        </desc>
        <defs>
          <marker id="pipe-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#1D4E89" />
          </marker>
        </defs>
        {/* phase brackets */}
        <g fontSize="11" fontWeight={600} fill="#475569" letterSpacing="0.08em">
          <line x1={2} x2={6 * (W + GAP) - GAP + 2} y1={14} y2={14} stroke="#CBD5E1" />
          <text x={2} y={8}>AUTOMATED PRELIMINARY SCRUTINY</text>
          <line x1={6 * (W + GAP) + 2} x2={total + 2} y1={14} y2={14} stroke="#E8772E" strokeWidth={2} />
          <text x={6 * (W + GAP) + 2} y={8} fill="#B45309">
            HUMAN AUTHORITY
          </text>
        </g>
        {PIPELINE_STEPS.map((s, i) => {
          const x = 2 + i * (W + GAP);
          const y = 30;
          const human = HUMAN.has(i);
          const lines = WIDE_LINES[i];
          return (
            <g key={s.short}>
              <rect
                x={x}
                y={y}
                width={W}
                height={H}
                rx={8}
                fill={human ? "#0B2E59" : "#FFFFFF"}
                stroke={human ? "#0B2E59" : "#1D4E89"}
                strokeWidth={1.5}
              />
              <circle cx={x + 18} cy={y + 18} r={10} fill={human ? "#E8772E" : "#EEF3FA"} />
              <text
                x={x + 18}
                y={y + 22}
                textAnchor="middle"
                fontSize="11"
                fontWeight={700}
                fill={human ? "#FFFFFF" : "#0B2E59"}
              >
                {i + 1}
              </text>
              {lines.map((ln, j) => (
                <text
                  key={j}
                  x={x + 12}
                  y={y + 50 + j * 16}
                  fontSize="13"
                  fontWeight={600}
                  fill={human ? "#FFFFFF" : "#0B2E59"}
                >
                  {ln}
                </text>
              ))}
              {i < PIPELINE_STEPS.length - 1 && (
                <line
                  x1={x + W + 2}
                  x2={x + W + GAP - 3}
                  y1={y + H / 2}
                  y2={y + H / 2}
                  stroke="#1D4E89"
                  strokeWidth={1.5}
                  markerEnd="url(#pipe-arrow)"
                />
              )}
            </g>
          );
        })}
        {/* rectification loop: review back to read */}
        <path
          d={`M ${2 + 6 * (W + GAP) + W / 2} ${30 + H} V ${150} H ${2 + 2 * (W + GAP) + W / 2} V ${30 + H + 4}`}
          fill="none"
          stroke="#E8772E"
          strokeWidth={1.5}
          className="vs-flow-dash"
          markerEnd="url(#pipe-arrow)"
        />
        <text
          x={2 + 4 * (W + GAP) + W / 2}
          y={166}
          textAnchor="middle"
          fontSize="12"
          fill="#B45309"
          fontWeight={500}
        >
          Rectification loop: institution re-uploads, pipeline and rules run again
        </text>
      </svg>

      {/* Narrow layout */}
      <svg
        viewBox={`0 0 352 ${PIPELINE_STEPS.length * 78 + 10}`}
        className="block w-full lg:hidden"
        role="img"
        aria-labelledby="pipe-title-m"
      >
        <title id="pipe-title-m">VeriSense end-to-end pipeline</title>
        <defs>
          <marker id="pipe-arrow-m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#1D4E89" />
          </marker>
        </defs>
        {PIPELINE_STEPS.map((s, i) => {
          const y = 4 + i * 78;
          const human = HUMAN.has(i);
          return (
            <g key={s.short}>
              <rect
                x={2}
                y={y}
                width={318}
                height={60}
                rx={8}
                fill={human ? "#0B2E59" : "#FFFFFF"}
                stroke={human ? "#0B2E59" : "#1D4E89"}
                strokeWidth={1.5}
              />
              <circle cx={26} cy={y + 30} r={12} fill={human ? "#E8772E" : "#EEF3FA"} />
              <text x={26} y={y + 34} textAnchor="middle" fontSize="12" fontWeight={700} fill={human ? "#FFF" : "#0B2E59"}>
                {i + 1}
              </text>
              <text x={48} y={y + 26} fontSize="14" fontWeight={600} fill={human ? "#FFF" : "#0B2E59"}>
                {s.label}
              </text>
              <text x={48} y={y + 45} fontSize="11" fill={human ? "#C7D7EE" : "#475569"}>
                {s.detail}
              </text>
              {i < PIPELINE_STEPS.length - 1 && (
                <line
                  x1={160}
                  x2={160}
                  y1={y + 62}
                  y2={y + 76}
                  stroke="#1D4E89"
                  strokeWidth={1.5}
                  markerEnd="url(#pipe-arrow-m)"
                />
              )}
            </g>
          );
        })}
        <path
          d={`M 320 ${4 + 6 * 78 + 30} H 344 V ${4 + 2 * 78 + 30} H 324`}
          fill="none"
          stroke="#E8772E"
          strokeWidth={1.5}
          className="vs-flow-dash"
          markerEnd="url(#pipe-arrow-m)"
        />
      </svg>
      <figcaption className="mt-4 text-sm text-slate-600 lg:hidden">
        The dashed line is the rectification loop: after an officer requests rectification, the institution re-uploads
        and the pipeline and rules run again.
      </figcaption>
    </figure>
  );
}
