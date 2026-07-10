"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { Label } from "@/app/components/ui/Label";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { SearchInput } from "@/app/components/ui/SearchInput";
import { Select } from "@/app/components/ui/Select";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { VARIANT_STYLES } from "@/app/components/ui/variants";
import { ApiError, getJournal, getPortfolios } from "@/app/lib/api";
import type { JournalEntry, PaperPortfolio } from "@/app/lib/types";

import { EntryCard, entryVariant } from "./EntryCard";

const PAGE_SIZE = 50;

type TypeFilter = "ALL" | "DECISION" | "FILL" | "NOTE" | "RISK_EVENT";
const TYPE_FILTERS: TypeFilter[] = ["ALL", "DECISION", "FILL", "NOTE", "RISK_EVENT"];

function errMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Unexpected error.";
}

export default function JournalPage() {
  // --- portfolios (filter dropdown; a failure here degrades to "All") --------
  const [portfolios, setPortfolios] = useState<PaperPortfolio[]>([]);
  const [portfolioId, setPortfolioId] = useState<string>(""); // "" = all

  const loadPortfolios = useCallback(async () => {
    try {
      const res = await getPortfolios();
      setPortfolios(res.portfolios);
    } catch {
      setPortfolios([]);
    }
  }, []);

  useEffect(() => {
    void loadPortfolios();
  }, [loadPortfolios]);

  // --- journal ---------------------------------------------------------------
  const [entries, setEntries] = useState<JournalEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadJournal = useCallback(async (pid: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getJournal(pid || undefined);
      setEntries(res.journal);
    } catch (err) {
      setError(errMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadJournal(portfolioId);
  }, [portfolioId, loadJournal]);

  // --- filters ------------------------------------------------------------------
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("ALL");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(PAGE_SIZE);

  useEffect(() => {
    setLimit(PAGE_SIZE);
  }, [portfolioId, typeFilter, query]);

  const filtered = useMemo(() => {
    if (!entries) return [];
    // API returns newest first; sort defensively anyway (nulls last).
    const sorted = [...entries].sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
    const q = query.trim().toLowerCase();
    return sorted.filter((entry) => {
      if (typeFilter !== "ALL" && entry.entry_type.toUpperCase().trim() !== typeFilter) return false;
      if (!q) return true;
      const refSymbol =
        entry.refs && typeof entry.refs.symbol === "string" ? (entry.refs.symbol as string) : "";
      return (
        entry.title.toLowerCase().includes(q) ||
        entry.body.toLowerCase().includes(q) ||
        refSymbol.toLowerCase().includes(q)
      );
    });
  }, [entries, typeFilter, query]);

  const visible = filtered.slice(0, limit);

  // --- render ---------------------------------------------------------------------
  return (
    <MotionPage>
      <PageHeader
        title="Journal"
        subtitle="Append-only audit trail — every paper decision is traceable to its backtest and risk evaluation."
      />

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div className="w-full sm:w-64">
          <Label htmlFor="journal-portfolio">Portfolio</Label>
          <Select id="journal-portfolio" value={portfolioId} onChange={(e) => setPortfolioId(e.target.value)}>
            <option value="">All portfolios</option>
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex flex-wrap gap-1.5 pb-0.5">
          {TYPE_FILTERS.map((t) => {
            const active = typeFilter === t;
            const style = t === "ALL" ? null : VARIANT_STYLES[entryVariant(t)];
            return (
              <button
                key={t}
                type="button"
                onClick={() => setTypeFilter(t)}
                className={`rounded-full border px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wide transition-colors ${
                  active
                    ? style
                      ? `${style.border} ${style.bg} ${style.text}`
                      : "border-accent/40 bg-accent-soft text-accent"
                    : "border-white/10 text-text-muted hover:bg-white/[0.05] hover:text-text"
                }`}
              >
                {t === "ALL" ? "All" : t.replace(/_/g, " ")}
              </button>
            );
          })}
        </div>
        <div className="w-full min-w-[200px] flex-1 sm:w-auto">
          <SearchInput value={query} onChange={setQuery} placeholder="Search title, body, or symbol…" />
        </div>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={() => void loadJournal(portfolioId)} />
      ) : loading && entries === null ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        entries && entries.length > 0 ? (
          <EmptyState
            title="No entries match the current filters"
            hint="Try clearing the search, the type filter, or the portfolio filter."
          />
        ) : (
          <EmptyState
            title="No journal entries yet"
            hint="Every order, fill, rejection, and risk event lands here automatically."
          />
        )
      ) : (
        <>
          <ol className="relative space-y-4 before:absolute before:bottom-3 before:left-[7px] before:top-3 before:w-px before:bg-white/10">
            {visible.map((entry) => {
              const dot = VARIANT_STYLES[entryVariant(entry.entry_type)].dot;
              return (
                <li key={entry.id} className="relative pl-8">
                  <span
                    className={`absolute left-0 top-6 h-[15px] w-[15px] rounded-full border-[3px] border-bg ${dot}`}
                    aria-hidden="true"
                  />
                  <EntryCard entry={entry} />
                </li>
              );
            })}
          </ol>

          <div className="mt-6 flex flex-col items-center gap-2">
            <span className="text-xs text-text-faint">
              Showing {visible.length} of {filtered.length} entries
            </span>
            {filtered.length > limit && (
              <Button variant="secondary" onClick={() => setLimit((prev) => prev + PAGE_SIZE)}>
                Show more
              </Button>
            )}
          </div>
        </>
      )}
    </MotionPage>
  );
}
