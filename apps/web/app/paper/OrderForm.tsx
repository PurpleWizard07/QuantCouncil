"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/app/components/ui/Button";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { Input } from "@/app/components/ui/Input";
import { Label } from "@/app/components/ui/Label";
import { Section } from "@/app/components/ui/Section";
import { Select } from "@/app/components/ui/Select";
import { Textarea } from "@/app/components/ui/Textarea";
import { useToast } from "@/app/components/ui/Toast";
import { ApiError, createPaperOrder, type CreatePaperOrderBody } from "@/app/lib/api";
import { fmtInr, truncateId } from "@/app/lib/format";
import type { AssetRecord, CreateOrderResponse, OrderSide, PaperPortfolio } from "@/app/lib/types";

export interface OrderFormProps {
  portfolio: PaperPortfolio;
  assets: AssetRecord[] | null;
  assetsError: string | null;
  onRetryAssets: () => void;
  onOrderPlaced: () => void;
}

interface SubmitError {
  kind: "risk" | "rejected" | "other";
  message: string;
}

const EMPTY_FORM = {
  symbol: "",
  side: "BUY" as OrderSide,
  quantity: "1",
  priceReference: "",
  stopLoss: "",
  backtestId: "",
  riskEvaluationId: "",
  thesis: "",
};

type FormState = typeof EMPTY_FORM;

/**
 * Order panel: always rendered (a persistent side card, per the contract's
 * "CollapsibleSection or side card" option) rather than a toggled
 * CollapsibleSection, because CollapsibleSection's open state is internal/
 * uncontrolled and this file cannot edit that shared component to add a
 * controlled-open prop. The page's "New paper order" button scrolls this
 * panel into view instead of toggling visibility.
 */
