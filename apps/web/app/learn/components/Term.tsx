"use client";

import { useState, type ReactNode } from "react";

import { getGlossaryEntry } from "@/app/learn/lib/glossary";

/**
 * Inline glossary term: dotted underline, click/tap to reveal the Simple +
 * Technical definition without leaving the page. Falls back to a plain link
 * to the glossary page if the id isn't found, so a typo never hides content.
 */
export function Term({ id, children }: { id: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const entry = getGlossaryEntry(id);

  if (!entry) {
    return (
      <a href="/learn/glossary" className="underline decoration-dotted">
        {children}
      </a>
    );
  }

  return (
    <span className="relative inline">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="cursor-help border-b border-dotted border-accent/50 font-medium text-text hover:text-accent"
        aria-expanded={open}
      >
        {children}
      </button>
      {open && (
        <span
          role="tooltip"
          className="glass absolute left-0 top-full z-20 mt-1.5 w-72 rounded-xl p-3.5 text-left text-xs leading-relaxed shadow-lg"
        >
          <span className="mb-1 block text-sm font-semibold text-accent">{entry.term}</span>
          <span className="block text-text">{entry.simple}</span>
          <span className="mt-1.5 block text-text-muted">{entry.technical}</span>
          <a href={`/learn/glossary#${entry.id}`} className="mt-1.5 inline-block text-accent underline">
            Full entry →
          </a>
        </span>
      )}
    </span>
  );
}
