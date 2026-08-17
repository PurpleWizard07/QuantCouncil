"use client";

import { Button } from "./Button";

export interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

/** Standard error panel: message plus an optional retry button. No fake fallback data. */
export function ErrorState({ message, onRetry, className = "" }: ErrorStateProps) {
  return (
    <div
      className={`surface flex flex-col items-center gap-3 rounded-2xl border-negative/30 p-8 text-center ${className}`}
    >
      <div className="text-sm font-medium text-negative">Something went wrong</div>
      <p className="max-w-sm text-xs text-text-muted">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
