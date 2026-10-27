import { cn } from "@/lib/utils";

export function scoreTone(score: number) {
  if (score >= 80) return { bar: "bg-green-600", text: "text-green-800" };
  if (score >= 60) return { bar: "bg-amber-500", text: "text-amber-800" };
  return { bar: "bg-red-600", text: "text-red-800" };
}

/** Horizontal compliance score bar (0-100). */
export function ScoreBar({ value, className, showValue = true }: { value: number | null | undefined; className?: string; showValue?: boolean }) {
  const v = Math.max(0, Math.min(100, Math.round(Number(value ?? 0))));
  const tone = scoreTone(v);
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="h-1.5 w-full min-w-[3rem] overflow-hidden rounded-full bg-slate-200"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={v}
        aria-label="Compliance score"
      >
        <div className={cn("h-full rounded-full", tone.bar)} style={{ width: `${v}%` }} />
      </div>
      {showValue && <span className={cn("tabular w-8 text-right text-xs font-semibold", tone.text)}>{v}</span>}
    </div>
  );
}

/** Thin segmented progress showing verified / total. */
export function ProgressFraction({ done, total, className }: { done: number; total: number; className?: string }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-1.5 w-full min-w-[2.5rem] overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-primary-600" style={{ width: `${pct}%` }} />
      </div>
      <span className="tabular whitespace-nowrap text-xs text-muted-foreground">
        {done}/{total}
      </span>
    </div>
  );
}

/** Circular score gauge for headers. */
export function ScoreRing({ value, label, size = 56, invert = false }: { value: number; label: React.ReactNode; size?: number; invert?: boolean }) {
  const v = Math.max(0, Math.min(100, Math.round(value ?? 0)));
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  // for risk, higher is worse
  const toneScore = invert ? 100 - v : v;
  const color = toneScore >= 80 ? "#15803D" : toneScore >= 60 ? "#D97706" : "#B91C1C";
  return (
    <div className="flex items-center gap-2.5">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#E2E8F0" strokeWidth="5" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${(v / 100) * c} ${c}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" fontSize={size / 3.6} fontWeight={600} fill="#0F172A">
          {v}
        </text>
      </svg>
      <span className="text-xs font-medium leading-tight text-muted-foreground">{label}</span>
    </div>
  );
}
