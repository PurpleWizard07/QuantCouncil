"use client";

import { useCallback, useMemo, useState } from "react";

import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { Button } from "@/app/components/ui/Button";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { StepIndicator, type Step } from "@/app/components/ui/StepIndicator";
import { fmtInr, fmtInt, fmtNum, fmtPct, truncateId } from "@/app/lib/format";
import type {
  AssetRecord,
  BacktestRunResponse,
  CommitteeEvaluateResponse,
  CreateOrderResponse,
  RiskEvaluateResponse,
  StrategyRecord,
} from "@/app/lib/types";

import { StepBacktest } from "./StepBacktest";
import { StepCommittee } from "./StepCommittee";
import { StepOrder } from "./StepOrder";
import { StepRisk } from "./StepRisk";
import { StepShell, type StepPhase } from "./StepShell";
import { StepStrategy } from "./StepStrategy";
import { StepSymbol } from "./StepSymbol";

interface PipelineState {
  symbol: AssetRecord | null;
  strategy: StrategyRecord | null;
  backtest: BacktestRunResponse | null;
  risk: RiskEvaluateResponse | null;
  committee: CommitteeEvaluateResponse | null;
  order: CreateOrderResponse | null;
}

const INITIAL_STATE: PipelineState = {
  symbol: null,
  strategy: null,
  backtest: null,
  risk: null,
  committee: null,
  order: null,
};

const STEP_TITLES = [
  "Select symbol",
  "Select strategy",
  "Run backtest",
  "Evaluate risk",
  "Run AI committee",
  "Create paper order",
];

function isDone(n: number, s: PipelineState): boolean {
  switch (n) {
    case 1:
      return !!s.symbol;
    case 2:
      return !!s.strategy;
    case 3:
      return !!s.backtest?.persisted && !!s.backtest.backtest_id;
    case 4:
      return !!s.risk?.risk_evaluation_id;
    case 5:
      return !!s.committee;
    case 6:
      return !!s.order;
    default:
      return false;
  }
}

