import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: LucideIcon;
  tone?: "default" | "danger" | "warning" | "success" | "info";
  to?: string;
}

const TONE = {
  default: "text-navy bg-navy-50",
  danger: "text-red-700 bg-red-50",
  warning: "text-amber-700 bg-amber-50",
  success: "text-green-700 bg-green-50",
  info: "text-blue-700 bg-blue-50",
};

export function KpiCard({ label, value, hint, icon: Icon, tone = "default", to }: KpiCardProps) {
  const body = (
    <div className="flex h-full items-start justify-between gap-3 p-4">
      <div className="min-w-0">
        <p className="text-xs font-medium leading-5 text-muted-foreground">{label}</p>
        <p className="tabular mt-1.5 text-2xl font-semibold tracking-tight text-foreground">{value}</p>
        {hint && <p className="mt-1 text-xs leading-5 text-muted-foreground">{hint}</p>}
      </div>
      {Icon && (
        <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-md", TONE[tone])}>
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      )}
    </div>
  );
  const cls = "card-surface block h-full transition-colors";
  return to ? (
    <Link to={to} className={cn(cls, "hover:border-primary-600/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring")}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export default KpiCard;
