"use client";

import { useCallback, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { useToast } from "@/app/components/ui/Toast";
import { evaluateRisk } from "@/app/lib/api";
import type { RiskEvaluateResponse } from "@/app/lib/types";
import { RiskResultPanel } from "@/app/risk/RiskResultPanel";

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error.";
}

export interface StepRiskProps {
  backtestId: string;
  result: RiskEvaluateResponse | null;
  onSuccess: (result: RiskEvaluateResponse) => void;
  onContinue: () => void;
}

/** Step 4: run the deterministic risk engine against the persisted backtest. */
export function StepRisk({ backtestId, result, onSuccess, onContinue }: StepRiskProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(() => {
    setLoading(true);
    setError(null);
    evaluateRisk({ backtest_id: backtestId })
      .then((res) => {
        onSuccess(res);
        showToast(`Risk decision: ${res.decision}`, res.decision === "APPROVED" ? "success" : "error");
      })
      .catch((e) => {
        setError(errMsg(e));
        showToast(errMsg(e), "error");
      })
      .finally(() => setLoading(false));
  }, [backtestId, onSuccess, showToast]);

  return (
    <div className="flex flex-col gap-5">
      {!result && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-text-muted">
            Runs the deterministic risk engine against backtest{" "}
            <span className="font-mono-ui text-text">{backtestId}</span>.
          </p>
          <Button variant="primary" loading={loading} onClick={run}>
            Evaluate risk
          </Button>
        </div>
      )}

      {error && <ErrorState message={error} onRetry={run} />}

      {result && (
        <>
          <RiskResultPanel result={result} riskEvaluationId={result.risk_evaluation_id} backtestId={result.backtest_id} />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Button variant="ghost" loading={loading} onClick={run}>
              Re-run evaluation
            </Button>
            <Button variant="primary" disabled={!result.risk_evaluation_id} onClick={onContinue}>
              Continue to AI committee
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
