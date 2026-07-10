"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { CollapsibleSection } from "@/app/components/ui/CollapsibleSection";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { JsonViewer } from "@/app/components/ui/JsonViewer";
import { VARIANT_STYLES } from "@/app/components/ui/variants";
import { fmtDate } from "@/app/lib/format";
import type { StrategyRecord } from "@/app/lib/types";

/** A Link styled to match the kit's Button (secondary variant) -- Button itself renders a <button>. */
function LinkButton({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.06] px-3.5 py-2 text-sm font-medium text-text transition-colors duration-150 hover:bg-white/[0.1]"
    >
      {children}
    </Link>
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

/**
 * `stop_loss` / `position_sizing` are `{"type": ..., "value": <fraction>}` per
 * docs/strategy-format.md. StrategyRecord types these as `unknown` (loose by
 * design), so this narrows just the `value` fraction we need for display.
 */
function extractFractionValue(value: unknown): number | null {
  const rec = asRecord(value);
  if (!rec) return null;
  return typeof rec.value === "number" ? rec.value : null;
}

function chipClass(variant: "accent" | "neutral"): string {
  const style = VARIANT_STYLES[variant];
  return `inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.text} ${style.border}`;
}

export interface StrategyCardProps {
  strategy: StrategyRecord;
}

export function StrategyCard({ strategy }: StrategyCardProps) {
  const isBuiltin = strategy.source === "builtin";
  const universeCount = Array.isArray(strategy.universe) ? strategy.universe.length : 0;
  const stopLossPct = extractFractionValue(strategy.stop_loss);
  const sizingPct = extractFractionValue(strategy.position_sizing);

  return (
    <GlassCard hover>
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-mono-ui text-lg font-semibold text-text">{strategy.name}</h3>
        {isBuiltin ? (
          <span className={chipClass("accent")}>Built-in</span>
        ) : (
          <div className="flex shrink-0 items-center gap-2">
            <span className={chipClass("neutral")}>Persisted</span>
            <DecisionBadge status={strategy.status} size="sm" />
          </div>
        )}
      </div>

      <p className="mt-2 min-h-[2.5rem] text-sm text-text-muted">
        {strategy.description || "No description provided."}
      </p>

      <dl className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs">
        <Fact label="Timeframe" value={strategy.timeframe} />
        <Fact label="Direction" value={strategy.direction.replace(/_/g, " ")} />
        <Fact label="Stop-loss" value={stopLossPct != null ? `${(stopLossPct * 100).toFixed(1)}%` : "—"} />
        <Fact
          label="Sizing"
          value={sizingPct != null ? `${(sizingPct * 100).toFixed(1)}% risk/trade` : "—"}
        />
        <Fact label="Universe" value={`${universeCount} symbol${universeCount === 1 ? "" : "s"}`} />
      </dl>

      {!isBuiltin && strategy.created_at && (
        <p className="mt-2 text-[11px] text-text-faint">Created {fmtDate(strategy.created_at)}</p>
      )}

      <div className="mt-4">
        <CollapsibleSection title="Full definition">
          <JsonViewer data={strategy} label={`${strategy.name}.json`} />
        </CollapsibleSection>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <LinkButton href="/research">Research →</LinkButton>
        <LinkButton href="/backtests">Run backtest →</LinkButton>
      </div>
    </GlassCard>
  );
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] font-medium uppercase tracking-wide text-text-faint">{label}</dt>
      <dd className="mt-0.5 font-medium text-text">{value}</dd>
    </div>
  );
}
