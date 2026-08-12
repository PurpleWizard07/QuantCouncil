import type { ReactNode } from "react";

/**
 * A horizontal (wraps on mobile) box-and-arrow flow diagram -- replaces the
 * two Mermaid flowcharts in the source content (the order-settlement
 * lifecycle, and the algo-trading pipeline) with a component that renders
 * natively in the app without a Mermaid runtime dependency.
 *
 * Composed via <Step> children rather than an array prop: MDX content
 * authoring is simplest when every prop is a plain string, and this avoids
 * passing complex object/array literals through the MDX compiler.
 */
export function Pipeline({ children }: { children: ReactNode }) {
  return (
    <div className="my-6 flex flex-wrap items-stretch gap-2 rounded-xl border border-white/10 bg-white/[0.02] p-4">
      {children}
    </div>
  );
}

export function Step({ label, detail, last = false }: { label: string; detail?: string; last?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex min-w-[9rem] max-w-[13rem] flex-col rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
        <span className="text-xs font-semibold text-text">{label}</span>
        {detail && <span className="mt-0.5 text-[11px] leading-snug text-text-muted">{detail}</span>}
      </div>
      {!last && (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="shrink-0 text-text-faint" aria-hidden="true">
          <path d="M4 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </div>
  );
}
