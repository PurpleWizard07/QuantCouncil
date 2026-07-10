# QuantCouncil Backtesting Engine (Phase 3)

The authoritative reference for the Phase 3 Strategy Lab: strategy schema validation, the
signals interpreter, the deterministic backtester, the metrics set, and the stateless backtest
API endpoints. Component boundaries are defined in [architecture.md](architecture.md); the
delivery history and deviations from the original plan are in
[development-roadmap.md](development-roadmap.md); the underlying engineering decisions are
logged in [assumptions.md](assumptions.md). The strategy definition format itself is specified
in [strategy-format.md](strategy-format.md).

Everything in this layer is deterministic Python (pandas/numpy). **No LLM touches, adjusts, or
produces any number here** — every metric on every backtest comes from
`packages/quant_engine/quant_engine/metrics.py` and nowhere else.

## Strategy Definitions and Validation

`quant_engine.strategy.validate_strategy(definition)` is the single schema gate. It accepts a
plain dict (e.g. loaded from JSON), validates it strictly against
[strategy-format.md](strategy-format.md) v1, and returns a normalized deep copy that downstream
code trusts without re-validating. Any violation raises `StrategyValidationError` naming the
offending key/value and the allowed options.

- **Strict:** unknown top-level keys, condition/target keys, operators, indicators, and
  combinator keys are all rejected — nothing is silently ignored.
- **`stop_loss.type: "atr"` is explicitly rejected** with a "reserved for a later phase"
  message; only `"percent"` is valid in v1.
