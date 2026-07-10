"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { CollapsibleSection } from "@/app/components/ui/CollapsibleSection";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { JsonViewer } from "@/app/components/ui/JsonViewer";
import { Skeleton } from "@/app/components/ui/Skeleton";
import { getStrategies } from "@/app/lib/api";
import type { StrategyRecord } from "@/app/lib/types";

import { summarizeStrategyRules } from "./ruleSummary";

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error.";
}

function strategyKey(strategy: StrategyRecord): string {
  return strategy.id ?? `builtin:${strategy.name}`;
}

export interface StepStrategyProps {
  selected: StrategyRecord | null;
  onSelect: (strategy: StrategyRecord) => void;
  onContinue: () => void;
}

/** Step 2: pick a strategy definition, builtin or persisted. */
export function StepStrategy({ selected, onSelect, onContinue }: StepStrategyProps) {
  const [strategies, setStrategies] = useState<StrategyRecord[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getStrategies()
      .then((res) => {
        setStrategies(res.strategies);
        setWarning(res.warning ?? null);
      })
      .catch((e) => setError(errMsg(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-40 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  if (!strategies || strategies.length === 0) {
    return (
      <EmptyState
        title="No strategies available"
        hint="Neither builtin nor persisted strategies were returned by the API."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {warning && (
        <div className="rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-xs text-warning">
          {warning}
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {strategies.map((strategy) => {
          const isSelected = strategyKey(strategy) === (selected ? strategyKey(selected) : "");
          const rules = summarizeStrategyRules(strategy);
          return (
            <GlassCard
              key={strategyKey(strategy)}
              hover
              variant={isSelected ? "accent" : "default"}
              className="flex cursor-pointer flex-col gap-3"
              padding="md"
            >
              <div onClick={() => onSelect(strategy)} className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-text">{strategy.name}</div>
                    {strategy.description && (
                      <p className="mt-1 text-xs text-text-muted">{strategy.description}</p>
                    )}
                  </div>
                  <span className="shrink-0 rounded-full border border-white/10 bg-white/[0.05] px-2 py-0.5 text-[10px] uppercase tracking-wide text-text-muted">
                    {strategy.source}
                    {strategy.status ? ` · ${strategy.status}` : ""}
                  </span>
                </div>

                <div className="flex flex-wrap gap-1.5 text-[11px]">
                  {rules.entry.length > 0 && (
                    <span className="rounded-full border border-positive/30 bg-positive-soft px-2 py-0.5 text-positive">
                      entry: {rules.entry.join(", ")}
                    </span>
                  )}
                  {rules.exit.length > 0 && (
                    <span className="rounded-full border border-negative/30 bg-negative-soft px-2 py-0.5 text-negative">
                      exit: {rules.exit.join(", ")}
                    </span>
                  )}
                </div>
              </div>

              <CollapsibleSection title="Full definition">
                <JsonViewer data={strategy} label={strategy.name} />
              </CollapsibleSection>
            </GlassCard>
          );
        })}
      </div>
      <div className="flex justify-end">
        <Button variant="primary" disabled={!selected} onClick={onContinue}>
          Continue to backtest
        </Button>
      </div>
    </div>
  );
}
