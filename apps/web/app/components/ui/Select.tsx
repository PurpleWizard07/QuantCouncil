"use client";

import type { SelectHTMLAttributes } from "react";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {}

/** A styled native <select>. Native is fine -- no custom listbox needed. */
export function Select({ className = "", children, ...rest }: SelectProps) {
  return (
    <select
      {...rest}
      className={`w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-text outline-none transition-colors focus:border-accent/50 focus:ring-2 focus:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    >
      {children}
    </select>
  );
}
