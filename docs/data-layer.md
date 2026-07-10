# QuantCouncil Data Layer (Phase 2)

The authoritative reference for the Phase 2 data layer: the market-data source, the symbol
universe, the connector interface, validation, the local cache, the indicator set, and the
market-data API endpoints. Component boundaries are defined in
[architecture.md](architecture.md); the delivery history and deviations from the original plan
are in [development-roadmap.md](development-roadmap.md); the underlying engineering decisions
are logged in [assumptions.md](assumptions.md).

Everything in this layer is deterministic Python (pandas/numpy/DuckDB). No LLM touches, adjusts,
or produces any number here.

## Active Data Source: yfinance

- **Provider:** Yahoo Finance via the free `yfinance` package — no paid data anywhere in v1
  (local-first principle, see [non-goals.md](non-goals.md)).
- **Scope:** daily OHLCV bars only (`timeframe="1d"`); any other timeframe is rejected with
  `ValueError`.
- **Symbol mapping:** QuantCouncil stores plain NSE symbols internally (e.g. `RELIANCE`,
  `M&M`); the connector maps them to Yahoo tickers by appending `.NS`
  (`data_connectors.universe.to_yfinance_symbol`).
- **Unadjusted prices (documented v1 simplification):** the connector calls `yfinance` with
  `auto_adjust=False` and keeps raw OHLC as reported. Splits and bonus issues therefore appear
  as sharp price jumps on the ex-date instead of a smoothly adjusted series.
  `validate_ohlcv_report` flags such jumps as warnings (see [Validation](#validation) below).
- **Fetch behavior:** the requested end date is inclusive (the connector compensates for
  yfinance's exclusive-end convention), MultiIndex columns are flattened, duplicates and NaN
  rows are dropped, rows are sorted ascending by date. Empty or failed fetches raise
  `DataFetchError` — malformed data is never silently passed through.

**OpenBB status:** `OpenBBConnector` is registered in the factory under the name `"openbb"` so
the connector interface is demonstrably swappable, but it is an **inactive placeholder** —
calling it raises `NotImplementedError`. Integration is deferred deliberately: the OpenBB SDK's
install footprint is not worth the cost while yfinance covers the entire Phase 2 scope.

## Symbol Universe

**Source of truth:** `data/nifty50_symbols.json` — 50 records with the shape:

```json
{
  "as_of": "2025-03",
  "source": "manual NSE snapshot ...",
  "symbols": [
    {"symbol": "RELIANCE", "name": "...", "exchange": "NSE", "sector": "...", "yfinance_symbol": "RELIANCE.NS"}
  ]
}
```

`data_connectors.universe` loads this JSON at import time and derives:

| Export | Meaning |
|---|---|
| `NIFTY50` | The 50 constituents as plain NSE symbols, in file order. |
| `get_universe()` | The full metadata records (symbol, name, exchange, sector, yfinance_symbol); returns defensive copies. |
| `YFINANCE_SUFFIX` / `to_yfinance_symbol()` | `.NS` suffix handling for Yahoo Finance. |

**Provenance and refresh policy:** the JSON is a point-in-time manual snapshot from publicly
available NSE index data around the March 2025 index review. It is refreshed **manually** —
there is no automatic reconstitution. Backtests over long histories therefore carry
**survivorship bias**; this is an accepted limitation of the v1 learning lab. When the index is
reconstituted or a symbol is renamed, the JSON file is the single place to update.

**Path resolution:** the module locates the JSON by walking up from its own source file looking
for `data/nifty50_symbols.json` (up to 8 parent directories), so it works from any working
directory within the monorepo checkout. It is **not** designed to work as a standalone wheel
install outside the monorepo — the data file would not be bundled. Accepted v1 simplification
for a personal, local-first project.

Sector labels in the JSON are best-effort descriptive tags for display and grouping, not an
official NSE/GICS classification.

## Connector Interface

Every data source implements the abstract `OHLCVConnector` contract in `data_connectors.base`:

- **`get_ohlcv(symbol, start_date, end_date, timeframe="1d")`** — the public entry point, and
  the only method downstream code (quant_engine, the cache, the API) should call. It validates
  inputs (ISO date strings or `date` objects; `start <= end`; daily-only), delegates to the
  provider, and routes the result through `validate_ohlcv` before returning.
- **`fetch_daily(symbol, start, end)`** — the thin provider-specific hook each connector
  implements. Never call it directly from outside the package.
- **`get_connector(name="yfinance")`** — the factory in `data_connectors.registry`. Registered
  names: `"yfinance"` (active) and `"openbb"` (inactive placeholder). Depending on the factory
  rather than a concrete class is what keeps the data source swappable.

**DataFrame contract** (guaranteed by `get_ohlcv`, assumed by everything downstream):

- Columns exactly `[date, open, high, low, close, volume]`.
- `date` tz-naive, ascending, no duplicates.
- No NaN rows.

**Failure modes** are distinguished by exception type: `DataFetchError` (the provider failed —
network, invalid/delisted symbol, empty response), `DataValidationError` (the provider returned
data that violates the contract), and `CacheError` (the local cache detected an internal
inconsistency, e.g. a filename-sanitization collision).

## Validation

`data_connectors.validation.validate_ohlcv(df, min_rows=None)` enforces the contract with
**hard checks** (each failure raises `DataValidationError`):

| Check | Rule |
|---|---|
| Columns | All of `[date, open, high, low, close, volume]` present; extras dropped from the result. |
| Dates | Parseable, coerced tz-naive; **duplicate dates are a hard error**, not silently deduplicated. |
| Numerics | OHLC and volume coerced numeric; rows with any resulting NaN are dropped (count logged). |
| Volume | `volume >= 0`. |
| Bar geometry | `high >= low`; `high >= open, close` and `low <= open, close` within a `1e-6` relative tolerance (scaled to price magnitude) for floating-point noise. |
| Ordering | Result sorted ascending by date. |
| `min_rows` | If given, raises when fewer rows remain after cleaning (lookback enforcement). |

`validate_ohlcv_report(df, min_rows=None)` performs the same hard checks and additionally
returns a list of **non-fatal warning strings**, including single-day close-to-close moves
larger than 40% flagged as possible unadjusted corporate actions (the flip side of
`auto_adjust=False`). Warnings never fail a fetch — a genuine 40% move can also be legitimate
news.

## Local Cache (DuckDB + Parquet)

`data_connectors.cache` provides transparent local caching so repeat requests never re-hit the
provider:

- **Location:** `data/processed/ohlcv/`, one Parquet file per symbol.
- **Filenames:** Windows-safe — every non-alphanumeric character is replaced with `_`
  (`M&M` → `M_M.parquet`). Because that mapping is many-to-one in theory, the true symbol is
  also stored inside the file and verified on every read/write; a mismatch raises `CacheError`.
- **Reads:** date-range slices are queried through DuckDB directly against the Parquet file.
- **Coverage heuristic (documented v1 simplification):** a cached file "covers" a requested
  `[start, end]` range iff `min(cached date) <= start` and `max(cached date) >= end`. Exact
  trading-calendar coverage is not tracked, so a requested `start` falling on a non-trading day
  earlier than the first cached bar can under-cover and trigger a redundant re-fetch. That is an
  accepted asymmetry, not a correctness bug — a redundant re-fetch merges harmlessly back into
  the same file.
- **`CachedConnector(connector, cache, refresh=False)`:** exposes the same
  `get_ohlcv(...)` signature as any connector (drop-in replacement). On a covered request the
  wrapped connector is never called; on a miss it fetches, merges into the cache, and returns
  the freshly fetched slice. `refresh=True` forces a re-download and merge regardless of
  coverage (useful for refreshing recent days, which providers can revise).
- **Merges:** existing and new rows are concatenated, duplicate dates dropped keeping the
  newest fetch, sorted ascending, and written **atomically** (temp file, then OS-level
  replace) so a crash mid-write can never leave a truncated cache file.

Typical usage:

```python
from data_connectors import CachedConnector, OHLCVCache, get_connector

connector = CachedConnector(get_connector("yfinance"), OHLCVCache())
df = connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-12-31")
```

## Indicators (quant_engine)

`packages/quant_engine/quant_engine/indicators.py` is fully implemented and tested. All
functions are pure, deterministic pandas over a Series with an ascending tz-naive date index;
they preserve the input index, never mutate inputs, and reject `window < 1` with `ValueError`.

| Function | Definition | Warm-up (leading NaN) |
|---|---|---|
| `sma(series, window)` | Rolling arithmetic mean. | First `window - 1` values |
| `ema(series, window)` | `ewm(span=window, adjust=False)`, i.e. `alpha = 2/(window+1)`. | First `window - 1` values (masked — see below) |
| `rsi(series, window=14)` | Wilder's RSI. | First `window` values |
| `atr(high, low, close, window=14)` | Wilder's ATR over True Range = `max(high-low, abs(high-prev_close), abs(low-prev_close))`. | First `window` values |
| `rolling_high(series, window)` | Rolling max (pass highs for Donchian-style levels). | First `window - 1` values |
| `rolling_low(series, window)` | Rolling min. | First `window - 1` values |
| `volume_sma(series, window)` | Rolling mean of volume (delegates to `sma`). | First `window - 1` values |
| `highest_close(series, window)` | Rolling max of close (delegates to `rolling_high`). | First `window - 1` values |
| `daily_returns(series)` | Simple close-to-close `pct_change`. | First value |
| `volatility(series, window=20, annualize=True, periods_per_year=252)` | Rolling std of daily returns, times `sqrt(periods_per_year)` when annualized. | First `window` values (needs `window + 1` prices) |

Conventions (see [assumptions.md](assumptions.md) for rationale):

- **Warm-up NaN:** every indicator emits NaN until it has a full lookback window, so no value
  is ever computed from partial data.
- **EMA masking:** a recursive EMA is technically defined from the first bar (seeded with the
  first observation), but the first `window - 1` values are explicitly masked to NaN for
  cross-indicator consistency.
- **Wilder smoothing:** RSI and ATR share one smoothing primitive —
  `ewm(alpha=1/window, adjust=False)` (full-history recursion), not the classic
  simple-average-seed variant. Values are internally consistent but may differ slightly from
  third-party TA libraries. RSI boundary cases are explicit: zero-loss windows → 100, zero-gain
  windows → 0, flat windows → 50 (no division errors).
- **Volatility takes PRICES:** `volatility` receives the price series and computes daily
  returns internally — do not pass a returns series. The annualization factor reuses
  `quant_engine.metrics.TRADING_DAYS_PER_YEAR` (252).

`signals`, `backtest`, and `metrics` in `quant_engine` were implemented in Phase 3 — see
[backtesting-engine.md](backtesting-engine.md).

## API Endpoints

The Phase 2 market-data surface in `apps/api` (port 8000):

| Endpoint | Behavior |
|---|---|
| `GET /assets` | The universe from `get_universe()`: `{"count": 50, "assets": [...]}`. Served from the JSON file — no database dependency; Postgres asset seeding is deferred to Phase 3. |
| `GET /assets/{symbol}/ohlcv` | Daily OHLCV for one symbol. Query params: `start_date` (default: end minus 365 days), `end_date` (default: today), `timeframe` (default `"1d"`; anything else → `400`). Unknown symbol (case-insensitive lookup against the universe) → `404`; provider failure (`DataFetchError`) → `502`. Served through `CachedConnector`, so repeat calls hit the Parquet cache. |
| `GET /assets/{symbol}/indicators` | Same params and error semantics as the OHLCV endpoint. Returns a fixed default indicator set: `sma_20`, `sma_50`, `ema_20`, `rsi_14`, `atr_14`, `volume_sma_20`, `rolling_high_20`, `rolling_low_20`, `daily_returns`, `volatility_20`. NaN warm-up values are serialized as `null`. |

**No lookback pre-fetch (v1):** the indicators endpoint computes over exactly the requested
date range, so the warm-up region at the start of the response is `null` (e.g. the first 49
values of `sma_50`). Fetching extra history before `start_date` to fill the warm-up is a
possible later refinement.

## Running the Tests

From the repo root (uses `pytest.ini`; `testpaths = apps/api packages`):

```
.venv/Scripts/python.exe -m pytest -q        # or plain `pytest` inside the activated venv
```

Data-layer test suites: `packages/data_connectors/tests` (62 tests) and
`packages/quant_engine/tests` (58 Phase 2 indicator/foundation tests; the package suite has
grown to 183 with Phase 3 — see [backtesting-engine.md](backtesting-engine.md)). The repo-wide
suite has 310 tests (Phase 3.5 adds persistence tests). All yfinance interaction is mocked —
**no test ever touches the network**, so the suite runs offline and deterministically.

## Phase 2 Limitations

Known, deliberate gaps — tracked for Phase 3 and beyond:

1. **Database ingestion and asset seeding are now in Phase 3.5.** The API serves the universe
   from JSON and OHLCV from the Parquet cache (Phase 2 design). DB population happens through
   Alembic migrations, `seed_assets.py`, and the `ingest_ohlcv.py` CLI — all documented in
   [persistence.md](persistence.md).
2. **No lookback pre-fetch on the indicators endpoint.** Warm-up `null`s appear at the start of
   every response window.
3. **Unadjusted prices** (`auto_adjust=False`): splits/bonuses appear as price jumps; only
   flagged, never corrected, in v1.
4. **Cache coverage heuristic edge case:** min/max-date containment can under-cover when a
   requested boundary falls on a non-trading day, causing a harmless redundant re-fetch.
5. **Docker image excludes the data layer.** The `apps/api` Dockerfile currently installs only
   the API's own requirements and copies only `apps/api/` — the `packages/*` code and
   `data/nifty50_symbols.json` are not in the image, so the new endpoints work in local dev
   but not yet in the full-Docker quickstart.
