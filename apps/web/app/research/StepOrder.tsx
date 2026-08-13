"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { ErrorState } from "@/app/components/ui/ErrorState";
import { GlassCard } from "@/app/components/ui/GlassCard";
import { InlineSpinner } from "@/app/components/ui/InlineSpinner";
import { Input } from "@/app/components/ui/Input";
import { Label } from "@/app/components/ui/Label";
import { Select } from "@/app/components/ui/Select";
import { Textarea } from "@/app/components/ui/Textarea";
import { useToast } from "@/app/components/ui/Toast";
import { VetoSeal } from "@/app/components/ui/VetoSeal";
import { ApiError, createPaperOrder, createPortfolio, getPortfolios } from "@/app/lib/api";
import { fmtInr, fmtInt, truncateId } from "@/app/lib/format";
import type { AssetRecord, CreateOrderResponse, PaperPortfolio } from "@/app/lib/types";

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Unexpected error.";
}

export interface StepOrderProps {
  symbol: AssetRecord;
  backtestId: string;
  riskEvaluationId: string;
  riskApproved: boolean;
  riskDecision: string;
  riskFailedRules: unknown[];
  riskWarnings: unknown[];
  riskReasons: unknown[];
  result: CreateOrderResponse | null;
  onSuccess: (result: CreateOrderResponse) => void;
}

