"use client";

import type { ReactNode } from "react";

import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { Select } from "@/app/components/ui/Select";
import { StatGlow } from "@/app/components/ui/StatGlow";
import { MetricBar } from "@/app/components/ui/charts/MetricBar";
import { truncateId } from "@/app/lib/format";
import type {
  BearCaseOutput,
  BullCaseOutput,
  CioDecisionOutput,
  CioRawOutput,
  QuantResearcherOutput,
  RiskNarratorOutput,
  TechnicalAnalystOutput,
} from "@/app/lib/types";

/**
 * Shared six-agent committee debate layout, used by BOTH /committee
 * (standalone console) and Step 5 of /research (guided pipeline). Owned
 * jointly by those two route dirs per the conventions contract -- do not
 * move this file without updating both imports.
 */

export const PROVIDER_OPTIONS = [
  { value: "mock", label: "Mock (offline, keyless)" },
  { value: "auto", label: "Auto" },
  { value: "anthropic", label: "Anthropic" },
  { value: "gemini", label: "Gemini" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "ollama", label: "Ollama (local)" },
];

export const PROVIDER_HINT =
  "mock is offline & keyless; cloud providers need their own API keys configured on the server.";

export interface ProviderSelectProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

export function ProviderSelect({ value, onChange, disabled, className = "" }: ProviderSelectProps) {
  return (
    <div className={className}>
      <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        {PROVIDER_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </Select>
      <p className="mt-1.5 text-[11px] text-text-faint">{PROVIDER_HINT}</p>
    </div>
  );
}

export function ProviderChips({
  requested,
  selected,
}: {
  requested: string;
  selected: string;
}) {
  const mismatch = requested !== selected;
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="text-text-muted">Requested</span>
      <span className="rounded-full border border-white/10 bg-white/[0.05] px-2.5 py-1 font-mono-ui text-text">
        {requested}
      </span>
      <span className="text-text-faint">→</span>
      <span className="text-text-muted">Selected</span>
      <span
        className={`rounded-full border px-2.5 py-1 font-mono-ui ${
          mismatch ? "border-warning/40 bg-warning-soft text-warning" : "border-accent/40 bg-accent-soft text-accent"
        }`}
      >
        {selected}
      </span>
      {mismatch && <span className="text-text-faint">(fell back)</span>}
    </div>
  );
}

function CardShell({
  title,
  badge,
  children,
  variant = "default",
}: {
  title: string;
  badge?: ReactNode;
  children: ReactNode;
  variant?: "default" | "positive" | "negative";
}) {
  return (
    <GlassCard variant={variant} className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-text">{title}</h3>
        {badge}
      </div>
      {children}
    </GlassCard>
  );
}

function BulletList({ items, tone = "muted" }: { items: string[]; tone?: "muted" | "negative" | "warning" }) {
  if (items.length === 0) return <p className="text-xs text-text-faint">None.</p>;
  const toneClass = tone === "negative" ? "text-negative" : tone === "warning" ? "text-warning" : "text-text-muted";
  return (
    <ul className={`list-inside list-disc space-y-1 text-xs ${toneClass}`}>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

export function TechnicalAnalystCard({ data }: { data: TechnicalAnalystOutput }) {
  return (
    <CardShell title="Technical Analyst" badge={<DecisionBadge status={data.view} size="sm" />}>
      <MetricBar label="Confidence" value={data.confidence} variant="watchlist" />
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Signals</div>
        <BulletList items={data.signals} />
      </div>
      {data.warnings.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-warning">Warnings</div>
          <BulletList items={data.warnings} tone="warning" />
        </div>
      )}
      <p className="text-xs leading-relaxed text-text-muted">{data.summary}</p>
    </CardShell>
  );
}

export function QuantResearcherCard({ data }: { data: QuantResearcherOutput }) {
  return (
    <CardShell title="Quant Researcher" badge={<DecisionBadge status={data.strategy_quality} size="sm" />}>
      <p className="text-xs italic leading-relaxed text-text-muted">{data.rule_interpretation}</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-positive">Strengths</div>
          <BulletList items={data.strengths} />
        </div>
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-negative">Weaknesses</div>
          <BulletList items={data.weaknesses} tone="negative" />
        </div>
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Improvement ideas</div>
        <BulletList items={data.improvement_ideas} />
      </div>
      <p className="text-xs leading-relaxed text-text-muted">{data.summary}</p>
    </CardShell>
  );
}

export function BullCaseCard({ data }: { data: BullCaseOutput }) {
  return (
    <CardShell title="Bull Case" variant="positive">
      <MetricBar label="Case strength" value={data.case_strength} variant="positive" />
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Arguments</div>
        <BulletList items={data.arguments} />
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Best case</div>
        <p className="text-xs leading-relaxed text-text-muted">{data.best_case_scenario}</p>
      </div>
      <p className="text-xs leading-relaxed text-text-muted">{data.summary}</p>
    </CardShell>
  );
}

export function BearCaseCard({ data }: { data: BearCaseOutput }) {
  return (
    <CardShell title="Bear Case" variant="negative">
      <MetricBar label="Case strength" value={data.case_strength} variant="negative" />
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Risks</div>
        <BulletList items={data.risks} tone="negative" />
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Failure modes</div>
        <BulletList items={data.failure_modes} tone="negative" />
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Worst case</div>
        <p className="text-xs leading-relaxed text-text-muted">{data.worst_case_scenario}</p>
      </div>
      <p className="text-xs leading-relaxed text-text-muted">{data.summary}</p>
    </CardShell>
  );
}

export function RiskNarratorCard({ data }: { data: RiskNarratorOutput }) {
  return (
    <CardShell title="Risk Narrator">
      <p className="text-sm font-medium leading-relaxed text-text">{data.plain_english_verdict}</p>
      <p className="text-xs leading-relaxed text-text-muted">{data.risk_summary}</p>
      {data.failed_rules_explained.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-negative">Failed rules explained</div>
          <BulletList items={data.failed_rules_explained} tone="negative" />
        </div>
      )}
      {data.warnings_explained.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-warning">Warnings explained</div>
          <BulletList items={data.warnings_explained} tone="warning" />
        </div>
      )}
    </CardShell>
  );
}

