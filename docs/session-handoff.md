# Session Handoff

Concise state-of-the-project handoff for the next working session. Deep detail lives in the
linked docs; this file is the "where were we?" entry point. Update it at the end of each phase.

**Last updated:** 2026-07-11 — Phase 9 (Daily Ops + Hardening) complete; 516 tests passing.

## Current State

- **Phase 1 (Foundation): complete.** Monorepo, FastAPI + Next.js skeletons, PostgreSQL 16 via
  Docker Compose, SQLAlchemy models for all 10 contract tables, the documentation set.
- **Phase 2 (Data Layer): complete.** File-and-cache data layer (JSON universe, validated
  yfinance connector, Parquet/DuckDB cache, indicators, market-data API endpoints). Full design
  in [data-layer.md](data-layer.md).
- **Phase 3 (Quant Engine + Backtesting): complete.** Strategy schema validation, signals
  interpreter, deterministic backtester, full metrics set, three built-in strategies, and
  stateless backtest API endpoints. Full design in [backtesting-engine.md](backtesting-engine.md).
- **Phase 3.5 (Persistence + Database Integration): complete.** Alembic migrations, asset seeding,
  OHLCV ingestion CLI, strategy persistence, backtest persistence (runs + artifacts), retrieval API.
  Full design in [persistence.md](persistence.md).
- **Phase 4 (Rule-Based Risk Engine): complete.** Versioned risk policy (YAML), deterministic risk
  evaluation engine, APPROVED/REJECTED/NEEDS_REVIEW verdicts, risk score (0–100, higher = safer),
  hard veto binding the CIO agent, snapshot-based reproducibility, and three API endpoints.
  Full design in [risk-engine.md](risk-engine.md).
- **Phase 5 (Paper Portfolio Engine): complete.** Fully local, deterministic paper trading:
  portfolios (₹10,00,000 starting capital, per-contract settings), immediate simulated fills
  (deliberate deviation from the next-open design — versioned, logged in
  [assumptions.md](assumptions.md)), the risk veto enforced on BUYs (HTTP 403 unless the
  persisted evaluation is approved), SELLs always allowed, mark-to-market NAV/drawdown,
  risk-off latch at 8% drawdown, append-only journal (FILL/RISK_EVENT), REJECTED-row audit
  trail, 11 API endpoints. No schema changes (the Phase 1 models fit as-is). Full reference
  in [paper-trading-engine.md](paper-trading-engine.md).
- **Phase 6 (AI Committee): complete.** Six agents in `packages/agents` (Technical Analyst,
  Quant Researcher, Bull, Bear, Risk Narrator, CIO) with strict Pydantic JSON outputs. Five
  LLM providers (Anthropic official SDK, Gemini REST, OpenRouter REST, Ollama local, MOCK
  deterministic offline default). Provider abstraction with manual mode (specific provider only)
  and auto mode (priority-ordered fallback; always available via mock default). Zero-credentials
  guarantee — the system runs with ZERO LLM keys, using mock deterministically. Dual-layer
  risk veto binding: code-level override (CIO raw PAPER_TRADE → NO_TRADE if risk rejected, with
  audit warning) and schema validator (rejects contradictory state independently). Seven-row
  persistence per committee run (5 analysts + raw CIO + final CIO with approved_by_risk). Two
  API endpoints (`POST /committee/evaluate`, `GET /committee/backtests/{id}`). Full reference in
  [ai-committee.md](ai-committee.md) and [llm-providers.md](llm-providers.md).
- **Phase 7+8 (Dashboard + End-to-End Research): complete.** 10-route dark-only Next.js 15 dashboard
  (`apps/web`, App Router, React 19, no shadcn) with 6-step guided research pipeline (`/research`): select
  symbol → select strategy → run backtest → evaluate risk → run committee → create paper order (human-only).
  Ten routes: `/` (overview), `/research` (pipeline), `/market` (universe), `/strategies` (cards),
  `/backtests` (runs), `/risk` (evals), `/committee` (debate), `/paper` (fund), `/journal` (audit),
  `/settings` (config). Glassmorphism design with semantic status colors, soft glows, tabular numbers,
  motion transitions. No fake data. Human-only order rule: button disabled until risk APPROVED; form
  requires thesis + stop-loss + quantity. Veto visualization: rose REJECTED banner blocks step 4→5;
  amber override banner if code-level veto fires. Two new backend list endpoints: `GET /backtests?limit=20`
  and `GET /risk/evaluations?limit=20`. Frontend: `npm run build` passes, 13 routes live, zero TypeScript
  errors. Full design in [dashboard.md](dashboard.md). MCP removed from near-term roadmap (see far-future
  note in [development-roadmap.md](development-roadmap.md)).
