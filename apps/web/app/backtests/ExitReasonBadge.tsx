"use client";

import { VARIANT_STYLES, type StatusVariant } from "@/app/components/ui/variants";

/**
 * Trade exit reasons ("signal" | "stop_loss" | "max_holding" | "end_of_data",
 * per `quant_engine.backtest.Backtester`) aren't in DecisionBadge's status
 * vocabulary either. A small local badge gives each reason a meaningful tint
 * (stop-loss = negative, signal = accent, time-based = warning) while reusing
 * the shared VARIANT_STYLES tokens.
 */
const REASON_VARIANT: Record<string, StatusVariant> = {
  SIGNAL: "accent",
  STOP_LOSS: "negative",
  MAX_HOLDING: "warning",
  END_OF_DATA: "neutral",
};

export function ExitReasonBadge({ reason }: { reason: string | null | undefined }) {
  const normalized = (reason ?? "").toUpperCase().trim();
  const variant = REASON_VARIANT[normalized] ?? "neutral";
  const style = VARIANT_STYLES[variant];
  const label = reason ? reason.replace(/_/g, " ") : "—";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.text} ${style.border}`}
    >
      {label}
    </span>
  );
}
