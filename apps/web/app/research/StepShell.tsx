"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";

import { GlassCard } from "@/app/components/ui/GlassCard";
import { SPRING, TRANSITION } from "@/app/lib/motion";

export type StepPhase = "locked" | "active" | "done";

export interface StepShellProps {
  index: number;
  title: string;
  phase: StepPhase;
  /** Persistent, always-rendered-once-done readout of this step's key
   * numbers -- the spine's "stratum." Richer than a one-line caption. */
  strata?: ReactNode;
  /** A brief echo of the PREVIOUS step's result, shown only while this step
   * is active -- carries evidence forward visually/temporally rather than
   * via a literal shared-element flight (two permanently-coexisting nodes
   * can't legitimately share a layoutId; see research/page.tsx). */
  carryForward?: ReactNode;
  lockedHint?: string;
  onExpand?: () => void;
  children?: ReactNode;
}

/**
 * One step of the research pipeline's spine: a dimmed locked placeholder, a
 * clickable permanent stratum once done, or the full interactive content
 * while active. Only one step is ever "active" at a time.
 */
export function StepShell({
  index,
  title,
  phase,
  strata,
  carryForward,
  lockedHint,
  onExpand,
  children,
}: StepShellProps) {
  if (phase === "locked") {
    return (
      <GlassCard padding="md" className="relative z-10 opacity-45">
        <div className="flex items-center gap-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/10 text-xs text-text-faint">
            {index}
          </span>
          <div>
            <div className="text-sm font-medium text-text-faint">{title}</div>
            {lockedHint && <div className="text-xs text-text-faint">{lockedHint}</div>}
          </div>
        </div>
      </GlassCard>
    );
  }

  if (phase === "done") {
    return (
      <button type="button" onClick={onExpand} className="relative z-10 w-full text-left">
        <GlassCard hover padding="md" className="cursor-pointer">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-positive bg-positive text-bg">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M5 13l4 4L19 7"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
              <div className="text-sm font-medium text-text">{title}</div>
            </div>
            <span className="text-xs text-text-faint">Edit</span>
          </div>
          {strata && <div className="mt-3 border-t border-white/[0.06] pt-3">{strata}</div>}
        </GlassCard>
      </button>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={TRANSITION.surface}
      className="relative z-10"
    >
      <GlassCard variant="highlighted" padding="lg">
        <div className="mb-4 flex items-center gap-3">
          <span className="glow-accent flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-accent bg-accent-soft text-xs font-semibold text-accent">
            {index}
          </span>
          <div className="text-sm font-semibold text-text">{title}</div>
        </div>
        {carryForward && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...SPRING, delay: 0.05 }}
            className="mb-4 rounded-lg border border-border-soft bg-white/[0.02] px-3 py-2"
          >
            {carryForward}
          </motion.div>
        )}
        {children}
      </GlassCard>
    </motion.div>
  );
}
