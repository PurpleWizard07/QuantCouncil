"use client";

import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { Section } from "@/app/components/ui/Section";
import { SkeletonTable } from "@/app/components/ui/Skeleton";
import { fmtDate, fmtInr, fmtInt } from "@/app/lib/format";
import type { PaperPosition } from "@/app/lib/types";

import { symbolForPosition, type SymbolMaps } from "./symbols";

export type PositionFilter = "OPEN" | "CLOSED" | "ALL";

export interface PositionsTableProps {
  positions: PaperPosition[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  symbolMaps: SymbolMaps;
  filter: PositionFilter;
  onFilterChange: (filter: PositionFilter) => void;
}

const FILTERS: PositionFilter[] = ["OPEN", "CLOSED", "ALL"];

function pnlClass(value: number | null | undefined): string {
  if (value == null) return "text-text-muted";
  if (value > 0) return "text-positive";
  if (value < 0) return "text-negative";
  return "text-text-muted";
}

export function PositionsTable({
  positions,
  loading,
  error,
  onRetry,
  symbolMaps,
  filter,
  onFilterChange,
}: PositionsTableProps) {
  const filtered = positions ? (filter === "ALL" ? positions : positions.filter((p) => p.status === filter)) : [];

  const columns: DataTableColumn<PaperPosition>[] = [
    {
      key: "symbol",
      header: "Symbol",
      render: (row) => (
        <span className="font-mono-ui text-text">{symbolForPosition(symbolMaps, row.id, row.asset_id)}</span>
      ),
    },
    { key: "status", header: "Status", render: (row) => <DecisionBadge status={row.status} size="sm" /> },
    { key: "quantity", header: "Qty", numeric: true, render: (row) => fmtInt(row.quantity) },
    { key: "avg_entry_price", header: "Avg entry", numeric: true, render: (row) => fmtInr(row.avg_entry_price) },
    {
      key: "stop_loss",
      header: "Stop",
      numeric: true,
      render: (row) => <span className="font-mono-ui">{fmtInr(row.stop_loss)}</span>,
    },
    { key: "last_price", header: "Last", numeric: true, render: (row) => fmtInr(row.last_price) },
    {
      key: "unrealized_pnl",
      header: "Unrealized P&L",
      numeric: true,
      render: (row) => <span className={pnlClass(row.unrealized_pnl)}>{fmtInr(row.unrealized_pnl)}</span>,
    },
    {
      key: "realized_pnl",
      header: "Realized P&L",
      numeric: true,
      render: (row) => <span className={pnlClass(row.realized_pnl)}>{fmtInr(row.realized_pnl)}</span>,
    },
    { key: "opened_at", header: "Opened", render: (row) => fmtDate(row.opened_at) },
    { key: "closed_at", header: "Closed", render: (row) => fmtDate(row.closed_at) },
  ];

  const chips = (
    <div className="flex gap-1.5">
      {FILTERS.map((f) => (
        <button
          key={f}
          type="button"
          onClick={() => onFilterChange(f)}
          className={`rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide transition-colors ${
            filter === f
              ? "border-accent/40 bg-accent-soft text-accent"
              : "border-white/10 text-text-muted hover:bg-white/[0.05] hover:text-text"
          }`}
        >
          {f === "ALL" ? "All" : f.charAt(0) + f.slice(1).toLowerCase()}
        </button>
      ))}
    </div>
  );

  return (
    <Section title="Positions" actions={chips}>
      {error ? (
        <ErrorState message={error} onRetry={onRetry} />
      ) : loading && positions === null ? (
        <SkeletonTable rows={4} cols={9} />
      ) : (
        <DataTable
          columns={columns}
          data={filtered}
          getRowKey={(row) => row.id}
          emptyState={
            <EmptyState
              title={positions && positions.length === 0 ? "No positions yet" : `No ${filter.toLowerCase()} positions`}
              hint={
                positions && positions.length === 0 ? "Place a paper order to open your first position." : undefined
              }
            />
          }
        />
      )}
    </Section>
  );
}