export function OverrideBanner({
  overrideWarning,
  cioRaw,
}: {
  overrideWarning: string | null;
  cioRaw: CioRawOutput;
}) {
  if (!overrideWarning) return null;
  return (
    <div className="glass flex flex-col gap-2 rounded-2xl border border-negative/40 bg-negative-soft p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-negative">Committee override enforced</span>
        <span className="rounded-full border border-negative/40 bg-negative-soft px-2 py-0.5 font-mono-ui text-[10px] uppercase text-negative">
          raw CIO wanted: {cioRaw.decision}
        </span>
      </div>
      <p className="text-xs leading-relaxed text-negative/90">{overrideWarning}</p>
      <p className="text-[11px] leading-relaxed text-text-muted">
        The raw CIO call proposed <span className="font-mono-ui text-text">{cioRaw.decision}</span>, but the risk
        veto was active. A code-level validator (not a prompt) forced the decision of record down to a non-trade
        outcome — this is enforced twice: once in application code, once in the agent output schema.
      </p>
    </div>
  );
}

export function CioCard({
  cio,
  requestedProvider,
  selectedProvider,
}: {
  cio: CioDecisionOutput;
  requestedProvider: string;
  selectedProvider: string;
}) {
  const glowVariant = cio.decision === "PAPER_TRADE" ? "positive" : cio.decision === "WATCHLIST" ? "watchlist" : "negative";

  return (
    <GlassCard variant="highlighted" padding="lg" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-text-muted">CIO — Final Decision</h3>
        <ProviderChips requested={requestedProvider} selected={selectedProvider} />
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <StatGlow variant={glowVariant} pulse={cio.decision === "NO_TRADE"}>
          <DecisionBadge status={cio.decision} className="scale-125 origin-left px-4 py-1.5 text-sm" />
        </StatGlow>
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-medium ${
            cio.approved_by_risk
              ? "border-positive/40 bg-positive-soft text-positive"
              : "border-negative/40 bg-negative-soft text-negative"
          }`}
        >
          approved_by_risk: {cio.approved_by_risk ? "true" : "false"}
        </span>
      </div>

      <p className="text-sm leading-relaxed text-text">{cio.summary}</p>
      <p className="text-xs leading-relaxed text-text-muted">{cio.reason}</p>

      {cio.conditions_to_reconsider.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
            Conditions to reconsider
          </div>
          <BulletList items={cio.conditions_to_reconsider} />
        </div>
      )}

      <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-white/[0.06] pt-3 text-[11px] text-text-faint">
        <span title={cio.audit_refs.backtest_id}>backtest {truncateId(cio.audit_refs.backtest_id)}</span>
        <span title={cio.audit_refs.risk_evaluation_id}>risk eval {truncateId(cio.audit_refs.risk_evaluation_id)}</span>
        {cio.audit_refs.agent_decision_ids.map((id) => (
          <span key={id} title={id}>
            agent {truncateId(id)}
          </span>
        ))}
      </div>
    </GlassCard>
  );
}
