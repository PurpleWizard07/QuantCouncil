"use client";

export type StepState = "locked" | "active" | "done";

export interface Step {
  label: string;
  state: StepState;
  description?: string;
}

export interface StepIndicatorProps {
  steps: Step[];
  orientation?: "horizontal" | "vertical";
  className?: string;
}

function StepCircle({ state, index }: { state: StepState; index: number }) {
  const classes =
    state === "done"
      ? "bg-positive text-bg border-positive"
      : state === "active"
        ? "bg-accent-soft text-accent border-accent glow-accent"
        : "bg-white/[0.03] text-text-faint border-white/10";
  return (
    <span
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${classes}`}
    >
      {state === "done" ? (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ) : (
        index + 1
      )}
    </span>
  );
}

/**
 * Numbered step tracker with locked/active/done states -- built for the
 * research pipeline (draft -> backtest -> risk -> committee -> paper trade)
 * but generic enough for any multi-step flow.
 */
export function StepIndicator({ steps, orientation = "horizontal", className = "" }: StepIndicatorProps) {
  if (orientation === "vertical") {
    return (
      <div className={`flex flex-col ${className}`}>
        {steps.map((step, i) => (
          <div key={step.label} className="flex gap-3">
            <div className="flex flex-col items-center">
              <StepCircle state={step.state} index={i} />
              {i < steps.length - 1 && (
                <span
                  className={`w-px flex-1 ${step.state === "done" ? "bg-positive/50" : "bg-white/10"}`}
                  style={{ minHeight: 24 }}
                />
              )}
            </div>
            <div className="pb-6">
              <div className={`text-sm font-medium ${step.state === "locked" ? "text-text-faint" : "text-text"}`}>
                {step.label}
              </div>
              {step.description && <div className="mt-0.5 text-xs text-text-muted">{step.description}</div>}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`flex items-start ${className}`}>
      {steps.map((step, i) => (
        <div key={step.label} className="flex flex-1 flex-col items-center last:flex-none">
          <div className="flex w-full items-center">
            <StepCircle state={step.state} index={i} />
            {i < steps.length - 1 && (
              <span className={`mx-2 h-px flex-1 ${step.state === "done" ? "bg-positive/50" : "bg-white/10"}`} />
            )}
          </div>
          <div className="mt-2 max-w-[9rem] text-center">
            <div className={`text-xs font-medium ${step.state === "locked" ? "text-text-faint" : "text-text"}`}>
              {step.label}
            </div>
            {step.description && <div className="mt-0.5 text-[11px] text-text-muted">{step.description}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}
