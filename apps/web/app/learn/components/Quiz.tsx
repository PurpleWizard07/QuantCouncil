"use client";

import { useState } from "react";

import { Button } from "@/app/components/ui/Button";

export interface QuizProps {
  question: string;
  options: string[];
  /** Index into `options` of the correct choice. */
  answerIndex: number;
  explanation?: string;
}

/** A single check-your-understanding question: pick one, check, see why. */
export function Quiz({ question, options = [], answerIndex, explanation }: QuizProps) {
  const [selected, setSelected] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);

  const isCorrect = checked && selected === answerIndex;
  const isWrong = checked && selected !== null && selected !== answerIndex;

  return (
    <div className="my-6 rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-text-faint">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
          <path d="M9.5 9.5a2.5 2.5 0 1 1 3.6 2.24c-.6.32-1.1.86-1.1 1.76" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M12 17v.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        Check your understanding
      </div>
      <p className="mb-3 text-sm font-medium text-text">{question}</p>
      <div className="flex flex-col gap-2">
        {options.map((option, i) => {
          const isSelected = selected === i;
          const showAsCorrect = checked && i === answerIndex;
          const showAsWrong = checked && isSelected && i !== answerIndex;
          return (
            <button
              key={option}
              type="button"
              onClick={() => !checked && setSelected(i)}
              disabled={checked}
              className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                showAsCorrect
                  ? "border-positive/50 bg-positive-soft text-positive"
                  : showAsWrong
                    ? "border-negative/50 bg-negative-soft text-negative"
                    : isSelected
                      ? "border-accent/50 bg-accent-soft text-accent"
                      : "border-white/10 bg-transparent text-text-muted hover:bg-white/[0.05] hover:text-text"
              } disabled:cursor-default`}
            >
              {option}
            </button>
          );
        })}
      </div>
      <div className="mt-3 flex items-center gap-3">
        {!checked ? (
          <Button variant="secondary" onClick={() => setChecked(true)} disabled={selected === null}>
            Check answer
          </Button>
        ) : (
          <Button
            variant="ghost"
            onClick={() => {
              setChecked(false);
              setSelected(null);
            }}
          >
            Try again
          </Button>
        )}
        {isCorrect && <span className="text-sm font-medium text-positive">Correct.</span>}
        {isWrong && <span className="text-sm font-medium text-negative">Not quite.</span>}
      </div>
      {checked && explanation && (
        <p className="mt-3 border-t border-white/10 pt-3 text-sm leading-relaxed text-text-muted">{explanation}</p>
      )}
    </div>
  );
}
