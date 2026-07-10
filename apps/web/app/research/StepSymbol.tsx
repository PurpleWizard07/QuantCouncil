"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { SearchInput } from "@/app/components/ui/SearchInput";
import { Skeleton } from "@/app/components/ui/Skeleton";
import { getAssets } from "@/app/lib/api";
import type { AssetRecord } from "@/app/lib/types";

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error.";
}

export interface StepSymbolProps {
  selected: AssetRecord | null;
  onSelect: (asset: AssetRecord) => void;
  onContinue: () => void;
}

/** Step 1: pick a symbol from the seeded asset universe. */
export function StepSymbol({ selected, onSelect, onContinue }: StepSymbolProps) {
  const [assets, setAssets] = useState<AssetRecord[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const autoSelected = useRef(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getAssets()
      .then((res) => setAssets(res.assets))
      .catch((e) => setError(errMsg(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (autoSelected.current || selected || !assets || assets.length === 0) return;
    const reliance = assets.find((a) => a.symbol === "RELIANCE");
    if (reliance) {
      autoSelected.current = true;
      onSelect(reliance);
    }
  }, [assets, selected, onSelect]);

  const filtered = useMemo(() => {
    if (!assets) return [];
    const q = query.trim().toLowerCase();
    if (!q) return assets;
    return assets.filter(
      (a) =>
        a.symbol.toLowerCase().includes(q) ||
        a.name.toLowerCase().includes(q) ||
        (a.sector ?? "").toLowerCase().includes(q),
    );
  }, [assets, query]);

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  if (!assets || assets.length === 0) {
    return (
      <EmptyState
        title="No assets in the universe yet"
        hint="Seed the asset universe via the backend CLI before running the research pipeline."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <SearchInput value={query} onChange={setQuery} placeholder="Search symbol, name, or sector..." />
      <div className="grid max-h-80 grid-cols-2 gap-2.5 overflow-y-auto pr-1 sm:grid-cols-3 lg:grid-cols-4">
        {filtered.map((asset) => {
          const isSelected = selected?.symbol === asset.symbol;
          return (
            <button
              key={asset.symbol}
              type="button"
              onClick={() => onSelect(asset)}
              className={`rounded-xl border p-3 text-left transition-colors ${
                isSelected
                  ? "border-accent/50 bg-accent-soft"
                  : "border-white/10 bg-white/[0.02] hover:bg-white/[0.05]"
              }`}
            >
              <div className={`text-sm font-semibold ${isSelected ? "text-accent" : "text-text"}`}>
                {asset.symbol}
              </div>
              <div className="truncate text-xs text-text-muted">{asset.name}</div>
              {asset.sector && (
                <div className="mt-1 text-[10px] uppercase tracking-wide text-text-faint">{asset.sector}</div>
              )}
            </button>
          );
        })}
      </div>
      {filtered.length === 0 && <p className="text-xs text-text-faint">No matches for &quot;{query}&quot;.</p>}
      <div className="flex justify-end">
        <Button variant="primary" disabled={!selected} onClick={onContinue}>
          Continue to strategy
        </Button>
      </div>
    </div>
  );
}
