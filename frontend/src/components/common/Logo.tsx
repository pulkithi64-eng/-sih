import { cn } from "@/lib/utils";

interface LogoMarkProps {
  className?: string;
  /** Use on dark backgrounds (sidebar, hero). */
  inverted?: boolean;
  title?: string;
}

/** Original VeriSense mark: a shield with a verification tick. Not an official emblem. */
export function LogoMark({ className, inverted = false, title = "VeriSense" }: LogoMarkProps) {
  const shield = inverted ? "#FFFFFF" : "#0B2E59";
  const tick = inverted ? "#0B2E59" : "#FFFFFF";
  return (
    <svg viewBox="0 0 32 32" role="img" aria-label={title} className={cn("h-8 w-8 shrink-0", className)}>
      <path d="M16 2 4 6.5v8.2c0 7.3 5 13.4 12 15.3 7-1.9 12-8 12-15.3V6.5L16 2Z" fill={shield} />
      <path
        d="M16 4.6 6.4 8.2v6.5c0 6 4 11 9.6 12.7 5.6-1.7 9.6-6.7 9.6-12.7V8.2L16 4.6Z"
        fill="none"
        stroke="#E8772E"
        strokeWidth="1"
      />
      <path
        d="m10.5 15.8 3.8 3.8 7.4-7.6"
        fill="none"
        stroke={tick}
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface LogoProps extends LogoMarkProps {
  /** Show the "AICTE" prefix + tagline beneath the wordmark. */
  withTagline?: boolean;
  compact?: boolean;
}

/** Mark + wordmark lockup. */
export function Logo({ className, inverted = false, withTagline = false, compact = false }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark inverted={inverted} className={compact ? "h-7 w-7" : "h-8 w-8"} />
      {!compact && (
        <span className="flex flex-col leading-none">
          <span className={cn("text-[1.05rem] font-semibold tracking-tight", inverted ? "text-white" : "text-navy")}>
            <span className={cn("font-medium", inverted ? "text-white/70" : "text-muted-foreground")}>AICTE </span>
            VeriSense
          </span>
          {withTagline && (
            <span className={cn("mt-1 text-2xs font-medium", inverted ? "text-white/60" : "text-muted-foreground")}>
              Application Validation &amp; Compliance Verification
            </span>
          )}
        </span>
      )}
    </span>
  );
}

export default Logo;