export function OrderForm({ portfolio, assets, assetsError, onRetryAssets, onOrderPlaced }: OrderFormProps) {
  const { showToast } = useToast();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<SubmitError | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<CreateOrderResponse | null>(null);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function validate(): string | null {
    if (!form.symbol) return "Select a symbol.";
    const qty = Number(form.quantity);
    if (!Number.isInteger(qty) || qty < 1) {
      return "Quantity must be a whole number of at least 1.";
    }
    if (!form.thesis.trim()) {
      return form.side === "SELL" ? "Thesis (used as exit reason) is required." : "Thesis is required.";
    }
    if (form.side === "BUY") {
      const stop = Number(form.stopLoss);
      if (!form.stopLoss.trim() || !Number.isFinite(stop) || stop <= 0) {
        return "Stop-loss price is required for a BUY order.";
      }
      if (!form.backtestId.trim()) return "backtest_id is required for a BUY order.";
      if (!form.riskEvaluationId.trim()) return "risk_evaluation_id is required for a BUY order.";
      if (form.priceReference.trim()) {
        const ref = Number(form.priceReference);
        if (Number.isFinite(ref) && stop >= ref) {
          return "Stop-loss must be below the reference price.";
        }
      }
    }
    return null;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = validate();
    setValidationMessage(message);
    if (message) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const body: CreatePaperOrderBody = {
        portfolio_id: portfolio.id,
        symbol: form.symbol,
        side: form.side,
        quantity: Number(form.quantity),
        thesis: form.thesis.trim(),
      };
      if (form.side === "SELL") body.exit_reason = form.thesis.trim();
      if (form.priceReference.trim()) body.price_reference = Number(form.priceReference);
      if (form.stopLoss.trim()) body.stop_loss_price = Number(form.stopLoss);
      if (form.backtestId.trim()) body.backtest_id = form.backtestId.trim();
      if (form.riskEvaluationId.trim()) body.risk_evaluation_id = form.riskEvaluationId.trim();

      const result = await createPaperOrder(body);
      setLastResult(result);
      setForm(EMPTY_FORM);
      setValidationMessage(null);
      showToast(`${result.order.side} ${result.order.quantity} filled @ ${fmtInr(result.fill.fill_price)}`, "success");
      onOrderPlaced();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setSubmitError({ kind: "risk", message: err.message });
      } else if (err instanceof ApiError && err.status === 400) {
        setSubmitError({ kind: "rejected", message: err.message });
      } else {
        setSubmitError({
          kind: "other",
          message: err instanceof ApiError ? err.message : "Failed to place the order.",
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Section
      title="New paper order"
      description={`Against ${portfolio.name}${portfolio.risk_mode === "RISK_OFF" ? " · risk-off: new BUYs will be vetoed" : ""}`}
    >
      <GlassCard padding="lg">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="order-symbol">Symbol</Label>
            {assetsError ? (
              <ErrorState message={assetsError} onRetry={onRetryAssets} />
            ) : (
              <Select
                id="order-symbol"
                value={form.symbol}
                onChange={(e) => update("symbol", e.target.value)}
                disabled={!assets}
              >
                <option value="">{assets ? "Select a symbol…" : "Loading symbols…"}</option>
                {assets?.map((asset) => (
                  <option key={asset.symbol} value={asset.symbol}>
                    {asset.symbol} — {asset.name}
                  </option>
                ))}
              </Select>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="order-side">Side</Label>
              <Select id="order-side" value={form.side} onChange={(e) => update("side", e.target.value as OrderSide)}>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="order-qty">Quantity</Label>
              <Input
                id="order-qty"
                type="number"
                min={1}
                step={1}
                value={form.quantity}
                onChange={(e) => update("quantity", e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="order-price-ref">Price reference</Label>
              <Input
                id="order-price-ref"
                type="number"
                step="any"
                placeholder="Blank = latest cached close"
                value={form.priceReference}
                onChange={(e) => update("priceReference", e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="order-stop">Stop-loss {form.side === "BUY" ? "(required)" : "(unused for SELL)"}</Label>
              <Input
                id="order-stop"
                type="number"
                step="any"
                placeholder="Mandatory; must be below reference"
                value={form.stopLoss}
                onChange={(e) => update("stopLoss", e.target.value)}
                className="font-mono-ui"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="order-backtest">Backtest ID {form.side === "BUY" ? "(required for BUY)" : "(optional)"}</Label>
              <Input
                id="order-backtest"
                placeholder="UUID"
                value={form.backtestId}
                onChange={(e) => update("backtestId", e.target.value)}
                className="font-mono-ui"
              />
            </div>
            <div>
              <Label htmlFor="order-risk-eval">
                Risk evaluation ID {form.side === "BUY" ? "(required for BUY)" : "(optional)"}
              </Label>
              <Input
                id="order-risk-eval"
                placeholder="UUID"
                value={form.riskEvaluationId}
                onChange={(e) => update("riskEvaluationId", e.target.value)}
                className="font-mono-ui"
              />
            </div>
          </div>
          <p className="-mt-2 text-xs text-text-faint">
            BUY requires an APPROVED, persisted risk evaluation — get backtest/risk-evaluation ids from the Research
            Pipeline.
          </p>

          <div>
            <Label htmlFor="order-thesis">Thesis {form.side === "SELL" ? "(doubles as exit reason)" : ""}</Label>
            <Textarea
              id="order-thesis"
              rows={3}
              value={form.thesis}
              onChange={(e) => update("thesis", e.target.value)}
              placeholder={form.side === "SELL" ? "Why are you exiting?" : "Why are you entering this position?"}
            />
          </div>

          {validationMessage && (
            <div className="rounded-lg border border-warning/40 bg-warning-soft px-3 py-2 text-xs text-warning">
              {validationMessage}
            </div>
          )}

          {submitError?.kind === "risk" && (
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-negative">Risk veto</div>
              <ErrorState message={submitError.message} />
            </div>
          )}
          {submitError?.kind === "rejected" && (
            <GlassCard variant="warning" padding="sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-warning">Order rejected</div>
              <p className="mt-1 text-sm text-text-muted">{submitError.message}</p>
            </GlassCard>
          )}
          {submitError?.kind === "other" && (
            <GlassCard variant="negative" padding="sm">
              <p className="text-sm text-text-muted">{submitError.message}</p>
            </GlassCard>
          )}

          <Button type="submit" variant="primary" loading={submitting} className="w-full">
            Place {form.side} order
          </Button>
        </form>

        {lastResult && (
          <GlassCard variant="positive" padding="sm" className="mt-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-positive">Order filled</div>
            <dl className="mt-2 space-y-1 text-xs text-text-muted">
              <div className="flex justify-between gap-2">
                <dt>Fill price</dt>
                <dd className="font-mono-ui text-text">{fmtInr(lastResult.fill.fill_price)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Cost</dt>
                <dd className="font-mono-ui text-text">{fmtInr(lastResult.fill.cost)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Cash after</dt>
                <dd className="font-mono-ui text-text">{fmtInr(lastResult.portfolio.current_cash)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>NAV after</dt>
                <dd className="font-mono-ui text-text">{fmtInr(lastResult.portfolio.current_nav)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Journal ref</dt>
                <dd className="font-mono-ui text-accent">{truncateId(lastResult.journal_entry_id)}</dd>
              </div>
            </dl>
          </GlassCard>
        )}
      </GlassCard>
    </Section>
  );
}
