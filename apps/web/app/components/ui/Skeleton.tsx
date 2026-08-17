"use client";

export interface SkeletonProps {
  className?: string;
}

/** A single pulsing placeholder block. Compose into SkeletonCard/SkeletonTable. */
export function Skeleton({ className = "" }: SkeletonProps) {
  return <div className={`animate-pulse rounded-md bg-white/[0.06] ${className}`} />;
}

export interface SkeletonCardProps {
  className?: string;
  lines?: number;
}

/** Loading placeholder matching MetricCard's shape. */
export function SkeletonCard({ className = "" }: SkeletonCardProps) {
  return (
    <div className={`surface rounded-2xl p-5 ${className}`}>
      <Skeleton className="mb-3 h-3 w-24" />
      <Skeleton className="mb-2 h-7 w-32" />
      <Skeleton className="h-3 w-20" />
    </div>
  );
}

export interface SkeletonTableProps {
  rows?: number;
  cols?: number;
  className?: string;
}

/** Loading placeholder matching DataTable's shape. */
export function SkeletonTable({ rows = 5, cols = 4, className = "" }: SkeletonTableProps) {
  return (
    <div className={`surface space-y-3 rounded-xl p-4 ${className}`}>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
