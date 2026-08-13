/**
 * Shared status-variant styling used by DecisionBadge, GlassCard, MetricCard,
 * StatGlow, etc. One source of truth for "what does 'positive' look like"
 * so every component tints identically.
 */

export type StatusVariant = "positive" | "negative" | "warning" | "watchlist" | "accent" | "neutral";

export interface VariantStyle {
  text: string;
  bg: string;
  border: string;
  glow: string;
  dot: string;
  hex: string;
}

export const VARIANT_STYLES: Record<StatusVariant, VariantStyle> = {
  positive: {
    text: "text-positive",
    bg: "bg-positive-soft",
    border: "border-positive/40",
    glow: "glow-positive",
    dot: "bg-positive",
    hex: "#34b27a",
  },
  negative: {
    text: "text-negative",
    bg: "bg-negative-soft",
    border: "border-negative/40",
    glow: "glow-negative",
    dot: "bg-negative",
    hex: "#e15c6e",
  },
  warning: {
    text: "text-warning",
    bg: "bg-warning-soft",
    border: "border-warning/40",
    glow: "glow-warning",
    dot: "bg-warning",
    hex: "#e0a83e",
  },
  watchlist: {
    text: "text-watchlist",
    bg: "bg-watchlist-soft",
    border: "border-watchlist/40",
    glow: "glow-watchlist",
    dot: "bg-watchlist",
    hex: "#5698c7",
  },
  accent: {
    text: "text-accent",
    bg: "bg-accent-soft",
    border: "border-accent/40",
    glow: "glow-accent",
    dot: "bg-accent",
    hex: "#4cc3d9",
  },
  neutral: {
    text: "text-text-muted",
    bg: "bg-white/[0.05]",
    border: "border-white/10",
    glow: "",
    dot: "bg-text-faint",
    hex: "#7c8798",
  },
};
