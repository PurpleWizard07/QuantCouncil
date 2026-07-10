# QuantCouncil Development Roadmap

Phased delivery plan for QuantCouncil. Each phase lists its deliverables and the acceptance
criteria that gate the next phase.

**Gating rule: do not start a phase until the previous phase's acceptance criteria pass.**

Scope, exclusions, and hard rules are defined in [architecture.md](architecture.md) and
[non-goals.md](non-goals.md). Nothing in this roadmap may introduce a non-goal.

Strategies move through a fixed lifecycle that the phases below progressively enable:
`DRAFT -> BACKTESTED -> RISK_EVALUATED -> RISK_APPROVED -> PAPER_TRADING -> WATCHLIST -> RETIRED`
(exact strings; state machine defined in [strategy-format.md](strategy-format.md)).

---

## Phase 1 — Foundation (COMPLETED)

**Deliverables**

- Monorepo layout: `apps/web`, `apps/api`, `packages/quant_engine`, `packages/risk_engine`,
  `packages/agents`, `packages/data_connectors`, `packages/mcp_server`, `infra/`, `data/`, `docs/`.
- FastAPI skeleton (`apps/api`) with a health endpoint and CORS for `http://localhost:3000`.
- Next.js 15 dashboard shell (`apps/web`) on port 3000.
- PostgreSQL 16 via Docker Compose in `infra/`; `infra/migrations/` holds a README placeholder
  (Alembic arrives in Phase 3; originally slated for Phase 2 — see the Phase 2 deviation note).
- SQLAlchemy 2.x typed models for all 10 tables plus a `create_all` init script.
- This documentation set (architecture, roadmap, non-goals, paper-trading design, strategy
  format, risk policy, assumptions).

**Acceptance criteria**

- `docker compose up` in `infra/` starts Postgres 16 on port 5432 with the canonical
  environment variables.
- The init script creates exactly the 10 contract tables (`assets`, `ohlcv_daily`,
  `strategy_definitions`, `backtest_runs`, `risk_evaluations`, `agent_decisions`,
  `paper_portfolios`, `paper_orders`, `paper_positions`, `trade_journal`).
- `GET /health` on port 8000 returns a healthy response.
- The dashboard shell renders at `http://localhost:3000` and can call the API health endpoint
  cross-origin.
- `pytest` passes from the repo root (`testpaths = apps/api packages`).
- All six constitution docs plus [assumptions.md](assumptions.md) exist in `docs/`.

---

## Phase 2 — Data Layer (COMPLETED)

> **Scope deviation from the original plan.** The project owner's Phase 2 specification
> superseded the roadmap as originally written: Alembic migrations, Postgres `ohlcv_daily`
> ingestion + asset seeding, and the ingestion CLI were **deferred to Phase 3**, and the
> indicator set was **pulled forward from Phase 3 into Phase 2**. Phase 2 as delivered is a
> file-and-cache data layer (JSON universe, validated connector, Parquet/DuckDB cache, API
> endpoints) with no database writes. The full delivered design is documented in
> [data-layer.md](data-layer.md).

**Deliverables (as delivered)**

- NIFTY 50 universe as data: `data/nifty50_symbols.json` (manual NSE snapshot, `as_of`
  2025-03) is the source of truth; `data_connectors.universe` loads it and exposes `NIFTY50`,
  `get_universe()`, and `to_yfinance_symbol()` (`.NS` suffix).
- Abstract `OHLCVConnector` contract with `get_ohlcv(symbol, start_date, end_date,
  timeframe="1d")` as the public entry point, plus a `get_connector(name)` factory
  (`"yfinance"` active; `"openbb"` registered as an inactive placeholder).
- yfinance connector: raw unadjusted prices (`auto_adjust=False`, documented simplification),
  inclusive end dates, response cleaning, `DataFetchError` on empty/failed fetches.
- Validation pipeline: `validate_ohlcv` hard checks (columns, tz-naive dates, duplicate dates,
  numeric OHLC, volume >= 0, bar geometry with tolerance, sorting, NaN-row drops) and
  `validate_ohlcv_report` warnings (>40% single-day moves flagged as possible corporate
  actions).
- DuckDB + Parquet local cache under `data/processed/ohlcv/` (one file per symbol,
  Windows-safe filenames, atomic writes) with `CachedConnector` for transparent caching and
  `refresh=True` forced re-download.