/** Step 6: the ONLY step that mutates portfolio state -- always a human click. */
export function StepOrder({
  symbol,
  backtestId,
  riskEvaluationId,
  riskApproved,
  riskDecision,
  riskFailedRules,
  riskWarnings,
  riskReasons,
  result,
  onSuccess,
}: StepOrderProps) {
  const { showToast } = useToast();
  const [portfolios, setPortfolios] = useState<PaperPortfolio[] | null>(null);
  const [portfoliosLoading, setPortfoliosLoading] = useState(false);
  const [portfoliosError, setPortfoliosError] = useState<string | null>(null);
  const [creatingPortfolio, setCreatingPortfolio] = useState(false);

  const [portfolioId, setPortfolioId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [priceReference, setPriceReference] = useState("");
  const [stopLossPrice, setStopLossPrice] = useState("");
  const [thesis, setThesis] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<{ status: number; message: string } | null>(null);

  const loadPortfolios = useCallback(() => {
    setPortfoliosLoading(true);
    setPortfoliosError(null);
    getPortfolios()
      .then((res) => {
        setPortfolios(res.portfolios);
        setPortfolioId((prev) => prev || (res.portfolios.length > 0 ? res.portfolios[0].id : ""));
      })
      .catch((e) => setPortfoliosError(errMsg(e)))
      .finally(() => setPortfoliosLoading(false));
  }, []);

  useEffect(() => {
    if (riskApproved) loadPortfolios();
  }, [riskApproved, loadPortfolios]);

  const makeDefaultPortfolio = useCallback(() => {
    setCreatingPortfolio(true);
    createPortfolio({})
      .then((p) => {
        showToast(`Created portfolio "${p.name}"`, "success");
        setPortfolioId(p.id);
        loadPortfolios();
      })
      .catch((e) => showToast(errMsg(e), "error"))
      .finally(() => setCreatingPortfolio(false));
  }, [loadPortfolios, showToast]);

  const submit = useCallback(() => {
    setFormError(null);
    const qty = Number.parseInt(quantity, 10);
    if (!portfolioId) {
      setFormError("Select a portfolio.");
      return;
    }
    if (!Number.isFinite(qty) || qty < 1) {
      setFormError("Quantity must be a whole number of at least 1.");
      return;
    }
    const stopLoss = Number.parseFloat(stopLossPrice);
    if (!Number.isFinite(stopLoss)) {
      setFormError("Stop-loss price is required.");
      return;
    }
    let priceRef: number | undefined;
    if (priceReference.trim()) {
      priceRef = Number.parseFloat(priceReference);
      if (!Number.isFinite(priceRef)) {
        setFormError("Price reference must be a number.");
        return;
      }
      if (stopLoss >= priceRef) {
        setFormError("Stop-loss price must be below the reference price.");
        return;
      }
    }
    if (!thesis.trim()) {
      setFormError("A thesis is required before placing a paper order.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    createPaperOrder({
      portfolio_id: portfolioId,
      symbol: symbol.symbol,
      side: "BUY",
      quantity: qty,
      thesis: thesis.trim(),
      backtest_id: backtestId,
      risk_evaluation_id: riskEvaluationId,
      ...(priceRef !== undefined ? { price_reference: priceRef } : {}),
      stop_loss_price: stopLoss,
    })
      .then((res) => {
        onSuccess(res);
        showToast("Paper order filled", "success");
      })
      .catch((e) => {
        if (e instanceof ApiError) setSubmitError({ status: e.status, message: e.message });
        else setSubmitError({ status: 0, message: errMsg(e) });
        showToast(errMsg(e), "error");
      })
      .finally(() => setSubmitting(false));
  }, [
    portfolioId,
    quantity,
    stopLossPrice,
    priceReference,
    thesis,
    symbol,
    backtestId,
    riskEvaluationId,
    onSuccess,
    showToast,
  ]);

  if (!riskApproved) {
    return (
      <div className="flex flex-col gap-3">
        <VetoSeal
          key={riskEvaluationId || riskDecision}
          decision={riskDecision === "REJECTED" ? "REJECTED" : "NEEDS_REVIEW"}
          failedRules={riskFailedRules}
          warnings={riskWarnings}
          reasons={riskReasons}
          variant="inline"
        />
        <p className="text-xs leading-relaxed text-text-faint">
          Paper trading is blocked for this backtest until a fresh, approved risk evaluation exists — no LLM agent
          and no button in this UI can override the veto.
        </p>
      </div>
    );
  }

  if (result) {
    return (
      <GlassCard variant="positive" className="flex flex-col gap-4">
        <div className="text-sm font-semibold text-positive">Paper order filled</div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div>
            <div className="text-xs text-text-muted">Fill price</div>
            <div className="text-sm font-semibold tabular-nums text-text">{fmtInr(result.fill.fill_price)}</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Cost</div>
            <div className="text-sm font-semibold tabular-nums text-text">{fmtInr(result.fill.cost)}</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Quantity</div>
            <div className="text-sm font-semibold tabular-nums text-text">{fmtInt(result.order.quantity)}</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Portfolio cash after</div>
            <div className="text-sm font-semibold tabular-nums text-text">
              {fmtInr(result.portfolio.current_cash)}
            </div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Portfolio NAV after</div>
            <div className="text-sm font-semibold tabular-nums text-text">{fmtInr(result.portfolio.current_nav)}</div>
          </div>
          <div>
            <div className="text-xs text-text-muted">Journal ref</div>
            <div className="font-mono-ui text-sm text-text" title={result.journal_entry_id}>
              {truncateId(result.journal_entry_id)}
            </div>
          </div>
        </div>
        <p className="text-[11px] text-text-faint">Simulated paper order — no real money, no broker.</p>
      </GlassCard>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="surface rounded-xl border border-warning/30 bg-warning-soft p-3 text-xs text-warning">
        This is a human action. QuantCouncil never places a paper order automatically — you are confirming it.
      </div>

      {portfoliosLoading && (
        <div className="flex items-center gap-2 text-sm text-text-muted">
          <InlineSpinner size="sm" /> Loading portfolios…
        </div>
      )}
      {!portfoliosLoading && portfoliosError && <ErrorState message={portfoliosError} onRetry={loadPortfolios} />}
      {!portfoliosLoading && !portfoliosError && portfolios && portfolios.length === 0 && (
        <div className="surface flex flex-col items-center gap-3 rounded-xl p-6 text-center">
          <p className="text-sm text-text-muted">No paper portfolios yet.</p>
          <Button variant="secondary" loading={creatingPortfolio} onClick={makeDefaultPortfolio}>
            Create default portfolio
          </Button>
        </div>
      )}

      {!portfoliosLoading && portfolios && portfolios.length > 0 && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="order-portfolio">Portfolio</Label>
              <Select id="order-portfolio" value={portfolioId} onChange={(e) => setPortfolioId(e.target.value)}>
                {portfolios.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — cash {fmtInr(p.current_cash)}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="order-qty">Quantity</Label>
              <Input
                id="order-qty"
                type="number"
                min={1}
                step={1}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="order-price-ref">Price reference (optional)</Label>
              <Input
                id="order-price-ref"
                type="number"
                step="any"
                value={priceReference}
                onChange={(e) => setPriceReference(e.target.value)}
                placeholder="blank = latest cached close"
              />
            </div>
            <div>
              <Label htmlFor="order-stop-loss">Stop-loss price</Label>
              <Input
                id="order-stop-loss"
                type="number"
                step="any"
                value={stopLossPrice}
                onChange={(e) => setStopLossPrice(e.target.value)}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="order-thesis">Thesis</Label>
            <Textarea
              id="order-thesis"
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              placeholder="Why this trade, in your own words..."
            />
          </div>

          {formError && <p className="text-xs text-negative">{formError}</p>}

          {submitError?.status === 403 && (
            <ErrorState message={submitError.message} onRetry={() => setSubmitError(null)} />
          )}
          {submitError?.status === 400 && (
            <div className="surface rounded-xl border border-warning/40 bg-warning-soft p-4 text-center">
              <div className="text-sm font-medium text-warning">Order rejected by portfolio limits</div>
              <p className="mt-2 text-xs text-text-muted">{submitError.message}</p>
            </div>
          )}
          {submitError && submitError.status !== 403 && submitError.status !== 400 && (
            <ErrorState message={submitError.message} onRetry={() => setSubmitError(null)} />
          )}

          <div className="flex justify-end">
            <Button variant="primary" loading={submitting} onClick={submit}>
              Place paper order (BUY)
            </Button>
          </div>
          <p className="text-right text-[11px] text-text-faint">Simulated paper order — no real money, no broker.</p>
        </div>
      )}
    </div>
  );
}
