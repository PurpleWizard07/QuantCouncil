"use client";

import { useEffect, useState } from "react";

import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { InlineSpinner } from "@/app/components/ui/InlineSpinner";
import { MetricCard } from "@/app/components/ui/MetricCard";
import { Section } from "@/app/components/ui/Section";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { EquityCurveChart } from "@/app/components/ui/charts/EquityCurveChart";
import type { StatusVariant } from "@/app/components/ui/variants";
import { ApiError, getBacktest, getLatestRiskForBacktest } from "@/app/lib/api";
import { fmtDate, fmtInr, fmtInt, fmtNum, fmtPct, truncateId } from "@/app/lib/format";
import type {
  BacktestDetailResponse,
  RiskEvaluationDetailResponse,
  TradeRecord,
} from "@/app/lib/types";

import { BacktestStatusBadge } from "./BacktestStatusBadge";
import { ExitReasonBadge } from "./ExitReasonBadge";

/**
 * The backend's real trade dict includes `holding_days`, `entry_cost`, and
 * `exit_cost` (confirmed in apps/api/tests/test_backtests_api.py's
 * TRADE_KEYS), but the shared TradeRecord type in lib/types.ts only declares
 * the fields listed there. Extending locally (rather than editing the shared
 * type) is enough: TradeRecord's actual fields all stay required, and these
 * extra ones are optional, so a plain TradeRecord[] is still assignable here.
 */
interface TradeRecordExtra extends TradeRecord {
  holding_days?: number | null;
}

function signAccent(value: number | null | undefined): StatusVariant | undefined {
  if (value == null || !Number.isFinite(value)) return undefined;
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return undefined;
}

function profitFactorAccent(value: number | null | undefined): StatusVariant | undefined {
  if (value == null || !Number.isFinite(value)) return undefined;
  return value >= 1 ? "positive" : "negative";
}

function drawdownLabel(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `-${fmtPct(value)}`;
}

function ConfigChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 font-mono-ui text-xs text-text-muted">
      <span className="text-text-faint">{label}</span>
      <span className="text-text">{value}</span>
    </span>
  );
}

/** Risk verdict for this run: pending/none/loaded/error, 404 treated as "not evaluated yet" not an error. */
function RiskChip({ backtestId }: { backtestId: string }) {
  const [state, setState] = useState<"loading" | "none" | "loaded" | "error">("loading");
  const [risk, setRisk] = useState<RiskEvaluationDetailResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = () => {
    setState("loading");
    getLatestRiskForBacktest(backtestId)
      .then((res) => {
        setRisk(res);
        setState("loaded");
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setState("none");
          return;
        }
        setMessage(err instanceof ApiError ? err.message : "Could not load risk evaluation.");
        setState("error");
      });
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backtestId]);

  if (state === "loading") {
    return (
      <span className="inline-flex items-center gap-2 text-xs text-text-muted">
        <InlineSpinner size="sm" /> Checking risk…
      </span>
    );
  }
  if (state === "none") {
    return (
      <span className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.05] px-2.5 py-1 text-xs font-medium text-text-muted">
        Not evaluated yet
      </span>
    );
  }
  if (state === "error") {
    return (
      <span className="inline-flex items-center gap-2 text-xs text-negative">
        {message}
        <button type="button" onClick={load} className="underline underline-offset-2">
          Retry
        </button>
      </span>
    );
  }
  return <DecisionBadge status={risk?.decision} size="sm" />;
}

