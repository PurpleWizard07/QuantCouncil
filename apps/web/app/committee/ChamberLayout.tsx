"use client";

import { motion } from "motion/react";

import { GlassCard } from "@/app/components/ui/GlassCard";
import { VARIANT_STYLES, type StatusVariant } from "@/app/components/ui/variants";
import { DURATION, EASE, STAGGER_STEP } from "@/app/lib/motion";
import type { BearCaseOutput, BullCaseOutput, CommitteeEvaluateResponse } from "@/app/lib/types";

import {
  BulletList,
  CioCard,
  OverrideBanner,
  QuantResearcherCard,
  RiskNarratorCard,
  TechnicalAnalystCard,
} from "./components";

/**
 * The committee chamber: a presiding CIO head, an evidence row feeding the
 * debate, an opposed bull/bear axis, and the risk narrator as the floor
 * beneath it all. Specific to the standalone /committee console -- Step 5 of
 * the research pipeline keeps the plain stacked grid from ./components,
 * since a wizard step isn't "the chamber," it's one stop inside a bigger one.
 */

/** Explicit per-role accent used only for the on-resolve settle flash --
 * bull/bear reuse their existing status colors; the three non-adversarial
 * roles get one each so every card in the chamber settles distinctly. */
const ROLE_ACCENT: Record<"technical" | "quant" | "bull" | "bear" | "risk", StatusVariant> = {
  technical: "watchlist",
  quant: "accent",
  bull: "positive",
  bear: "negative",
  risk: "warning",
};

function SettleFlash({ role, delay }: { role: keyof typeof ROLE_ACCENT; delay: number }) {
  const hex = VARIANT_STYLES[ROLE_ACCENT[role]].hex;
  return (
    <motion.div
      className="pointer-events-none absolute inset-0 rounded-2xl"
      style={{ boxShadow: `inset 0 0 0 1px ${hex}` }}
      initial={{ opacity: 0 }}
      animate={{ opacity: [0, 0.9, 0] }}
      transition={{ duration: DURATION.ceremony, ease: EASE, delay }}
    />
  );
}

/** The head's own landing cue -- warm, distinct from the five role accents,
 * timed to land just as the last of them fades: the chamber settling into
 * the one authoritative verdict. */
function HeadArrivalGlow({ delay }: { delay: number }) {
  return (
    <motion.div
      className="pointer-events-none absolute inset-0 rounded-2xl"
      style={{ boxShadow: "inset 0 0 0 1px var(--color-warm), 0 0 28px -4px rgba(198,161,91,0.5)" }}
      initial={{ opacity: 0 }}
      animate={{ opacity: [0, 1, 0] }}
      transition={{ duration: DURATION.ceremony, ease: EASE, delay }}
    />
  );
}

/** A slim, fixed-height sweep -- deliberately NOT sized against the
 * chamber's own (unbounded, content-driven) height, so it stays robust
 * regardless of how long the six agents' generated text runs. */
function DeliberationPulse() {
  return (
    <div className="relative mt-4 h-1 w-full overflow-hidden rounded-full bg-white/[0.06]" aria-hidden="true">
      <motion.div
        className="absolute inset-y-0 w-1/3 rounded-full bg-gradient-to-r from-transparent via-accent/70 to-transparent"
        animate={{ left: ["-33%", "100%"] }}
        transition={{ duration: 2.4, ease: "linear", repeat: Infinity }}
      />
    </div>
  );
}

function ChamberHead({ result, loading }: { result: CommitteeEvaluateResponse | null; loading: boolean }) {
  if (!result) {
    return (
      <GlassCard padding="lg" className="opacity-45">
        <div className="flex items-center gap-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/10 text-xs text-text-faint">
            CIO
          </span>
          <div className="text-sm font-medium text-text-faint">Awaiting committee verdict</div>
        </div>
        {loading && <DeliberationPulse />}
      </GlassCard>
    );
  }
  return (
    <div className="relative">
      <div className="metal-edge pb-1.5">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-warm">Presiding — CIO</span>
      </div>
      <CioCard
        cio={result.cio}
        requestedProvider={result.requested_provider}
        selectedProvider={result.selected_provider}
      />
      <HeadArrivalGlow delay={5 * STAGGER_STEP} />
    </div>
  );
}

function EvidenceRow({ result }: { result: CommitteeEvaluateResponse }) {
  return (
    <div>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-faint">Evidence</div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="relative">
          <TechnicalAnalystCard data={result.technical_analyst} />
          <SettleFlash role="technical" delay={0} />
        </div>
        <div className="relative">
          <QuantResearcherCard data={result.quant_researcher} />
          <SettleFlash role="quant" delay={STAGGER_STEP} />
        </div>
      </div>
    </div>
  );
}

