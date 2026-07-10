"use client";

import type { LabelHTMLAttributes } from "react";

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {}

/** Small uppercase-ish form label used above Input/Select/Textarea. */
export function Label({ className = "", children, ...rest }: LabelProps) {
  return (
    <label {...rest} className={`mb-1.5 block text-xs font-medium text-text-muted ${className}`}>
      {children}
    </label>
  );
}