function BacktestDetailContent({ detail }: { detail: BacktestDetailResponse }) {
  const metrics = detail.metrics;
  const trades: TradeRecordExtra[] = detail.trades;

  const tradeColumns: DataTableColumn<TradeRecordExtra>[] = [
    { key: "entry_date", header: "Entry date", render: (row) => fmtDate(row.entry_date) },
    { key: "entry_price", header: "Entry", numeric: true, render: (row) => fmtInr(row.entry_price) },
    { key: "exit_date", header: "Exit date", render: (row) => fmtDate(row.exit_date) },
    { key: "exit_price", header: "Exit", numeric: true, render: (row) => fmtInr(row.exit_price) },
    { key: "quantity", header: "Qty", numeric: true, render: (row) => fmtInt(row.quantity) },
    {
      key: "pnl",
      header: "PnL",
      numeric: true,
      render: (row) => (
        <span className={row.pnl == null ? "" : row.pnl >= 0 ? "text-positive" : "text-negative"}>
          {fmtInr(row.pnl)}
        </span>
      ),
    },
    {
      key: "return_pct",
      header: "Return",
      numeric: true,
      render: (row) => (
        <span className={row.return_pct == null ? "" : row.return_pct >= 0 ? "text-positive" : "text-negative"}>
          {fmtPct(row.return_pct, { showSign: true })}
        </span>
      ),
    },
    { key: "holding_days", header: "Held (days)", numeric: true, render: (row) => fmtInt(row.holding_days) },
    { key: "exit_reason", header: "Exit reason", render: (row) => <ExitReasonBadge reason={row.exit_reason} /> },
  ];

  return (
    <div className="space-y-4">
      <div className="surface rounded-2xl p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-mono-ui text-base font-semibold text-text">
              {detail.strategy_name ?? "—"}
            </h3>
            <p className="mt-1 text-sm text-text-muted">
              <span className="font-mono-ui font-semibold text-text">{detail.symbol ?? "—"}</span>
              {" · "}
              {fmtDate(detail.start_date)} – {fmtDate(detail.end_date)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <BacktestStatusBadge status={detail.status} />
            <RiskChip backtestId={detail.backtest_id} />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <ConfigChip label="Capital" value={fmtInr(detail.config.initial_capital)} />
          <ConfigChip label="Slippage" value={fmtPct(detail.config.slippage_pct)} />
          <ConfigChip label="Cost" value={fmtPct(detail.config.transaction_cost_pct)} />
          <ConfigChip label="Max allocation" value={fmtPct(detail.config.max_allocation_pct)} />
        </div>
      </div>

      {!metrics ? (
        <p className="text-sm text-text-muted">No metrics available for this run yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Total return"
            value={fmtPct(metrics.total_return, { showSign: true })}
            accent={signAccent(metrics.total_return)}
          />
          <MetricCard
            label="CAGR"
            value={fmtPct(metrics.cagr, { showSign: true })}
            accent={signAccent(metrics.cagr)}
          />
          <MetricCard
            label="Max drawdown"
            value={drawdownLabel(metrics.max_drawdown)}
            accent={metrics.max_drawdown ? "negative" : undefined}
          />
          <MetricCard label="Win rate" value={fmtPct(metrics.win_rate)} />
          <MetricCard
            label="Profit factor"
            value={fmtNum(metrics.profit_factor)}
            accent={profitFactorAccent(metrics.profit_factor)}
          />
          <MetricCard label="Sharpe" value={fmtNum(metrics.sharpe)} accent={signAccent(metrics.sharpe)} />
          <MetricCard label="Num trades" value={fmtInt(metrics.num_trades)} />
          <MetricCard label="Final equity" value={fmtInr(metrics.final_equity)} />
        </div>
      )}

      <div className="surface rounded-2xl p-5">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-text-muted">
          Equity curve
        </h3>
        {detail.equity_curve.length > 0 ? (
          <EquityCurveChart data={detail.equity_curve} height={260} />
        ) : (
          <p className="text-sm text-text-muted">No equity curve data for this run.</p>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-text-muted">
          Trades ({trades.length})
        </h3>
        <DataTable
          columns={tradeColumns}
          data={trades}
          getRowKey={(row, i) => `${row.entry_date}-${row.exit_date}-${i}`}
          compact
          emptyState={
            <EmptyState
              title="No trades"
              hint="This run produced no closed trades over the selected window."
            />
          }
        />
      </div>
    </div>
  );
}

export function BacktestDetailPanel({ backtestId }: { backtestId: string }) {
  const [detail, setDetail] = useState<BacktestDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    getBacktest(backtestId)
      .then(setDetail)
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : "Could not load this backtest run."),
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backtestId]);

  return (
    <Section title="Run detail" description={`Backtest ${truncateId(backtestId)}`}>
      {loading ? (
        <div className="space-y-4">
          <SkeletonCard />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !detail ? null : (
        <BacktestDetailContent detail={detail} />
      )}
    </Section>
  );
}
