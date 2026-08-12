export type PayoffType = "long-call" | "long-put" | "short-call" | "short-put";

const CONFIG: Record<
  PayoffType,
  { label: string; points: string; color: string; maxLoss: string; maxGain: string }
> = {
  "long-call": {
    label: "Long Call",
    points: "10,130 150,130 280,20",
    color: "var(--color-accent)",
    maxLoss: "Premium paid",
    maxGain: "Unlimited",
  },
  "long-put": {
    label: "Long Put",
    points: "10,20 150,130 280,130",
    color: "var(--color-accent)",
    maxLoss: "Premium paid",
    maxGain: "Large (to zero)",
  },
  "short-call": {
    label: "Short Call (naked)",
    points: "10,70 150,70 280,155",
    color: "var(--color-negative)",
    maxLoss: "Unlimited",
    maxGain: "Premium received",
  },
  "short-put": {
    label: "Short Put",
    points: "10,155 150,70 280,70",
    color: "var(--color-warning)",
    maxLoss: "Large (strike − premium)",
    maxGain: "Premium received",
  },
};

/**
 * A generic, illustrative payoff diagram for one of the four basic option
 * positions -- replaces the ASCII-art versions in the source content with a
 * real inline SVG. Shapes are schematic (not drawn to scale from real
 * numbers), matching how the source itself presents them.
 */
export function PayoffDiagram({ type }: { type: PayoffType }) {
  const cfg = CONFIG[type];
  return (
    <figure className="my-6 rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <svg viewBox="0 0 300 170" width="100%" height="170" role="img" aria-label={`${cfg.label} payoff diagram`}>
        {/* zero P/L line */}
        <line x1="10" y1="100" x2="290" y2="100" stroke="rgba(255,255,255,0.14)" strokeWidth="1" />
        {/* strike marker */}
        <line x1="150" y1="10" x2="150" y2="160" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3 3" />
        <text x="150" y="167" textAnchor="middle" fontSize="10" fill="var(--color-text-faint)">
          K (strike)
        </text>
        <text x="292" y="103" fontSize="10" fill="var(--color-text-faint)">
          S
        </text>
        <text x="6" y="14" fontSize="10" fill="var(--color-text-faint)">
          P/L
        </text>
        {/* payoff line */}
        <polyline points={cfg.points} fill="none" stroke={cfg.color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-2 border-t border-white/10 pt-2.5 text-xs">
        <span className="font-medium text-text">{cfg.label}</span>
        <span className="text-text-muted">
          Max loss: <span className="text-text">{cfg.maxLoss}</span> · Max gain: <span className="text-text">{cfg.maxGain}</span>
        </span>
      </div>
    </figure>
  );
}
