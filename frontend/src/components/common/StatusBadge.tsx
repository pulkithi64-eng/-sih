import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  CircleSlash,
  Clock,
  CloudOff,
  Eye,
  FileWarning,
  HelpCircle,
  type LucideIcon,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Shared status badge (CONTRACT section 7). Handles verification statuses primarily, plus
 * application, finding and checklist statuses so all status chips in the product look alike.
 */

type Tone = "green" | "red" | "orange" | "blue" | "slate" | "amber" | "gray" | "navy" | "violet";

const TONE_CLASS: Record<Tone, string> = {
  green: "bg-green-50 text-green-800 border-green-200",
  red: "bg-red-50 text-red-800 border-red-200",
  orange: "bg-orange-50 text-orange-800 border-orange-300",
  blue: "bg-blue-50 text-blue-800 border-blue-200",
  slate: "bg-slate-100 text-slate-700 border-slate-300",
  amber: "bg-amber-50 text-amber-800 border-amber-300",
  gray: "bg-gray-50 text-gray-600 border-gray-200",
  navy: "bg-navy-50 text-navy border-navy-100",
  violet: "bg-violet-50 text-violet-800 border-violet-200",
};

export const TONE_DOT: Record<Tone, string> = {
  green: "bg-green-600",
  red: "bg-red-600",
  orange: "bg-orange-600",
  blue: "bg-blue-600",
  slate: "bg-slate-500",
  amber: "bg-amber-500",
  gray: "bg-gray-400",
  navy: "bg-navy",
  violet: "bg-violet-600",
};

interface StatusDef {
  label: string;
  tone: Tone;
  icon: LucideIcon;
}

const VERIFICATION: Record<string, StatusDef> = {
  VERIFIED: { label: "Verified", tone: "green", icon: CheckCircle2 },
  MISMATCH_DETECTED: { label: "Mismatch detected", tone: "red", icon: XCircle },
  EXPIRED: { label: "Expired", tone: "orange", icon: FileWarning },
  VERIFICATION_PENDING: { label: "Verification pending", tone: "blue", icon: Clock },
  SOURCE_UNAVAILABLE: { label: "Source unavailable", tone: "slate", icon: CloudOff },
  MANUAL_REVIEW_REQUIRED: { label: "Manual review required", tone: "amber", icon: Eye },
  NOT_APPLICABLE: { label: "Not applicable", tone: "gray", icon: CircleSlash },
};

const APPLICATION: Record<string, StatusDef> = {
  DRAFT: { label: "Draft", tone: "gray", icon: CircleDashed },
  SUBMITTED: { label: "Submitted", tone: "blue", icon: Clock },
  UNDER_VALIDATION: { label: "Under validation", tone: "blue", icon: Clock },
  DEFICIENCIES_FLAGGED: { label: "Deficiencies flagged", tone: "red", icon: AlertTriangle },
  RECTIFICATION_REQUESTED: { label: "Rectification requested", tone: "amber", icon: FileWarning },
  SOURCE_VERIFICATION_PENDING: { label: "Source verification pending", tone: "slate", icon: CloudOff },
  UNDER_REVIEW: { label: "Under review", tone: "navy", icon: Eye },
  INSPECTION_ORDERED: { label: "Inspection ordered", tone: "violet", icon: Eye },
  RECOMMENDED: { label: "Recommended", tone: "green", icon: CheckCircle2 },
  DECIDED: { label: "Decided", tone: "navy", icon: CheckCircle2 },
};

const FINDING: Record<string, StatusDef> = {
  OPEN: { label: "Open", tone: "red", icon: CircleDashed },
  ACKNOWLEDGED: { label: "Acknowledged", tone: "blue", icon: Eye },
  RECTIFIED: { label: "Rectified", tone: "green", icon: CheckCircle2 },
  DISMISSED: { label: "Dismissed", tone: "gray", icon: CircleSlash },
  ESCALATED: { label: "Escalated", tone: "violet", icon: AlertTriangle },
};

const CHECKLIST: Record<string, StatusDef> = {
  PRESENT: { label: "Present", tone: "green", icon: CheckCircle2 },
  MISSING: { label: "Missing", tone: "red", icon: XCircle },
  EXPIRED: { label: "Expired", tone: "orange", icon: FileWarning },
  INVALID: { label: "Invalid", tone: "red", icon: AlertTriangle },
  NOT_REQUIRED: { label: "Not required", tone: "gray", icon: CircleSlash },
};

export type StatusKind = "verification" | "application" | "finding" | "checklist";

const MAPS: Record<StatusKind, Record<string, StatusDef>> = {
  verification: VERIFICATION,
  application: APPLICATION,
  finding: FINDING,
  checklist: CHECKLIST,
};

export function getStatusDef(status: string, kind?: StatusKind): StatusDef {
  if (kind && MAPS[kind][status]) return MAPS[kind][status];
  const found = VERIFICATION[status] ?? APPLICATION[status] ?? FINDING[status] ?? CHECKLIST[status];
  return (
    found ?? {
      label: status
        ? status.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase())
        : "Unknown",
      tone: "gray",
      icon: HelpCircle,
    }
  );
}

/** Hex colours for charts (same semantics as badges). */
export const VERIFICATION_CHART_COLOR: Record<string, string> = {
  VERIFIED: "#15803D",
  MISMATCH_DETECTED: "#B91C1C",
  EXPIRED: "#EA580C",
  VERIFICATION_PENDING: "#1D4ED8",
  SOURCE_UNAVAILABLE: "#64748B",
  MANUAL_REVIEW_REQUIRED: "#D97706",
  NOT_APPLICABLE: "#CBD5E1",
};

export interface StatusBadgeProps {
  status: string;
  kind?: StatusKind;
  size?: "sm" | "md";
  showIcon?: boolean;
  className?: string;
  label?: string;
}

export function StatusBadge({ status, kind, size = "sm", showIcon = true, className, label }: StatusBadgeProps) {
  const def = getStatusDef(status, kind);
  const Icon = def.icon;
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-1 whitespace-nowrap rounded-full border font-medium",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        TONE_CLASS[def.tone],
        className,
      )}
      title={label ?? def.label}
    >
      {showIcon && <Icon className={size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5"} aria-hidden />}
      <span className="truncate">{label ?? def.label}</span>
    </span>
  );
}

export default StatusBadge;
