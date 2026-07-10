"use client";

import { VARIANT_STYLES, type StatusVariant } from "@/app/components/ui/variants";

/**
 * DecisionBadge's shared status vocabulary doesn't cover backtest run status
 * (PENDING/RUNNING/COMPLETED/FAILED per `app.db.models.BacktestStatus`) --
 * every value there falls back to a neutral badge. This local component maps
 * the real run-status vocabulary to meaningful colors while reusing the same
 * VARIANT_STYLES tokens, so it stays visually consistent with DecisionBadge.
 */
const STATUS_VARIANT: Record<string, StatusVariant> = {
  COMPLETED: "positive",
  FAILED: "negative",
  RUNNING: "watchlist",
  PENDING: "warning",
};

export function BacktestStatusBadge({
  status,
  size = "md",
}: {
  status: string | null | undefined;
  size?: "sm" | "md";
}) {
  const normalized = (status ?? "").toUpperCase().trim();
  const variant = STATUS_VARIANT[normalized] ?? "neutral";
  const style = VARIANT_STYLES[variant];
  const label = status ? status.replace(/_/g, " ") : "UNKNOWN";
  const sizeClass = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-wide ${sizeClass} ${style.bg} ${style.text} ${style.border}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden="true" />
      {label}
    </span>
  );
}
