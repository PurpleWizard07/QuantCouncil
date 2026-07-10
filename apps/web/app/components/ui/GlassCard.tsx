"use client";

import type { ReactNode } from "react";

import { VARIANT_STYLES, type StatusVariant } from "./variants";

export type GlassCardVariant = "default" | "highlighted" | StatusVariant;

export interface GlassCardProps {
  children: ReactNode;
  variant?: GlassCardVariant;
  padding?: "none" | "sm" | "md" | "lg";
  hover?: boolean;
  className?: string;
}

const PADDING: Record<NonNullable<GlassCardProps["padding"]>, string> = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-7",
};

/**
 * The base glass panel every card-shaped surface in the app is built from.
 * `variant="highlighted"` adds an accent glow ring; a StatusVariant tints
 * the border/glow to that semantic color (e.g. a REJECTED backtest card).
 */
export function GlassCard({
  children,
  variant = "default",
  padding = "md",
  hover = false,
  className = "",
}: GlassCardProps) {
  const isStatus = variant !== "default" && variant !== "highlighted";
  const statusStyle = isStatus ? VARIANT_STYLES[variant as StatusVariant] : null;

  const borderClass = variant === "highlighted" ? "border-accent/40" : (statusStyle?.border ?? "");
  const glowClass = variant === "highlighted" ? "glow-accent" : (statusStyle?.glow ?? "");
  const hoverClass = hover ? "glass-hover" : "";

  return (
    <div
      className={`glass rounded-2xl ${PADDING[padding]} ${borderClass} ${glowClass} ${hoverClass} ${className}`}
    >
      {children}
    </div>
  );
}
