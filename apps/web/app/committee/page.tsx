"use client";

import { useCallback, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { Input } from "@/app/components/ui/Input";
import { JsonViewer } from "@/app/components/ui/JsonViewer";
import { Label } from "@/app/components/ui/Label";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { SkeletonTable } from "@/app/components/ui/Skeleton";
import { useToast } from "@/app/components/ui/Toast";
import { evaluateCommittee, getCommitteeForBacktest } from "@/app/lib/api";
import { fmtDateTime, truncateId } from "@/app/lib/format";
import type { AgentDecisionRecord, CommitteeEvaluateResponse } from "@/app/lib/types";

import { ProviderChips, ProviderSelect } from "./components";
import { ChamberLayout } from "./ChamberLayout";

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error.";
}

function RunCommittee() {
  const { showToast } = useToast();
  const [backtestId, setBacktestId] = useState("");
  const [riskEvaluationId, setRiskEvaluationId] = useState("");
  const [provider, setProvider] = useState("mock");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CommitteeEvaluateResponse | null>(null);

  const run = useCallback(() => {
    const bId = backtestId.trim();
    const rId = riskEvaluationId.trim();
    if (!bId || !rId) return;
    setLoading(true);
    setError(null);
    evaluateCommittee({ backtest_id: bId, risk_evaluation_id: rId, provider })
      .then((res) => {
        setResult(res);
        showToast(`CIO decision: ${res.cio.decision}`, res.cio.decision === "PAPER_TRADE" ? "success" : "info");
      })
      .catch((e) => {
        setError(errMsg(e));
        showToast(errMsg(e), "error");
      })
      .finally(() => setLoading(false));
  }, [backtestId, riskEvaluationId, provider, showToast]);

  return (
    <div className="flex flex-col gap-5">
      <GlassCard>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="cm-backtest-id">Backtest ID</Label>
            <Input
              id="cm-backtest-id"
              value={backtestId}
              onChange={(e) => setBacktestId(e.target.value)}
              placeholder="backtest_id"
              className="font-mono-ui"
            />
          </div>
          <div>
            <Label htmlFor="cm-risk-id">Risk evaluation ID</Label>
            <Input
              id="cm-risk-id"
              value={riskEvaluationId}
              onChange={(e) => setRiskEvaluationId(e.target.value)}
              placeholder="risk_evaluation_id"
              className="font-mono-ui"
            />
          </div>
          <div>
            <Label htmlFor="cm-provider">Provider</Label>
            <ProviderSelect value={provider} onChange={setProvider} />
          </div>
          <div className="flex items-end">
            <Button
              variant="primary"
              loading={loading}
              disabled={!backtestId.trim() || !riskEvaluationId.trim()}
              onClick={run}
              className="w-full"
            >
              Run committee
            </Button>
          </div>
        </div>
      </GlassCard>

      {error && <ErrorState message={error} onRetry={run} />}
      {(loading || result) && (
        <>
          {result && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <ProviderChips requested={result.requested_provider} selected={result.selected_provider} />
            </div>
          )}
          <ChamberLayout result={result} loading={loading} />
        </>
      )}
    </div>
  );
}

function DecisionsTable({ decisions }: { decisions: AgentDecisionRecord[] }) {
  const [selected, setSelected] = useState<AgentDecisionRecord | null>(null);
  const sorted = [...decisions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  const columns: DataTableColumn<AgentDecisionRecord>[] = [
    { key: "id", header: "ID", render: (row) => <span className="font-mono-ui text-xs">{truncateId(row.id)}</span> },
    {
      key: "agent_role",
      header: "Agent role",
      render: (row) => (
        <span className="rounded-full border border-white/10 bg-white/[0.05] px-2 py-0.5 text-[11px] uppercase tracking-wide text-text-muted">
          {row.agent_role}
        </span>
      ),
    },
    {
      key: "model",
      header: "Model",
      render: (row) => {
        const isFinal = (row.model ?? "").endsWith(":final");
        return (
          <span
            className={`font-mono-ui text-xs ${isFinal ? "font-semibold text-accent" : "text-text-muted"}`}
          >
            {row.model ?? "—"}
          </span>
        );
      },
    },
    { key: "created_at", header: "Created", render: (row) => fmtDateTime(row.created_at) },
  ];

  return (
    <div className="flex flex-col gap-4">
      <DataTable
        columns={columns}
        data={sorted}
        getRowKey={(row) => row.id}
        onRowClick={setSelected}
      />
      {selected && (
        <GlassCard variant={(selected.model ?? "").endsWith(":final") ? "highlighted" : "default"}>
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-text-muted">
            <span>{selected.agent_role}</span>
            <span className="text-text-faint">·</span>
            <span className="font-mono-ui">{selected.model ?? "—"}</span>
            <span className="text-text-faint">·</span>
            <span>{fmtDateTime(selected.created_at)}</span>
          </div>
          <JsonViewer data={selected.output} label="agent output" />
        </GlassCard>
      )}
    </div>
  );
}

function History() {
  const [backtestId, setBacktestId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<AgentDecisionRecord[] | null>(null);

  const load = useCallback(() => {
    const id = backtestId.trim();
    if (!id) return;
    setLoading(true);
    setError(null);
    getCommitteeForBacktest(id)
      .then((res) => setDecisions(res.decisions))
      .catch((e) => setError(errMsg(e)))
      .finally(() => setLoading(false));
  }, [backtestId]);

  return (
    <div className="flex flex-col gap-4">
      <GlassCard>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Label htmlFor="hist-backtest-id">Backtest ID</Label>
            <Input
              id="hist-backtest-id"
              value={backtestId}
              onChange={(e) => setBacktestId(e.target.value)}
              placeholder="backtest_id"
              className="font-mono-ui"
            />
          </div>
          <Button variant="secondary" loading={loading} disabled={!backtestId.trim()} onClick={load}>
            Load history
          </Button>
        </div>
      </GlassCard>

      {loading && <SkeletonTable rows={4} cols={4} />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && decisions && decisions.length === 0 && (
        <EmptyState title="No committee decisions for this backtest" hint="Run the committee against it first." />
      )}
      {!loading && !error && decisions && decisions.length > 0 && <DecisionsTable decisions={decisions} />}
    </div>
  );
}

export default function CommitteePage() {
  return (
    <MotionPage>
      <PageHeader
        title="AI Committee"
        subtitle="Six-role LLM committee debates the evidence. The CIO proposes; risk always has the veto."
      />

      <Section
        title="Run committee evaluation"
        description="Requires a persisted backtest and a persisted risk evaluation for it."
      >
        <RunCommittee />
      </Section>

      <Section title="Committee history" description="Persisted agent decisions for a given backtest.">
        <History />
      </Section>

      <Section title="How the veto binds the committee">
        <GlassCard>
          <p className="text-sm leading-relaxed text-text-muted">
            <span className="font-medium text-text">approved_by_risk</span> is copied by code from the persisted
            risk evaluation — the CIO agent cannot set it. A raw <DecisionBadge status="PAPER_TRADE" size="sm" className="mx-1" />{" "}
            call under a rejected risk evaluation is overridden to{" "}
            <DecisionBadge status="NO_TRADE" size="sm" className="mx-1" />, enforced twice: once in application
            code, once in the agent output schema validator. The committee narrates and proposes — it never creates
            paper orders. Only a human, from the Research pipeline or elsewhere, can do that.
          </p>
        </GlassCard>
      </Section>
    </MotionPage>
  );
}
