"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/app/components/ui/Button";
import { Input } from "@/app/components/ui/Input";
import { Label } from "@/app/components/ui/Label";
import { Select } from "@/app/components/ui/Select";
import { useToast } from "@/app/components/ui/Toast";
import { ApiError, getStrategies, runBacktest, type RunBacktestBody } from "@/app/lib/api";
import type { StrategyRecord } from "@/app/lib/types";

export interface QuickRunFormProps {
  onRunComplete: (backtestId: string) => void;
}

/**
 * Strips the API-added metadata keys (`source`, `id`, `status`, `created_at`)
 * so a strategy record fetched from GET /strategies can be replayed as an
 * inline `strategy` definition on POST /backtests/run -- the backend's
 * validator rejects unknown top-level keys (see docs/strategy-format.md).
 * Only needed for built-ins, which have no `id` to reference via
 * `strategy_id`; persisted strategies are sent by id instead (see below).
 */
function stripMetadata(strategy: StrategyRecord): Record<string, unknown> {
  const { source: _source, id: _id, status: _status, created_at: _createdAt, ...rest } = strategy;
  return rest;
}

/** Compact quick-run form: symbol + strategy, persists the run, then hands the new id back up. */
export function QuickRunForm({ onRunComplete }: QuickRunFormProps) {
  const { showToast } = useToast();
  const [strategies, setStrategies] = useState<StrategyRecord[]>([]);
  const [strategiesLoading, setStrategiesLoading] = useState(true);
  const [selectedName, setSelectedName] = useState("");
  const [symbol, setSymbol] = useState("");
  const [running, setRunning] = useState(false);

  useEffect(() => {
    getStrategies()
      .then((res) => {
        setStrategies(res.strategies);
        if (res.strategies.length > 0) setSelectedName(res.strategies[0].name);
      })
      .catch(() => {
        // Silent: the form just degrades to "no strategies available" -- the
        // Strategies page and this page's own run list already surface load
        // errors prominently, no need to duplicate an ErrorState here.
      })
      .finally(() => setStrategiesLoading(false));
  }, []);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const strategy = strategies.find((s) => s.name === selectedName);
    const trimmedSymbol = symbol.trim().toUpperCase();
    if (!strategy || !trimmedSymbol) return;

    const body: RunBacktestBody =
      strategy.source === "persisted" && strategy.id
        ? { strategy_id: strategy.id, symbol: trimmedSymbol, persist: true }
        : { strategy: stripMetadata(strategy), symbol: trimmedSymbol, persist: true };

    setRunning(true);
    runBacktest(body)
      .then((res) => {
        showToast(`Backtest complete: ${res.strategy_name} on ${res.symbol}.`, "success");
        if (res.backtest_id) onRunComplete(res.backtest_id);
      })
      .catch((err: unknown) => {
        const message = err instanceof ApiError ? err.message : "Backtest run failed.";
        showToast(message, "error");
      })
      .finally(() => setRunning(false));
  };

  return (
    <form onSubmit={handleSubmit}>
      <h3 className="mb-3 text-sm font-semibold text-text">Quick run</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <div>
          <Label htmlFor="quick-run-symbol">Symbol</Label>
          <Input
            id="quick-run-symbol"
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            placeholder="e.g. RELIANCE"
            disabled={running}
          />
        </div>
        <div>
          <Label htmlFor="quick-run-strategy">Strategy</Label>
          <Select
            id="quick-run-strategy"
            value={selectedName}
            onChange={(event) => setSelectedName(event.target.value)}
            disabled={running || strategiesLoading || strategies.length === 0}
          >
            {strategies.length === 0 && <option value="">No strategies available</option>}
            {strategies.map((s, i) => (
              <option key={s.id ?? `${s.source}-${s.name}-${i}`} value={s.name}>
                {s.name} ({s.source})
              </option>
            ))}
          </Select>
        </div>
        <Button
          type="submit"
          variant="primary"
          loading={running}
          disabled={running || !symbol.trim() || !selectedName || strategiesLoading}
        >
          Run + persist
        </Button>
      </div>
      <p className="mt-2 text-xs text-text-faint">
        Runs with <code className="font-mono-ui">persist: true</code> and appends the new run to the
        list above. For the full guided flow with risk gating and committee review, use the Research
        Pipeline instead.
      </p>
    </form>
  );
}
