# QuantCouncil Paper Portfolio Engine (Phase 5)

The authoritative reference for the Phase 5 Paper Portfolio Engine: simulation philosophy,
portfolio lifecycle, order mechanics, position management, risk enforcement, and API surface.
Component boundaries are defined in [architecture.md](architecture.md); the delivery history
and deviations from the original plan are in [development-roadmap.md](development-roadmap.md);
the underlying engineering decisions are logged in [assumptions.md](assumptions.md).

Everything in this layer is deterministic Python (`apps/api/app/services/paper_engine.py`,
HTTP surface `apps/api/app/routers/paper.py`) with **no AI, no broker connectivity, and no
real execution** — paper trading is pure simulation, locally deterministic, with all state
persisted in SQLite/Postgres. **No real orders exist anywhere in the codebase** — this is
enforced architecturally and audited in Phase 8.

## Philosophy: "AI Can Propose. Math Can Approve. Risk Can Veto."

The paper engine is the **ultimate downstream consumer** of the risk veto. When the risk
engine returns `approved=false`, the CIO agent decision **cannot** be `PAPER_TRADE`
(enforced by Pydantic validator). This constraint flows through to paper order creation:
an unapproved risk evaluation blocks BUY orders with HTTP 403. Exit orders (SELLs) are
**always allowed** — risk-off-mode is a guard rail, not a cage.

---

## Core Flow

```
1. Persisted backtest (backtest_id)
       ↓
2. Risk evaluation (POST /risk/evaluate → risk_evaluation_id, approved field)
       ↓
3. Create portfolio (POST /paper/portfolios → portfolio_id)
       ↓
4. CREATE BUY ORDER (POST /paper/orders)
   ├─ Validation checks: portfolio exists, symbol exists, quantity ≥ 1
   ├─ Price reference: request's price_reference OR latest cached close
   ├─ THE VETO: risk_evaluation_id → evaluation.approved must be true (403 if false)
   ├─ Portfolio limits: risk-off gate, max_open_positions, allocation gate, risk-per-trade gate
   └─ If all pass: order → FILLED immediately, position created/increased, cash/NAV updated, journal entry
       ↓
5. MARK-TO-MARKET (POST /paper/portfolios/{id}/mark-to-market)
   ├─ Fetch latest closes for all open positions
   ├─ Update unrealized P&L
   ├─ Update NAV = cash + Σ(qty × last_close)
   └─ If drawdown ≥ 8%: risk_off flag latches true (one-way, no auto-reset)
       ↓
6. CREATE SELL ORDER (POST /paper/orders, side="SELL")
   ├─ NO approval check — exits are always allowed, even during risk-off
   ├─ Must have open position with sufficient quantity (or 400 error)
   └─ Order → FILLED immediately, cash updated, realized P&L recorded, journal entry
       ↓
7. QUERY AUDIT TRAIL (GET /paper/journal)
   ├─ FILL entries: BUY/SELL, with risk evaluation refs on BUY
   └─ RISK_EVENT entries: drawdown thresholds, risk-off latch
```

---

## Portfolio Lifecycle

### POST /paper/portfolios (create)

**Request:**

```json
{
  "name": "My Paper Fund"
}
```

Optional; if omitted, defaults to `"Default Paper Fund"`.

