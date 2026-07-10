"use client";

import type { ReactNode } from "react";

import type { StatusVariant } from "./variants";

export interface StatGlowProps {
  variant: StatusVariant;
  children: ReactNode;
  pulse?: boolean;
  className?: string;
}

const GLOW_SHADOW: Record<StatusVariant, string> = {
  positive: "shadow-[0_0_40px_-8px_rgba(52,211,153,0.55)]",
  negative: "shadow-[0_0_40px_-8px_rgba(251,113,133,0.55)]",
  warning: "shadow-[0_0_40px_-8px_rgba(251,191,36,0.55)]",
  watchlist: "shadow-[0_0_40px_-8px_rgba(56,189,248,0.55)]",
  accent: "shadow-[0_0_40px_-8px_rgba(34,211,238,0.55)]",
  neutral: "",
};

/**
 * Wraps a value/decision (e.g. a big APPROVED/REJECTED label) in a soft
 * semantic glow halo for emphasis -- used where a decision deserves visual
 * weight beyond a small DecisionBadge (e.g. the dashboard's latest verdict).
 */
export function StatGlow({ variant, children, pulse = false, className = "" }: StatGlowProps) {
  return (
    <div
      className={`inline-flex rounded-xl transition-shadow duration-500 ${GLOW_SHADOW[variant]} ${pulse ? "animate-pulse-glow" : ""} ${className}`}
    >
      {children}
    </div>
  );
}
