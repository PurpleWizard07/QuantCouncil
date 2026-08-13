"use client";

import { fmtInr } from "@/app/lib/format";
import type { EquityCurvePoint } from "@/app/lib/types";

import { CurveChart } from "./CurveChart";

export interface EquityCurveChartProps {
  data: EquityCurvePoint[];
  height?: number;
  className?: string;
}

/** Gradient area chart for a backtest/portfolio equity curve ({date, equity}[]). */
export function EquityCurveChart({ data, height = 240, className = "" }: EquityCurveChartProps) {
  return (
    <CurveChart<EquityCurvePoint>
      data={data}
      xKey="date"
      yKey="equity"
      color="#4cc3d9"
      variant="area"
      height={height}
      className={className}
      valueFormatter={(v) => fmtInr(v)}
    />
  );
}
