"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { DataTable, type DataTableColumn } from "@/app/components/ui/DataTable";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { MetricCard } from "@/app/components/ui/MetricCard";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { SearchInput } from "@/app/components/ui/SearchInput";
import { Section } from "@/app/components/ui/Section";
import { SkeletonTable } from "@/app/components/ui/Skeleton";
import { ApiError, getAssets } from "@/app/lib/api";
import type { AssetRecord } from "@/app/lib/types";

import { AssetDetailPanel } from "./AssetDetailPanel";

/** Chip button for the sector filter row -- glass-consistent but not a full GlassCard. */
function SectorChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
        active
          ? "border-accent/40 bg-accent-soft text-accent"
          : "border-white/10 bg-white/[0.03] text-text-muted hover:bg-white/[0.06] hover:text-text"
      }`}
    >
      {label}
    </button>
  );
}

export default function MarketPage() {
  const [assets, setAssets] = useState<AssetRecord[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sector, setSector] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    getAssets()
      .then((res) => setAssets(res.assets))
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load the NIFTY 50 universe.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sectors = useMemo(() => {
    if (!assets) return [];
    const set = new Set<string>();
    for (const asset of assets) if (asset.sector) set.add(asset.sector);
    return Array.from(set).sort();
  }, [assets]);

  const filtered = useMemo(() => {
    if (!assets) return [];
    const query = search.trim().toLowerCase();
    return assets.filter((asset) => {
      const matchesSector = !sector || asset.sector === sector;
      const matchesQuery =
        query.length === 0 ||
        asset.symbol.toLowerCase().includes(query) ||
        asset.name.toLowerCase().includes(query) ||
        (asset.sector ?? "").toLowerCase().includes(query);
      return matchesSector && matchesQuery;
    });
  }, [assets, search, sector]);

  const columns: DataTableColumn<AssetRecord>[] = [
    {
      key: "symbol",
      header: "Symbol",
      render: (row) => <span className="font-mono-ui font-bold text-text">{row.symbol}</span>,
    },
    { key: "name", header: "Name" },
    { key: "sector", header: "Sector", render: (row) => row.sector ?? "—" },
    { key: "exchange", header: "Exchange" },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (row) => (
        <div className="flex items-center justify-end gap-2">
          <Button variant="secondary" onClick={() => setSelectedSymbol(row.symbol)}>
            View
          </Button>
          <Link
            href="/research"
            className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-accent transition-colors hover:text-accent/80"
          >
            Research →
          </Link>
        </div>
      ),
    },
  ];

  return (
    <MotionPage>
      <PageHeader
        title="Market"
        subtitle="NIFTY 50 universe: daily OHLCV, price charts, and indicators."
      />

      <Section title="Universe overview">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Universe size"
            value={assets ? assets.length : "—"}
            loading={loading && !error}
            subtext="NIFTY 50 constituents"
          />
          <MetricCard label="Exchange" value="NSE" subtext="National Stock Exchange" />
          <MetricCard label="Data source" value="yfinance" subtext="daily bars, cached locally" />
          <MetricCard label="Timeframe" value="1D" subtext="daily only in v1" />
        </div>
      </Section>

      <Section
        title="NIFTY 50 universe"
        description="Browse the tracked universe, filter by sector, and open a symbol below."
        actions={
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search symbol, name, sector…"
            className="w-72"
          />
        }
      >
        {sectors.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            <SectorChip label="All sectors" active={sector === null} onClick={() => setSector(null)} />
            {sectors.map((s) => (
              <SectorChip key={s} label={s} active={sector === s} onClick={() => setSector(s)} />
            ))}
          </div>
        )}

        {loading ? (
          <SkeletonTable rows={8} cols={5} />
        ) : error ? (
          <ErrorState message={error} onRetry={load} />
        ) : (
          <DataTable
            columns={columns}
            data={filtered}
            getRowKey={(row) => row.symbol}
            emptyState={
              <EmptyState
                title="No matching assets"
                hint="Try a different search term or clear the sector filter."
              />
            }
          />
        )}
      </Section>

      {selectedSymbol && (
        <AssetDetailPanel symbol={selectedSymbol} onClose={() => setSelectedSymbol(null)} />
      )}
    </MotionPage>
  );
}
