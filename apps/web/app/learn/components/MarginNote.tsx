"use client";

import { getGlossaryEntry } from "@/app/learn/lib/glossary";

import { useMarginNote } from "./MarginNoteProvider";

/** The margin panel a clicked `<Term>` opens into, at lg+ where there's an
 * actual margin to use. Renders nothing when no term is active. */
export function MarginNote() {
  const { activeTermId, setActiveTermId } = useMarginNote();
  if (!activeTermId) return null;
  const entry = getGlossaryEntry(activeTermId);
  if (!entry) return null;

  return (
    <div className="surface rounded-xl border border-warm/30 p-3.5 text-xs leading-relaxed">
      <div className="mb-2 flex items-start justify-between gap-2">
        <span className="font-serif text-sm font-medium text-warm">{entry.term}</span>
        <button
          type="button"
          onClick={() => setActiveTermId(null)}
          className="shrink-0 text-text-faint transition-colors hover:text-text"
          aria-label="Close definition"
        >
          ×
        </button>
      </div>
      <p className="text-text">{entry.simple}</p>
      <p className="mt-1.5 text-text-muted">{entry.technical}</p>
      <a href={`/learn/glossary#${entry.id}`} className="mt-1.5 inline-block text-accent underline">
        Full entry →
      </a>
    </div>
  );
}
