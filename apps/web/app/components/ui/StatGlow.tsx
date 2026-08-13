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
  positive: "shadow-[0_0_40px_-8px_rgba(52,178,122,0.55)]",
  negative: "shadow-[0_0_40px_-8px_rgba(225,92,110,0.55)]",
  warning: "shadow-[0_0_40px_-8px_rgba(224,168,62,0.55)]",
  watchlist: "shadow-[0_0_40px_-8px_rgba(86,152,199,0.55)]",
  accent: "shadow-[0_0_40px_-8px_rgba(76,195,217,0.55)]",
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
