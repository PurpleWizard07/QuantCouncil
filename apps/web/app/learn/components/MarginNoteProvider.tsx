"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

export interface MarginNoteContextValue {
  activeTermId: string | null;
  setActiveTermId: (id: string | null) => void;
}

const MarginNoteContext = createContext<MarginNoteContextValue | null>(null);

/** Mount around a lesson's `<article>` + `<aside>` pair. Lets any `<Term>`
 * in the article's MDX content open its definition in the margin `<aside>`
 * instead of a floating popover -- the "critical edition" reading. */
export function MarginNoteProvider({ children }: { children: ReactNode }) {
  const [activeTermId, setActiveTermId] = useState<string | null>(null);
  return (
    <MarginNoteContext.Provider value={{ activeTermId, setActiveTermId }}>{children}</MarginNoteContext.Provider>
  );
}

/** Safe outside a provider (e.g. a page with no margin column): degrades to
 * a no-op so `<Term>` never crashes, it just has nowhere to route the note. */
export function useMarginNote(): MarginNoteContextValue {
  const ctx = useContext(MarginNoteContext);
  return ctx ?? { activeTermId: null, setActiveTermId: () => {} };
}
