import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Container({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8", className)}>{children}</div>;
}

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn("text-xs font-semibold uppercase tracking-[0.14em] text-[#1D4E89]", className)}>
      <span className="mr-2 inline-block h-[2px] w-5 translate-y-[-3px] bg-[#E8772E] align-middle" aria-hidden />
      {children}
    </p>
  );
}

type SectionProps = {
  id?: string;
  eyebrow?: string;
  title?: ReactNode;
  intro?: ReactNode;
  tone?: "white" | "canvas" | "navy";
  className?: string;
  children?: ReactNode;
};

export function Section({ id, eyebrow, title, intro, tone = "white", className, children }: SectionProps) {
  const toneCls =
    tone === "canvas" ? "bg-[#F5F7FA]" : tone === "navy" ? "bg-[#0B2E59] text-white" : "bg-white";
  return (
    <section id={id} className={cn("scroll-mt-20 py-16 sm:py-20", toneCls, className)}>
      <Container>
        {(eyebrow || title || intro) && (
          <header className="mb-10 max-w-3xl">
            {eyebrow && <Eyebrow className={tone === "navy" ? "text-blue-200" : undefined}>{eyebrow}</Eyebrow>}
            {title && (
              <h2
                className={cn(
                  "mt-3 text-2xl font-semibold leading-tight sm:text-3xl",
                  tone === "navy" ? "text-white" : "text-[#0B2E59]",
                )}
              >
                {title}
              </h2>
            )}
            {intro && (
              <p className={cn("mt-4 text-base leading-relaxed", tone === "navy" ? "text-blue-100" : "text-slate-600")}>
                {intro}
              </p>
            )}
          </header>
        )}
        {children}
      </Container>
    </section>
  );
}

export function PageHero({
  eyebrow,
  title,
  intro,
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  intro: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="vs-grid-bg border-b border-slate-200 bg-[#F5F7FA]">
      <Container className="py-14 sm:py-16">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight text-[#0B2E59] sm:text-4xl">{title}</h1>
        <p className="mt-4 max-w-3xl text-base leading-relaxed text-slate-600 sm:text-lg">{intro}</p>
        {children}
      </Container>
    </section>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("rounded-lg border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]", className)}>
      {children}
    </div>
  );
}

export function AdvisoryMarker({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800",
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden />
      Advisory — requires officer review
    </span>
  );
}

export function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-xs font-medium text-slate-700",
        className,
      )}
    >
      {children}
    </span>
  );
}
