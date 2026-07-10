"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { Input } from "@/app/components/ui/Input";
import { InlineSpinner } from "@/app/components/ui/InlineSpinner";
import { Label } from "@/app/components/ui/Label";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { SkeletonTable } from "@/app/components/ui/Skeleton";
import { useToast } from "@/app/components/ui/Toast";
import { ApiError, evaluateRisk, getRiskEvaluation, listRiskEvaluations } from "@/app/lib/api";
import { fmtDateTime, truncateId } from "@/app/lib/format";
import type { RiskEvaluateResponse, RiskEvaluationDetailResponse, RiskEvaluationListItem } from "@/app/lib/types";

import { RiskResultPanel } from "./RiskResultPanel";

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error.";
}

/** Section 1: recent risk evaluations table + click-to-inspect detail panel. */
function RecentEvaluations() {
  const [items, setItems] = useState<RiskEvaluationListItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RiskEvaluationDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    listRiskEvaluations(20)
      .then((res) =>
        setItems(
          [...res.evaluations].sort(
            (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
          ),
        ),
      )
      .catch((e) => setError(errMsg(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selectRow = useCallback((row: RiskEvaluationListItem) => {
    setSelectedId(row.risk_evaluation_id);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    getRiskEvaluation(row.risk_evaluation_id)
      .then((res) => setDetail(res))
      .catch((e) => setDetailError(errMsg(e)))
      .finally(() => setDetailLoading(false));
  }, []);

  const columns: DataTableColumn<RiskEvaluationListItem>[] = [
    {
      key: "risk_evaluation_id",
      header: "Eval ID",
      render: (row) => <span className="font-mono-ui text-xs">{truncateId(row.risk_evaluation_id)}</span>,
    },
    {
      key: "backtest_run_id",
      header: "Backtest ID",
      render: (row) => <span className="font-mono-ui text-xs text-text-muted">{truncateId(row.backtest_run_id)}</span>,
    },
    {
      key: "decision",
      header: "Decision",
      render: (row) => <DecisionBadge status={row.decision} size="sm" pulse={row.decision === "REJECTED"} />,
    },
    { key: "risk_score", header: "Score", numeric: true, render: (row) => row.risk_score },
    { key: "policy_version", header: "Policy", render: (row) => row.policy_version },
    { key: "created_at", header: "Created", render: (row) => fmtDateTime(row.created_at) },
  ];

  if (loading) return <SkeletonTable rows={6} cols={6} />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!items || items.length === 0) {
    return (
      <EmptyState
        title="No risk evaluations yet"
        hint="Run a backtest in the Research pipeline, then evaluate its risk -- or paste a backtest id into the form below."
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <DataTable
        columns={columns}
        data={items}
        getRowKey={(row) => row.risk_evaluation_id}
        onRowClick={selectRow}
      />
      {selectedId && (
        <GlassCard variant={selectedId === detail?.risk_evaluation_id ? "highlighted" : "default"}>
          {detailLoading ? (
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <InlineSpinner size="sm" /> Loading evaluation…
            </div>
          ) : detailError ? (
            <ErrorState message={detailError} onRetry={() => selectRow({ risk_evaluation_id: selectedId } as RiskEvaluationListItem)} />
          ) : detail ? (
            <RiskResultPanel
              result={detail}
              riskEvaluationId={detail.risk_evaluation_id}
              backtestId={detail.backtest_id}
              createdAt={fmtDateTime(detail.created_at)}
            />
          ) : null}
        </GlassCard>
      )}
    </div>
  );
}

/** Section 2: evaluate an arbitrary backtest id on demand. */
function EvaluateForm() {
  const { showToast } = useToast();
  const [backtestId, setBacktestId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RiskEvaluateResponse | null>(null);

  const run = useCallback(() => {
    const id = backtestId.trim();
    if (!id) return;
    setLoading(true);
    setError(null);
    evaluateRisk({ backtest_id: id })
      .then((res) => {
        setResult(res);
        showToast(`Risk decision: ${res.decision}`, res.decision === "APPROVED" ? "success" : "error");
      })
      .catch((e) => {
        setError(errMsg(e));
        showToast(errMsg(e), "error");
      })
      .finally(() => setLoading(false));
  }, [backtestId, showToast]);

  return (
    <div className="flex flex-col gap-5">
      <GlassCard>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Label htmlFor="backtest-id">Backtest ID</Label>
            <Input
              id="backtest-id"
              value={backtestId}
              onChange={(e) => setBacktestId(e.target.value)}
              placeholder="e.g. 3f1a9c2e-..."
              className="font-mono-ui"
            />
          </div>
          <Button variant="primary" loading={loading} disabled={!backtestId.trim()} onClick={run}>
            Evaluate risk
          </Button>
        </div>
      </GlassCard>

      {error && <ErrorState message={error} onRetry={run} />}
      {result && (
        <GlassCard variant="highlighted">
          <RiskResultPanel
            result={result}
            riskEvaluationId={result.risk_evaluation_id}
            backtestId={result.backtest_id}
          />
        </GlassCard>
      )}
    </div>
  );
}

export default function RiskPage() {
  return (
    <MotionPage>
      <PageHeader
        title="Risk"
        subtitle="Deterministic risk engine verdicts — the veto over every proposed paper trade."
      />

      <GlassCard className="mb-8" padding="md">
        <p className="text-sm text-text-muted">
          Every backtest is scored by a <span className="text-text">deterministic Python engine</span> against a
          versioned policy (currently reproducible per <span className="font-mono-ui text-text">policy_version</span>,
          see <span className="font-mono-ui text-text-faint">docs/risk-policy.md</span>). The engine has{" "}
          <span className="font-medium text-text">binding veto power</span>: a{" "}
          <DecisionBadge status="REJECTED" size="sm" className="mx-1" /> or{" "}
          <DecisionBadge status="NEEDS_REVIEW" size="sm" className="mx-1" /> decision blocks paper trading outright —
          no LLM agent, and no human clicking through the UI, can override it.
        </p>
      </GlassCard>

      <Section
        title="Evaluate a backtest"
        description="Paste a persisted backtest id to run (or re-run) the risk engine against it."
      >
        <EvaluateForm />
      </Section>

      <Section title="Recent evaluations" description="Latest 20 risk evaluations, newest first.">
        <RecentEvaluations />
      </Section>
    </MotionPage>
  );
}
