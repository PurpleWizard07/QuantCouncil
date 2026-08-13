"use client";

import { motion } from "motion/react";

export interface RiskScoreGaugeProps {
  score: number; // 0-100, higher = safer
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

function bandColor(score: number): string {
  if (score >= 70) return "#34b27a"; // positive: low risk
  if (score >= 40) return "#e0a83e"; // warning: moderate risk
  return "#e15c6e"; // negative: high risk
}

function bandLabel(score: number): string {
  if (score >= 70) return "Low risk";
  if (score >= 40) return "Moderate risk";
  return "High risk";
}

const HEIGHT_CLASS: Record<NonNullable<RiskScoreGaugeProps["size"]>, string> = {
  sm: "h-1.5",
  md: "h-2",
  lg: "h-3",
};

/**
 * A 0-100 risk-score gauge, higher = safer, banded rose -> amber -> emerald.
 * Rendered as an animated horizontal gradient bar (readable at a glance,
 * scales down cleanly for a compact dashboard card).
 */
export function RiskScoreGauge({ score, label = "Risk score", size = "md", className = "" }: RiskScoreGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const color = bandColor(clamped);

  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-xs font-medium text-text-muted">{label}</span>
        <span className="text-sm font-semibold tabular-nums" style={{ color }}>
          {Math.round(clamped)}
          <span className="text-text-faint">/100</span>
        </span>
      </div>
      <div className={`relative w-full overflow-hidden rounded-full bg-white/[0.06] ${HEIGHT_CLASS[size]}`}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: "linear-gradient(90deg, #e15c6e, #e0a83e, #34b27a)" }}
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      <div className="mt-1 text-[11px] text-text-faint">{bandLabel(clamped)}</div>
    </div>
  );
}
