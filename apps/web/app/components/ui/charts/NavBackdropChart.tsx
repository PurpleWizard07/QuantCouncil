"use client";

import { useId } from "react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

import type { NavSnapshot } from "@/app/lib/types";

/** Decorative only: no axes, grid, or tooltip -- this sits BEHIND a hero NAV
 * numeral, not beside it, so it stays out of the way of the figure itself. */
export function NavBackdropChart({ snapshots }: { snapshots: NavSnapshot[] }) {
  const gradientId = useId();
  if (snapshots.length < 2) return null;
  return (
    <div className="absolute inset-0 opacity-[0.35]" aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={snapshots} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4cc3d9" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#4cc3d9" stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="nav"
            stroke="#4cc3d9"
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
