import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

/** Compact marker shown next to every AI output. */
export function AdvisoryTag({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded border border-dashed border-saffron/60 bg-saffron/5 px-1.5 py-0.5 text-2xs font-medium text-orange-800",
        className,
      )}
      title="AI-generated output. Advisory only; requires officer review."
    >
      <Info className="h-3 w-3" aria-hidden />
      Advisory
    </span>
  );
}

/** Banner form of the advisory notice. */
export function AdvisoryNote({ className, children }: { className?: string; children?: React.ReactNode }) {
  return (
    <div
      role="note"
      className={cn(
        "flex items-start gap-2 rounded-md border border-saffron/30 bg-orange-50/60 px-3 py-2 text-xs text-orange-900",
        className,
      )}
    >
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>
        <strong className="font-semibold">Advisory — requires officer review.</strong>{" "}
        {children ?? "Automated checks assist scrutiny; they do not constitute an approval decision."}
      </span>
    </div>
  );
}

export default AdvisoryNote;
