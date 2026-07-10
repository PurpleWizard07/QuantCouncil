"use client";

import { GlassCard } from "@/app/components/ui/GlassCard";
import { JsonViewer } from "@/app/components/ui/JsonViewer";
import { VARIANT_STYLES, type StatusVariant } from "@/app/components/ui/variants";
import { fmtDateTime, fmtInr, truncateId } from "@/app/lib/format";
import type { JournalEntry } from "@/app/lib/types";

/**
 * The shared DecisionBadge's status map covers FILLED/PENDING/... but NOT the
 * journal entry_type vocabulary (DECISION/FILL/NOTE/RISK_EVENT), which would
 * all fall through to neutral. Shared components are frozen for this task, so
 * this local badge composes the same VARIANT_STYLES tokens for pixel-identical
 * styling with the correct per-type tint.
 */
export const ENTRY_TYPE_VARIANT: Record<string, StatusVariant> = {
  DECISION: "watchlist",
  FILL: "positive",
  NOTE: "neutral",
  RISK_EVENT: "negative",
};

export function entryVariant(entryType: string): StatusVariant {
  return ENTRY_TYPE_VARIANT[entryType.toUpperCase().trim()] ?? "neutral";
}

function EntryTypeBadge({ entryType }: { entryType: string }) {
  const style = VARIANT_STYLES[entryVariant(entryType)];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${style.bg} ${style.text} ${style.border}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden="true" />
      {entryType.replace(/_/g, " ")}
    </span>
  );
}

// --- refs helpers (refs is Record<string, unknown> | null; never trust shapes) ---

function refString(refs: Record<string, unknown> | null, key: string): string | null {
  if (!refs) return null;
  const value = refs[key];
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function refNumber(refs: Record<string, unknown> | null, key: string): number | null {
  if (!refs) return null;
  const value = refs[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max)}…`;
}

const CHIP_BASE = "inline-flex max-w-full items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]";

function Chip({
  children,
  tone = "neutral",
  mono = false,
  title,
}: {
  children: React.ReactNode;
  tone?: StatusVariant;
  mono?: boolean;
  title?: string;
}) {
  const style = VARIANT_STYLES[tone];
  return (
    <span
      title={title}
      className={`${CHIP_BASE} ${style.border} ${style.text} ${tone === "neutral" ? "bg-white/[0.03]" : style.bg} ${mono ? "font-mono-ui" : ""}`}
    >
      {children}
    </span>
  );
}

const LINKED_ID_KEYS: { key: string; label: string }[] = [
  { key: "paper_order_id", label: "order" },
  { key: "position_id", label: "position" },
  { key: "backtest_id", label: "backtest" },
  { key: "risk_evaluation_id", label: "risk eval" },
];

export function EntryCard({ entry }: { entry: JournalEntry }) {
  const refs = entry.refs;
  const symbol = refString(refs, "symbol");
  const thesis = refString(refs, "thesis");
  const riskSummary = refString(refs, "risk_summary");
  const rejectionReason = refString(refs, "rejection_reason");
  const exitReason = refString(refs, "exit_reason");
  const result = refString(refs, "result");
  const realizedPnl = refNumber(refs, "realized_pnl");

  const hasChips =
    symbol != null ||
    thesis != null ||
    riskSummary != null ||
    rejectionReason != null ||
    exitReason != null ||
    result != null ||
    realizedPnl != null ||
    LINKED_ID_KEYS.some(({ key }) => refString(refs, key) != null);

  return (
    <GlassCard padding="md" hover>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <EntryTypeBadge entryType={entry.entry_type} />
          <span className="text-sm font-semibold text-text">{entry.title}</span>
        </div>
        <span className="text-xs tabular-nums text-text-faint">{fmtDateTime(entry.created_at)}</span>
      </div>

      {entry.body && <p className="mt-2 text-sm leading-relaxed text-text-muted">{entry.body}</p>}

      {hasChips && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {symbol && (
            <Chip tone="accent" mono>
              {symbol}
            </Chip>
          )}
          {thesis && (
            <Chip tone="neutral" title={thesis}>
              thesis: {truncate(thesis, 90)}
            </Chip>
          )}
          {riskSummary && <Chip tone="warning">{truncate(riskSummary, 90)}</Chip>}
          {rejectionReason && (
            <Chip tone="negative" title={rejectionReason}>
              {truncate(rejectionReason, 90)}
            </Chip>
          )}
          {exitReason && (
            <Chip tone="neutral" title={exitReason}>
              exit: {truncate(exitReason, 90)}
            </Chip>
          )}
          {result && <Chip tone="watchlist">{truncate(result, 90)}</Chip>}
          {realizedPnl != null && (
            <Chip tone={realizedPnl > 0 ? "positive" : realizedPnl < 0 ? "negative" : "neutral"}>
              realized {fmtInr(realizedPnl)}
            </Chip>
          )}
          {LINKED_ID_KEYS.map(({ key, label }) => {
            const id = refString(refs, key);
            return id ? (
              <Chip key={key} tone="neutral" mono title={id}>
                {label} {truncateId(id)}
              </Chip>
            ) : null;
          })}
        </div>
      )}

      {refs != null && (
        <div className="mt-3">
          <JsonViewer data={refs} label="refs" collapsed />
        </div>
      )}
    </GlassCard>
  );
}