- Indicator set in `packages/quant_engine` (pulled forward from Phase 3): `sma`, `ema`, `rsi`,
  `atr`, `rolling_high`, `rolling_low`, `volume_sma`, `highest_close`, `daily_returns`,
  `volatility` — all deterministic pandas with documented warm-up-NaN conventions.
- API endpoints in `apps/api`: `GET /assets`, `GET /assets/{symbol}/ohlcv`,
  `GET /assets/{symbol}/indicators` (fixed default indicator set, NaN serialized as `null`).

**Deferred to Phase 3.5** (moved, not dropped; originally deferred "to Phase 3", then moved
again when Phase 3 was split — see the Phase 3 deviation note)

- Alembic migrations replacing the `create_all` bootstrap; `infra/migrations/` becomes real.
- Postgres ingestion into `ohlcv_daily` and asset seeding for all 50 NIFTY constituents.
- Ingestion CLI (fetch, validate, load, refresh).

**Acceptance criteria (met)**

- `data/nifty50_symbols.json` holds 50 records; `get_universe()` returns all of them and
  `GET /assets` serves `{"count": 50, ...}` with no database dependency.
- `get_ohlcv` returns contract-valid frames (exact columns, ascending tz-naive dates, no
  duplicates, no NaN rows) for any universe symbol; contract violations raise instead of
  passing through.
- Repeat requests for a cached range are served from the Parquet cache without calling the
  provider; cache merges are idempotent (no duplicate dates) and written atomically.
- Duplicate dates in provider data are a hard validation error; >40% single-day moves are
  surfaced as warnings by `validate_ohlcv_report`.
- Indicator unit tests pass against independently hand-computed known values.
- `pytest` passes from the repo root with **no network access** (all yfinance interaction
  mocked): 62 data_connectors tests, 58 quant_engine tests.

---

## Phase 3 — Quant Engine + Backtesting (COMPLETED)

> **Scope deviation from the original plan.** The project owner's Phase 3 specification split
> the original Phase 3 in two: the deterministic engine and a **stateless** API surface shipped
> in Phase 3; persistence (`backtest_runs`, `strategy_definitions`, artifacts under
> `data/backtests/`) and the data items deferred from Phase 2 (Alembic, Postgres ingestion +
> seeding, ingestion CLI) moved to **Phase 3.5** below. The full delivered design is documented
> in [backtesting-engine.md](backtesting-engine.md).

**Deliverables (as delivered)**

- Strategy schema validation: `quant_engine.strategy.validate_strategy` — strict against
  [strategy-format.md](strategy-format.md) v1, plus two new optional fields
  (`max_holding_days`, `costs`); `"atr"` stop type explicitly rejected as reserved.
- Signals interpreter: `quant_engine.signals.generate_signals(df, rules)` — condition trees
  (`all`/`any`, nested), the four v1 operators, target `multiplier`, NaN-safe boolean signal
  columns, audit indicator columns, no lookahead. The `highest_close` prior-window-exclusive
  semantics are implemented via a one-bar shift in the interpreter (Phase 2 open thread
  resolved).
- Deterministic backtester: `quant_engine.backtest.Backtester` — daily bars, long-only,
  next-day-open fills with adverse slippage (0.05% default), per-side transaction costs
  (0.05% default), 10% allocation cap, risk-percent sizing bounded by allocation and cash,
  whole shares, one position max, gap-aware fixed percent stops, optional max-holding exits,
  end-of-data force close, close-marked equity curve, full trade records. (Plain readable
  bar loop for the simulation; metrics stay vectorized.)
- Full contract metrics set in `quant_engine.metrics` (the only source of metric values):
  `total_return`, `cagr`, `max_drawdown`, `win_rate`, `avg_win`, `avg_loss`, `profit_factor`,
  `num_trades`, `exposure_time`, `sharpe` (Sharpe-like ratio), `best_trade`, `worst_trade`,
  plus `starting_capital` / `final_equity` on the result and a `compute_all` helper.
- The three initial strategies as code-defined templates in `quant_engine.strategies`
  (SMA crossover, RSI mean reversion, volume breakout swing), validated and backtestable
  end-to-end.
- Stateless API endpoints in `apps/api`: `GET /strategies` (the built-in templates) and
  `POST /backtests/run` (run a built-in strategy over one symbol; returns full metrics +
  equity curve + trade list with `"persisted": false`).

