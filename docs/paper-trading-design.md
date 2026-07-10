# QuantCouncil Paper Trading Design

Design of the paper trading engine (delivered in Phase 5 of the
[development roadmap](development-roadmap.md); originally slated for Phase 6). Everything in
this document concerns **simulated** trading only. See the final section for the binding
statement on real orders.

> **Phase 5 as-implemented.** The engine shipped in Phase 5 with one deliberate, versioned
> deviation from this design: orders fill **immediately** at a price reference rather than at
> the next trading day's open (see the marked notes in the Order Lifecycle and Fill Simulation
> sections below). The rules table, journal entry types, allowed execution actions, and the
> No Real Orders statement are unchanged and implemented as designed. The authoritative
> as-built reference is [paper-trading-engine.md](paper-trading-engine.md).

## Paper Portfolio Rules

| Rule | Value | Notes |
|---|---|---|
| Starting capital | Rs 10,00,000 (1,000,000 INR) | Fixed at portfolio creation. |
| Max allocation per stock | 10% of NAV | Cost basis of a single asset's position may not exceed 10% of current NAV at entry. |
| Max risk per paper trade | 1% of NAV | (entry price - stop-loss price) * quantity <= 1% of NAV at entry. |
| Max open positions | 10 | New entries rejected while 10 positions are open. |
| Portfolio drawdown trigger | 8% | Drawdown >= 8% from peak NAV activates risk-off mode. |
| Stop-loss | Mandatory | Every paper trade must carry a stop-loss; orders without one are rejected. |
| Backtest prerequisite | Mandatory | No paper trade without a persisted `backtest_runs` row for the strategy. |
| Risk-evaluation prerequisite | Mandatory | No paper trade without a persisted `risk_evaluations` row; no paper trade if the risk engine rejects (see [risk-policy.md](risk-policy.md)). |

## Order Lifecycle

```
PENDING -> FILLED
PENDING -> REJECTED
PENDING -> CANCELLED
```

- **PENDING** — order created by `create_paper_order` after all prerequisites pass; awaiting
  the next trading day's open.
- **FILLED** — `simulate_order_fill` executed the order at the simulated fill price.
- **REJECTED** — a rule failed (missing stop-loss, allocation/risk/position limits, risk-off
  mode for entries, missing backtest or risk approval). The rejection reason is journaled.
- **CANCELLED** — withdrawn before fill (manual cancellation or a superseding decision).

`FILLED`, `REJECTED`, and `CANCELLED` are terminal states.

> **Phase 5 as-implemented.** Because fills are immediate (see the next section), `PENDING`
> is effectively transient: `POST /paper/orders` validates, fills, and persists in a single
> request, so every persisted order lands directly in `FILLED` or `REJECTED`. `CANCELLED`
> is unused in Phase 5 — there is no window in which an order can be withdrawn. The state
> diagram above remains the design target if next-open fills are restored later.

## Fill Simulation Model (v1)

> **Phase 5 as-implemented.** The delivered engine fills orders **immediately** at a price
> reference — the request's `price_reference`, else the latest available cached close —
> instead of at the next trading day's open. This is a deliberate, versioned simplification
> logged in [assumptions.md](assumptions.md). The slippage and transaction-cost defaults are
> unchanged from this design (0.05% adverse slippage per fill, 0.05% cost per side — the
> backtester's defaults), so paper results remain comparable to backtests. Next-open fills
> remain a possible future refinement. If no price is available, the order request fails
> with 502 rather than waiting `PENDING`.

- Orders are filled at the **next trading day's open price**, adjusted for slippage and
  transaction costs using the same defaults as the backtester (0.05% slippage per fill,
  0.05% transaction cost per side; see [backtesting-engine.md](backtesting-engine.md)).
- **Documented assumption:** the paper engine must reuse the backtester's fill
  model — same slippage and cost defaults — so paper results
  remain comparable to backtests. The Phase 1 zero-slippage simplification was superseded
  by the Phase 3 backtester defaults. See [assumptions.md](assumptions.md).
- If the next trading day has no bar for the asset (data gap), the order stays `PENDING` until
  the next available bar or is cancelled after a configurable staleness window.
  (Not applicable in Phase 5: fills are immediate, so there is no waiting state.)

## Position Tracking

- One `paper_positions` row per asset per portfolio while open: quantity, average entry price,
  entry date, stop-loss price, and links to the originating order.
- `update_paper_positions` applies fills; `mark_to_market` revalues open positions at the
  latest close.
- Realized P&L is recorded when a position is closed (exit signal, stop-loss hit, or manual
  exit). Unrealized P&L = (last close - avg entry price) * quantity.
- Stop-loss evaluation runs on daily closes in v1: if a bar's close breaches the stop, an exit
  order is generated and filled at the next open (consistent with the fill model above).

> **Phase 5 as-implemented.** Stop-loss prices are required on every BUY and stored on the
> position (an add-on's stop replaces the position's previous stop), but automatic stop-loss
> monitoring is **not yet implemented** — no exit order is auto-generated when a close
> breaches the stop. Exits in Phase 5 are manual SELL orders. Stop-loss evaluation on daily
> closes remains future work.

## NAV and Drawdown

- **NAV** = cash + sum over open positions of (position quantity * last close).
  Computed by `calculate_paper_nav`, deterministically, from persisted state.
- **Drawdown** = (peak NAV - current NAV) / peak NAV, where peak NAV is the running maximum
  NAV since portfolio inception. Peak NAV is persisted on `paper_portfolios`.

## Risk-Off Mode

Triggered when drawdown >= 8%.

- **No new entries**: all entry orders are rejected while risk-off is active.
- **Exits still allowed**: stop-losses, exit signals, and manual exits continue to function —
  risk-off must never trap the portfolio in losing positions.
- **Manual reset after review**: risk-off does not auto-clear when NAV recovers. A human
  reviews the journal and explicitly resets the flag; the reset is journaled as a
  `RISK_EVENT`.

## Trade Journal

`trade_journal` is append-only. Entry types:

| Type | Written when | Required audit refs |
|---|---|---|
| `DECISION` | A CIO committee decision is recorded (PAPER_TRADE / NO_TRADE / WATCHLIST). | `backtest_id`, `risk_evaluation_id`, `agent_decision_ids` |
| `FILL` | A paper order transitions to FILLED (also journaled: REJECTED / CANCELLED). | `paper_order_id`, plus the originating `DECISION` entry's refs |
| `NOTE` | A human adds free-form commentary. | Any related entity ids (optional) |
| `RISK_EVENT` | Risk-off activation/reset, stop-loss triggers, limit rejections. | `paper_portfolio_id`, plus the triggering entity id |

Audit rule: from any `FILL` entry it must be possible to reach the strategy's backtest, its
risk evaluation, and the agent decisions that approved it. This is verified by the Phase 8
audit checks in the [development roadmap](development-roadmap.md).

## Allowed Execution Actions (Verbatim)

The complete set of execution actions any component (including agents and the optional MCP
server) may perform:

- `create_paper_order`
- `simulate_order_fill`
- `mark_to_market`
- `update_paper_positions`
- `calculate_paper_nav`
- `write_trade_journal_entry`

## No Real Orders — Ever

**No code path in QuantCouncil may ever place, modify, or cancel a real order, connect to a
broker, or touch real money.** The disallowed actions (`place_real_order`,
`modify_real_order`, `cancel_real_order`, `connect_broker_account`,
`fetch_real_broker_holdings`, `execute_live_strategy`, `auto_trade_real_money`) are
permanently out of scope in every phase — see [non-goals.md](non-goals.md). Any pull request
introducing broker connectivity violates the project constitution.