- **Phase 9 (Daily Ops + Hardening): complete (2026-07-11).** Daily operations loop via
  `POST /paper/portfolios/{id}/daily-cycle`: (1) fetch all prices first (502 on any miss, zero state change);
  (2) stop-loss sweep — auto-exit any position with close ≤ stop_loss at the breaching close (full quantity,
  normal SELL pipeline, journaled); risk-off never blocks exits; (3) mark-to-market; (4) upsert NAV snapshot
  (one row per portfolio per day). NAV history via `GET /paper/portfolios/{id}/nav-history?limit=365` for
  charting (oldest-to-newest). Journaled risk-off reset via `POST /paper/portfolios/{id}/risk-off/reset`
  (manual, required note, clears flag and writes RISK_EVENT). New `nav_snapshots` table (id, portfolio_id FK,
  date, nav, cash, drawdown, risk_off, created_at; unique portfolio_id+date) via Alembic migration `2810b70e4708`
  (chain: `356085dfc427 → 853ec0ddce66 → 2810b70e4708`). Dashboard `/paper` route: NAV history chart (empty until
  first cycle), "Run daily cycle" action (toast summary, amber card listing triggered stops), risk-off banner
  with inline reset form. Live end-to-end shakedown: clean 3-migration apply on fresh Postgres; 50 assets seeded;
  1118 bars × 3 symbols ingested; 6 real backtests persisted; all 6 risk evals REJECTED by min-30-trades gate
  (expected, sparse daily data); live veto test verified; daily-cycle snapshot verified; risk-off reset verified.
  **Zero product bugs found.** GitHub publication: repo pushed to https://github.com/PurpleWizard07/QuantCouncil.
  Full design in [development-roadmap.md](development-roadmap.md) and [paper-trading-engine.md](paper-trading-engine.md).
- **Test suite: green.** 516 tests passing from the repo root (Phase 9 +20 daily-ops tests; prior phases:
  62 data_connectors, 183 quant_engine incl. integration, 53 risk_engine, 105 apps/api incl. persistence + risk +
  37 paper tests, +85 agents tests incl. veto binding + 14 committee API tests, +6 list endpoint tests).
  No test touches the network (yfinance and all LLM providers mocked).

## What Exists Where

