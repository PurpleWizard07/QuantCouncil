"use client";

import { useState, type ReactNode } from "react";

import { getGlossaryEntry } from "@/app/learn/lib/glossary";

import { useMarginNote } from "./MarginNoteProvider";

/**
 * Inline glossary term: dotted underline, click/tap to reveal the Simple +
 * Technical definition without leaving the page. Falls back to a plain link
 * to the glossary page if the id isn't found, so a typo never hides content.
 *
 * At lg+ (inside a MarginNoteProvider with a MarginNote in the page's aside)
 * the definition opens in the margin, critical-edition style, and the local
 * popover below stays hidden. Below lg -- or on a page with no margin
 * column -- the popover is the only thing that ever renders it, so it's
 * always the fallback, never dead weight.
 */
export function Term({ id, children }: { id: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { activeTermId, setActiveTermId } = useMarginNote();
  const entry = getGlossaryEntry(id);

  if (!entry) {
    return (
      <a href="/learn/glossary" className="underline decoration-dotted">
        {children}
      </a>
    );
  }

  const active = activeTermId === id;

  function toggle() {
    const next = !open;
    setOpen(next);
    setActiveTermId(next ? id : null);
  }

  return (
    <span className="relative inline">
      <button
        type="button"
        onClick={toggle}
        className={`cursor-help border-b border-dotted font-medium hover:text-accent ${
          active ? "border-accent bg-accent-soft text-accent" : "border-accent/50 text-text"
        }`}
        aria-expanded={open}
      >
        {children}
      </button>
      {open && (
        <span
          role="tooltip"
          className="glass absolute left-0 top-full z-20 mt-1.5 w-72 rounded-xl p-3.5 text-left text-xs leading-relaxed shadow-lg lg:hidden"
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