**Acceptance criteria (met)**

- Determinism: identical inputs produce identical metrics and artifacts across repeated runs
  (pure pandas/numpy; no randomness, no network).
- Every metric in the contract set is produced for every run, including the fully defined
  zero-trade edge case.
- All three initial strategies run end-to-end from definition through signals to a complete
  `BacktestResult`, both via Python and via `POST /backtests/run`.
- Backtest simulation semantics verified by hand-computed tests (fills with slippage, costs,
  stop triggers including gap-downs and entry-bar stops, sizing bounds, max-holding and
  end-of-data exits).

---

## Phase 3.5 — Persistence + Deferred Data Items (COMPLETED)

Everything Phase 3 computed statelessly becomes durable, plus the data items deferred from
Phase 2. Persistence now powers strategy storage, backtest runs, and full OHLCV ingestion.

**Deliverables (delivered)**

- `backtest_runs` persistence: every backtest stored with its metrics; equity curve and trade
  list written as artifacts under `data/backtests/`, referenced from the row.
- `strategy_definitions` storage and `POST /strategies` (create/store custom definitions in
  the [strategy-format.md](strategy-format.md) schema; lifecycle starts at `DRAFT`).
- `GET /backtests/{id}` — retrieve a persisted run (metrics + artifact references).
- Alembic migrations replacing the `create_all` bootstrap; `infra/migrations/` becomes real
  (`infra/migrations/env.py` resolves `DATABASE_URL` or `ALEMBIC_DATABASE_URL` at runtime).
- Postgres ingestion into `ohlcv_daily` plus asset seeding for all 50 NIFTY constituents.
- Ingestion CLI (fetch, validate, load, refresh; `--symbol`, `--all`, `--start`, `--end`, `--refresh`).

**Acceptance criteria (met)**

- Re-running a stored backtest's inputs reproduces its stored metrics (foundation for the
  Phase 8 reproducibility audit).
- Artifacts exist on disk and are referenced from the `backtest_runs` row with repo-relative paths.
- All 50 assets seeded; ingestion loads multi-year daily OHLCV for every symbol with zero
  duplicate (asset_id, date) rows in `ohlcv_daily`; re-running ingestion is idempotent.
- `alembic upgrade head` builds the full schema from an empty database; downgrade is safe.
- Strategy persistence model documented: builtin vs. persisted, POST /strategies name conflict rules,
  persist flag behavior, side-effect-free failures.

---

## Phase 4 — Risk Engine (COMPLETED)

**Deliverables (delivered)**

- Risk policy configuration (versioned YAML) per [risk-policy.md](risk-policy.md) — policy v1.0.0
  with hard gates, warning thresholds, and portfolio placeholders.
- Deterministic evaluation engine (`packages/risk_engine/engine.py`) evaluating backtest metrics
  and strategy constraints against policy gates.
- Strict JSON contract output (decision, approved, risk_score, policy_version, reasons,
  failed_rules, warnings, metrics_snapshot, policy_snapshot).
- Risk score computation (0–100, higher = safer; score direction flipped from draft, versioned change).
- Hard veto wiring: a non-approved evaluation (`approved=false`) blocks paper trading downstream
  (enforced by CIO agent Pydantic validator in `packages/agents`).
- Persistence of every evaluation to `risk_evaluations` with snapshots via Alembic migration
  `853ec0ddce66_risk_evaluation_snapshots`.
- Three API endpoints: `POST /risk/evaluate` (backtest_id or inline), `GET /risk/evaluations/{id}`,
  `GET /backtests/{id}/risk`.

**Acceptance criteria (met)**

- Every evaluation emits contract-valid JSON; `approved` is `true` iff `decision == "APPROVED"`
  (validator-enforced).
- Each failing hard gate appears in `failed_rules` with a machine-readable rule id; warnings
  never cause rejection alone.
- Evaluations persist with `policy_version` and snapshots; re-evaluating with the same policy
  version and inputs is deterministic (proven by tests).
- 27 engine tests cover APPROVED, REJECTED, NEEDS_REVIEW paths, decision logic, score computation,
  and edge cases. 14 API tests cover endpoints and error scenarios. 12 policy tests cover YAML
  loading and validation. Total: 53 new tests; 366 repo-wide.

---

## Phase 5 — Paper Trading Engine (COMPLETED)

