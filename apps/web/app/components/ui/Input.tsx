"use client";

import type { InputHTMLAttributes } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

const BASE_CLASS =
  "w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-text placeholder:text-text-faint outline-none transition-colors focus:border-accent/50 focus:bg-white/[0.05] focus:ring-2 focus:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-50";

/** Styled text input. */
export function Input({ className = "", ...rest }: InputProps) {
  return <input {...rest} className={`${BASE_CLASS} ${className}`} />;
}
