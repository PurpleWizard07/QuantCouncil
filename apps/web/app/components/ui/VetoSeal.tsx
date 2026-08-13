"use client";

import { motion } from "motion/react";

import { DURATION, EASE, STAGGER_STEP } from "@/app/lib/motion";

/** Best-effort stringification for the loosely-typed reasons/warnings/failed_rules arrays. */
function toText(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/**
 * failed_rules is the meaningful array for a hard REJECTED gate, but a softer
 * NEEDS_REVIEW veto plausibly fires mainly off warnings instead -- fall back
 * so the plate never etches empty when there's real content one array over.
 */
function pickEtchedItems(
  failedRules: unknown[],
  warnings: unknown[],
  reasons: unknown[],
): { items: unknown[]; label: string } {
  if (failedRules.length > 0) return { items: failedRules, label: "Failed rules" };
  if (warnings.length > 0) return { items: warnings, label: "Warnings" };
  if (reasons.length > 0) return { items: reasons, label: "Reasons" };
  return { items: [], label: "Failed rules" };
}

function CornerBracket({ corner, delay }: { corner: "tl" | "tr" | "bl" | "br"; delay: number }) {
  const rotate = { tl: 0, tr: 90, bl: 270, br: 180 }[corner];
  const position = {
    tl: "left-2 top-2",
    tr: "right-2 top-2",
    bl: "left-2 bottom-2",
    br: "right-2 bottom-2",
  }[corner];
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      className={`absolute ${position}`}
      style={{ transform: `rotate(${rotate}deg)` }}
      aria-hidden="true"
    >
      <motion.path
        d="M1 9V1H9"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: DURATION.ceremony, ease: EASE, delay }}
      />
    </svg>
  );
}

export interface VetoSealProps {
  /** REJECTED (hard gate, fully sealed) or NEEDS_REVIEW (soft gate, half-latched). */
  decision: "REJECTED" | "NEEDS_REVIEW";
  failedRules: unknown[];
  warnings?: unknown[];
  reasons?: unknown[];
  /** "panel" = full detail (RiskResultPanel). "inline" = compact, caps the etched list (StepOrder). */
  variant?: "panel" | "inline";
  className?: string;
}

/**
 * The binding veto, rendered as a locked plate rather than a status banner --
 * this is the one moment the whole app exists to enforce. REJECTED gets the
 * full warm seal; NEEDS_REVIEW gets the same construction half-committed
 * (fainter brackets, amber-tinted border, no glow) since it's a softer gate.
 *
 * Callers MUST key this component (or its wrapper) on something that changes
 * per evaluation, e.g. `key={riskEvaluationId ?? decision}` -- otherwise a
 * re-evaluation that flips the decision updates props in place and the
 * landing animation (which only fires on mount) will not replay.
 */
export function VetoSeal({
  decision,
  failedRules,
  warnings = [],
  reasons = [],
  variant = "panel",
  className = "",
}: VetoSealProps) {
  const sealed = decision === "REJECTED";
  const { items, label } = pickEtchedItems(failedRules, warnings, reasons);
  const visible = variant === "inline" ? items.slice(0, 3) : items;
  const overflow = items.length - visible.length;

  const borderClass = sealed ? "border-warm/50" : "border-warning/40";
  const bracketClass = sealed ? "text-warm" : "text-warm/50";
  const glowClass = sealed ? "glow-warm" : "";
  const padding = variant === "inline" ? "p-4" : "p-6";
  const labelSize = variant === "inline" ? "text-lg" : "text-2xl";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: DURATION.ceremony, ease: EASE }}
      className={`surface relative overflow-hidden rounded-xl border ${borderClass} ${glowClass} ${padding} ${className}`}
    >
      <span className={bracketClass}>
        <CornerBracket corner="tl" delay={0.15} />
        <CornerBracket corner="tr" delay={0.15} />
        <CornerBracket corner="bl" delay={0.15} />
        <CornerBracket corner="br" delay={0.15} />
      </span>

      <div className="metal-edge pb-3">
        <span className={`font-serif font-medium tracking-wide ${labelSize} ${sealed ? "text-warm" : "text-warning"}`}>
          {decision.replace(/_/g, " ")}
        </span>
      </div>

      {visible.length === 0 ? (
        <p className="mt-3 text-xs text-text-faint">No {label.toLowerCase()} recorded.</p>
      ) : (
        <ul className="mt-3 overflow-hidden rounded-lg border border-border-soft">
          {visible.map((rule, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: DURATION.element, ease: EASE, delay: 0.3 + i * STAGGER_STEP }}
              className={`flex gap-3 px-3 py-2 font-mono-ui text-[13px] tracking-[0.01em] text-warm/90 ${
                i % 2 === 1 ? "bg-white/[0.02]" : ""
              } ${i > 0 ? "border-t border-border-soft" : ""}`}
            >
              <span className="shrink-0 text-warm/50">{String(i + 1).padStart(2, "0")} ·</span>
              <span className="min-w-0 break-words">{toText(rule)}</span>
            </motion.li>
          ))}
        </ul>
      )}
      {overflow > 0 && <p className="mt-2 text-[11px] text-text-faint">+{overflow} more on the risk page.</p>}
    </motion.div>
  );
}
