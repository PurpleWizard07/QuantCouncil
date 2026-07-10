"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { Button } from "@/app/components/ui/Button";
import { CurveChart } from "@/app/components/ui/charts/CurveChart";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { Input } from "@/app/components/ui/Input";
import { Label } from "@/app/components/ui/Label";
import { MetricCard } from "@/app/components/ui/MetricCard";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { Select } from "@/app/components/ui/Select";
import { Skeleton, SkeletonCard } from "@/app/components/ui/Skeleton";
import { useToast } from "@/app/components/ui/Toast";
import {
  ApiError,
  createPortfolio,
  getAssets,
  getJournal,
  getNavHistory,
  getOrders,
  getPortfolios,
  getPositions,
  markToMarket,
  resetRiskOff,
  runDailyCycle,
} from "@/app/lib/api";
import { fmtDate, fmtInr, fmtInt, fmtPct, PLACEHOLDER, truncateId } from "@/app/lib/format";
import type {
  AssetRecord,
  JournalEntry,
  NavSnapshot,
  PaperOrder,
  PaperPortfolio,
  PaperPosition,
  StopTriggered,
} from "@/app/lib/types";

import { OrderForm } from "./OrderForm";
import { OrdersTable } from "./OrdersTable";
import { PositionsTable, type PositionFilter } from "./PositionsTable";
import { buildSymbolMaps } from "./symbols";

function errMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Unexpected error.";
}

function pnlNode(value: number | null): ReactNode {
  if (value == null) return PLACEHOLDER;
  const cls = value > 0 ? "text-positive" : value < 0 ? "text-negative" : "";
  return <span className={cls}>{fmtInr(value)}</span>;
}