**Response (201):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Paper Fund",
  "current_cash": 1000000.0,
  "current_nav": 1000000.0,
  "peak_nav": 1000000.0,
  "risk_off": false,
  "created_at": "2026-07-08T10:30:00Z"
}
```

**Defaults (hardcoded in Phase 5):**

| Field | Value |
|---|---|
| `starting_capital` | ₹10,00,000 (1,000,000 INR) |
| `max_allocation_per_stock` | 0.10 (10% of NAV) |
| `max_risk_per_trade` | 0.01 (1% of NAV) |
| `max_open_positions` | 10 |
| `risk_off_drawdown` | 0.08 (8%) |
| `require_stop_loss` | `true` |

Settings are stored as JSON in the portfolio row; all limits are enforced.

**Response (503):** Database unreachable.

---

### GET /paper/portfolios

List all portfolios.

**Response (200):**

```json
{
  "count": 2,
  "portfolios": [
    {
      "id": "550e8400-...",
      "name": "My Paper Fund",
      "current_cash": 900000.0,
      "current_nav": 1050000.0,
      "peak_nav": 1050000.0,
      "risk_off": false,
      "created_at": "2026-07-08T10:30:00Z"
    },
    ...
  ]
}
```

---

### GET /paper/portfolios/{id}

Retrieve portfolio state (current cash, NAV, drawdown).

**Response (200):** Portfolio details (same as POST response above).

**Errors:**

| Code | Meaning |
|---|---|
| `404` | Portfolio not found |
| `503` | Database unreachable |

---

## Order Creation and Fill Simulation

### Fill Reference and Price

When an order is created, the fill price is determined by:

1. **Explicit price_reference in the request:** use it directly (if provided).
2. **Latest cached close:** if no price_reference, fetch the latest available OHLCV close
   for the symbol via the shared OHLCV service (~10-day lookback window).
3. **Unavailable:** 502 error; no state corrupted.

---

### BUY Order: Full Validation and Veto Sequence

**Request:**

```json
{
  "portfolio_id": "550e8400-e29b-41d4-a716-446655440000",
  "side": "BUY",
  "symbol": "RELIANCE",
  "quantity": 10,
  "price_reference": 2850.0,
  "thesis": "SMA crossover signal; strong momentum",
  "stop_loss_price": 2700.0,
  "backtest_id": "550e8400-e29b-41d4-a716-446655440001",
  "risk_evaluation_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Validation Sequence (validated in order; earliest failure returns error):**

1. **Portfolio exists** → 404 if not.
2. **Symbol resolves to seeded Asset row** → 404 if unknown.
3. **Quantity is integer ≥ 1** → 400 if not.
4. **Thesis is non-empty string** → 400 if missing/empty.
5. **Stop-loss price exists and < reference price** → 400 if missing or >= reference.
6. **Backtest ID exists** → 404 if not.
7. **Risk evaluation ID exists** → 404 if not.
8. **Evaluation belongs to the backtest** → 400 if mismatch.
9. **THE VETO: evaluation.approved == true** → **403 if false**. Error response includes `decision`, `risk_score`, and rejected order id (persisted REJECTED row).

**Portfolio-Level Gates (if all above pass):**

10. **Risk-off blocks new entries** → if `portfolio.risk_off == true`, reject with 400. Audit: RISK_EVENT journal entry.
11. **Max open positions gate** → if position count == `max_open_positions` AND symbol is a new entry (not an add-on), reject with 400. Add-ons are allowed. Audit: RISK_EVENT journal entry.
12. **Allocation gate** → compute fill price: `ref_price * (1 + 0.0005)` for a BUY. Tentative cost basis: `qty * fill_price`. Check: `(existing_cost_basis + tentative_cost) ≤ 0.10 * NAV`. If exceeded, reject with 400. Audit: RISK_EVENT journal entry.
13. **Per-trade risk gate** → max risk = `(fill_price - stop_loss_price) * qty ≤ 0.01 * NAV`. If exceeded, reject with 400. Audit: RISK_EVENT journal entry.
14. **Sufficient cash** → `NAV ≥ qty * fill_price + (transaction cost)`. If insufficient, reject with 400. Audit: RISK_EVENT journal entry.

**All gates passed: FILL order immediately**

- Compute actual fill: `ref_price * (1 + 0.0005)` (BUY slippage, adverse).
- Compute transaction cost: `qty * fill_price * 0.0005` (entry-side cost).
- Debit cash: `qty * fill_price + cost`.
- Recompute NAV.
- Create or update position:
  - If no position: `avg_entry = fill_price`, `quantity = qty`, `stop_loss = stop_loss_price`.
  - If position exists (add-on): weighted-average entry = `(existing_qty * existing_avg + qty * fill_price) / (existing_qty + qty)`. Update `stop_loss = stop_loss_price` (replaces old stop).
- Persist `PaperOrder` row: `status=FILLED`, `fill_price`, `filled_at=now`, `stop_loss`, refs to backtest/risk-eval.
- Write journal FILL entry: `type=FILL`, `side=BUY`, `quantity`, `fill_price`, `cost`, `risk_summary="<decision> (score <N>)"`, `thesis`, and refs.

**Response (201):**

```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440003",
  "portfolio_id": "550e8400-e29b-41d4-a716-446655440000",
  "symbol": "RELIANCE",
  "side": "BUY",
  "quantity": 10,
  "status": "FILLED",
  "fill_price": 2852.85,
  "stop_loss_price": 2700.0,
  "filled_at": "2026-07-08T10:30:00Z",
  "thesis": "SMA crossover signal; strong momentum",
  "backtest_id": "550e8400-e29b-41d4-a716-446655440001",
  "risk_evaluation_id": "550e8400-e29b-41d4-a716-446655440002",
  "updated_portfolio": {
    "current_cash": 869571.5,
    "current_nav": 1000000.0,
    "peak_nav": 1000000.0,
    "risk_off": false
  },
  "journal_entry_id": "550e8400-e29b-41d4-a716-446655440004"
}
```

**Errors (400 / 403 / 404 / 502 / 503):**

| Code | Meaning | Side Effect |
|---|---|---|
| `400` | Validation failed (bad quantity, missing thesis, limit gate rejected) | PaperOrder REJECTED row + journal entry (business rejections only) |
| `403` | Risk evaluation not approved (approved=false) | PaperOrder REJECTED row + journal entry; error includes decision, risk_score, order_id |
| `404` | Portfolio/asset/backtest/evaluation not found | No row persisted (pure input error) |
| `502` | Price unavailable (OHLCV fetch failed) | No state corrupted; client retries later |
| `503` | Database down | No state corrupted |

---

### SELL Order: Always Allowed

**Request:**

```json
{
  "portfolio_id": "550e8400-e29b-41d4-a716-446655440000",
  "side": "SELL",
  "symbol": "RELIANCE",
  "quantity": 5,
  "price_reference": 2900.0,
  "exit_reason": "Reversal on daily close",
  "backtest_id": "550e8400-... (optional)",
  "risk_evaluation_id": "550e8400-... (optional)"
}
```

**Validation (no approval check):**

1. **Portfolio exists** → 404 if not.
2. **Symbol exists** → 404 if not.
3. **Quantity is integer ≥ 1** → 400 if not.
4. **Exit reason is non-empty string** → 400 if missing/empty.
5. **Open position exists with sufficient quantity** → 400 if quantity exceeds open (oversell). Audit: REJECTED row + RISK_EVENT journal entry.

**Fill order immediately (always allowed):**

- Compute fill: `ref_price * (1 - 0.0005)` (SELL, adverse slippage).
- Compute transaction cost: `qty * fill_price * 0.0005` (exit-side cost).
- Credit cash: `qty * fill_price - cost`.
- Compute realized P&L for this sale: `(fill - avg_entry) * qty - cost`. (Entry-side cost already debited at BUY.)
- Update position:
  - Reduce quantity by the sold amount.
  - If quantity reaches 0: mark position `status=CLOSED`, persist accumulated realized P&L.
  - If quantity > 0: position remains open.
- Persist `PaperOrder` row: `status=FILLED`, `fill_price`, `filled_at=now`.
- Write journal FILL entry: `side=SELL`, `quantity`, `fill_price`, `cost`, `exit_reason`, `result` (realized P&L and position-closed flag).

**Response (201):**

```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440005",
  "portfolio_id": "550e8400-e29b-41d4-a716-446655440000",
  "symbol": "RELIANCE",
  "side": "SELL",
  "quantity": 5,
  "status": "FILLED",
  "fill_price": 2897.5,
  "filled_at": "2026-07-08T11:00:00Z",
  "exit_reason": "Reversal on daily close",
  "realized_pnl": 686.25,
  "position_closed": false,
  "updated_portfolio": {
    "current_cash": 884941.0,
    "current_nav": 1001431.25,
    "peak_nav": 1001431.25,
    "risk_off": false
  },
  "journal_entry_id": "550e8400-e29b-41d4-a716-446655440006"
}
```

---

## Position Management

### GET /paper/positions

List all open positions across all portfolios (or filtered).

**Query parameters:**

- `portfolio_id` (optional): filter by portfolio.
- `status` (optional): `"OPEN"` or `"CLOSED"`.

**Response (200):**

```json
{
  "count": 2,
  "positions": [
    {
      "id": "550e8400-...",
      "portfolio_id": "550e8400-...",
      "symbol": "RELIANCE",
      "quantity": 5,
      "avg_entry_price": 2852.85,
      "stop_loss_price": 2700.0,
      "last_price": 2897.5,
      "unrealized_pnl": 223.25,
      "accumulated_realized_pnl": 686.25,
      "status": "OPEN",
      "opened_at": "2026-07-08T10:30:00Z",
      "entry_date": "2026-07-08"
    },
    ...
  ]
}
```

All prices stored with 4-decimal precision; P&L with 2 decimals.

---

### GET /paper/portfolios/{id}/positions

Positions for a specific portfolio.

**Response:** Same as above, filtered to portfolio_id.

---

## Mark-to-Market and Risk-Off

### POST /paper/portfolios/{id}/mark-to-market

Fetch latest closes for all open positions, revalue, check drawdown.

**Request:** (empty body or no parameters)

**Processing:**

1. Fetch latest close for each open position (via OHLCV service, ~10-day cache).
2. If any fetch fails: 502 error; no state corrupted.
3. For each position: `unrealized_pnl = (latest_close - avg_entry) * qty`.
4. Recompute NAV: `cash + Σ(qty * latest_close)`.
5. Compute drawdown: `(peak_nav - nav) / peak_nav`.
6. If drawdown ≥ `0.08` (8%): set `portfolio.risk_off = true`. Write RISK_EVENT journal entry. **One-way latch: no auto-reset.**
7. Update `peak_nav` if `nav > peak_nav`.

**Response (200):**

```json
{
  "portfolio_id": "550e8400-...",
  "current_cash": 884941.0,
  "current_nav": 985000.0,
  "peak_nav": 1001431.25,
  "drawdown": 0.0163,
  "risk_off": false,
  "marked_at": "2026-07-08T12:00:00Z",
  "positions_marked": 2
}
```

**Errors:**

| Code | Meaning |
|---|---|
| `404` | Portfolio not found |
| `502` | Price unavailable for one or more positions |
| `503` | Database unreachable |

---

## Trade Journal

Append-only audit trail. All entries include timestamps.

| Entry Type | Written When | Mandatory Refs |
|---|---|---|
| `FILL` (BUY) | Paper order transitioned to FILLED (BUY side) | `paper_order_id`, `position_id`, `backtest_id`, `risk_evaluation_id`, `symbol`, `side`, `quantity`, `fill_price`, `transaction_cost`, `risk_summary` ("< decision> (score N)"), `thesis` |
| `FILL` (SELL) | Paper order transitioned to FILLED (SELL side) | `paper_order_id`, `position_id` (if still exists), `symbol`, `side`, `quantity`, `fill_price`, `transaction_cost`, `exit_reason`, `realized_pnl`, `position_closed` |
| `RISK_EVENT` | Risk-off latch activated (drawdown ≥ 8%) | `portfolio_id`, `event_type` ("risk_off_activated"), `description` |
| `RISK_EVENT` | Portfolio limit rejected a BUY order | `portfolio_id`, `paper_order_id` (REJECTED row), `event_type` ("limit_rejected"), `description` |

**Rejected order audit trail:** When a BUY is rejected (gate failure, risk veto, etc.), a
`PaperOrder` row with `status=REJECTED` is persisted **before** the HTTP error returns.
A corresponding `RISK_EVENT` or rejection journal entry references the rejected order id,
so it is fully auditable.

---

## Money and Accounting

All money is stored as floats, rounded for display:

- **Cash and NAV:** 2 decimals (₹).
- **Prices:** 4 decimals (₹).
- **P&L:** 2 decimals (₹).

**Mark-to-market rule:** Until the first `POST /mark-to-market`, positions are valued at
`avg_entry_price` (cost basis). After first mark, `last_price` becomes the mark. This is
a Phase 5 simplification; marking happens on demand, not automatically.

**NAV formula:** `cash + Σ(qty * mark)` where mark is `last_price` if marked, else `avg_entry_price`.

**Drawdown formula:** `(peak_nav - current_nav) / peak_nav`.

---

## API Endpoints (Complete List)

### Portfolio Management

- `POST /paper/portfolios` — Create portfolio (201).
- `GET /paper/portfolios` — List all (200).
- `GET /paper/portfolios/{id}` — Get one (200/404).

### Order Management

- `POST /paper/orders` — Create order (BUY/SELL); fill immediately (201, or 400/403/404/502/503 on error).
- `GET /paper/orders` — List all orders (optional `portfolio_id` filter).
- `GET /paper/orders/{id}` — Get one order.

### Positions

- `GET /paper/positions` — List all positions (optional `portfolio_id`, `status` filters).
- `GET /paper/portfolios/{id}/positions` — List positions for a portfolio.

### Mark-to-Market

- `POST /paper/portfolios/{id}/mark-to-market` — Revalue positions, check drawdown.

### Trade Journal

- `GET /paper/journal` — List all journal entries (optional `portfolio_id` filter); newest first.
- `GET /paper/portfolios/{id}/journal` — Journal for a portfolio.

---

## Typical 6-Step Workflow

```bash
# 1. Run and persist a backtest
curl -X POST http://localhost:8000/backtests/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": {...full strategy JSON...},
    "symbol": "RELIANCE",
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    "persist": true
  }'
# Returns: {"backtest_id": "550e8400-...", ...}

# 2. Evaluate the backtest's risk
curl -X POST http://localhost:8000/risk/evaluate \
  -H "Content-Type: application/json" \
  -d '{"backtest_id": "550e8400-..."}'
# Returns: {"risk_evaluation_id": "550e8400-...", "approved": true, "decision": "APPROVED", ...}

# 3. Create a paper portfolio
curl -X POST http://localhost:8000/paper/portfolios \
  -H "Content-Type: application/json" \
  -d '{"name": "My Fund"}'
# Returns: {"id": "550e8400-...", "current_cash": 1000000.0, ...}

# 4. Create a BUY order (fills immediately if all gates pass)
curl -X POST http://localhost:8000/paper/orders \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": "550e8400-...",
    "side": "BUY",
    "symbol": "RELIANCE",
    "quantity": 10,
    "price_reference": 2850.0,
    "thesis": "SMA crossover signal",
    "stop_loss_price": 2700.0,
    "backtest_id": "550e8400-...",
    "risk_evaluation_id": "550e8400-..."
  }'
# Returns: {"order_id": "550e8400-...", "status": "FILLED", "fill_price": 2852.85, ...}
# If risk_evaluation.approved=false: 403 with decision and risk_score

# 5. Mark positions to market
curl -X POST http://localhost:8000/paper/portfolios/550e8400-.../mark-to-market
# Returns: {"current_nav": ..., "drawdown": ..., "risk_off": ...}

# 6. View the audit trail
curl http://localhost:8000/paper/portfolios/550e8400-.../journal
# Returns: [{"type": "FILL", "side": "BUY", ...}, {"type": "RISK_EVENT", ...}, ...]
```

---

## Limitations (Phase 5)

1. **Immediate fills (Phase 5 deviation).** Orders fill at the price reference (or latest close)
   immediately upon creation, not at the next trading day's open. This is a Phase 5 simplification
   for rapid prototyping; Phase 6+ may restore next-open-fill semantics. Slippage and costs are
   the same as the backtester for comparability.

2. **Stop-loss stored but not auto-triggered.** The `stop_loss_price` is persisted on the position
   but not automatically monitored. Stops remain a stored constraint; manual SELL orders are the
   only way to exit in Phase 5. Phase 6 will add auto-triggered stop monitoring on daily closes.

3. **Risk-off is one-way without reset endpoint.** When drawdown ≥ 8%, `risk_off` latches true
   and blocks new BUY entries. No automatic recovery endpoint exists in Phase 5; the flag must be
   reset manually by a human review (a future endpoint). Documented limitation: risk-off is a
   defensive brake, not a recoverable state.

4. **No partial fills.** All orders are all-or-nothing: either the full quantity fills or the
   order is rejected. No order book, no partial execution.

5. **Single-currency (INR).** Prices and P&L are exclusively in Indian Rupees. Multi-currency
   support deferred.

6. **No real-order execution or broker connectivity.** This is the fundamental constraint: every
   order is simulated, every fill is in-memory, and no external broker connection exists.
   [non-goals.md](non-goals.md) documents the permanent exclusion of real execution.

---

## No Real Execution — Ever

**No code path in QuantCouncil may ever place, modify, or cancel a real order, connect to a
broker, or touch real money.** All paper orders are purely simulated; all fills happen in the
database and journal only. The disallowed actions listed in [non-goals.md](non-goals.md)
are permanently out of scope in every phase. Any pull request introducing broker connectivity
violates the project constitution.

Full details on non-goals and scope boundaries in [non-goals.md](non-goals.md).

---

## Testing

From the repo root:

```
pytest
```

Paper trading tests (Phase 5):

- 37 new tests in `apps/api/tests/` covering order creation, fill simulation, position
  tracking, NAV calculation, drawdown, risk-off latch, journal entries, and error scenarios.
- All tests use SQLite in-memory for speed; all prices/costs/P&L use exact-arithmetic
  assertions (no floating-point tolerance slop).
- Total: 403 tests passing repo-wide (was 366; +37 paper tests).
