"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type ReactNode } from "react";

import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { SkeletonTable } from "@/app/components/ui/Skeleton";
import { ApiError, listBacktests } from "@/app/lib/api";
import { fmtDate, fmtDateTime, fmtInt, fmtNum, fmtPct, truncateId } from "@/app/lib/format";
import type { BacktestListItem } from "@/app/lib/types";

import { BacktestDetailPanel } from "./BacktestDetailPanel";
import { BacktestStatusBadge } from "./BacktestStatusBadge";
import { QuickRunForm } from "./QuickRunForm";

const LIST_LIMIT = 20;

function drawdownLabel(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `-${fmtPct(value)}`;
}

function ResearchCta({ children }: { children: ReactNode }) {
  return (
    <Link
      href="/research"
      className="inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-3.5 py-2 text-sm font-medium text-bg shadow-[0_0_20px_-6px_rgba(76,195,217,0.6)] transition-colors hover:bg-accent/90"
    >
      {children}
    </Link>
  );
}

function BacktestsPageInner() {
  const searchParams = useSearchParams();
  const [runs, setRuns] = useState<BacktestListItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get("backtest_id"));

  const load = () => {
    setLoading(true);
    setError(null);
    listBacktests(LIST_LIMIT)
      .then((res) => setRuns(res.backtests))
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : "Could not load backtest runs."),
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const columns: DataTableColumn<BacktestListItem>[] = [
    {
      key: "backtest_id",
      header: "Run",
      render: (row) => <span className="font-mono-ui text-text-muted">{truncateId(row.backtest_id)}</span>,
    },
    { key: "strategy_name", header: "Strategy", render: (row) => row.strategy_name ?? "—" },
    {
      key: "symbol",
      header: "Symbol",
      render: (row) => <span className="font-mono-ui font-semibold text-text">{row.symbol ?? "—"}</span>,
    },
    {
      key: "window",
      header: "Window",
      render: (row) => `${fmtDate(row.start_date)} – ${fmtDate(row.end_date)}`,
    },
    { key: "status", header: "Status", render: (row) => <BacktestStatusBadge status={row.status} /> },
    {
      key: "total_return",
      header: "Return",
      numeric: true,
      render: (row) => (
        <span
          className={
            row.metrics.total_return == null ? "" : row.metrics.total_return >= 0 ? "text-positive" : "text-negative"
          }
        >
          {fmtPct(row.metrics.total_return, { showSign: true })}
        </span>
      ),
    },
    {
      key: "max_drawdown",
      header: "Max DD",
      numeric: true,
      render: (row) => (
        <span className={row.metrics.max_drawdown ? "text-negative" : ""}>
          {drawdownLabel(row.metrics.max_drawdown)}
        </span>
      ),
    },
    { key: "sharpe", header: "Sharpe", numeric: true, render: (row) => fmtNum(row.metrics.sharpe) },
    { key: "num_trades", header: "Trades", numeric: true, render: (row) => fmtInt(row.metrics.num_trades) },
    { key: "created_at", header: "Created", render: (row) => fmtDateTime(row.created_at) },
  ];

  return (
    <MotionPage>
      <PageHeader
        title="Backtests"
        subtitle="Deterministic backtest runs: metrics, equity curves, and trade lists."
      />

      <Section
        title="Recent runs"
        description={`Last ${LIST_LIMIT} persisted runs, newest first. Click a row to inspect it below.`}
      >
        {loading ? (
          <SkeletonTable rows={6} cols={9} />
        ) : error ? (
          <ErrorState message={error} onRetry={load} />
        ) : !runs || runs.length === 0 ? (
          <EmptyState
            title="No persisted backtests yet"
            hint="Run your first backtest via the Research Pipeline, or use the quick-run form below."
            action={<ResearchCta>Open Research Pipeline →</ResearchCta>}
          />
        ) : (
          <DataTable
            columns={columns}
            data={runs}
            getRowKey={(row) => row.backtest_id}
            onRowClick={(row) => setSelectedId(row.backtest_id)}
          />
        )}
      </Section>

      {selectedId && <BacktestDetailPanel backtestId={selectedId} />}

      <Section
        title="New backtest"
        description="The full guided flow (strategy pick → backtest → risk gate → AI committee) lives in the Research Pipeline. Use the quick form for a bare persisted run."
      >
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[2fr_1fr]">
          <GlassCard>
            <QuickRunForm
              onRunComplete={(id) => {
                setSelectedId(id);
                load();
              }}
            />
          </GlassCard>
          <GlassCard variant="highlighted">
            <h3 className="text-sm font-semibold text-text">Research Pipeline</h3>
            <p className="mt-2 text-sm text-text-muted">
              Strategy selection, backtest, risk gate, and AI committee review, guided end to end.
            </p>
            <div className="mt-4">
              <ResearchCta>Open Research Pipeline →</ResearchCta>
            </div>
          </GlassCard>
        </div>
      </Section>
    </MotionPage>
  );
}

export default function BacktestsPage() {
  return (
    <Suspense fallback={null}>
      <BacktestsPageInner />
    </Suspense>
  );
}
