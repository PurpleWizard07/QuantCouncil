"use client";

import { motion } from "motion/react";

import { VARIANT_STYLES, type StatusVariant } from "../variants";

export interface MetricBarProps {
  label: string;
  /** Fraction 0..1 of the bar to fill. */
  value: number;
  /** Text shown at the right end (e.g. "62%", "12/20"). Defaults to a percentage of `value`. */
  valueLabel?: string;
  variant?: StatusVariant;
  className?: string;
}

/** Small labeled progress bar for compact metric readouts (win rate, exposure, ...). */
export function MetricBar({ label, value, valueLabel, variant = "accent", className = "" }: MetricBarProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const style = VARIANT_STYLES[variant];

  return (
    <div className={className}>
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className="text-xs text-text-muted">{label}</span>
        <span className={`text-xs font-semibold tabular-nums ${style.text}`}>
          {valueLabel ?? `${(clamped * 100).toFixed(0)}%`}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <motion.div
          className="h-full rounded-full"
          style={{ background: style.hex }}
          initial={{ width: 0 }}
          animate={{ width: `${clamped * 100}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}
