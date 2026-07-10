"use client";

export interface TooltipPayloadItem {
  dataKey?: string | number;
  value?: number | string;
  color?: string;
  name?: string;
}

export interface ChartTooltipProps {
  active?: boolean;
  label?: string | number;
  payload?: TooltipPayloadItem[];
  valueFormatter?: (value: number | string) => string;
  labelFormatter?: (label: string | number) => string;
}

/** Dark-styled tooltip shared by every recharts wrapper below. */
export function ChartTooltip({ active, label, payload, valueFormatter, labelFormatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="glass rounded-lg px-3 py-2 text-xs shadow-lg">
      {label !== undefined && (
        <div className="mb-1 text-text-faint">{labelFormatter ? labelFormatter(label) : label}</div>
      )}
      {payload.map((item, i) => (
        <div key={`${item.dataKey ?? i}`} className="flex items-center gap-2 tabular-nums text-text">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: item.color }} />
          {item.value !== undefined && (valueFormatter ? valueFormatter(item.value) : String(item.value))}
        </div>
      ))}
    </div>
  );
}