export default function PaperPage() {
  const { showToast } = useToast();

  // --- portfolios -----------------------------------------------------------
  const [portfolios, setPortfolios] = useState<PaperPortfolio[] | null>(null);
  const [portfoliosLoading, setPortfoliosLoading] = useState(true);
  const [portfoliosError, setPortfoliosError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const loadPortfolios = useCallback(async () => {
    setPortfoliosLoading(true);
    setPortfoliosError(null);
    try {
      const res = await getPortfolios();
      setPortfolios(res.portfolios);
      setSelectedId((prev) => {
        if (prev && res.portfolios.some((p) => p.id === prev)) return prev;
        return res.portfolios[0]?.id ?? null;
      });
    } catch (err) {
      setPortfoliosError(errMessage(err));
    } finally {
      setPortfoliosLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPortfolios();
  }, [loadPortfolios]);

  const portfolio = useMemo(
    () => portfolios?.find((p) => p.id === selectedId) ?? null,
    [portfolios, selectedId],
  );

  // --- per-portfolio data -----------------------------------------------------
  const [positions, setPositions] = useState<PaperPosition[] | null>(null);
  const [positionsLoading, setPositionsLoading] = useState(false);
  const [positionsError, setPositionsError] = useState<string | null>(null);
  const [positionFilter, setPositionFilter] = useState<PositionFilter>("OPEN");

  const [orders, setOrders] = useState<PaperOrder[] | null>(null);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState<string | null>(null);

  // The journal feed is fetched here ONLY to reconstruct asset_id -> symbol
  // (see symbols.ts): orders/positions carry no symbol string in the API
  // contract. A journal fetch failure is non-fatal — tables fall back to
  // "#<asset_id>" labels.
  const [journal, setJournal] = useState<JournalEntry[]>([]);

  const loadPositions = useCallback(async (pid: string) => {
    setPositionsLoading(true);
    setPositionsError(null);
    try {
      const res = await getPositions(pid);
      setPositions(res.positions);
    } catch (err) {
      setPositionsError(errMessage(err));
    } finally {
      setPositionsLoading(false);
    }
  }, []);

  const loadOrders = useCallback(async (pid: string) => {
    setOrdersLoading(true);
    setOrdersError(null);
    try {
      const res = await getOrders(pid);
      setOrders(res.orders);
    } catch (err) {
      setOrdersError(errMessage(err));
    } finally {
      setOrdersLoading(false);
    }
  }, []);

  const loadJournal = useCallback(async (pid: string) => {
    try {
      const res = await getJournal(pid);
      setJournal(res.journal);
    } catch {
      setJournal([]);
    }
  }, []);

  const [navHistory, setNavHistory] = useState<NavSnapshot[] | null>(null);
  const [navHistoryLoading, setNavHistoryLoading] = useState(false);
  const [navHistoryError, setNavHistoryError] = useState<string | null>(null);

  const loadNavHistory = useCallback(async (pid: string) => {
    setNavHistoryLoading(true);
    setNavHistoryError(null);
    try {
      const res = await getNavHistory(pid, 365);
      setNavHistory(res.snapshots);
    } catch (err) {
      setNavHistoryError(errMessage(err));
    } finally {
      setNavHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setPositions(null);
      setOrders(null);
      setJournal([]);
      setNavHistory(null);
      return;
    }
    void loadPositions(selectedId);
    void loadOrders(selectedId);
    void loadJournal(selectedId);
    void loadNavHistory(selectedId);
  }, [selectedId, loadPositions, loadOrders, loadJournal, loadNavHistory]);

  const symbolMaps = useMemo(() => buildSymbolMaps(journal), [journal]);

  // --- assets (feeds the order form's symbol select) ---------------------------
  const [assets, setAssets] = useState<AssetRecord[] | null>(null);
  const [assetsError, setAssetsError] = useState<string | null>(null);

  const loadAssets = useCallback(async () => {
    setAssetsError(null);
    try {
      const res = await getAssets();
      setAssets(res.assets);
    } catch (err) {
      setAssetsError(errMessage(err));
    }
  }, []);

  useEffect(() => {
    void loadAssets();
  }, [loadAssets]);

  // --- actions ------------------------------------------------------------------
  const refreshAll = useCallback(() => {
    void loadPortfolios();
    if (selectedId) {
      void loadPositions(selectedId);
      void loadOrders(selectedId);
      void loadJournal(selectedId);
      void loadNavHistory(selectedId);
    }
  }, [loadPortfolios, loadPositions, loadOrders, loadJournal, loadNavHistory, selectedId]);

  async function handleCreatePortfolio() {
    setCreating(true);
    try {
      const created = await createPortfolio();
      showToast(`Created "${created.name}" with ${fmtInr(created.starting_capital)} simulated capital.`, "success");
      await loadPortfolios();
    } catch (err) {
      showToast(errMessage(err), "error");
    } finally {
      setCreating(false);
    }
  }

  const [mtmLoading, setMtmLoading] = useState(false);
  const [mtmError, setMtmError] = useState<string | null>(null);

  const handleMarkToMarket = useCallback(async () => {
    if (!selectedId) return;
    setMtmLoading(true);
    setMtmError(null);
    try {
      const res = await markToMarket(selectedId);
      showToast(
        `Marked to market — NAV ${fmtInr(res.nav)}${res.risk_off ? " · RISK-OFF is active" : ""}`,
        res.risk_off ? "error" : "success",
      );
      refreshAll();
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        setMtmError(`No cached price for a symbol — ingest data first. Server detail: ${err.message}`);
      } else {
        setMtmError(errMessage(err));
      }
    } finally {
      setMtmLoading(false);
    }
  }, [selectedId, refreshAll, showToast]);

  // --- daily cycle: stop-loss sweep -> mark-to-market -> NAV snapshot -----------
  const [dailyCycleLoading, setDailyCycleLoading] = useState(false);
  const [dailyCycleError, setDailyCycleError] = useState<string | null>(null);
  const [stopsTriggered, setStopsTriggered] = useState<StopTriggered[] | null>(null);

  const handleRunDailyCycle = useCallback(async () => {
    if (!selectedId) return;
    setDailyCycleLoading(true);
    setDailyCycleError(null);
    try {
      const res = await runDailyCycle(selectedId);
      const n = res.stops_triggered.length;
      showToast(
        `${n} stop${n === 1 ? "" : "s"} triggered · NAV ${fmtInr(res.mark_to_market.nav)} · snapshot ${fmtDate(res.snapshot.date)}`,
        "success",
      );
      setStopsTriggered(n > 0 ? res.stops_triggered : null);
      refreshAll();
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        setDailyCycleError(`No cached price for an open position — ingest data first. Server detail: ${err.message}`);
      } else {
        setDailyCycleError(errMessage(err));
      }
    } finally {
      setDailyCycleLoading(false);
    }
  }, [selectedId, refreshAll, showToast]);

  // --- risk-off manual reset ------------------------------------------------------
  const [showResetForm, setShowResetForm] = useState(false);
  const [resetNote, setResetNote] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  useEffect(() => {
    // Any of these are stale once the selected portfolio changes.
    setStopsTriggered(null);
    setDailyCycleError(null);
    setShowResetForm(false);
    setResetNote("");
    setResetError(null);
  }, [selectedId]);

  const handleResetRiskOff = useCallback(async () => {
    if (!selectedId) return;
    if (!resetNote.trim()) {
      setResetError("A note is required to reset risk-off.");
      return;
    }
    setResetLoading(true);
    setResetError(null);
    try {
      await resetRiskOff(selectedId, resetNote.trim());
      showToast("Risk-off cleared (journaled)", "success");
      setShowResetForm(false);
      setResetNote("");
      refreshAll();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setResetError(err.message);
      } else {
        setResetError(errMessage(err));
      }
    } finally {
      setResetLoading(false);
    }
  }, [selectedId, resetNote, refreshAll, showToast]);

  const orderPanelRef = useRef<HTMLDivElement>(null);

  // --- derived metrics ------------------------------------------------------------
  const openPositions = useMemo(() => positions?.filter((p) => p.status === "OPEN") ?? null, [positions]);
  const unrealizedPnl = useMemo(
    () => (openPositions ? openPositions.reduce((sum, p) => sum + (p.unrealized_pnl ?? 0), 0) : null),
    [openPositions],
  );
  const realizedPnl = useMemo(
    () => (positions ? positions.reduce((sum, p) => sum + (p.realized_pnl ?? 0), 0) : null),
    [positions],
  );
  const drawdown =
    portfolio && portfolio.peak_nav != null && portfolio.peak_nav > 0
      ? (portfolio.peak_nav - portfolio.current_nav) / portfolio.peak_nav
      : null;
  const riskOff = portfolio?.risk_mode === "RISK_OFF";
  const positionsPending = positionsLoading && positions === null;

  // --- render ------------------------------------------------------------------
  const headerActions = portfolio ? (
    <>
      {portfolios && portfolios.length > 1 && (
        <div className="min-w-[220px]">
          <Label htmlFor="portfolio-select" className="sr-only">
            Portfolio
          </Label>
          <Select id="portfolio-select" value={selectedId ?? ""} onChange={(e) => setSelectedId(e.target.value)}>
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
        </div>
      )}
      <Button variant="secondary" loading={mtmLoading} onClick={() => void handleMarkToMarket()}>
        Mark to market
      </Button>
      <Button variant="primary" loading={dailyCycleLoading} onClick={() => void handleRunDailyCycle()}>
        Run daily cycle
      </Button>
      <Button
        variant="primary"
        onClick={() => orderPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
      >
        New paper order
      </Button>
    </>
  ) : undefined;

  return (
    <MotionPage>
      <PageHeader
        title="Paper Fund"
        subtitle="Simulated cockpit — NAV, positions, and simulated order flow. No broker, no real money, ever."
        actions={headerActions}
      />

      {portfolio && (
        <p className="-mt-6 mb-6 text-xs text-text-faint">
          Daily cycle = stop-loss sweep → mark-to-market → NAV snapshot.
        </p>
      )}

      {portfoliosError ? (
        <ErrorState message={portfoliosError} onRetry={() => void loadPortfolios()} />
      ) : portfoliosLoading && portfolios === null ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : !portfolio ? (
        <EmptyState
          title="No paper portfolio yet"
          hint="Create the default simulated fund (₹10,00,000 fake capital) to start paper trading."
          action={
            <Button variant="primary" loading={creating} onClick={() => void handleCreatePortfolio()}>
              Create Default Paper Fund
            </Button>
          }
        />
      ) : (
        <>
          {riskOff && (
            <GlassCard variant="negative" padding="sm" className="mb-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <DecisionBadge status="RISK_OFF" pulse />
                  <p className="text-sm text-negative">
                    Risk-off latched — new BUYs blocked; SELLs still allowed; manual reset available — the reset is
                    journaled.
                  </p>
                </div>
                {!showResetForm && (
                  <Button variant="ghost" onClick={() => setShowResetForm(true)}>
                    Reset risk-off
                  </Button>
                )}
              </div>

              {showResetForm && (
                <div className="mt-4 border-t border-negative/20 pt-4">
                  <Label htmlFor="risk-off-note">Reset note (required, journaled)</Label>
                  <Input
                    id="risk-off-note"
                    value={resetNote}
                    onChange={(e) => setResetNote(e.target.value)}
                    placeholder="Why is risk-off being cleared?"
                  />
                  {resetError && (
                    <div className="mt-2 rounded-lg border border-warning/40 bg-warning-soft px-3 py-2 text-xs text-warning">
                      {resetError}
                    </div>
                  )}
                  <div className="mt-3 flex items-center gap-2">
                    <Button variant="danger" loading={resetLoading} onClick={() => void handleResetRiskOff()}>
                      Confirm reset
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setShowResetForm(false);
                        setResetNote("");
                        setResetError(null);
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </GlassCard>
          )}

          {mtmError && (
            <div className="mb-6">
              <ErrorState message={mtmError} onRetry={() => void handleMarkToMarket()} />
            </div>
          )}

          {dailyCycleError && (
            <div className="mb-6">
              <ErrorState message={dailyCycleError} onRetry={() => void handleRunDailyCycle()} />
            </div>
          )}

          {stopsTriggered && stopsTriggered.length > 0 && (
            <GlassCard variant="warning" padding="sm" className="mb-6">
              <div className="mb-2 flex items-center justify-between gap-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-warning">
                  Stop-loss triggered ({stopsTriggered.length})
                </div>
                <button
                  type="button"
                  onClick={() => setStopsTriggered(null)}
                  className="text-xs text-text-muted transition-colors hover:text-text"
                >
                  Dismiss
                </button>
              </div>
              <ul className="space-y-1.5">
                {stopsTriggered.map((s) => (
                  <li
                    key={s.order_id}
                    className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 font-mono-ui text-xs text-text-muted"
                  >
                    <span className="font-semibold text-text">{s.symbol}</span>
                    <span>{fmtInt(s.quantity)} sh</span>
                    <span>
                      stop {fmtInr(s.stop_loss)} vs close {fmtInr(s.close)}
                    </span>
                    <span className="text-accent">{truncateId(s.order_id)}</span>
                  </li>
                ))}
              </ul>
            </GlassCard>
          )}

          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="NAV"
              value={fmtInr(portfolio.current_nav)}
              accent="accent"
              subtext={`Peak ${fmtInr(portfolio.peak_nav)} · drawdown ${fmtPct(drawdown)}`}
            />
            <MetricCard
              label="Cash"
              value={fmtInr(portfolio.current_cash)}
              subtext={`Started with ${fmtInr(portfolio.starting_capital)}`}
            />
            <MetricCard
              label="Unrealized P&L"
              value={pnlNode(unrealizedPnl)}
              loading={positionsPending}
              subtext="Open positions, last mark"
            />
            <MetricCard
              label="Realized P&L"
              value={pnlNode(realizedPnl)}
              loading={positionsPending}
              subtext="All positions, net of costs"
            />
            <MetricCard
              label="Open positions"
              value={openPositions ? fmtInt(openPositions.length) : PLACEHOLDER}
              loading={positionsPending}
            />
            <MetricCard
              label="Risk mode"
              value={<DecisionBadge status={portfolio.risk_mode} pulse={riskOff} />}
              subtext={riskOff ? "New BUYs are vetoed" : "Entries allowed"}
            />
          </div>

          <Section
            title="NAV history"
            description={
              navHistory && navHistory.length > 0
                ? `Latest snapshot ${fmtDate(navHistory[navHistory.length - 1].date)} · drawdown ${fmtPct(
                    navHistory[navHistory.length - 1].drawdown,
                  )}`
                : undefined
            }
          >
            {navHistoryError ? (
              <ErrorState
                message={navHistoryError}
                onRetry={() => {
                  if (selectedId) void loadNavHistory(selectedId);
                }}
              />
            ) : navHistoryLoading && navHistory === null ? (
              <GlassCard padding="md">
                <Skeleton className="h-[240px] w-full" />
              </GlassCard>
            ) : navHistory && navHistory.length > 0 ? (
              <GlassCard padding="md">
                <CurveChart
                  data={navHistory}
                  xKey="date"
                  yKey="nav"
                  height={240}
                  color="#22d3ee"
                  variant="area"
                  valueFormatter={(v) => fmtInr(v)}
                />
              </GlassCard>
            ) : (
              <EmptyState
                title="No NAV snapshots yet"
                hint="Run the daily cycle to record the first one."
              />
            )}
          </Section>

          <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
            <div className="min-w-0">
              <PositionsTable
                positions={positions}
                loading={positionsLoading}
                error={positionsError}
                onRetry={() => {
                  if (selectedId) void loadPositions(selectedId);
                }}
                symbolMaps={symbolMaps}
                filter={positionFilter}
                onFilterChange={setPositionFilter}
              />
              <OrdersTable
                orders={orders}
                loading={ordersLoading}
                error={ordersError}
                onRetry={() => {
                  if (selectedId) void loadOrders(selectedId);
                }}
                symbolMaps={symbolMaps}
              />
            </div>
            <div ref={orderPanelRef} className="min-w-0 scroll-mt-24">
              <OrderForm
                portfolio={portfolio}
                assets={assets}
                assetsError={assetsError}
                onRetryAssets={() => void loadAssets()}
                onOrderPlaced={refreshAll}
              />
            </div>
          </div>
        </>
      )}

      <div className="mt-4 rounded-2xl border border-warning/30 bg-warning-soft px-4 py-3 text-center text-xs font-medium tracking-wide text-warning">
        Simulated portfolio — fake capital, no broker, no real orders. Paper trading only.
      </div>
    </MotionPage>
  );
}
