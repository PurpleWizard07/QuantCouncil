"use client";

import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { DecisionBadge } from "@/app/components/ui/DecisionBadge";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { Section } from "@/app/components/ui/Section";
import { SkeletonTable } from "@/app/components/ui/Skeleton";
import { fmtDateTime, fmtInr, fmtInt, truncateId } from "@/app/lib/format";
import type { PaperOrder } from "@/app/lib/types";

import { symbolForOrder, type SymbolMaps } from "./symbols";

export interface OrdersTableProps {
  orders: PaperOrder[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  symbolMaps: SymbolMaps;
}

/** REJECTED rows read subtly rose-tinted (DataTable has no per-row className
 * hook to add, so the tint is applied per-cell via each column's render). */
function rowTone(order: PaperOrder): string {
  return order.status === "REJECTED" ? "text-negative/80" : "text-text";
}

export function OrdersTable({ orders, loading, error, onRetry, symbolMaps }: OrdersTableProps) {
  const columns: DataTableColumn<PaperOrder>[] = [
    {
      key: "id",
      header: "Order",
      render: (row) => <span className={`font-mono-ui text-xs ${rowTone(row)}`}>{truncateId(row.id)}</span>,
    },
    {
      key: "symbol",
      header: "Symbol",
      render: (row) => (
        <span className={`font-mono-ui ${rowTone(row)}`}>{symbolForOrder(symbolMaps, row.id, row.asset_id)}</span>
      ),
    },
    {
      key: "side",
      header: "Side",
      render: (row) => (
        <span className={`font-semibold ${row.side === "BUY" ? "text-positive" : "text-negative"}`}>{row.side}</span>
      ),
    },
    { key: "quantity", header: "Qty", numeric: true, render: (row) => fmtInt(row.quantity) },
    { key: "status", header: "Status", render: (row) => <DecisionBadge status={row.status} size="sm" /> },
    { key: "fill_price", header: "Fill", numeric: true, render: (row) => fmtInr(row.fill_price) },
    {
      key: "stop_loss",
      header: "Stop",
      numeric: true,
      render: (row) => <span className={`font-mono-ui ${rowTone(row)}`}>{fmtInr(row.stop_loss)}</span>,
    },
    { key: "created_at", header: "Created", render: (row) => fmtDateTime(row.created_at) },
  ];

  return (
    <Section title="Recent orders">
      {error ? (
        <ErrorState message={error} onRetry={onRetry} />
      ) : loading && orders === null ? (
        <SkeletonTable rows={5} cols={8} />
      ) : (
        <DataTable
          columns={columns}
          data={orders ?? []}
          getRowKey={(row) => row.id}
          compact
          emptyState={<EmptyState title="No orders yet" hint="Orders placed from the panel will show up here." />}
        />
      )}
    </Section>
  );
}
