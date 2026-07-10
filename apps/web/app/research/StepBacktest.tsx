"use client";

import { useCallback, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { Input } from "@/app/components/ui/Input";
import { Label } from "@/app/components/ui/Label";
import { MetricCard } from "@/app/components/ui/MetricCard";
import { useToast } from "@/app/components/ui/Toast";
import { EquityCurveChart } from "@/app/components/ui/charts/EquityCurveChart";
import { runBacktest, type RunBacktestBody } from "@/app/lib/api";
import { fmtDate, fmtInr, fmtInt, fmtNum, fmtPct, truncateId } from "@/app/lib/format";
import type { AssetRecord, BacktestRunResponse, StrategyRecord, TradeRecord } from "@/app/lib/types";

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error.";
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function defaultDates(): { start: string; end: string } {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(start.getFullYear() - 2);
  return { start: isoDate(start), end: isoDate(end) };
}

/** Strips API/lifecycle metadata so a builtin strategy definition can be sent inline. */
function stripStrategyMetadata(strategy: StrategyRecord): Record<string, unknown> {
  const clone: Record<string, unknown> = { ...strategy };
  delete clone.source;
  delete clone.id;
  delete clone.status;
  delete clone.created_at;
  return clone;
}

export interface StepBacktestProps {
  symbol: AssetRecord;
  strategy: StrategyRecord;
  result: BacktestRunResponse | null;
  onSuccess: (result: BacktestRunResponse) => void;
  onContinue: () => void;
}

/** Step 3: run the backtest for the chosen symbol + strategy over a date range. */
export function StepBacktest({ symbol, strategy, result, onSuccess, onContinue }: StepBacktestProps) {
  const { showToast } = useToast();
  const [dates] = useState(defaultDates());
  const [startDate, setStartDate] = useState(dates.start);
  const [endDate, setEndDate] = useState(dates.end);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(() => {
    setLoading(true);
    setError(null);
    const body: RunBacktestBody =
      strategy.source === "persisted" && strategy.id
        ? { strategy_id: strategy.id, symbol: symbol.symbol, start_date: startDate, end_date: endDate, persist: true }
        : {
            strategy: stripStrategyMetadata(strategy),
            symbol: symbol.symbol,
            start_date: startDate,
            end_date: endDate,
            persist: true,
          };
    runBacktest(body)
      .then((res) => {
        onSuccess(res);
        showToast(`Backtest complete — ${res.trades.length} trades`, "success");
      })
      .catch((e) => {
        setError(errMsg(e));
        showToast(errMsg(e), "error");
      })
      .finally(() => setLoading(false));
  }, [strategy, symbol, startDate, endDate, onSuccess, showToast]);

  const copyId = useCallback(() => {
    if (!result?.backtest_id) return;
    navigator.clipboard
      .writeText(result.backtest_id)
      .then(() => showToast("Backtest ID copied", "success"))
      .catch(() => showToast("Could not copy to clipboard", "error"));
  }, [result, showToast]);

  const tradeColumns: DataTableColumn<TradeRecord>[] = [
    { key: "entry_date", header: "Entry date", render: (r) => fmtDate(r.entry_date) },
    { key: "entry_price", header: "Entry price", numeric: true, render: (r) => fmtInr(r.entry_price) },
    { key: "exit_date", header: "Exit date", render: (r) => fmtDate(r.exit_date) },
    { key: "exit_price", header: "Exit price", numeric: true, render: (r) => fmtInr(r.exit_price) },
    { key: "quantity", header: "Qty", numeric: true, render: (r) => fmtInt(r.quantity) },
    {
      key: "pnl",
      header: "PnL",
      numeric: true,
      render: (r) => <span className={(r.pnl ?? 0) >= 0 ? "text-positive" : "text-negative"}>{fmtInr(r.pnl)}</span>,
    },
    { key: "return_pct", header: "Return", numeric: true, render: (r) => fmtPct(r.return_pct) },
    { key: "exit_reason", header: "Exit reason", render: (r) => <DecisionBadge status={r.exit_reason} size="sm" /> },
  ];

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="bt-start">Start date</Label>
          <Input id="bt-start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="bt-end">End date</Label>
          <Input id="bt-end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
      </div>

      <div className="flex justify-end">
        <Button variant="primary" loading={loading} onClick={run}>
          Run backtest
        </Button>
      </div>

      {error && <ErrorState message={error} onRetry={run} />}

      {loading && !result && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <MetricCard key={i} label="" value="" loading />
          ))}
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Total return"
              value={fmtPct(result.metrics.total_return)}
              accent={(result.metrics.total_return ?? 0) >= 0 ? "positive" : "negative"}
            />
            <MetricCard label="CAGR" value={fmtPct(result.metrics.cagr)} />
            <MetricCard label="Max drawdown" value={fmtPct(result.metrics.max_drawdown)} accent="negative" />
            <MetricCard label="Win rate" value={fmtPct(result.metrics.win_rate)} />
            <MetricCard label="Profit factor" value={fmtNum(result.metrics.profit_factor)} />
            <MetricCard label="Sharpe" value={fmtNum(result.metrics.sharpe)} />
            <MetricCard label="Num trades" value={fmtInt(result.metrics.num_trades)} />
            <MetricCard label="Final equity" value={fmtInr(result.metrics.final_equity)} />
          </div>

          <EquityCurveChart data={result.equity_curve} />

          <DataTable
            columns={tradeColumns}
            data={result.trades}
            getRowKey={(r, i) => `${r.symbol}-${r.entry_date}-${i}`}
          />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-text-muted">
              {result.persisted && result.backtest_id ? (
                <button
                  type="button"
                  onClick={copyId}
                  className="font-mono-ui text-text-muted underline decoration-dotted underline-offset-2 hover:text-text"
                  title="Click to copy"
                >
                  backtest_id: {truncateId(result.backtest_id)}
                </button>
              ) : (
                <span>Not persisted{result.note ? ` — ${result.note}` : ""}</span>
              )}
            </div>
            <Button variant="primary" disabled={!result.persisted || !result.backtest_id} onClick={onContinue}>
              Continue to risk evaluation
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
