"use client";

import type { ReactNode } from "react";

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
  className?: string;
}

/** Standard "nothing here yet" panel: icon, title, hint, optional action button. */
export function EmptyState({ icon, title, hint, action, className = "" }: EmptyStateProps) {
  return (
    <div className={`surface flex flex-col items-center justify-center gap-3 rounded-2xl p-10 text-center ${className}`}>
      {icon && <div className="text-text-faint">{icon}</div>}
      <div className="text-sm font-medium text-text">{title}</div>
      {hint && <p className="max-w-sm text-xs text-text-muted">{hint}</p>}
      {action}
    </div>
  );
}
