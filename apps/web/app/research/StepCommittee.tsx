"use client";

import { useCallback, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { useToast } from "@/app/components/ui/Toast";
import {
  BearCaseCard,
  BullCaseCard,
  CioCard,
  OverrideBanner,
  ProviderChips,
  ProviderSelect,
  QuantResearcherCard,
  RiskNarratorCard,
  TechnicalAnalystCard,
} from "@/app/committee/components";
import { evaluateCommittee } from "@/app/lib/api";
import type { CommitteeEvaluateResponse } from "@/app/lib/types";

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error.";
}

export interface StepCommitteeProps {
  backtestId: string;
  riskEvaluationId: string;
  result: CommitteeEvaluateResponse | null;
  onSuccess: (result: CommitteeEvaluateResponse) => void;
  onContinue: () => void;
}

/** Step 5: run the six-agent AI committee against the backtest + risk evaluation. */
export function StepCommittee({ backtestId, riskEvaluationId, result, onSuccess, onContinue }: StepCommitteeProps) {
  const { showToast } = useToast();
  const [provider, setProvider] = useState("mock");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(() => {
    setLoading(true);
    setError(null);
    evaluateCommittee({ backtest_id: backtestId, risk_evaluation_id: riskEvaluationId, provider })
      .then((res) => {
        onSuccess(res);
        showToast(`CIO decision: ${res.cio.decision}`, res.cio.decision === "PAPER_TRADE" ? "success" : "info");
      })
      .catch((e) => {
        setError(errMsg(e));
        showToast(errMsg(e), "error");
      })
      .finally(() => setLoading(false));
  }, [backtestId, riskEvaluationId, provider, onSuccess, showToast]);

  return (
    <div className="flex flex-col gap-5">
      {!result && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <ProviderSelect value={provider} onChange={setProvider} className="max-w-xs flex-1" />
          <Button variant="primary" loading={loading} onClick={run}>
            Run AI committee
          </Button>
        </div>
      )}

      {error && <ErrorState message={error} onRetry={run} />}

      {result && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <ProviderChips requested={result.requested_provider} selected={result.selected_provider} />
            <Button variant="ghost" loading={loading} onClick={run}>
              Re-run committee
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <TechnicalAnalystCard data={result.technical_analyst} />
            <QuantResearcherCard data={result.quant_researcher} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <BullCaseCard data={result.bull_case} />
            <BearCaseCard data={result.bear_case} />
          </div>

          <RiskNarratorCard data={result.risk_narrator} />

          <OverrideBanner overrideWarning={result.override_warning} cioRaw={result.cio_raw} />

          <CioCard
            cio={result.cio}
            requestedProvider={result.requested_provider}
            selectedProvider={result.selected_provider}
          />

          <div className="flex justify-end">
            <Button variant="primary" onClick={onContinue}>
              Continue to paper order
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
