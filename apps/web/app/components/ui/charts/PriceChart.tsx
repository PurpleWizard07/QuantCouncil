"use client";

import { fmtInr } from "@/app/lib/format";

import { CurveChart } from "./CurveChart";

export interface PricePoint {
  date: string;
  close: number | null;
}

export interface PriceChartProps {
  data: PricePoint[];
  height?: number;
  variant?: "area" | "line";
  className?: string;
}

/** Line/area chart for a symbol's close-price series ({date, close}[]). */
export function PriceChart({ data, height = 240, variant = "area", className = "" }: PriceChartProps) {
  return (
    <CurveChart<PricePoint>
      data={data}
      xKey="date"
      yKey="close"
      color="#3fa6a0"
      variant={variant}
      height={height}
      className={className}
      valueFormatter={(v) => fmtInr(v)}
    />
  );
}