/** Mirrored progress bar: `side="left"` grows from the shared center axis
 * leftward, `side="right"` grows from it rightward, so the two panels read
 * as one balance rather than two independent metrics. case_strength is a
 * 0-1 fraction, same convention as MetricBar elsewhere in this codebase. */
function OpposedBar({
  side,
  value,
  variant,
  delay,
}: {
  side: "left" | "right";
  value: number;
  variant: "positive" | "negative";
  delay: number;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  const hex = VARIANT_STYLES[variant].hex;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
      <div className={`flex h-full w-full ${side === "left" ? "justify-end" : "justify-start"}`}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: hex }}
          initial={{ width: 0 }}
          animate={{ width: `${clamped * 100}%` }}
          transition={{ duration: DURATION.surface, ease: EASE, delay }}
        />
      </div>
    </div>
  );
}

function ChamberBullPanel({ data }: { data: BullCaseOutput }) {
  return (
    <GlassCard variant="positive" className="flex flex-col gap-3 sm:rounded-r-none sm:border-r-0">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-text">Bull Case</h3>
        <span className="font-mono-ui text-xs font-semibold tabular-nums text-positive">
          {(Math.max(0, Math.min(1, data.case_strength)) * 100).toFixed(0)}%
        </span>
      </div>
      <OpposedBar side="left" value={data.case_strength} variant="positive" delay={0} />
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Arguments</div>
        <BulletList items={data.arguments} />
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Best case</div>
        <p className="text-xs leading-relaxed text-text-muted">{data.best_case_scenario}</p>
      </div>
      <p className="text-xs leading-relaxed text-text-muted">{data.summary}</p>
    </GlassCard>
  );
}

function ChamberBearPanel({ data }: { data: BearCaseOutput }) {
  return (
    <GlassCard variant="negative" className="flex flex-col gap-3 sm:rounded-l-none sm:border-l-0">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-text">Bear Case</h3>
        <span className="font-mono-ui text-xs font-semibold tabular-nums text-negative">
          {(Math.max(0, Math.min(1, data.case_strength)) * 100).toFixed(0)}%
        </span>
      </div>
      <OpposedBar side="right" value={data.case_strength} variant="negative" delay={STAGGER_STEP} />
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Risks</div>
        <BulletList items={data.risks} tone="negative" />
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Failure modes</div>
        <BulletList items={data.failure_modes} tone="negative" />
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Worst case</div>
        <p className="text-xs leading-relaxed text-text-muted">{data.worst_case_scenario}</p>
      </div>
      <p className="text-xs leading-relaxed text-text-muted">{data.summary}</p>
    </GlassCard>
  );
}

function DebateAxis({ result }: { result: CommitteeEvaluateResponse } ) {
  return (
    <div className="relative grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-border sm:grid-cols-2 sm:gap-0">
      <div
        className="pointer-events-none absolute inset-y-0 left-1/2 z-10 hidden w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-border-strong to-transparent sm:block"
        aria-hidden="true"
      />
      <div className="relative">
        <ChamberBullPanel data={result.bull_case} />
        <SettleFlash role="bull" delay={2 * STAGGER_STEP} />
      </div>
      <div className="relative">
        <ChamberBearPanel data={result.bear_case} />
        <SettleFlash role="bear" delay={3 * STAGGER_STEP} />
      </div>
    </div>
  );
}

function RiskFloor({ result }: { result: CommitteeEvaluateResponse }) {
  return (
    <div className="relative">
      <div
        className="mb-2 h-px w-full bg-gradient-to-r from-transparent via-border-strong to-transparent"
        aria-hidden="true"
      />
      <RiskNarratorCard data={result.risk_narrator} />
      <SettleFlash role="risk" delay={4 * STAGGER_STEP} />
    </div>
  );
}

export function ChamberLayout({
  result,
  loading,
}: {
  result: CommitteeEvaluateResponse | null;
  loading: boolean;
}) {
  return (
    <div className="flex flex-col gap-6">
      <ChamberHead result={result} loading={loading} />
      {result && (
        // Keyed on the risk evaluation this verdict is for, so a re-run
        // (same page, new result) replays the settle-flash sequence.
        <div key={result.risk_evaluation_id} className="flex flex-col gap-6">
          <EvidenceRow result={result} />
          <DebateAxis result={result} />
          <RiskFloor result={result} />
          <OverrideBanner overrideWarning={result.override_warning} cioRaw={result.cio_raw} />
        </div>
      )}
    </div>
  );
}
