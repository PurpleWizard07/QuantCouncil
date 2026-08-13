"use client";

/**
 * Dashboard: the standing sheet. Every number on this page comes from the
 * API -- there is no fake data anywhere; missing data renders an honest
 * empty state. Each section loads, errors, and retries independently.
 *
 * The backtest -> risk -> committee strip below is chained by id (fetches
 * the latest backtest, then that backtest's risk evaluation and committee
 * verdict specifically) rather than three independent "latest of X" queries
 * -- so what's on screen is one proposal followed through three stages, not
 * three unrelated latests that happen to be adjacent.
 */

import Link from "next/link";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { Button } from "@/app/components/ui/Button";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { LedgerRow } from "@/app/components/ui/LedgerRow";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { Skeleton } from "@/app/components/ui/Skeleton";
import { useToast } from "@/app/components/ui/Toast";
import { NavBackdropChart } from "@/app/components/ui/charts/NavBackdropChart";
import { RiskScoreGauge } from "@/app/components/ui/charts/RiskScoreGauge";
import {
  ApiError,
  createPortfolio,
  getCommitteeForBacktest,
  getHealth,
  getHealthDb,
  getJournal,
  getLatestRiskForBacktest,
  getNavHistory,
  getPositions,
  getPortfolios,
  listBacktests,
  markToMarket,
} from "@/app/lib/api";
import { fmtDateTime, fmtInr, fmtPct, truncateId } from "@/app/lib/format";
import type {
  AgentDecisionRecord,
  BacktestListItem,
  JournalEntry,
  PaperPortfolio,
  RiskEvaluationDetailResponse,
} from "@/app/lib/types";

// --- tiny local loader hook ---------------------------------------------------

interface Load<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  errorStatus: number | null;
  reload: () => void;
}

function useLoad<T>(fetcher: () => Promise<T>, enabled = true): Load<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setErrorStatus(null);
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setErrorStatus(err instanceof ApiError ? err.status : null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, enabled]);

  return { data, loading, error, errorStatus, reload };
}

// --- hero standing sheet: NAV + backdrop curve + ledger rail -------------------

function NavHeroBand() {
  const { showToast } = useToast();
  const portfolios = useLoad(() => getPortfolios());
  const first: PaperPortfolio | null = portfolios.data?.portfolios[0] ?? null;
  const firstId = first?.id ?? null;
  const positions = useLoad(() => getPositions(firstId ?? undefined), firstId !== null);
  const navHistory = useLoad(() => getNavHistory(firstId!, 60), firstId !== null);
  const [creating, setCreating] = useState(false);
  const [marking, setMarking] = useState(false);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const created = await createPortfolio();
      showToast(`Portfolio "${created.name}" created with ${fmtInr(created.starting_capital)}.`, "success");
      portfolios.reload();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Failed to create portfolio.", "error");
    } finally {
      setCreating(false);
    }
  };

  const handleMarkToMarket = async () => {
    if (!firstId) return;
    setMarking(true);
    try {
      const result = await markToMarket(firstId);
      showToast(
        `Marked to market: NAV ${fmtInr(result.nav)}, drawdown ${fmtPct(result.drawdown)}${
          result.risk_off ? " — RISK-OFF ACTIVE" : ""
        }`,
        result.risk_off ? "error" : "success",
      );
      portfolios.reload();
      positions.reload();
      navHistory.reload();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Mark-to-market failed.", "error");
    } finally {
      setMarking(false);
    }
  };

  if (portfolios.loading) {
    return (
      <div className="surface rounded-2xl p-8">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="mt-4 h-16 w-72" />
      </div>
    );
  }

  if (portfolios.error) {
    return <ErrorState message={portfolios.error} onRetry={portfolios.reload} />;
  }

  if (!first) {
    return (
      <EmptyState
        title="No paper portfolio yet"
        hint="Create the default simulated portfolio (₹10,00,000 virtual capital) to start tracking NAV, cash, and positions."
        action={
          <Button variant="primary" loading={creating} onClick={handleCreate}>
            Create default portfolio
          </Button>
        }
      />
    );
  }

  const openPositions = positions.data ? positions.data.positions.filter((p) => p.status === "OPEN") : [];
  const unrealizedPnl = openPositions.reduce((sum, p) => sum + (p.unrealized_pnl ?? 0), 0);
  const navDelta = first.current_nav - first.starting_capital;
  const navDeltaPct = first.starting_capital ? navDelta / first.starting_capital : 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="surface overflow-hidden rounded-2xl">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px]">
          {/* NAV hero */}
          <div className="relative overflow-hidden p-6 sm:p-8">
            {navHistory.data && <NavBackdropChart snapshots={navHistory.data.snapshots} />}
            <div className="relative z-10">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-warm">Paper NAV</div>
              <div className="mt-2 font-serif text-5xl font-medium tabular-nums text-text sm:text-6xl lg:text-7xl">
                {fmtInr(first.current_nav, { decimals: 0 })}
              </div>
              <div className="metal-edge mt-4 flex flex-wrap items-baseline gap-x-2 gap-y-1 pt-3">
                <span
                  className={`text-sm font-semibold tabular-nums ${navDelta >= 0 ? "text-positive" : "text-negative"}`}
                >
                  {navDelta >= 0 ? "+" : ""}
                  {fmtInr(navDelta, { decimals: 0 })} ({fmtPct(navDeltaPct, { showSign: true })})
                </span>
                <span className="text-xs text-text-faint">
                  since {fmtInr(first.starting_capital, { decimals: 0 })} starting · {first.name}
                </span>
              </div>
            </div>
          </div>

          {/* Ledger rail */}
          <div className="border-t border-white/[0.06] px-6 py-5 lg:border-l lg:border-t-0 lg:px-7">
            <div className="flex flex-col divide-y divide-white/[0.05]">
              <LedgerRow label="Cash" value={fmtInr(first.current_cash, { decimals: 0 })} />
              <LedgerRow
                label="Open positions"
                value={positions.loading ? "…" : String(openPositions.length)}
              />
              <LedgerRow
                label="Unrealized P&L"
                value={positions.loading ? "…" : fmtInr(unrealizedPnl, { decimals: 0 })}
                tone={unrealizedPnl > 0 ? "positive" : unrealizedPnl < 0 ? "negative" : undefined}
              />
              <div className="flex items-center justify-between py-2.5">
                <span className="text-[11px] font-medium uppercase tracking-wide text-text-faint">Risk mode</span>
                <DecisionBadge status={first.risk_mode} size="sm" pulse={first.risk_mode === "RISK_OFF"} />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href="/research">
          <Button variant="primary">Run research pipeline</Button>
        </Link>
        <Link href="/paper">
          <Button variant="secondary">View paper portfolio</Button>
        </Link>
        <Link href="/journal">
          <Button variant="secondary">View journal</Button>
        </Link>
        <Button
          variant="secondary"
          loading={marking}
          onClick={handleMarkToMarket}
          title="Revalue open positions at the latest close"
        >
          Mark to market
        </Button>
      </div>
    </div>
  );
}

