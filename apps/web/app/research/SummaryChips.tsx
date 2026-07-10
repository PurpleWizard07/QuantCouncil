"use client";

import type { ReactNode } from "react";

import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { truncateId } from "@/app/lib/format";
import type { AssetRecord, StrategyRecord } from "@/app/lib/types";

function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-text-muted">
      {children}
    </span>
  );
}

export interface SummaryChipsProps {
  symbol?: AssetRecord | null;
  strategy?: StrategyRecord | null;
  backtestId?: string | null;
  riskDecision?: string | null;
  cioDecision?: string | null;
}

/** Compact "where am I" chip row shown above the pipeline once anything is complete. */
export function SummaryChips({ symbol, strategy, backtestId, riskDecision, cioDecision }: SummaryChipsProps) {
  if (!symbol && !strategy && !backtestId && !riskDecision && !cioDecision) return null;
  return (
    <div className="mb-6 flex flex-wrap items-center gap-2">
      {symbol && <Chip>{symbol.symbol}</Chip>}
      {strategy && <Chip>{strategy.name}</Chip>}
      {backtestId && (
        <Chip>
          <span className="font-mono-ui">{truncateId(backtestId)}</span>
        </Chip>
      )}
      {riskDecision && <DecisionBadge status={riskDecision} size="sm" />}
      {cioDecision && <DecisionBadge status={cioDecision} size="sm" />}
    </div>
  );
}
