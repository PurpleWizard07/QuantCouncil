"use client";

import { useMemo, useState } from "react";

import { SearchInput } from "@/app/components/ui/SearchInput";
import { GLOSSARY } from "@/app/learn/lib/glossary";

export function GlossarySearch() {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return GLOSSARY;
    return GLOSSARY.filter(
      (entry) =>
        entry.term.toLowerCase().includes(q) ||
        entry.simple.toLowerCase().includes(q) ||
        entry.technical.toLowerCase().includes(q),
    );
  }, [query]);

  return (
    <div>
      <SearchInput value={query} onChange={setQuery} placeholder="Search the glossary…" className="mb-6 max-w-md" />
      {filtered.length === 0 ? (
        <p className="text-sm text-text-muted">No terms match &ldquo;{query}&rdquo;.</p>
      ) : (
        <dl className="flex flex-col gap-5">
          {filtered.map((entry) => (
            <div key={entry.id} id={entry.id} className="scroll-mt-24 border-b border-white/[0.06] pb-4">
              <dt className="text-sm font-semibold text-text">{entry.term}</dt>
              <dd className="mt-1 text-sm leading-relaxed text-text-muted">
                <span className="text-text">{entry.simple}</span>
                <span className="mt-1 block text-text-faint">{entry.technical}</span>
                {entry.example && <span className="mt-1 block italic text-text-faint">e.g. {entry.example}</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
