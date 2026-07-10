"use client";

/**
 * Dashboard: the command-center overview. Every number on this page comes
 * from the API -- there is no fake data anywhere; missing data renders an
 * honest empty state. Each panel loads, errors, and retries independently.
 *
 * Known backlog item (documented, not worked around with fake data): there is
 * no global "list committee verdicts" endpoint -- the latest committee
 * verdict is resolved via the latest backtest's GET /committee/backtests/{id}.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { MetricCard } from "@/app/components/ui/MetricCard";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { Skeleton, SkeletonCard } from "@/app/components/ui/Skeleton";
import { useToast } from "@/app/components/ui/Toast";
import { RiskScoreGauge } from "@/app/components/ui/charts/RiskScoreGauge";
import {
  ApiError,
  createPortfolio,
  getCommitteeForBacktest,
  getHealth,
  getHealthDb,
  getJournal,
  getPositions,
  getPortfolios,
  listBacktests,
  listRiskEvaluations,
  markToMarket,
} from "@/app/lib/api";
import { fmtDateTime, fmtInr, fmtPct, truncateId } from "@/app/lib/format";
import type {
  AgentDecisionRecord,
  BacktestListItem,
  JournalEntry,
  PaperPortfolio,
  RiskEvaluationListItem,
} from "@/app/lib/types";

// --- tiny local loader hook ---------------------------------------------------

interface Load<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

function useLoad<T>(fetcher: () => Promise<T>, enabled = true): Load<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, enabled]);

  return { data, loading, error, reload };
}

// --- portfolio metrics row -----------------------------------------------------

function PortfolioMetricsRow() {
  const { showToast } = useToast();
  const portfolios = useLoad(() => getPortfolios());
  const first: PaperPortfolio | null = portfolios.data?.portfolios[0] ?? null;
  const firstId = first?.id ?? null;
  const positions = useLoad(() => getPositions(firstId ?? undefined), firstId !== null);
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
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Mark-to-market failed.", "error");
    } finally {
      setMarking(false);
    }
  };

  if (portfolios.loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
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

  const openCount = positions.data
    ? positions.data.positions.filter((p) => p.status === "OPEN").length
    : null;

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Paper NAV" value={fmtInr(first.current_nav)} subtext={first.name} accent="accent" />
        <MetricCard
          label="Cash"
          value={fmtInr(first.current_cash)}
          subtext={`of ${fmtInr(first.starting_capital)} starting`}
        />
        <MetricCard
          label="Open positions"
          value={positions.loading ? "…" : openCount !== null ? String(openCount) : "—"}
          subtext={positions.error ? "failed to load" : undefined}
        />
        <MetricCard
          label="Risk mode"
          value={<DecisionBadge status={first.risk_mode} pulse={first.risk_mode === "RISK_OFF"} />}
          subtext={first.risk_mode === "RISK_OFF" ? "New BUY entries are blocked" : "Entries allowed within limits"}
        />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
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
    </>
  );
}

// --- latest backtest ------------------------------------------------------------

function LatestBacktestCard() {
  const backtests = useLoad(() => listBacktests(1));

  if (backtests.loading) return <SkeletonCard />;
  if (backtests.error) return <ErrorState message={backtests.error} onRetry={backtests.reload} />;

  const latest: BacktestListItem | undefined = backtests.data?.backtests[0];
  if (!latest) {
    return (
      <EmptyState
        title="No backtests yet"
        hint="Run a backtest from the Backtests page (or the research pipeline) to see it here."
        action={
          <Link href="/backtests">
            <Button variant="secondary">Go to Backtests</Button>
          </Link>
        }
      />
    );
  }

  return (
    <GlassCard>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-text">{latest.strategy_name ?? "Unnamed strategy"}</div>
          <div className="mt-0.5 font-mono-ui text-xs text-text-faint">
            {latest.symbol ?? "—"} · {truncateId(latest.backtest_id)} · {fmtDateTime(latest.created_at)}
          </div>
        </div>
        <DecisionBadge status={latest.status} size="sm" />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-2">
        <div>
          <div className="text-[11px] uppercase tracking-wide text-text-faint">Total return</div>
          <div
            className={`mt-0.5 text-sm font-semibold tabular-nums ${
              (latest.metrics.total_return ?? 0) >= 0 ? "text-positive" : "text-negative"
            }`}
          >
            {fmtPct(latest.metrics.total_return, { showSign: true })}
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide text-text-faint">Max drawdown</div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums text-text">
            {fmtPct(latest.metrics.max_drawdown)}
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide text-text-faint">Sharpe</div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums text-text">
            {latest.metrics.sharpe != null ? latest.metrics.sharpe.toFixed(2) : "—"}
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide text-text-faint">Trades</div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums text-text">
            {latest.metrics.num_trades ?? "—"}
          </div>
        </div>
      </div>
      <div className="mt-4 border-t border-white/[0.06] pt-3">
        <Link href="/backtests" className="text-xs font-medium text-accent hover:underline">
          View all backtests →
        </Link>
      </div>
    </GlassCard>
  );
}

// --- latest risk evaluation ------------------------------------------------------

function LatestRiskCard() {
  const evaluations = useLoad(() => listRiskEvaluations(1));

  if (evaluations.loading) return <SkeletonCard />;
  if (evaluations.error) return <ErrorState message={evaluations.error} onRetry={evaluations.reload} />;

  const latest: RiskEvaluationListItem | undefined = evaluations.data?.evaluations[0];
  if (!latest) {
    return (
      <EmptyState
        title="No risk evaluations yet"
        hint="Evaluate a persisted backtest with the risk engine to see the verdict here."
        action={
          <Link href="/risk">
            <Button variant="secondary">Go to Risk</Button>
          </Link>
        }
      />
    );
  }

  return (
    <GlassCard>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-text">Latest risk verdict</div>
          <div className="mt-0.5 font-mono-ui text-xs text-text-faint">
            {truncateId(latest.risk_evaluation_id)} · policy {latest.policy_version} · {fmtDateTime(latest.created_at)}
          </div>
        </div>
        <DecisionBadge status={latest.decision} size="sm" pulse={latest.decision === "REJECTED"} />
      </div>
      <div className="mt-4">
        <RiskScoreGauge score={latest.risk_score} size="sm" />
      </div>
      <div className="mt-4 border-t border-white/[0.06] pt-3">
        <Link href="/risk" className="text-xs font-medium text-accent hover:underline">
          View all risk evaluations →
        </Link>
      </div>
    </GlassCard>
  );
}

// --- latest committee verdict ------------------------------------------------------

function LatestCommitteeCard() {
  const backtests = useLoad(() => listBacktests(1));
  const latestBacktestId = backtests.data?.backtests[0]?.backtest_id ?? null;
  const committee = useLoad(() => getCommitteeForBacktest(latestBacktestId!), latestBacktestId !== null);

  if (backtests.loading || (latestBacktestId !== null && committee.loading)) {
    return <SkeletonCard />;
  }
  if (backtests.error) return <ErrorState message={backtests.error} onRetry={backtests.reload} />;
  if (latestBacktestId !== null && committee.error) {
    return <ErrorState message={committee.error} onRetry={committee.reload} />;
  }

  // The authoritative verdict is the newest "cio" row whose model ends in
  // ":final" (see committee_service's seven-row persistence scheme). The
  // decisions list is already newest-first.
  const finalRow: AgentDecisionRecord | undefined = committee.data?.decisions.find(
    (row) => row.agent_role === "cio" && (row.model ?? "").endsWith(":final"),
  );

  if (!latestBacktestId || !finalRow) {
    return (
      <EmptyState
        title="No committee verdict yet"
        hint={
          latestBacktestId
            ? "The AI committee has not evaluated the latest backtest yet."
            : "Run a backtest first, then convene the AI committee on it."
        }
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

  return (
    <GlassCard>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-text">Latest committee verdict</div>
          <div className="mt-0.5 font-mono-ui text-xs text-text-faint">
            backtest {truncateId(latestBacktestId)} · {finalRow.model ?? "—"} · {fmtDateTime(finalRow.created_at)}
          </div>
        </div>
        <DecisionBadge status={output.decision} size="sm" />
      </div>
      {output.summary && <p className="mt-3 text-sm leading-relaxed text-text-muted">{output.summary}</p>}
      {output.override_warning && (
        <p className="mt-2 rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-xs text-warning">
          {output.override_warning}
        </p>
      )}
      <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-3">
        <span className="text-xs text-text-faint">Risk approved: {output.approved_by_risk ? "yes" : "no"}</span>
        <Link href="/committee" className="text-xs font-medium text-accent hover:underline">
          View committee →
        </Link>
      </div>
    </GlassCard>
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

      <Section title="Paper portfolio">
        <PortfolioMetricsRow />
      </Section>

      <Section title="Latest activity">
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <LatestBacktestCard />
          <LatestRiskCard />
          <LatestCommitteeCard />
        </div>
      </Section>

      <Section title="Recent journal entries">
        <RecentJournalCard />
      </Section>

      <SystemStatusStrip />
    </MotionPage>
  );
}