- **Two optional top-level fields (Phase 3 additions):** `max_holding_days` (integer >= 1;
  time-based exit) and `costs` (`{transaction_cost_pct, slippage_pct}`, each in `[0, 1)`;
  per-strategy overrides of the backtest config — see [Costs](#slippage-and-transaction-costs)).
- **Normalization:** numeric fields are coerced to `float`/`int`; `target.multiplier` defaults
  to `1.0`. Universe membership against the NIFTY 50 list is deliberately **not** checked here —
  that lookup belongs to the API layer, which owns the universe data.

The three initial strategies are defined verbatim as code constants in
`quant_engine.strategies` — `SMA_CROSSOVER`, `RSI_MEAN_REVERSION`, `VOLUME_BREAKOUT` — with
`get_builtin_strategies()` returning deep copies (in that order). They use the five-symbol
sample universes from the doc; expanding to the full NIFTY 50 list is the API/user layer's
concern.

## Signals Interpreter

`quant_engine.signals.generate_signals(df, rules)` turns an OHLCV contract frame plus a
strategy definition into deterministic entry/exit signals. It validates `rules` via
`validate_strategy` first, then evaluates the condition trees (`all`/`any` combinators, nested
arbitrarily) with the four v1 operators (`crosses_above`, `crosses_below`, `greater_than`,
`less_than`) over the v1 indicators (`sma`, `ema`, `rsi`, `volume_sma`, `close`, `volume`,
`highest_close`). All indicator math is delegated to `quant_engine.indicators` — the
interpreter never reimplements formulas.

Returned frame: a copy of `df` with these added columns.

| Column | Meaning |
|---|---|
| `entry_signal` | bool, no NaN — entry tree true on this bar. |
| `exit_signal` | bool, no NaN — exit tree true on this bar. |
| `stop_loss_price` | `close * (1 - stop_loss.value)` on entry bars, NaN elsewhere. **Indicative only** — entries fill at the *next* bar's open, so the backtester recomputes the real stop from the actual fill price. This column exists for signal auditability, not as the authoritative stop. |
| Indicator audit columns | `f"{indicator}_{window}"` (e.g. `sma_20`, `rsi_14`, `highest_close_20`); a multiplied target additionally gets `f"{base}_x{multiplier:g}"` (e.g. `volume_sma_20_x1.5`) holding the already-scaled series that was compared. |

Semantics guarantees:

- **No lookahead.** Signals on bar `t` use only data through bar `t`; crosses compare against
  `shift(1)`, never a negative shift.
- **NaN comparisons are False.** In the indicator warm-up region, conditions evaluate to
  `False`, not NaN — the signal columns are always clean bools.
- **`highest_close` shift lives in the interpreter (Phase 2 open thread — resolved).**
  [strategy-format.md](strategy-format.md) defines `highest_close(window)` over the prior
  `window` bars *excluding* the current bar; the raw indicator function
  `indicators.highest_close` is an inclusive rolling max. The interpreter bridges the gap by
  computing `indicators.highest_close(close, window).shift(1)` — so a breakout condition
  `close greater_than highest_close(20)` can actually fire on a new 20-day closing high. The
  `highest_close_<window>` audit column stores the shifted (exclusive) series.
- **Target multiplier** is supported per the doc: `volume greater_than volume_sma(20) x 1.5`
  compares against the scaled series.

## Backtester

`quant_engine.backtest.Backtester` simulates one symbol's OHLCV history against one strategy
definition. `run(df, rules, symbol="")` validates the frame, slices it to the configured date
window, generates signals, and delegates to `run_from_signals(signals_df, rules, symbol="")`,
which contains the entire simulation (and is what the engine tests drive directly with
hand-built signal frames).

### Configuration (`BacktestConfig`)

| Field | Default | Meaning |
|---|---|---|
| `initial_capital` | `1_000_000.0` | Starting capital, ₹10,00,000 — matches the paper portfolio rules. |
| `start_date` / `end_date` | `None` | Inclusive simulation window; `None` = full available data. |
| `next_day_open_fills` | `True` | The only supported mode; `False` raises `NotImplementedError`. |
| `slippage_pct` | `0.0005` | 0.05% per fill, always adverse (buys fill higher, sells fill lower). |
| `transaction_cost_pct` | `0.0005` | 0.05% of notional per side (charged on entry and exit). |
| `max_allocation_pct` | `0.10` | Max 10% of current equity committed to a single trade. |

### Execution model

- **Signal on close of bar t → fill at open of bar t+1.** An entry signal on the **last** bar
  is ignored (there is no next open). Entry signals while a position is open are ignored.
- **One open position max** (no pyramiding), **whole shares only**, **long-only**, **no
  leverage** (entries are constrained by available cash), **no partial fills**, **no intraday
  granularity** beyond the gap-aware stop check below.
- **Entry fill price** = `open[t+1] * (1 + slippage_pct)`.
- **Stop price** = `entry_fill_price * (1 - stop_loss.value)`, fixed for the life of the trade
  and recomputed from the **actual** fill — never taken from the indicative `stop_loss_price`
  column.
- **Exit priority per bar**, for an open position:
  1. **Scheduled next-open exits first.** If `exit_signal` was true on the previous bar (or
     the max-holding rule triggered there), sell at this bar's open:
     `open * (1 - slippage_pct)`, `exit_reason` `"signal"` or `"max_holding"`.
  2. **Gap-aware intraday stop check.** If `open <= stop_price` (gap down), exit at
     `open * (1 - slippage_pct)`; else if `low <= stop_price`, exit at
     `stop_price * (1 - slippage_pct)`. Reason `"stop_loss"`. The stop can trigger on the
     entry fill bar itself (enter at the open, low pierces the stop the same day).
  3. **Max holding.** If the strategy sets `max_holding_days` H and the position has been held
     H bars as of this bar's close (the entry fill bar counts as day 1), an exit is scheduled
     for the next bar's open, reason `"max_holding"`.
  4. **Exit signal.** `exit_signal` true on this bar while holding schedules an exit at the
     next open, reason `"signal"`.
- **End of data:** a position still open after the last bar is force-closed at the **last
  bar's close** `* (1 - slippage_pct)` with transaction cost, reason `"end_of_data"` — a
  documented v1 simplification so metrics always reflect fully realized trades. The equity
  curve's final point reflects the post-force-close cash.
- **Equity curve:** marked to market at every bar's close — `equity[t] = cash + qty *
  close[t]`. A flat account produces a flat curve at `initial_capital`.

### Position sizing

Evaluated at fill time with `equity = cash` (the account is flat immediately before an entry).
The traded quantity is the **minimum of three whole-share limits** — whichever binds:

| Limit | Formula |
|---|---|
| Risk (`risk_percent` sizing) | `floor(position_sizing.value * equity / (entry_fill_price * stop_loss.value))` — risking at most `value` of equity if the stop is hit. |
| Allocation cap | `floor(max_allocation_pct * equity / entry_fill_price)`. |
| Cash | largest `qty` with `qty * fill * (1 + transaction_cost_pct) <= cash`. |

If the result is `< 1` share, **no trade** happens on that bar (skip silently, stay flat).

### Slippage and transaction costs

Every fill pays `slippage_pct` in the adverse direction and `transaction_cost_pct` of its
notional. Cash flow: entry `cash -= qty*fill + qty*fill*transaction_cost_pct`; exit
`cash += qty*exit_fill - qty*exit_fill*transaction_cost_pct`. A strategy definition's optional
`costs` object overrides `transaction_cost_pct` / `slippage_pct` (each independently) for that
run; `max_allocation_pct` is **not** strategy-overridable.

### Trade record schema

One dict per closed round trip in `BacktestResult.trades`:

| Field | Meaning |
|---|---|
| `symbol` | The `symbol` argument if given; else `universe[0]` when the universe has exactly one symbol; else `"?"`. |
| `entry_date` / `exit_date` | Taken as-is from the frame's `date` column (typically `pandas.Timestamp`). |
| `entry_price` / `exit_price` | Actual fill prices, slippage included. |
| `quantity` | Whole shares. |
| `pnl` | INR, **net of both sides' transaction costs**. |
| `return_pct` | `pnl / (entry_price * quantity)`. |
| `holding_days` | Bars held, entry fill bar = 1. |
| `exit_reason` | `"signal"`, `"stop_loss"`, `"max_holding"`, or `"end_of_data"`. |
| `entry_cost` / `exit_cost` | Transaction cost of each leg, INR. |

## Metrics

`quant_engine.metrics` implements the full contract set as pure functions;
`metrics.compute_all(equity_curve, trades, position_flags)` is the single call the backtester
uses (no metric math is ever inlined elsewhere). `TRADING_DAYS_PER_YEAR = 252`.

| Metric | Definition | Conventions / edge cases |
|---|---|---|
| `total_return` | `last / first - 1` over the equity curve. | 0.0 for empty curve or `first == 0`. |
| `cagr` | `(last / first) ** (252 / n_periods) - 1`, `n_periods = len(curve) - 1` bars. | 0.0 if `n_periods < 1` or `first <= 0`. |
| `max_drawdown` | `max(1 - equity / running_max)`, positive fraction. | 0.0 for empty or monotonically non-decreasing curves. |
| `win_rate` | winners / total closed trades. | 0.0 with no trades. |
| `avg_win` / `avg_loss` | Mean PnL of winners / losers (INR). | 0.0 when none; `avg_loss` is negative when losers exist. |
| `profit_factor` | gross profit / abs(gross loss). | **`inf` when there are wins but zero losses** (documented choice); 0.0 when there are neither wins nor losses. |
| `num_trades` | Count of closed round trips. | — |
| `exposure_time` | Mean of the per-bar position flags (fraction of bars with an open position). | 0.0 for empty. |
| `sharpe` | Sharpe-like ratio from the equity curve's daily returns: `(mean - rf/252) / std(ddof=1) * sqrt(252)`, **rf = 0 in v1** (hence "Sharpe-like"). | 0.0 with fewer than 2 returns or zero/NaN standard deviation (e.g. a flat curve). |
| `best_trade` / `worst_trade` | Max / min trade PnL (INR). | 0.0 with no trades. |

`BacktestResult` carries all of the above plus `starting_capital` (the run's
`initial_capital`), `final_equity` (last equity point, after any end-of-data close),
`equity_curve` (DataFrame `[date, equity]`), and `trades`. The zero-trade case is fully
defined: all trade metrics 0.0, `num_trades = 0`, flat equity curve — never a crash.

## API Endpoints (Phase 3 + Phase 3.5)

The Strategy Lab surface in `apps/api` (port 8000). Phase 3 endpoints were stateless; Phase 3.5
adds persistence and retrieval.

| Endpoint | Behavior |
|---|---|
| `GET /strategies` | The three code-defined built-in templates plus any persisted strategies: `{"count": N, "strategies": [...]}`. Each has `source: "builtin"` or `source: "persisted"`. No database dependency for builtins (degraded return if DB down). |
| `POST /strategies` | (Phase 3.5) Create a custom strategy. Body: full strategy JSON per [strategy-format.md](strategy-format.md). Returns `{id, name, status, source: "persisted", created_at}` on `201`. Name conflicts with builtins or existing persisted rows → `409`. |
| `POST /backtests/run` | Body `{strategy?, strategy_id?, symbol, start_date?, end_date?, persist?}`. Runs a strategy over the symbol's OHLCV history (served through the Phase 2 cached connector). Default `persist=false` returns results with `"persisted": false` (stateless Phase 3 behavior). `persist=true` stores run in `backtest_runs`, writes artifacts to disk, and returns `backtest_id` with `"persisted": true`. See [persistence.md](persistence.md) for detail. |
| `GET /backtests/{id}` | (Phase 3.5) Retrieve a persisted run: metadata, all 14 metrics, equity_curve, trades, artifact paths. Returns full payload with `"persisted": true`. `404` if not found; `500` if artifact files are missing on disk. |

Example — `strategy` takes the **full strategy JSON** (copy a definition from
`GET /strategies`, dropping the `source`/`id`/`status`/`created_at` metadata keys), or pass
`strategy_id` for a persisted strategy instead:

```
curl -X POST http://localhost:8000/backtests/run \
  -H "Content-Type: application/json" \
  -d '{"strategy": <full strategy JSON per strategy-format.md>, "symbol": "RELIANCE", "start_date": "2023-01-01", "end_date": "2024-12-31"}'
```

Full persistence design (strategy storage, backtest runs, artifact management, retrieval) is documented in
[persistence.md](persistence.md).

Running a backtest from Python directly:

```python
from data_connectors import CachedConnector, OHLCVCache, get_connector
from quant_engine.backtest import Backtester
from quant_engine.strategies import get_builtin_strategies

df = CachedConnector(get_connector("yfinance"), OHLCVCache()).get_ohlcv(
    "RELIANCE", "2023-01-01", "2024-12-31"
)
rules = get_builtin_strategies()[0]          # SMA crossover
result = Backtester().run(df, rules, symbol="RELIANCE")
print(result.total_return, result.num_trades, result.final_equity)
```

## Limitations (v1, deliberate)

1. **Single symbol per run.** The backtester simulates one symbol's history at a time;
   iterating a strategy's universe is the API/user layer's job. Portfolio-level,
   multi-position simulation belongs to the paper trading engine (Phase 6).
2. **No strategy editing or versioning.** Persisted strategies are immutable; create a new one
   with a different name to modify. See [persistence.md](persistence.md) for detail.
3. **Unadjusted prices** (Phase 2 data layer, `auto_adjust=False`): splits/bonuses appear as
   price jumps and will distort backtests that span them; flagged by validation warnings,
   never corrected in v1.
4. **Survivorship bias:** the universe is a point-in-time manual NIFTY 50 snapshot; long
   histories are biased toward survivors.
5. **Next-day-open fills only**; the daily-bar stop check is gap-aware but otherwise has no
   intraday resolution — a bar that trades through the stop intra-day fills at the stop price
   (or the open on a gap), which is optimistic relative to real fast markets.
6. **End-of-data force close** realizes any open position at the last close, so
   right-edge-of-history results include a trade that a live portfolio would still be holding.

## Why There Is No Real Execution

QuantCouncil is a **paper-trading-only learning lab** — by constitution, not by omission. The
backtester and every later phase simulate; no broker API exists anywhere in the codebase, and
the disallowed execution actions enumerated verbatim in [non-goals.md](non-goals.md)
(`place_real_order`, `connect_broker_account`, `auto_trade_real_money`, ...) are permanently
out of scope in every component, tool surface, and phase. The deterministic engine documented
here is the **only** source of numbers: LLM agents (Phase 5) may read, summarize, and debate
these outputs, but they never compute, adjust, or invent a metric. Nothing this engine
produces is financial advice.

## Running the Tests

From the repo root (uses `pytest.ini`; `testpaths = apps/api packages`):

```
.venv/Scripts/python.exe -m pytest -q        # or plain `pytest` inside the activated venv
```

Phase 3 engine suites under `packages/quant_engine/tests`: `test_strategy.py` (schema
validation), `test_signals.py` (interpreter semantics, no-lookahead, the `highest_close`
shift), `test_backtest.py` (simulation semantics driven through `run_from_signals` with
hand-built signal frames — fills, stops, sizing bounds, costs, edge cases), `test_metrics.py`
(hand-computed metric values and edge conventions), plus the Phase 2 indicator and foundation
tests — 183 tests in the package (including `test_integration.py` end-to-end runs of all
three built-in strategies). The repo-wide suite (310 tests) runs offline; no test touches the
network.
