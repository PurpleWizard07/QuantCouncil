"use client";

import type { ReactNode } from "react";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  numeric?: boolean;
  width?: string;
  render?: (row: T) => ReactNode;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  data: T[];
  getRowKey: (row: T, index: number) => string;
  onRowClick?: (row: T) => void;
  emptyState?: ReactNode;
  compact?: boolean;
  className?: string;
}

/** Generic typed data table with right-aligned tabular-nums numeric columns. */
export function DataTable<T>({
  columns,
  data,
  getRowKey,
  onRowClick,
  emptyState,
  compact = false,
  className = "",
}: DataTableProps<T>) {
  const cellPad = compact ? "px-3 py-2" : "px-4 py-3";

  if (data.length === 0) {
    return (
      <div className={`glass rounded-xl ${className}`}>
        {emptyState ?? <div className="p-8 text-center text-sm text-text-muted">No data yet.</div>}
      </div>
    );
  }

  const alignClass = (col: DataTableColumn<T>) =>
    col.numeric || col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left";

  return (
    <div className={`glass overflow-x-auto rounded-xl ${className}`}>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-white/10">
            {columns.map((col) => (
              <th
                key={col.key}
                style={col.width ? { width: col.width } : undefined}
                className={`${cellPad} text-xs font-semibold uppercase tracking-wide text-text-muted ${alignClass(col)}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr
              key={getRowKey(row, index)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`border-b border-white/[0.05] transition-colors last:border-0 ${
                onRowClick ? "cursor-pointer hover:bg-white/[0.04]" : ""
              }`}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`${cellPad} text-text ${col.numeric ? "tabular-nums" : ""} ${alignClass(col)}`}
                >
                  {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