| Component | Location | State |
|---|---|---|
| Universe source of truth | `data/nifty50_symbols.json` (50 records, manual NSE snapshot `as_of` 2025-03) | Live |
| Universe loader | `packages/data_connectors/data_connectors/universe.py` (`NIFTY50`, `get_universe()`, `to_yfinance_symbol()`) | Live |
| Connector contract + factory | `data_connectors/base.py` (`OHLCVConnector.get_ohlcv`), `registry.py` (`get_connector`) | Live |
| yfinance connector | `data_connectors/yfinance_connector.py` (`auto_adjust=False`, unadjusted prices) | Live (active source) |
| OpenBB connector | `data_connectors/openbb_connector.py` | Registered placeholder; raises `NotImplementedError` |
| OHLCV validation | `data_connectors/validation.py` (`validate_ohlcv`, `validate_ohlcv_report`) | Live |
| Parquet/DuckDB cache | `data_connectors/cache.py` (`OHLCVCache`, `CachedConnector`), files under `data/processed/ohlcv/` | Live |
| Indicators | `packages/quant_engine/quant_engine/indicators.py` (sma, ema, rsi, atr, rolling_high, rolling_low, volume_sma, highest_close, daily_returns, volatility) | Live, fully tested |
| Strategy schema validation | `quant_engine/strategy.py` (`validate_strategy`, `StrategyValidationError`) | Live (Phase 3) |
| Built-in strategies | `quant_engine/strategies.py` (`SMA_CROSSOVER`, `RSI_MEAN_REVERSION`, `VOLUME_BREAKOUT`, `get_builtin_strategies()`) | Live (Phase 3) |
| Signals interpreter | `quant_engine/signals.py` (`generate_signals`) | Live (Phase 3) |
| Backtester | `quant_engine/backtest.py` (`BacktestConfig`, `Backtester.run` / `run_from_signals`, `BacktestResult`) | Live (Phase 3) |
| Metrics | `quant_engine/metrics.py` (full contract set + `compute_all`) | Live (Phase 3) |
| Alembic migrations | `infra/alembic.ini`, `infra/migrations/` (one initial migration: 356085dfc427_initial_schema) | Live (Phase 3.5) |
| Asset seeding | `apps/api/scripts/seed_assets.py` (idempotent 50-row upsert from `data/nifty50_symbols.json`) | Live (Phase 3.5) |
| OHLCV ingestion | `apps/api/scripts/ingest_ohlcv.py` (`--symbol`, `--all`, `--start`, `--end`, `--refresh`) | Live (Phase 3.5) |
| Backtest persistence | `apps/api/app/db/models.py` (`backtest_runs` table + artifact path columns); artifacts under `data/backtests/` | Live (Phase 3.5) |
| Strategy persistence | `apps/api/app/db/models.py` (`strategy_definitions` table); immutable builtins + mutable persisted rows | Live (Phase 3.5) |
| Risk engine | `packages/risk_engine` (policy YAML, engine, Pydantic contract, snapshot columns, repository functions) | Live (Phase 4) |
| Risk API endpoints | `apps/api/app/routers/risk.py` (`POST /risk/evaluate`, `GET /risk/evaluations/{id}`, `GET /backtests/{id}/risk`) | Live (Phase 4) |
| Paper engine | `apps/api/app/services/paper_engine.py` (service), `apps/api/app/routers/paper.py` (router, 14 endpoints: portfolios, orders, positions, mark-to-market, journal, daily-cycle, nav-history, risk-off-reset) | Live (Phase 5 + Phase 9) |
| NAV snapshots | `apps/api/app/db/models.py` (`nav_snapshots` table); migration `2810b70e4708` (Phase 9, chain: `356085dfc427 → 853ec0ddce66 → 2810b70e4708`) | Live (Phase 9) |
| Daily ops endpoints | `apps/api/app/routers/paper.py` (`POST /daily-cycle`, `GET /nav-history`, `POST /risk-off/reset`) | Live (Phase 9) |
| Agents | `packages/agents/agents/` (six roles + five providers: mock, anthropic, gemini, openrouter, ollama; committee orchestration; dual-layer veto binding) | Live (Phase 6) |
| Committee API endpoints | `apps/api/app/routers/committee.py` (`POST /committee/evaluate`, `GET /committee/backtests/{id}`) | Live (Phase 6) |
| Backtest list endpoint | `apps/api/app/routers/backtests.py` (`GET /backtests?limit=20`) | Live (Phase 7+8) |
| Risk evaluations list endpoint | `apps/api/app/routers/risk.py` (`GET /risk/evaluations?limit=20`) | Live (Phase 7+8) |
| API | `apps/api` — health, market-data endpoints (`/assets`, `/assets/{symbol}/ohlcv`, `/assets/{symbol}/indicators`), strategy endpoints (`GET /strategies`, `POST /strategies`), backtest endpoints (`POST /backtests/run` with persist flag, `GET /backtests/{id}`, `GET /backtests?limit=20`), risk endpoints (Phase 4), risk evaluations list (Phase 7+8), paper endpoints (`/paper/*` including daily-ops: `POST /daily-cycle`, `GET /nav-history`, `POST /risk-off/reset`, Phase 5 + Phase 9), committee endpoints (`/committee/*`, Phase 6) | Live (Phase 9 added daily-ops endpoints) |
| Web dashboard | `apps/web` (10 routes: `/`, `/research`, `/market`, `/strategies`, `/backtests`, `/risk`, `/committee`, `/paper` with NAV chart + daily-cycle action + risk-off reset, `/journal`, `/settings`; dark-only, Next.js 15 App Router, React 19, no shadcn, Tailwind v4 + recharts + motion) | Live (Phase 9 updated `/paper`) |

## How to Run Everything

From the repo root (Windows paths; see [../README.md](../README.md) for full quickstart):

```
# Tests (no network needed)
.venv/Scripts/python.exe -m pytest -q        # or plain `pytest` inside the activated venv

# Database (Docker Desktop running)
docker compose --env-file .env -f infra/docker-compose.yml up -d postgres

# Migrations (Alembic; Phase 3.5)
alembic -c infra/alembic.ini upgrade head

# Asset seeding and OHLCV ingestion (Phase 3.5)
python apps/api/scripts/seed_assets.py
python apps/api/scripts/ingest_ohlcv.py --all --start 2022-01-01 --end 2024-12-31

# API (from apps/api)
uvicorn app.main:app --reload --port 8000

# Web (from apps/web)
npm run dev
```

Run a backtest via the API (hits Yahoo Finance on a cache miss):

