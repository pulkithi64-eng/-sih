import { format, formatDistanceToNowStrict, isValid, parseISO } from "date-fns";

function toDate(v: string | number | Date | null | undefined): Date | null {
  if (v === null || v === undefined || v === "") return null;
  const d = v instanceof Date ? v : typeof v === "number" ? new Date(v) : parseISO(v);
  return isValid(d) ? d : null;
}

export function fmtDate(v: string | null | undefined, fallback = "—"): string {
  const d = toDate(v);
  return d ? format(d, "dd MMM yyyy") : v ? String(v) : fallback;
}

export function fmtDateTime(v: string | null | undefined, fallback = "—"): string {
  const d = toDate(v);
  return d ? format(d, "dd MMM yyyy, HH:mm") : v ? String(v) : fallback;
}

export function fmtRelative(v: string | null | undefined, fallback = "—"): string {
  const d = toDate(v);
  return d ? `${formatDistanceToNowStrict(d)} ago` : fallback;
}

export function fmtBytes(n: number | null | undefined): string {
  if (!n && n !== 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function fmtPct(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const v = n <= 1 && n > 0 && !Number.isInteger(n) ? n * 100 : n;
  return `${v.toFixed(digits)}%`;
}

/** Confidence values may arrive as 0-1 or 0-100. Normalise to 0-100. */
export function confPct(n: number | null | undefined): number {
  if (n === null || n === undefined || Number.isNaN(n)) return 0;
  return n <= 1 ? Math.round(n * 100) : Math.round(n);
}

export function fmtNumber(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: digits });
}

export function fmtValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "number") return fmtNumber(v, 2);
  if (Array.isArray(v)) return v.map((x) => (typeof x === "object" ? JSON.stringify(x) : String(x))).join(", ");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export function shortHash(h: string | null | undefined, n = 10): string {
  if (!h) return "—";
  return h.length > n ? `${h.slice(0, n)}…` : h;
}
