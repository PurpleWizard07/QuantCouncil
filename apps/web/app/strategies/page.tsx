"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { ApiError, getStrategies } from "@/app/lib/api";
import type { StrategyRecord } from "@/app/lib/types";

import { StrategyCard } from "./StrategyCard";

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<StrategyRecord[] | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    getStrategies()
      .then((res) => {
        setStrategies(res.strategies);
        setWarning(res.warning ?? null);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load strategies.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <MotionPage>
      <PageHeader
        title="Strategies"
        subtitle="Built-in templates and persisted strategy definitions with lifecycle status."
      />

      {warning && (
        <div className="mb-6 rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning">
          {warning}
        </div>
      )}

      <Section
        title="Strategy library"
        description="Built-in templates ship with the engine; persisted strategies move through the lifecycle as they're backtested, risk-evaluated, and approved."
      >
        {loading ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} className="h-64" />
            ))}
          </div>
        ) : error ? (
          <ErrorState message={error} onRetry={load} />
        ) : !strategies || strategies.length === 0 ? (
          <EmptyState
            title="No strategies yet"
            hint="Author a strategy definition via POST /strategies, or check back once built-in templates are seeded."
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {strategies.map((strategy, index) => (
              <StrategyCard
                key={strategy.id ?? `${strategy.source}-${strategy.name}-${index}`}
                strategy={strategy}
              />
            ))}
          </div>
        )}
      </Section>

      <Section title="Authoring">
        <GlassCard>
          <h3 className="text-sm font-semibold text-text">Strategy authoring is deferred</h3>
          <p className="mt-2 text-sm text-text-muted">
            A guided strategy-authoring UI is on the backlog. In the meantime, persisted strategies can
            be created directly via the API by POSTing a full, schema-valid strategy definition (see{" "}
            <code className="font-mono-ui text-text">docs/strategy-format.md</code>).
          </p>
          <div className="mt-3 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <span className="rounded bg-accent-soft px-1.5 py-0.5 font-mono-ui text-xs font-bold text-accent">
              POST
            </span>
            <code className="font-mono-ui text-sm text-text">/strategies</code>
          </div>
        </GlassCard>
      </Section>
    </MotionPage>
  );
}
