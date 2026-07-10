"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";

import { GlassCard } from "@/app/components/ui/GlassCard";

export type StepPhase = "locked" | "active" | "done";

export interface StepShellProps {
  index: number;
  title: string;
  phase: StepPhase;
  summary?: ReactNode;
  lockedHint?: string;
  onExpand?: () => void;
  children?: ReactNode;
}

/**
 * One step of the research pipeline's accordion: a dimmed locked placeholder,
 * a clickable collapsed summary once done, or the full interactive content
 * while active. Only one step is ever "active" at a time.
 */
export function StepShell({ index, title, phase, summary, lockedHint, onExpand, children }: StepShellProps) {
  if (phase === "locked") {
    return (
      <GlassCard padding="md" className="opacity-45">
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
      <button type="button" onClick={onExpand} className="w-full text-left">
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
          {summary && <div className="mt-3 border-t border-white/[0.06] pt-3">{summary}</div>}
        </GlassCard>
      </button>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <GlassCard variant="highlighted" padding="lg">
        <div className="mb-4 flex items-center gap-3">
          <span className="glow-accent flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-accent bg-accent-soft text-xs font-semibold text-accent">
            {index}
          </span>
          <div className="text-sm font-semibold text-text">{title}</div>
        </div>
        {children}
      </GlassCard>
    </motion.div>
  );
}