export default function ResearchPage() {
  const [state, setState] = useState<PipelineState>(INITIAL_STATE);
  const [expandedStep, setExpandedStep] = useState(1);

  const phaseOf = useCallback(
    (n: number): StepPhase => {
      if (n === expandedStep) return "active";
      if (isDone(n, state)) return "done";
      return "locked";
    },
    [expandedStep, state],
  );

  const reset = useCallback(() => {
    setState(INITIAL_STATE);
    setExpandedStep(1);
  }, []);

  const selectSymbol = useCallback((asset: AssetRecord) => {
    setState((prev) => {
      if (prev.symbol?.symbol === asset.symbol) return { ...prev, symbol: asset };
      return { ...prev, symbol: asset, backtest: null, risk: null, committee: null, order: null };
    });
  }, []);

  const selectStrategy = useCallback((strategy: StrategyRecord) => {
    setState((prev) => {
      const prevKey = prev.strategy?.id ?? prev.strategy?.name;
      const nextKey = strategy.id ?? strategy.name;
      if (prevKey === nextKey) return { ...prev, strategy };
      return { ...prev, strategy, backtest: null, risk: null, committee: null, order: null };
    });
  }, []);

  const onBacktestSuccess = useCallback((result: BacktestRunResponse) => {
    setState((prev) => ({ ...prev, backtest: result, risk: null, committee: null, order: null }));
  }, []);

  const onRiskSuccess = useCallback((result: RiskEvaluateResponse) => {
    setState((prev) => ({ ...prev, risk: result, committee: null, order: null }));
  }, []);

  const onCommitteeSuccess = useCallback((result: CommitteeEvaluateResponse) => {
    setState((prev) => ({ ...prev, committee: result, order: null }));
  }, []);

  const onOrderSuccess = useCallback((result: CreateOrderResponse) => {
    setState((prev) => ({ ...prev, order: result }));
  }, []);

  const stepIndicatorSteps: Step[] = useMemo(
    () =>
      STEP_TITLES.map((label, i) => ({
        label,
        state: phaseOf(i + 1),
      })),
    [phaseOf],
  );

  return (
    <MotionPage>
      <PageHeader
        title="Research Pipeline"
        subtitle="Guided flow: symbol → strategy → backtest → risk gate → AI committee → paper trade."
        actions={
          <Button variant="ghost" onClick={reset}>
            Start over
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[200px_1fr]">
        <div className="lg:sticky lg:top-24 lg:self-start">
          <StepIndicator steps={stepIndicatorSteps} orientation="vertical" />
        </div>

        <div className="relative flex flex-col gap-4">
          {/* The spine: continuous behind the gaps between cards, hidden
              wherever an opaque .surface card sits on top of it -- so it
              reads as connecting the nodes without needing pixel-perfect
              alignment with each card's own (padding-dependent) circle. */}
          <div className="pointer-events-none absolute bottom-0 left-[34px] top-0 z-0 w-px bg-border" aria-hidden="true" />

          <StepShell
            index={1}
            title="Select symbol"
            phase={phaseOf(1)}
            onExpand={() => setExpandedStep(1)}
            strata={
              state.symbol && (
                <div className="text-xs text-text-muted">
                  <span className="font-semibold text-text">{state.symbol.symbol}</span> — {state.symbol.name}
                  {state.symbol.sector ? ` · ${state.symbol.sector}` : ""}
                </div>
              )
            }
          >
            <StepSymbol selected={state.symbol} onSelect={selectSymbol} onContinue={() => setExpandedStep(2)} />
          </StepShell>

          <StepShell
            index={2}
            title="Select strategy"
            phase={phaseOf(2)}
            lockedHint="Select a symbol first."
            onExpand={() => setExpandedStep(2)}
            strata={
              state.strategy && (
                <div className="text-xs text-text-muted">
                  <span className="font-semibold text-text">{state.strategy.name}</span>
                  {state.strategy.description ? ` — ${state.strategy.description}` : ""}
                </div>
              )
            }
          >
            <StepStrategy selected={state.strategy} onSelect={selectStrategy} onContinue={() => setExpandedStep(3)} />
          </StepShell>

          <StepShell
            index={3}
            title="Run backtest"
            phase={phaseOf(3)}
            lockedHint="Select a symbol and strategy first."
            onExpand={() => setExpandedStep(3)}
            strata={
              state.backtest && (
                <div className="flex flex-wrap gap-x-6 gap-y-2">
                  <div>
                    <div className="text-[10px] uppercase tracking-wide text-text-faint">Total return</div>
                    <div
                      className={`font-mono-ui text-sm font-semibold tabular-nums ${
                        (state.backtest.metrics.total_return ?? 0) >= 0 ? "text-positive" : "text-negative"
                      }`}
                    >
                      {fmtPct(state.backtest.metrics.total_return, { showSign: true })}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wide text-text-faint">Sharpe</div>
                    <div className="font-mono-ui text-sm font-semibold tabular-nums text-text">
                      {fmtNum(state.backtest.metrics.sharpe)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wide text-text-faint">Max drawdown</div>
                    <div className="font-mono-ui text-sm font-semibold tabular-nums text-text">
                      {fmtPct(state.backtest.metrics.max_drawdown)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wide text-text-faint">Trades</div>
                    <div className="font-mono-ui text-sm font-semibold tabular-nums text-text">
                      {fmtInt(state.backtest.metrics.num_trades)}
                    </div>
                  </div>
                  {state.backtest.backtest_id && (
                    <div className="self-center font-mono-ui text-xs text-text-faint">
                      {truncateId(state.backtest.backtest_id)}
                    </div>
                  )}
                </div>
              )
            }
          >
            {state.symbol && state.strategy && (
              <StepBacktest
                symbol={state.symbol}
                strategy={state.strategy}
                result={state.backtest}
                onSuccess={onBacktestSuccess}
                onContinue={() => setExpandedStep(4)}
              />
            )}
          </StepShell>

          <StepShell
            index={4}
            title="Evaluate risk"
            phase={phaseOf(4)}
            lockedHint="Run a backtest first."
            onExpand={() => setExpandedStep(4)}
            carryForward={
              state.backtest && (
                <p className="text-xs text-text-muted">
                  Building on backtest{" "}
                  <span className="font-mono-ui text-text">{truncateId(state.backtest.backtest_id)}</span>: total
                  return{" "}
                  <span className="font-semibold text-text">{fmtPct(state.backtest.metrics.total_return)}</span>,
                  Sharpe <span className="font-semibold text-text">{fmtNum(state.backtest.metrics.sharpe)}</span>.
                </p>
              )
            }
            strata={
              state.risk && (
                <div className="flex flex-wrap items-center gap-4">
                  <DecisionBadge status={state.risk.decision} size="sm" />
                  <span className="font-serif text-2xl font-medium tabular-nums text-text">
                    {state.risk.risk_score}
                    <span className="text-sm text-text-faint">/100</span>
                  </span>
                  <span className="text-xs text-text-faint">
                    {state.risk.failed_rules.length} failed rule{state.risk.failed_rules.length === 1 ? "" : "s"} ·{" "}
                    {state.risk.warnings.length} warning{state.risk.warnings.length === 1 ? "" : "s"}
                  </span>
                </div>
              )
            }
          >
            {state.backtest?.backtest_id && (
              <StepRisk
                backtestId={state.backtest.backtest_id}
                result={state.risk}
                onSuccess={onRiskSuccess}
                onContinue={() => setExpandedStep(5)}
              />
            )}
          </StepShell>

          <StepShell
            index={5}
            title="Run AI committee"
            phase={phaseOf(5)}
            lockedHint="Evaluate risk first."
            onExpand={() => setExpandedStep(5)}
            carryForward={
              state.risk && (
                <p className="text-xs text-text-muted">
                  Building on risk verdict{" "}
                  <span className="font-serif text-sm font-medium text-text">
                    {state.risk.decision.replace(/_/g, " ")}
                  </span>{" "}
                  · score <span className="font-semibold text-text">{state.risk.risk_score}/100</span>.
                </p>
              )
            }
            strata={
              state.committee && (
                <div className="flex flex-wrap items-center gap-4">
                  <span className="font-serif text-2xl font-medium text-text">
                    {state.committee.cio.decision.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono-ui text-xs text-text-faint">via {state.committee.selected_provider}</span>
                  <span className="max-w-md truncate text-xs text-text-faint">{state.committee.cio.reason}</span>
                </div>
              )
            }
          >
            {state.backtest?.backtest_id && state.risk?.risk_evaluation_id && (
              <StepCommittee
                backtestId={state.backtest.backtest_id}
                riskEvaluationId={state.risk.risk_evaluation_id}
                result={state.committee}
                onSuccess={onCommitteeSuccess}
                onContinue={() => setExpandedStep(6)}
              />
            )}
          </StepShell>

          <StepShell
            index={6}
            title="Create paper order"
            phase={phaseOf(6)}
            lockedHint="Run the AI committee first."
            onExpand={() => setExpandedStep(6)}
            carryForward={
              state.committee && (
                <p className="text-xs text-text-muted">
                  Building on committee verdict{" "}
                  <span className="font-serif text-sm font-medium text-text">
                    {state.committee.cio.decision.replace(/_/g, " ")}
                  </span>
                  .
                </p>
              )
            }
            strata={
              state.order && (
                <div className="text-xs text-text-muted">
                  Filled <span className="font-semibold text-text">{fmtInr(state.order.fill.fill_price)}</span> ×{" "}
                  {state.order.order.quantity}
                </div>
              )
            }
          >
            {state.symbol && state.backtest?.backtest_id && state.risk && (
              <StepOrder
                symbol={state.symbol}
                backtestId={state.backtest.backtest_id}
                riskEvaluationId={state.risk.risk_evaluation_id ?? ""}
                riskApproved={state.risk.approved}
                riskDecision={state.risk.decision}
                riskFailedRules={state.risk.failed_rules}
                riskWarnings={state.risk.warnings}
                riskReasons={state.risk.reasons}
                result={state.order}
                onSuccess={onOrderSuccess}
              />
            )}
          </StepShell>
        </div>
      </div>
    </MotionPage>
  );
}
