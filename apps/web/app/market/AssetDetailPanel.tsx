"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { CollapsibleSection } from "@/app/components/ui/CollapsibleSection";
import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { MetricCard } from "@/app/components/ui/MetricCard";
import { Section } from "@/app/components/ui/Section";
import { Skeleton, SkeletonTable } from "@/app/components/ui/Skeleton";
import { PriceChart } from "@/app/components/ui/charts/PriceChart";
import { ApiError, getIndicators, getOhlcv } from "@/app/lib/api";
import { fmtDate, fmtInr, fmtInt, fmtNum, fmtPct } from "@/app/lib/format";
import type { IndicatorRow, OhlcvBar } from "@/app/lib/types";

const LOOKBACK_DAYS = 182; // ~6 months, per spec default for the selected-asset panel

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** 502 from the OHLCV/indicators endpoints means "no cached data / provider unreachable". */
function friendlyErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 502) {
    return "No cached data — run the ingestion CLI or check connectivity.";
  }
  if (err instanceof ApiError) return err.message;
  return "Something went wrong loading this data.";
}

export interface AssetDetailPanelProps {
  symbol: string;
  onClose: () => void;
}

export function AssetDetailPanel({ symbol, onClose }: AssetDetailPanelProps) {
  const [bars, setBars] = useState<OhlcvBar[] | null>(null);
  const [barsLoading, setBarsLoading] = useState(true);
  const [barsError, setBarsError] = useState<string | null>(null);

  const [indicatorRows, setIndicatorRows] = useState<IndicatorRow[] | null>(null);
  const [indicatorsLoading, setIndicatorsLoading] = useState(true);
  const [indicatorsError, setIndicatorsError] = useState<string | null>(null);

  const loadBars = () => {
    setBarsLoading(true);
    setBarsError(null);
    getOhlcv(symbol, { start_date: isoDaysAgo(LOOKBACK_DAYS), end_date: todayIso() })
      .then((res) => setBars(res.data))
      .catch((err: unknown) => setBarsError(friendlyErrorMessage(err)))
      .finally(() => setBarsLoading(false));
  };

  const loadIndicators = () => {
    setIndicatorsLoading(true);
    setIndicatorsError(null);
    getIndicators(symbol)
      .then((res) => setIndicatorRows(res.indicators))
      .catch((err: unknown) => setIndicatorsError(friendlyErrorMessage(err)))
      .finally(() => setIndicatorsLoading(false));
  };

  useEffect(() => {
    loadBars();
    loadIndicators();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const stats = useMemo(() => {
    if (!bars || bars.length === 0) return null;
    const closes = bars.map((b) => b.close).filter((v): v is number => v != null);
    const highs = bars.map((b) => b.high).filter((v): v is number => v != null);
    const lows = bars.map((b) => b.low).filter((v): v is number => v != null);
    return {
      lastClose: closes.length ? closes[closes.length - 1] : null,
      periodHigh: highs.length ? Math.max(...highs) : null,
      periodLow: lows.length ? Math.min(...lows) : null,
      bars: bars.length,
    };
  }, [bars]);

  const chartData = useMemo(() => (bars ?? []).map((b) => ({ date: b.date, close: b.close })), [bars]);
  const recentBars = useMemo(() => [...(bars ?? [])].slice(-10).reverse(), [bars]);

  const barColumns: DataTableColumn<OhlcvBar>[] = [
    { key: "date", header: "Date", render: (row) => fmtDate(row.date) },
    { key: "open", header: "Open", numeric: true, render: (row) => fmtInr(row.open) },
    { key: "high", header: "High", numeric: true, render: (row) => fmtInr(row.high) },
    { key: "low", header: "Low", numeric: true, render: (row) => fmtInr(row.low) },
    { key: "close", header: "Close", numeric: true, render: (row) => fmtInr(row.close) },
    { key: "volume", header: "Volume", numeric: true, render: (row) => fmtInt(row.volume) },
  ];

  const lastIndicatorRow =
    indicatorRows && indicatorRows.length > 0 ? indicatorRows[indicatorRows.length - 1] : null;

  return (
    <Section
      title={`Selected asset — ${symbol}`}
      description="Last ~6 months of daily bars, plus the current indicator readout."
      actions={
        <Button variant="ghost" onClick={onClose}>
          Close
        </Button>
      }
    >
      <div className="space-y-4">
        {barsLoading ? (
          <div className="surface rounded-2xl p-5">
            <Skeleton className="h-[260px] w-full" />
          </div>
        ) : barsError ? (
          <ErrorState message={barsError} onRetry={loadBars} />
        ) : (
          <>
            <div className="surface rounded-2xl p-5">
              <PriceChart data={chartData} height={260} />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Last close" value={fmtInr(stats?.lastClose)} />
              <MetricCard label="Period high" value={fmtInr(stats?.periodHigh)} accent="positive" />
              <MetricCard label="Period low" value={fmtInr(stats?.periodLow)} accent="negative" />
              <MetricCard label="Bars" value={fmtInt(stats?.bars)} subtext="last ~6 months" />
            </div>
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-text-muted">
                Recent bars (last 10, newest first)
              </h3>
              <DataTable columns={barColumns} data={recentBars} getRowKey={(row) => row.date} compact />
            </div>
          </>
        )}

        <CollapsibleSection title="Indicator preview">
          {indicatorsLoading ? (
            <SkeletonTable rows={1} cols={6} />
          ) : indicatorsError ? (
            <ErrorState message={indicatorsError} onRetry={loadIndicators} />
          ) : !lastIndicatorRow ? (
            <p className="text-sm text-text-muted">No indicator data available for this range.</p>
          ) : (
            <div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <IndicatorStat label="SMA 20" value={lastIndicatorRow.sma_20} formatter={fmtNum} />
                <IndicatorStat label="SMA 50" value={lastIndicatorRow.sma_50} formatter={fmtNum} />
                <IndicatorStat label="EMA 20" value={lastIndicatorRow.ema_20} formatter={fmtNum} />
                <IndicatorStat label="RSI 14" value={lastIndicatorRow.rsi_14} formatter={fmtNum} />
                <IndicatorStat label="ATR 14" value={lastIndicatorRow.atr_14} formatter={fmtNum} />
                <IndicatorStat
                  label="Volatility 20"
                  value={lastIndicatorRow.volatility_20}
                  formatter={(v) => fmtPct(v)}
                />
              </div>
              <p className="mt-3 text-xs text-text-faint">
                As of {fmtDate(lastIndicatorRow.date)}. A "—" on any indicator is its warm-up window
                (e.g. SMA 50 needs 50 bars of history before it produces a value) — not missing data.
              </p>
            </div>
          )}
        </CollapsibleSection>
      </div>
    </Section>
  );
}

function IndicatorStat({
  label,
  value,
  formatter,
}: {
  label: string;
  value: number | null;
  formatter: (value: number | null) => string;
}) {
  return (
    <div className="surface rounded-xl p-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-text-muted">{label}</div>
      <div className="mt-1 font-mono-ui text-sm font-semibold tabular-nums text-text">
        {formatter(value)}
      </div>
    </div>
  );
}
