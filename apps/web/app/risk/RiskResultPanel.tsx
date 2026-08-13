"use client";

import { CollapsibleSection } from "@/app/components/ui/CollapsibleSection";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { JsonViewer } from "@/app/components/ui/JsonViewer";
import { StatGlow } from "@/app/components/ui/StatGlow";
import { VetoSeal } from "@/app/components/ui/VetoSeal";
import { RiskScoreGauge } from "@/app/components/ui/charts/RiskScoreGauge";
import type { StatusVariant } from "@/app/components/ui/variants";
import { truncateId } from "@/app/lib/format";
import type { RiskEvaluationResult } from "@/app/lib/types";

/** Best-effort stringification for the loosely-typed reasons/warnings/failed_rules arrays. */
function toText(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function glowVariantFor(decision: string): StatusVariant {
  if (decision === "APPROVED") return "positive";
  if (decision === "NEEDS_REVIEW") return "warning";
  return "negative";
}

export interface RiskResultPanelProps {
  result: RiskEvaluationResult;
  riskEvaluationId?: string | null;
  backtestId?: string | null;
  createdAt?: string | null;
  className?: string;
}

/**
 * The rich risk-verdict readout, shared by the standalone /risk console and
 * Step 4 of the /research pipeline. The veto (REJECTED/NEEDS_REVIEW) must be
 * visually unmistakable -- a banner, a pulsing glow, and rose/amber lists.
 */
export function RiskResultPanel({
  result,
  riskEvaluationId,
  backtestId,
  createdAt,
  className = "",
}: RiskResultPanelProps) {
  const vetoed = result.decision !== "APPROVED";
  const glowVariant = glowVariantFor(result.decision);

  return (
    <div className={`flex flex-col gap-5 ${className}`}>
      {vetoed && (
        <VetoSeal
          key={riskEvaluationId ?? result.decision}
          decision={result.decision as "REJECTED" | "NEEDS_REVIEW"}
          failedRules={result.failed_rules}
          warnings={result.warnings}
          reasons={result.reasons}
          variant="panel"
        />
      )}

      <div className="flex flex-wrap items-center gap-4">
        <StatGlow variant={glowVariant} pulse={result.decision === "REJECTED"}>
          <DecisionBadge
            status={result.decision}
            pulse={result.decision === "REJECTED"}
            className="scale-125 origin-left px-4 py-1.5 text-sm"
          />
        </StatGlow>
        <span className="text-xs text-text-muted">
          Policy <span className="font-mono-ui text-text">{result.policy_version}</span>
        </span>
        {riskEvaluationId && (
          <span className="font-mono-ui text-xs text-text-faint" title={riskEvaluationId}>
            eval {truncateId(riskEvaluationId)}
          </span>
        )}
        {backtestId && (
          <span className="font-mono-ui text-xs text-text-faint" title={backtestId}>
            backtest {truncateId(backtestId)}
          </span>
        )}
        {createdAt && <span className="text-xs text-text-faint">{createdAt}</span>}
      </div>

      <div className={vetoed ? "veto-scope" : ""}>
        <RiskScoreGauge score={result.risk_score} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-negative">
            Failed rules ({result.failed_rules.length})
          </div>
          {result.failed_rules.length === 0 ? (
            <p className="text-xs text-text-faint">None — all hard gates passed.</p>
          ) : (
            <ul className="space-y-1.5">
              {result.failed_rules.map((rule, i) => (
                <li
                  key={i}
                  className="font-mono-ui text-xs text-negative"
                >
                  {toText(rule)}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-warning">
            Warnings ({result.warnings.length})
          </div>
          {result.warnings.length === 0 ? (
            <p className="text-xs text-text-faint">None.</p>
          ) : (
            <ul className="space-y-1.5">
              {result.warnings.map((warning, i) => (
                <li key={i} className="text-xs text-warning">
                  {toText(warning)}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
            Reasons ({result.reasons.length})
          </div>
          {result.reasons.length === 0 ? (
            <p className="text-xs text-text-faint">None given.</p>
          ) : (
            <ul className="space-y-1.5">
              {result.reasons.map((reason, i) => (
                <li key={i} className="text-xs text-text-muted">
                  {toText(reason)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <CollapsibleSection title="Metrics snapshot">
          <JsonViewer data={result.metrics_snapshot} label="metrics_snapshot" />
        </CollapsibleSection>
        <CollapsibleSection title="Policy snapshot">
          <JsonViewer data={result.policy_snapshot} label="policy_snapshot" />
        </CollapsibleSection>
      </div>
    </div>
  );
}