// --- connected case strip: backtest -> risk -> committee, chained by id -------

function StationLabel({ children }: { children: ReactNode }) {
  return <div className="text-[11px] font-semibold uppercase tracking-wide text-text-faint">{children}</div>;
}

function StationSkeleton({ label }: { label: string }) {
  return (
    <div className="p-5">
      <StationLabel>{label}</StationLabel>
      <Skeleton className="mt-3 h-8 w-32" />
      <Skeleton className="mt-2 h-4 w-full" />
    </div>
  );
}

function StationError({ label, message, onRetry }: { label: string; message: string; onRetry: () => void }) {
  return (
    <div className="p-5">
      <StationLabel>{label}</StationLabel>
      <div className="mt-3">
        <ErrorState message={message} onRetry={onRetry} />
      </div>
    </div>
  );
}

function StationEmpty({
  label,
  title,
  hint,
  action,
}: {
  label: string;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="p-5">
      <StationLabel>{label}</StationLabel>
      <div className="mt-3">
        <EmptyState title={title} hint={hint} action={action} />
      </div>
    </div>
  );
}

function CaseConnector() {
  return (
    <div className="flex shrink-0 items-center justify-center py-1 text-text-faint lg:px-1 lg:py-0">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="rotate-90 lg:rotate-0" aria-hidden="true">
        <path
          d="M5 12h14M13 6l6 6-6 6"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function BacktestStation({ onResolved }: { onResolved: (id: string | null) => void }) {
  const backtests = useLoad(() => listBacktests(1));
  const latest: BacktestListItem | undefined = backtests.data?.backtests[0];

  useEffect(() => {
    if (!backtests.loading) onResolved(latest?.backtest_id ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backtests.loading, latest?.backtest_id]);

  if (backtests.loading) return <StationSkeleton label="Backtest" />;
  if (backtests.error) return <StationError label="Backtest" message={backtests.error} onRetry={backtests.reload} />;
  if (!latest) {
    return (
      <StationEmpty
        label="Backtest"
        title="No backtests yet"
        hint="Run one from Backtests or the research pipeline."
        action={
          <Link href="/backtests">
            <Button variant="secondary">Go to Backtests</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="p-5">
      <StationLabel>Backtest</StationLabel>
      <div className="mt-2 text-sm font-semibold text-text">{latest.strategy_name ?? "Unnamed strategy"}</div>
      <div className="mt-0.5 font-mono-ui text-xs text-text-faint">
        {latest.symbol ?? "—"} · {truncateId(latest.backtest_id)}
      </div>
      <div className="mt-3">
        <DecisionBadge status={latest.status} size="sm" />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-text-faint">Return</div>
          <div
            className={`mt-0.5 text-sm font-semibold tabular-nums ${
              (latest.metrics.total_return ?? 0) >= 0 ? "text-positive" : "text-negative"
            }`}
          >
            {fmtPct(latest.metrics.total_return, { showSign: true })}
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-text-faint">Sharpe</div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums text-text">
            {latest.metrics.sharpe != null ? latest.metrics.sharpe.toFixed(2) : "—"}
          </div>
        </div>
      </div>
      <Link href="/backtests" className="mt-4 inline-block text-xs font-medium text-accent hover:underline">
        View all backtests →
      </Link>
    </div>
  );
}

function RiskStation({ backtestId }: { backtestId: string | null | undefined }) {
  const risk = useLoad<RiskEvaluationDetailResponse>(
    () => getLatestRiskForBacktest(backtestId!),
    typeof backtestId === "string",
  );

  if (backtestId === undefined) return <StationSkeleton label="Risk verdict" />;
  if (backtestId === null) {
    return <StationEmpty label="Risk verdict" title="No backtest to evaluate" hint="Run a backtest first." />;
  }
  if (risk.loading) return <StationSkeleton label="Risk verdict" />;
  if (risk.error && risk.errorStatus !== 404) {
    return <StationError label="Risk verdict" message={risk.error} onRetry={risk.reload} />;
  }
  if (!risk.data) {
    return (
      <StationEmpty
        label="Risk verdict"
        title="Not evaluated yet"
        hint="This backtest hasn't been through the risk engine."
        action={
          <Link href="/risk">
            <Button variant="secondary">Go to Risk</Button>
          </Link>
        }
      />
    );
  }

  const { data } = risk;
  const decisionClass =
    data.decision === "APPROVED" ? "text-positive" : data.decision === "REJECTED" ? "text-negative" : "text-warning";

  return (
    <div className="p-5">
      <StationLabel>Risk verdict</StationLabel>
      <div className={`mt-2 font-serif text-3xl font-medium ${decisionClass}`}>{data.decision.replace(/_/g, " ")}</div>
      <div className="mt-3">
        <RiskScoreGauge score={data.risk_score} size="sm" />
      </div>
      <div className="mt-3 font-mono-ui text-xs text-text-faint">
        policy {data.policy_version} · {fmtDateTime(data.created_at)}
      </div>
      <Link href="/risk" className="mt-4 inline-block text-xs font-medium text-accent hover:underline">
        View all risk evaluations →
      </Link>
    </div>
  );
}

function CommitteeStation({ backtestId }: { backtestId: string | null | undefined }) {
  const committee = useLoad(
    () => getCommitteeForBacktest(backtestId!),
    typeof backtestId === "string",
  );

  if (backtestId === undefined) return <StationSkeleton label="Committee verdict" />;
  if (backtestId === null) {
    return <StationEmpty label="Committee verdict" title="No backtest yet" hint="Run a backtest first." />;
  }
  if (committee.loading) return <StationSkeleton label="Committee verdict" />;
  if (committee.error) {
    return <StationError label="Committee verdict" message={committee.error} onRetry={committee.reload} />;
  }

  const finalRow: AgentDecisionRecord | undefined = committee.data?.decisions.find(
    (row) => row.agent_role === "cio" && (row.model ?? "").endsWith(":final"),
  );

  if (!finalRow) {
    return (
      <StationEmpty
        label="Committee verdict"
        title="No verdict yet"
        hint="Convene the AI committee on this backtest."
        action={
          <Link href="/committee">
            <Button variant="secondary">Go to AI Committee</Button>
          </Link>
        }
      />
    );
  }

  const output = finalRow.output as {
    decision?: string;
    summary?: string;
    approved_by_risk?: boolean;
    override_warning?: string | null;
  };
  const decisionClass =
    output.decision === "PAPER_TRADE"
      ? "text-positive"
      : output.decision === "NO_TRADE"
        ? "text-negative"
        : "text-watchlist";

  return (
    <div className="p-5">
      <StationLabel>Committee verdict</StationLabel>
      <div className={`mt-2 font-serif text-3xl font-medium ${decisionClass}`}>
        {(output.decision ?? "—").replace(/_/g, " ")}
      </div>
      {output.summary && <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-text-muted">{output.summary}</p>}
      {output.override_warning && (
        <p className="mt-2 rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-xs text-warning">
          {output.override_warning}
        </p>
      )}
      <Link href="/committee" className="mt-4 inline-block text-xs font-medium text-accent hover:underline">
        View committee →
      </Link>
    </div>
  );
}

function CaseStrip() {
  const [backtestId, setBacktestId] = useState<string | null | undefined>(undefined);

  return (
    <div className="surface overflow-hidden rounded-2xl">
      <div className="flex flex-col lg:flex-row">
        <div className="flex-1 border-b border-white/[0.06] lg:border-b-0 lg:border-r">
          <BacktestStation onResolved={setBacktestId} />
        </div>
        <CaseConnector />
        <div className="flex-1 border-b border-white/[0.06] lg:border-b-0 lg:border-r">
          <RiskStation backtestId={backtestId} />
        </div>
        <CaseConnector />
        <div className="flex-1">
          <CommitteeStation backtestId={backtestId} />
        </div>
      </div>
    </div>
  );
}

// --- recent journal entries -----------------------------------------------------

function RecentJournalCard() {
  const journal = useLoad(() => getJournal());

  if (journal.loading) {
    return (
      <GlassCard>
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 flex-1" />
            </div>
          ))}
        </div>
      </GlassCard>
    );
  }
  if (journal.error) return <ErrorState message={journal.error} onRetry={journal.reload} />;

  const entries: JournalEntry[] = journal.data?.journal.slice(0, 5) ?? [];
  if (entries.length === 0) {
    return (
      <EmptyState
        title="No journal entries yet"
        hint="Every fill, decision, and risk event is journaled automatically. Place a paper trade to start the audit trail."
        action={
          <Link href="/journal">
            <Button variant="secondary">Go to Journal</Button>
          </Link>
        }
      />
    );
  }

  return (
    <GlassCard padding="none">
      <ul className="divide-y divide-white/[0.05]">
        {entries.map((entry) => (
          <li key={entry.id} className="flex items-start gap-3 px-5 py-3.5">
            <DecisionBadge status={entry.entry_type} size="sm" className="mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-text">{entry.title}</div>
              <div className="mt-0.5 line-clamp-2 text-xs text-text-muted">{entry.body}</div>
            </div>
            <span className="shrink-0 text-[11px] tabular-nums text-text-faint">
              {fmtDateTime(entry.created_at)}
            </span>
          </li>
        ))}
      </ul>
      <div className="border-t border-white/[0.06] px-5 py-3">
        <Link href="/journal" className="text-xs font-medium text-accent hover:underline">
          View full journal →
        </Link>
      </div>
    </GlassCard>
  );
}

// --- system status strip ----------------------------------------------------------

function StatusDot({ ok, label }: { ok: boolean | null; label: string }) {
  const dotClass = ok === null ? "bg-text-faint" : ok ? "bg-positive animate-pulse-glow text-positive" : "bg-negative";
  const textClass = ok === null ? "text-text-faint" : ok ? "text-positive" : "text-negative";
  return (
    <span className="flex items-center gap-2 text-xs">
      <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} aria-hidden="true" />
      <span className={textClass}>{label}</span>
    </span>
  );
}

function SystemStatusStrip() {
  const health = useLoad(async () => {
    const api = await getHealth().then(
      () => true,
      () => false,
    );
    const db = await getHealthDb().then(
      (res) => res.database === "ok",
      () => false,
    );
    return { api, db };
  });

  return (
    <GlassCard padding="sm">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-text-faint">System</span>
        <StatusDot
          ok={health.data?.api ?? null}
          label={health.data ? (health.data.api ? "API online" : "API offline") : "API…"}
        />
        <StatusDot
          ok={health.data?.db ?? null}
          label={health.data ? (health.data.db ? "Database ok" : "Database unreachable") : "Database…"}
        />
        <span className="text-xs text-text-muted">
          Committee provider default: <code className="font-mono-ui text-accent">mock</code>
          <span className="text-text-faint"> (server-side, QUANTCOUNCIL_AGENT_PROVIDER)</span>
        </span>
      </div>
    </GlassCard>
  );
}

// --- page -------------------------------------------------------------------------

export default function DashboardPage() {
  return (
    <MotionPage>
      <PageHeader
        title="Dashboard"
        subtitle="AI can propose. Math can approve. Risk can veto. Everything here is simulated — real engine data only."
      />

      <div className="mb-8">
        <NavHeroBand />
      </div>

      <div className="mb-8">
        <CaseStrip />
      </div>

      <Section title="Recent journal entries">
        <RecentJournalCard />
      </Section>

      <SystemStatusStrip />
    </MotionPage>
  );
}