> **Scope deviation from the original plan.** The project owner's Phase 5 specification
> swapped the order of the remaining phases: the paper trading engine (originally Phase 6)
> was pulled forward into Phase 5, and the AI committee (originally Phase 5) moved to
> Phase 6. Additionally, the delivered fill model deviates from
> [paper-trading-design.md](paper-trading-design.md): orders fill **immediately** at a price
> reference (the request's `price_reference`, else the latest cached close) instead of at
> the next trading day's open — a deliberate, versioned simplification logged in
> [assumptions.md](assumptions.md); the backtester's slippage (0.05% adverse) and per-side
> transaction cost (0.05%) defaults are reused so paper results stay comparable to
> backtests. The full delivered design is documented in
> [paper-trading-engine.md](paper-trading-engine.md).

**Deliverables (as delivered)**

- Paper engine in `apps/api/app/services/paper_engine.py` with HTTP surface in
  `apps/api/app/routers/paper.py` (11 endpoints: portfolios, orders, positions,
  mark-to-market, journal). No schema changes — the Phase 1 models fit as-is (no new
  migration).
- Portfolios per the contract: ₹10,00,000 starting capital; settings JSON with 10% max
  allocation per stock, 1% max risk per trade, 10 max open positions, 8% risk-off drawdown,
  mandatory stop-loss.
- Simulated orders and fills: immediate fills at a price reference (see the deviation note),
  BUY at `ref × (1 + 0.0005)`, SELL at `ref × (1 − 0.0005)`, 0.05% per-side transaction cost,
  whole shares only; no partial fills, no order book, no intraday.
- The risk veto enforced on BUY creation: a persisted backtest and a persisted, **approved**
  risk evaluation are required; `approved=false` (REJECTED or NEEDS_REVIEW) blocks the BUY
  with HTTP 403 — the persisted evaluation row is the sole source of truth.
- SELLs always allowed (risk-reducing exits, including during risk-off); oversell rejected.
- Position tracking (weighted-average entry on add-ons, stop replacement), cash accounting,
  NAV, realized and unrealized P&L.
- Mark-to-market endpoint, drawdown tracking, and risk-off mode (8% portfolio drawdown
  latches risk-off and blocks new entries; one-way latch, no reset endpoint yet).
- Trade journal writing (`FILL` / `RISK_EVENT`) with audit refs, including persisted
  REJECTED order rows plus journal entries on business rejections (veto, limits,
  insufficient cash, oversell). `DECISION` entries arrive with the AI committee (Phase 6);
  stop-loss auto-monitoring and the risk-off reset endpoint are follow-ups.

**Acceptance criteria (met)**

- An order without a stop-loss is rejected; an order without a backtest, without a risk
  evaluation, or with a non-approved risk evaluation is rejected (the veto returns 403 with
  the decision and risk score).
- NAV equals cash plus the sum of position quantity times mark (last price once marked,
  average entry before the first mark-to-market), verified by test.
- Reaching 8% drawdown flips risk-off: new entries blocked, exits still allowed; the flag
  never auto-clears (manual reset endpoint deferred — documented limitation).
- Every fill and every business rejection produces a journal entry whose audit refs resolve
  to real rows (backtest, risk evaluation, order, position).
- Allocation (10% per stock), risk-per-trade (1%), and max-open-positions (10) limits are
  enforced and tested.
- 37 new paper tests, all SQLite/offline, with exact-arithmetic assertions for fills, costs,
  and P&L. Total: 403 repo-wide.

---

## Phase 6 — AI Committee (COMPLETED)

> **Scope beyond the original plan.** Phase 6 delivered a full provider abstraction beyond the
> original Anthropic-only design: five providers (Anthropic official SDK, Gemini REST,
> OpenRouter REST, Ollama local, MOCK deterministic offline default), manual mode (specific
> provider only), auto mode (priority-ordered fallback), and zero-credentials guarantee (all 502
> tests pass with ZERO LLM keys, using mock deterministically). Both [ai-committee.md](ai-committee.md)
> and [llm-providers.md](llm-providers.md) document the delivery.

**Deliverables (as delivered)**

- Six agents in `packages/agents`: Technical Analyst, Quant Researcher, Bull, Bear, Risk Narrator, CIO.
- Five LLM providers: Anthropic (official SDK, `messages.parse()`), Gemini (REST, free-tier available),
  OpenRouter (REST, free-model support via `:free`), Ollama (local REST), MOCK (deterministic offline default).
- Provider abstraction (`AgentProvider` interface + five implementations + factory).
- Manual mode (explicit provider, 503 if unconfigured; no fallback) and auto mode (priority order;
  always available via mock fallback).
- Strict Pydantic-validated JSON outputs for every agent; CIO output follows the contract exactly.
- Full input/output persistence for every agent call to `agent_decisions` (7 rows per run: 5 analysts + raw CIO + final CIO).
- CIO veto constraint enforced **in code** (Pydantic validator + code-level override in `run_committee()`):
  `approved_by_risk` is copied by code from the persisted risk evaluation; if `approved_by_risk=false`
  and raw CIO said `PAPER_TRADE`, code overrides to `NO_TRADE` with audit warning.
- Zero-credentials guarantee: default provider is MOCK (offline, deterministic); all 502 tests pass with
  zero LLM credentials.
- Two API endpoints: `POST /committee/evaluate` (run committee, return all agent outputs), `GET /committee/backtests/{id}`
  (retrieve persisted decisions).

**Acceptance criteria (met)**

- End-to-end committee run persists seven `agent_decisions` rows (5 analysts + raw CIO + final CIO) with complete
  inputs and outputs; audit refs allow full traceability.
- A CIO output of `PAPER_TRADE` with `approved_by_risk=false` raises a validation error at the schema level AND
  is caught by code-level override (dual enforcement); both are covered by automated tests.
- Agents only reference numbers present in their deterministic inputs; no agent computes or invents metrics
  (verified by test: compare agent outputs to input metrics verbatim).
- The system degrades gracefully when all LLM keys are absent: defaults to MOCK provider, 502 tests pass offline,
  endpoints return deterministic outputs.
- All five providers are interchangeable (drop-in implementations of `AgentProvider`); manual mode works for any;
  auto mode picks the first configured in priority order.

---

## Phase 7+8 — Dashboard + End-to-End Research (COMPLETED)

> **Phases 7 and 8 combined.** The original Phase 8 (MCP server) was removed from the
> near-term roadmap by project owner decision (see "Far-Future Ideas" section below).
> Phase 7 deliverables were all completed; Phase 8 scope was redirected.

**Deliverables (as delivered)**

- **10-route dark-only dashboard** (all in `apps/web`; Next.js 15 App Router, React 19):
  `/` (overview), `/research` (6-step pipeline), `/market` (universe view), `/strategies`
  (strategy cards), `/backtests` (persisted runs list + detail), `/risk` (evaluations list +
  console), `/committee` (debate view), `/paper` (fund cockpit), `/journal` (trade audit),
  `/settings` (read-only config).
- **6-step guided research workflow** in `/research`: select symbol → select strategy →
  run backtest → evaluate risk → run committee → create paper order. Human-only order
  creation rule strictly enforced (button enabled only when risk is APPROVED and user
  explicitly clicks).
- **Glassmorphism design** with cyan/teal accents, semantic status colors (emerald
  approved, rose rejected, amber warning/risk-off, sky watchlist), soft glows, tabular
  numbers, motion-enabled transitions.
- **API client** (`apps/web/app/lib/api.ts`) with typed helpers for all backend endpoints;
  NEXT_PUBLIC_API_URL configures the API base at build time (default `http://localhost:8000`).
- **No fake data anywhere.** Every widget shows real API data or honest empty/loading/error states.
- **Two new list endpoints** (`GET /backtests?limit=20` and `GET /risk/evaluations?limit=20`)
  for dashboard usability (6 new tests, all passing).
- **Veto visualization:** Unmistakable rose banner when risk evaluation is rejected; amber
  override banner when code-level veto fires in the committee (raw CIO said PAPER_TRADE but
  risk rejected).

**Acceptance criteria (met)**

- All 10 routes render end-to-end against a seeded database; 508 pytest tests passing
  (backend only).
- `npm run build` from `apps/web` completes with zero TypeScript errors; 13 routes live.
- The 6-step pipeline enforces human-only paper order creation: button disabled if risk
  not APPROVED, order form requires thesis + stop-loss + quantity, server rejects with
  exact veto reason on failure.
- Veto visualization is unmistakable: rose REJECTED banner blocks step 5→6 progression;
  amber override banner shows when code-level veto fires.
- API client has no retries; empty states are honest (no sample data).

---

## Phase 9 — Daily Ops + Hardening (COMPLETED 2026-07-11)

**Deliverables (as delivered)**

- **Daily operations loop** via `POST /paper/portfolios/{id}/daily-cycle`: (1) fetch all prices first (502 if any missing, zero state change); (2) stop-loss sweep — for each open position, if latest close ≤ stop-loss, exit at the breaching close via normal SELL pipeline (full quantity, immediate fill with slippage/costs, journaled); risk-off never blocks exits; (3) mark-to-market; (4) upsert NAV snapshot (one row per portfolio per day, idempotent).
- **NAV history for charting** via `GET /paper/portfolios/{id}/nav-history?limit=365` — snapshots oldest-to-newest.
- **Journaled risk-off reset** via `POST /paper/portfolios/{id}/risk-off/reset` with required note — manual, 400 if not currently risk-off or note empty; on success clears flag and writes RISK_EVENT journal entry.
- **New `nav_snapshots` table** (id, portfolio_id FK, date, nav, cash, drawdown, risk_off, created_at; unique portfolio_id+date) via Alembic migration `2810b70e4708` (chain: `356085dfc427 → 853ec0ddce66 → 2810b70e4708`).
- **Dashboard `/paper` route enhancements** (Phase 9): NAV history chart section (empty state until first cycle), "Run daily cycle" action (toast summary, amber card listing triggered stops), risk-off banner with inline journaled reset form.
- **Live end-to-end shakedown:** clean 3-migration apply on fresh Postgres; 50 assets seeded; 1118 bars × 3 symbols ingested; 6 real backtests persisted (11–15 trades each on 2022→2026 data); all 6 risk evaluations REJECTED by min-30-trades gate (expected, sparse daily data); live veto test (BUY against rejected eval → 403 + REJECTED order + journal entry); daily-cycle snapshot verified; risk-off reset flow verified. **Zero product bugs found.**
- **GitHub publication** — initial commit (v1 complete) pushed to https://github.com/PurpleWizard07/QuantCouncil; Phase 9 commit follows.
- **Test suite:** 516 pytest tests passing (up from Phase 7+8: +20 for daily-ops endpoints + nav-history + risk-off reset flows).

**Acceptance criteria (met)**

- Stop-loss sweep fetches all prices first; 502 on any miss with zero state change.
- Full-quantity exits only; fill at breaching close with standard slippage/costs.
- One snapshot per portfolio-date; upsert is idempotent.
- Risk-off reset requires non-empty note and currently-active risk-off flag; on success clears flag and journals the note.
- Manual browser verification of `/paper` route shows NAV chart loads (empty until first cycle), daily-cycle action works (toast + amber stops card), risk-off reset flow is journaled.
- All live shakedown tests passed with zero product bugs.

---

## Backlog (Deferred, Phase 9+)

**Not implemented in Phase 7+8 or Phase 9; listed for future phases.**

*Phase 9 completed: stop-loss auto-monitoring (daily-close granularity), risk-off reset flow (manual/journaled), daily NAV snapshots.*

- **Strategy-level P&L:** P&L shown only at portfolio level.
- **Provider quality improvements:** Real Anthropic/Gemini/OpenRouter/Ollama refinements;
  retry-on-malformed-JSON; resilience logic beyond single-shot Phase 6 plumbing.
- **Parameter sweeps:** No strategy grid search or optimization UI.
- **Walk-forward testing:** Single-window backtests only.
- **Overfitting detection:** No out-of-sample validation display.
- **Sector rotation:** Global strategies not yet enabled.
- **Multi-symbol batch research:** One symbol at a time in the pipeline.
- **Strategy authoring/editor UI:** JSON viewer only; no form-based builder.
- **Global committee-list endpoint:** No paginated list of all committee runs (only by backtest_id).
- **Light mode:** Dark-only by design.
- **Frontend component unit tests:** Integration tested via API; unit tests deferred.
- **Docker image completeness:** Excludes `packages/*` (local dev only; containerized deployment deferred).

---

## Far-Future Ideas

**MCP server** (originally Phase 8): Optional, zero-priority. If ever implemented, must expose
paper-trading and research tools only, with no real-order execution path (per
[non-goals.md](non-goals.md)); current placeholder lives in `packages/mcp_server`.
