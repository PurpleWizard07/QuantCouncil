"use client";

import type { ReactNode } from "react";

import { GlassCard } from "./GlassCard";
import { SkeletonCard } from "./Skeleton";
import { VARIANT_STYLES, type StatusVariant } from "./variants";

export interface MetricCardProps {
  label: string;
  value: ReactNode;
  delta?: string;
  deltaVariant?: "positive" | "negative" | "neutral";
  subtext?: string;
  accent?: StatusVariant;
  loading?: boolean;
  className?: string;
}

/** A single headline metric: label, big tabular-nums value, optional delta/subtext. */
export function MetricCard({
  label,
  value,
  delta,
  deltaVariant = "neutral",
  subtext,
  accent,
  loading = false,
  className = "",
}: MetricCardProps) {
  if (loading) return <SkeletonCard className={className} />;

  const accentStyle = accent ? VARIANT_STYLES[accent] : null;
  const deltaClass =
    deltaVariant === "positive" ? "text-positive" : deltaVariant === "negative" ? "text-negative" : "text-text-muted";

  return (
    <GlassCard className={className} padding="md">
      <div className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</div>
      <div
        className={`mt-2 text-2xl font-semibold tabular-nums ${accentStyle ? accentStyle.text : "text-text"}`}
      >
        {value}
      </div>
      {(delta || subtext) && (
        <div className="mt-1.5 flex items-center gap-2 text-xs">
          {delta && <span className={deltaClass}>{delta}</span>}
          {subtext && <span className="text-text-faint">{subtext}</span>}
        </div>
      )}
    </GlassCard>
  );
}
