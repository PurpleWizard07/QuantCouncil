"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

import { InlineSpinner } from "./InlineSpinner";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  icon?: ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-bg hover:bg-accent/90 shadow-[0_0_20px_-6px_rgba(34,211,238,0.6)]",
  secondary: "bg-white/[0.06] text-text border border-white/10 hover:bg-white/[0.1]",
  ghost: "bg-transparent text-text-muted hover:text-text hover:bg-white/[0.05]",
  danger: "bg-negative/90 text-bg hover:bg-negative shadow-[0_0_20px_-6px_rgba(251,113,133,0.6)]",
};

/** Standard button: primary/secondary/ghost/danger, with a built-in loading state. */
export function Button({
  variant = "secondary",
  loading = false,
  icon,
  className = "",
  children,
  disabled,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${VARIANT_CLASSES[variant]} ${className}`}
    >
      {loading ? <InlineSpinner size="sm" /> : icon}
      {children}
    </button>
  );
}
