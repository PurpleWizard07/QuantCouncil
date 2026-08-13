"use client";

import type { ReactNode } from "react";

export interface LedgerRowProps {
  label: string;
  value: ReactNode;
  tone?: "positive" | "negative";
}

/** One label/value line in a dense financial ledger rail -- see the
 * dashboard and paper-portfolio hero bands. Not a card; a table row. */
export function LedgerRow({ label, value, tone }: LedgerRowProps) {
  const toneClass = tone === "positive" ? "text-positive" : tone === "negative" ? "text-negative" : "text-text";
  return (
    <div className="flex items-baseline justify-between gap-3 py-2.5">
      <span className="text-[11px] font-medium uppercase tracking-wide text-text-faint">{label}</span>
      <span className={`font-mono-ui text-sm font-semibold tabular-nums ${toneClass}`}>{value}</span>
    </div>
  );
}