```
curl http://localhost:8000/strategies

curl -X POST http://localhost:8000/backtests/run \
  -H "Content-Type: application/json" \
  -d '{"strategy": <full strategy JSON from GET /strategies, minus source/id/status/created_at>, "symbol": "RELIANCE", "start_date": "2023-01-01", "end_date": "2024-12-31"}'
```

(Or pass `"strategy_id": "<uuid>"` of a saved strategy instead of `strategy`; add
`"persist": true` to store the run. See [persistence.md](persistence.md).)

Run a backtest from Python directly:

```python
from data_connectors import CachedConnector, OHLCVCache, get_connector
from quant_engine.backtest import Backtester
from quant_engine.strategies import get_builtin_strategies

df = CachedConnector(get_connector("yfinance"), OHLCVCache()).get_ohlcv(
    "RELIANCE", "2023-01-01", "2024-12-31"
)
result = Backtester().run(df, get_builtin_strategies()[0], symbol="RELIANCE")
print(result.total_return, result.num_trades, result.final_equity)
```

## Next Steps (Backlog)

Phase 7+8 is complete. No numbered phase is pending. Next work targets the backlog per
[development-roadmap.md](development-roadmap.md#backlog).

**High-priority backlog items:**

- **Stop-loss auto-monitoring:** Stops stored on positions but not auto-triggered. Evaluate
  against daily closes and generate SELLs automatically.
- **Risk-off reset flow:** Risk-off flag is one-way latch. Add journaled manual reset endpoint.
- **Provider resilience:** Real Anthropic/Gemini/OpenRouter/Ollama refinements; retry-on-malformed-JSON.
- **Docker image completeness:** Include `packages/*` and data files; enable containerized runs.
- **Indicator warm-up refinement:** Pre-fetch lookback before requested range on `/assets/{symbol}/indicators`.
- **Strategy authoring UI:** Form-based editor instead of JSON viewer only.
- **Multi-symbol batch research:** Allow running multiple symbols in one committee run.

For complete backlog, see [development-roadmap.md](development-roadmap.md#backlog).

## Open Threads

- **Docker image excludes the data layer and quant engine:** `apps/api/Dockerfile` installs
  only the API's own requirements and copies only `apps/api/`, so `packages/*` and
  `data/nifty50_symbols.json` are missing in the container. All post-Phase-1 endpoints work in
  local dev only; fix the image when containerized runs matter.
- **No lookback pre-fetch on `GET /assets/{symbol}/indicators`:** warm-up `null`s appear at
  the start of every response range. Candidate refinement: fetch extra history before
  `start_date` and trim. The same warm-up applies to backtests — a strategy needing SMA(50)
  produces no signals in the first 49 bars of the requested window.
- **Wilder smoothing variant:** RSI/ATR use `ewm(alpha=1/window, adjust=False)` full-history
  recursion, not the classic simple-average seed — values differ slightly from some TA
  libraries. Documented in [data-layer.md](data-layer.md) and [assumptions.md](assumptions.md);
  Phase 3 signal tests are consistent with this choice.
- **Universe snapshot is manual** (survivorship bias accepted); refresh
  `data/nifty50_symbols.json` by hand when the index reconstitutes.

Resolved this phase (Phase 6): **AI Committee** — six agents in `packages/agents` (Technical
Analyst, Quant Researcher, Bull, Bear, Risk Narrator, CIO) with five LLM providers (Anthropic
official SDK, Gemini REST, OpenRouter REST, Ollama local, MOCK deterministic offline default).
Provider abstraction with manual mode (specific provider only, 503 if unconfigured) and auto
mode (priority-ordered fallback; always available via mock default). Zero-credentials guarantee:
the system runs with ZERO LLM API keys, using mock deterministically, all 502 tests pass offline.
Dual-layer risk veto binding: (1) code-level override in `run_committee()` catches raw CIO
PAPER_TRADE + risk rejected → NO_TRADE with audit warning; (2) Pydantic schema validator
rejects contradictory state independently. Seven-row persistence per committee run (5 analysts
+ raw CIO untrusted + final CIO with approved_by_risk + audit refs). Two endpoints (`POST
/committee/evaluate`, `GET /committee/backtests/{id}`). The "committee runs agents and debates
but never computes metrics" guarantee is maintained: every figure cited comes verbatim from
deterministic inputs. The "committee never creates paper orders" guarantee is enforced by design
(committee calls are manual `POST /committee/evaluate`; paper order creation is a separate manual
`POST /paper/orders` endpoint where the veto is enforced a second time). All 502 tests passing
(+85 agents tests +14 committee API tests).
