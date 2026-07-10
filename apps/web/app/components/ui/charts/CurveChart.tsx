"use client";

import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fmtDate } from "@/app/lib/format";

import { ChartTooltip } from "./ChartTooltip";

export interface CurveChartProps<T extends object> {
  data: T[];
  xKey: Extract<keyof T, string>;
  yKey: Extract<keyof T, string>;
  height?: number;
  color?: string;
  variant?: "area" | "line";
  valueFormatter?: (value: number) => string;
  className?: string;
}

/** Compact axis tick for large rupee figures: 12,34,567 -> "12.3L", 1,23,45,678 -> "1.2Cr". */
function compactAxisNumber(value: number): string {
  if (!Number.isFinite(value)) return "";
  const abs = Math.abs(value);
  if (abs >= 1_00_00_000) return `${(value / 1_00_00_000).toFixed(1)}Cr`;
  if (abs >= 1_00_000) return `${(value / 1_00_000).toFixed(1)}L`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return value.toFixed(0);
}

/**
 * Generalized dark-styled curve chart (line or gradient area) driving both
 * EquityCurveChart and PriceChart below. Exported directly for any other
 * date-indexed numeric series (e.g. a custom NAV history chart).
 */
export function CurveChart<T extends object>({
  data,
  xKey,
  yKey,
  height = 240,
  color = "#22d3ee",
  variant = "area",
  valueFormatter,
  className = "",
}: CurveChartProps<T>) {
  const gradientId = `curve-gradient-${String(yKey)}`;

  return (
    <div className={className} style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis
            dataKey={xKey}
            tickFormatter={(value: string) => fmtDate(value)}
            tick={{ fill: "#5b6b81", fontSize: 11 }}
            axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            tick={{ fill: "#5b6b81", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
            tickFormatter={compactAxisNumber}
            domain={["auto", "auto"]}
          />
          <Tooltip
            content={
              <ChartTooltip
                valueFormatter={(v) => (valueFormatter ? valueFormatter(Number(v)) : String(v))}
                labelFormatter={(l) => fmtDate(String(l))}
              />
            }
          />
          {variant === "area" ? (
            <Area type="monotone" dataKey={yKey} stroke={color} strokeWidth={2} fill={`url(#${gradientId})`} />
          ) : (
            <Line type="monotone" dataKey={yKey} stroke={color} strokeWidth={2} dot={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
