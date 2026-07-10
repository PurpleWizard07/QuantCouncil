"use client";

import { VARIANT_STYLES, type StatusVariant } from "./variants";

/**
 * Canonical status -> visual variant map, covering EVERY status vocabulary
 * used across the app:
 *   - risk decisions: APPROVED / REJECTED / NEEDS_REVIEW
 *   - CIO committee decisions: PAPER_TRADE / NO_TRADE / WATCHLIST
 *   - paper order status: FILLED / PENDING / CANCELLED / REJECTED
 *   - open/closed (positions, generic): OPEN / CLOSED
 *   - technical view: BULLISH / BEARISH / NEUTRAL / MIXED
 *   - quant researcher strategy_quality: STRONG / ACCEPTABLE / WEAK / INVALID
 *   - portfolio risk mode: NORMAL / RISK_OFF
 *   - strategy lifecycle: DRAFT / BACKTESTED / RISK_EVALUATED / RISK_APPROVED /
 *     PAPER_TRADING / RETIRED
 * Any value not in this map (including null/undefined) renders as a neutral
 * badge with its own text -- unknown statuses are never hidden or thrown on.
 */
const STATUS_VARIANT_MAP: Record<string, StatusVariant> = {
  // risk engine decisions
  APPROVED: "positive",
  REJECTED: "negative",
  NEEDS_REVIEW: "warning",
  // CIO committee decisions
  PAPER_TRADE: "positive",
  NO_TRADE: "negative",
  WATCHLIST: "watchlist",
  // paper order / generic lifecycle status
  FILLED: "positive",
  PENDING: "warning",
  CANCELLED: "neutral",
  // open/closed (positions and similar)
  OPEN: "watchlist",
  CLOSED: "neutral",
  // technical analyst view
  BULLISH: "positive",
  BEARISH: "negative",
  NEUTRAL: "neutral",
  MIXED: "warning",
  // quant researcher strategy_quality
  STRONG: "positive",
  ACCEPTABLE: "watchlist",
  WEAK: "warning",
  INVALID: "negative",
  // portfolio risk mode
  NORMAL: "positive",
  RISK_OFF: "warning",
  // strategy lifecycle (app.db.models.StrategyStatus)
  DRAFT: "neutral",
  BACKTESTED: "watchlist",
  RISK_EVALUATED: "watchlist",
  RISK_APPROVED: "positive",
  PAPER_TRADING: "accent",
  RETIRED: "neutral",
};

export interface DecisionBadgeProps {
  status: string | null | undefined;
  size?: "sm" | "md";
  pulse?: boolean;
  className?: string;
}

/**
 * One badge component for every status vocabulary in the app. Pass the raw
 * backend string verbatim (e.g. `risk.decision`, `cio.decision`,
 * `order.status`, `strategy.status`); it is uppercased and looked up. Values
 * outside the known vocabulary render as a neutral badge, never crash.
 */
export function DecisionBadge({ status, size = "md", pulse = false, className = "" }: DecisionBadgeProps) {
  const normalized = (status ?? "").toUpperCase().trim();
  const variant = STATUS_VARIANT_MAP[normalized] ?? "neutral";
  const style = VARIANT_STYLES[variant];
  const label = status ? status.replace(/_/g, " ") : "UNKNOWN";
  const sizeClass = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-wide ${sizeClass} ${style.bg} ${style.text} ${style.border} ${className}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${style.dot} ${pulse ? "animate-pulse-glow" : ""}`}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}
