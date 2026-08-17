# QuantCouncil

QuantCouncil is a personal AI quant research and **paper trading** lab for learning,
simulation, backtesting, and AI-agent experimentation. It combines a deterministic
Python quant/backtesting core, a rule-based risk engine with veto power, and a
committee of LLM agents that debate and propose — but never compute — trading ideas.
Scope v1: Indian equities, NIFTY 50 universe, daily timeframe, long-only strategies,
paper trading only.

> **Philosophy: "AI can propose. Math can approve. Risk can veto."**

> **Safety and scope — read this first**
>
> - This is strictly a **personal learning and simulation project**.
> - **Paper trading only.** There is no broker connectivity, no real order
>   execution, and no real-money capability anywhere in the codebase — by design.
> - Nothing in this project is **financial advice**.
> - Real-money trading, broker APIs, options, futures, crypto, and intraday
>   scalping are explicit non-goals. See [docs/non-goals.md](docs/non-goals.md).

## How it works

The pipeline, end to end:

- Daily OHLCV data for the NIFTY 50 universe is ingested (yfinance, `.NS` symbols) and stored in Postgres.
- Strategies are defined declaratively (SMA crossover, RSI mean reversion, volume breakout swing) and start in `DRAFT`.
- The deterministic backtesting engine runs each strategy over historical data and produces the full metrics set (CAGR, max drawdown, Sharpe-like ratio, win rate, profit factor, ...), an equity curve, and a trade list.
- The rule-based risk engine evaluates every backtest against a versioned policy (hard gates, thresholds, risk scoring) and returns a strict `APPROVED` / `REJECTED` / `NEEDS_REVIEW` verdict with binding veto power.
- An AI agent committee (Phase 6, optional Anthropic Claude API) reads the numbers, debates, and proposes — it may reason and summarize but never invents calculations or fake results.
- The CIO agent issues the final decision (`PAPER_TRADE` / `NO_TRADE` / `WATCHLIST`) and is strictly bound by the risk veto: if the risk engine rejects, `PAPER_TRADE` is impossible (enforced in code).
- Approved ideas run in the paper trading engine: simulated orders, immediate fills at a reference price with backtester-matching slippage/costs, mark-to-market NAV, position tracking — never a real order.
- Every decision and trade is written to an auditable trade journal, and strategies move through a fixed lifecycle: `DRAFT -> BACKTESTED -> RISK_EVALUATED -> RISK_APPROVED -> PAPER_TRADING -> WATCHLIST -> RETIRED`.

Hierarchy rules: **LLMs propose. Deterministic Python computes. The risk engine
vetoes. The CIO agent is bound by the veto.**

### Paper portfolio rules

| Rule | Value |
| ---- | ----- |
| Starting paper capital | ₹10,00,000 (1,000,000 INR, simulated) |
| Max allocation per stock | 10% |
| Max risk per paper trade | 1% |
| Max open paper positions | 10 |
| Portfolio drawdown triggering risk-off mode | 8% |
| Stop-loss | Required for every paper trade |
| Prerequisites for any paper trade | A backtest and an approving risk evaluation |

Full design in [docs/paper-trading-design.md](docs/paper-trading-design.md); the as-built
engine is documented in [docs/paper-trading-engine.md](docs/paper-trading-engine.md).

## Repo layout

```
quantcouncil/
  apps/
    web/                 Next.js 15 + React 19 dashboard (App Router)
    api/                 FastAPI backend + SQLAlchemy models + init_db script
  packages/
    quant_engine/        Deterministic backtesting engine and metrics
    risk_engine/         Rule-based risk evaluation with veto power
    agents/              AI committee (technical analyst, quant researcher, bull, bear, risk narrator, CIO)
    data_connectors/     Market data ingestion (yfinance, NSE .NS symbols)
    mcp_server/          Inert placeholder (MCP deferred indefinitely; not implemented)
  infra/                 docker-compose (postgres/api/web) + future Alembic migrations
  data/                  Local data artifacts: raw/, processed/, backtests/ (gitignored)
  docs/                  Architecture, roadmap, non-goals, risk policy, and more
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop
- git

## Quickstart (local dev)

1. Clone the repository (or download the repo from GitHub):

   ```
   git clone https://github.com/PurpleWizard07/QuantCouncil.git
   cd QuantCouncil
   ```

2. Copy the environment file:

   ```
   copy .env.example .env        # Windows
   cp .env.example .env          # macOS / Linux
   ```

3. Start the database:

   ```
   docker compose --env-file .env -f infra/docker-compose.yml up -d postgres
   ```

   (`--env-file .env` matters: Compose otherwise looks for `.env` next to the
   compose file in `infra/`, not at the repo root.)

4. Create a virtual environment at the repo root and install dependencies:

   ```
   py -3 -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # macOS / Linux
   pip install -r requirements-dev.txt
   ```

5. Run database migrations:

   ```
   alembic -c infra/alembic.ini upgrade head
   ```

6. Seed assets and ingest historical data (optional; skips if already loaded):

   ```
   python apps/api/scripts/seed_assets.py
   python apps/api/scripts/ingest_ohlcv.py --all --start 2022-01-01 --end 2024-12-31
   ```

7. Run the API (from `apps/api`):

   ```
   uvicorn app.main:app --reload --port 8000
   ```

8. Run the web app (from `apps/web`):

   ```
   npm install
   npm run dev
   ```

9. Open http://localhost:3000 (dashboard) and http://localhost:8000/docs (API docs).

## Quickstart (full Docker)

1. Copy `.env.example` to `.env`.
2. Build and start everything:

   ```
   docker compose --env-file .env -f infra/docker-compose.yml up --build
   ```

3. Initialize the tables once:

   ```
   docker compose --env-file .env -f infra/docker-compose.yml exec api python scripts/init_db.py
   ```

## Market data (Phase 2)

Daily OHLCV for the NIFTY 50 universe is served by the API (free yfinance data,
plain NSE symbols, unadjusted prices):

```
GET /assets                                    # the 50-symbol universe
GET /assets/RELIANCE/ohlcv?start_date=2024-01-01&end_date=2024-12-31
GET /assets/RELIANCE/indicators                # sma_20/50, ema_20, rsi_14, atr_14, ...
```

Fetched data is cached locally as one Parquet file per symbol under
`data/processed/ohlcv/` (queried via DuckDB); repeat requests never re-hit the
provider. The universe itself lives in `data/nifty50_symbols.json` (manual NSE
snapshot). Full details — validation rules, cache behavior, indicator
conventions, limitations — in [docs/data-layer.md](docs/data-layer.md).

## Strategy Lab (Phase 3 + Phase 3.5)

The deterministic backtesting engine runs the three built-in strategies or custom strategies over any
NIFTY 50 symbol: next-day-open fills with 0.05% adverse slippage, 0.05% per-side
transaction costs, 1%-risk position sizing capped at 10% allocation, gap-aware
percent stops, and the full metrics set (CAGR, max drawdown, Sharpe-like ratio,
win rate, profit factor, ...) plus equity curve and trade list:

```
GET  /strategies                               # the 3 built-in + any persisted custom strategies
POST /strategies                               # (Phase 3.5) create a custom strategy
POST /backtests/run                            # run a strategy over one symbol; optionally persist results
GET  /backtests/{id}                           # (Phase 3.5) retrieve a persisted backtest run
```

```
curl -X POST http://localhost:8000/backtests/run -H "Content-Type: application/json" \
  -d '{"strategy": <full strategy JSON from GET /strategies>, "symbol": "RELIANCE", "start_date": "2023-01-01", "end_date": "2024-12-31", "persist": true}'
```

(`strategy` is the full definition object, not a name — or pass `"strategy_id": "<uuid>"` for a
saved strategy; see [docs/persistence.md](docs/persistence.md).)

Set `"persist": true` to store results in the database (Phase 3.5); default `persist: false`
computes on demand. Full details — execution model, sizing rules, metric conventions, persistence,
limitations — in [docs/backtesting-engine.md](docs/backtesting-engine.md) and
[docs/persistence.md](docs/persistence.md).

## Risk Engine (Phase 4)

Every backtest is automatically evaluated against a versioned risk policy: hard gates on metrics
(max drawdown, profit factor, trade count, Sharpe, total return), a deterministic APPROVED /
REJECTED / NEEDS_REVIEW verdict, and a risk score (0–100, higher = safer). The risk engine has
**binding veto power**: a non-approved evaluation blocks paper trading downstream (enforced by the
CIO agent validator). Evaluation results are persisted with snapshots for full reproducibility.

```
POST   /risk/evaluate                            # evaluate a backtest (persisted) or inline metrics
GET    /risk/evaluations/{id}                    # retrieve a persisted risk evaluation
GET    /backtests/{id}/risk                      # latest evaluation for a backtest
```

Example workflow:

```bash
# 1. Run and persist a backtest
curl -X POST http://localhost:8000/backtests/run \
  -H "Content-Type: application/json" \
  -d '{"strategy": {...}, "symbol": "RELIANCE", "start_date": "2023-01-01", "end_date": "2024-12-31", "persist": true}'
# Returns: {"backtest_id": "550e8400-...", ...}

# 2. Evaluate the backtest's risk
curl -X POST http://localhost:8000/risk/evaluate \
  -H "Content-Type: application/json" \
  -d '{"backtest_id": "550e8400-..."}'
# Returns: {"decision": "APPROVED", "approved": true, "risk_score": 72, ...}

# 3. Retrieve the evaluation later
curl http://localhost:8000/risk/evaluations/550e8400-...
```

Full details — policy configuration, engine logic, scoring formula, API surface, persistence —
in [docs/risk-engine.md](docs/risk-engine.md) and [docs/risk-policy.md](docs/risk-policy.md).

## Paper Fund (Phase 5 + Phase 9)

The paper portfolio simulates only after risk approval: a BUY requires a persisted backtest
and a persisted, **approving** risk evaluation — a non-approved evaluation blocks the order
with HTTP 403 (the persisted row is the sole source of truth). SELLs are always allowed
(exits reduce risk). Fills are immediate at a reference price with the backtester's slippage
and cost defaults; every fill and rejection is journaled. Fully local and deterministic —
no AI, no broker, no real orders.

Phase 9 adds daily operations: automated stop-loss sweep (on daily closes), mark-to-market, and NAV snapshots for tracking. Risk-off mode now has a manual, journaled reset endpoint.

```
POST /paper/portfolios                           # create a paper fund (₹10,00,000 default)
GET  /paper/portfolios[/{id}]                    # list / inspect portfolios
POST /paper/orders                               # BUY (risk-vetoed) / SELL (always allowed)
GET  /paper/orders[/{id}]                        # list / inspect orders
GET  /paper/positions                            # open/closed positions
GET  /paper/portfolios/{id}/positions            # positions for one portfolio
POST /paper/portfolios/{id}/mark-to-market       # revalue, NAV, drawdown, risk-off latch
POST /paper/portfolios/{id}/daily-cycle          # (Phase 9) stop-loss sweep → mark-to-market → NAV snapshot
GET  /paper/portfolios/{id}/nav-history          # (Phase 9) NAV snapshots (for charting)
POST /paper/portfolios/{id}/risk-off/reset       # (Phase 9) manual, journaled risk-off reset
GET  /paper/journal                              # audit trail (FILL / RISK_EVENT)
GET  /paper/portfolios/{id}/journal              # journal for one portfolio, newest first
```

The six-step workflow: (1) `POST /backtests/run` with `persist: true` → `backtest_id`;
(2) `POST /risk/evaluate` with the `backtest_id` → `risk_evaluation_id`; (3) `POST
/paper/portfolios` → `portfolio_id`; (4) `POST /paper/orders` with symbol, quantity, thesis,
`stop_loss_price`, and both ids → filled BUY (or 403 if risk did not approve); (5) `POST
/paper/portfolios/{id}/mark-to-market` → NAV and unrealized P&L; (6) `GET
/paper/portfolios/{id}/journal` → the audit trail.

Full details — order simulation, validation/veto sequence, position management, NAV/risk-off,
journal behavior, limitations — in [docs/paper-trading-engine.md](docs/paper-trading-engine.md).

## AI Committee (Phase 6)

The AI committee debates, reasons, and proposes — but never computes. Six agents (Technical
Analyst, Quant Researcher, Bull, Bear, Risk Narrator, CIO) evaluate every backtest and issue
a final decision. **Philosophy: "AI can propose. Math can approve. Risk can veto."** The risk
engine's verdict is binding: if risk says no, the CIO cannot say `PAPER_TRADE` (enforced in
code by Pydantic validator).

Agents run against five pluggable LLM providers:

```
POST /committee/evaluate                     # run the committee (two endpoints)
GET  /committee/backtests/{id}               # retrieve persisted decisions
```

Example (mock provider, no API keys needed):

```bash
# (Assume backtest_id and risk_evaluation_id from earlier steps)
curl -X POST http://localhost:8000/committee/evaluate \
  -H "Content-Type: application/json" \
  -d '{"backtest_id": "550e8400-...", "risk_evaluation_id": "550e8400-..."}'
# Returns: technical_analyst, quant_researcher, bull, bear, risk_narrator, cio (with approved_by_risk)
```

| Provider | Type | Setup | Cost | Note |
|---|---|---|---|---|
| **MOCK** | Deterministic offline | None | Free | Default (no keys needed); all tests use this |
| **Anthropic** | Premium cloud (official SDK) | `ANTHROPIC_API_KEY` | Per-token | Highest quality; optional |
| **Gemini** | Cloud (REST) | `GEMINI_API_KEY` | Free tier + paid | Google; free tier available |
| **OpenRouter** | Cloud routing (REST) | `OPENROUTER_API_KEY` | Per-token, free models | Flexible, free-model support (`:free` suffix) |
| **Ollama** | Local (REST) | Ollama service | Free | Privacy-first, offline; runs on your machine |

**Zero-credentials guarantee:** The system runs with zero LLM API keys. Default provider is
MOCK (deterministic, offline). All 502 tests pass without credentials. Configure optional
providers when you want premium quality.

Full details — agent architecture, provider selection (manual/auto modes), dual-layer veto
binding, persistence, API surface — in [docs/ai-committee.md](docs/ai-committee.md) and
[docs/llm-providers.md](docs/llm-providers.md).

## Dashboard (Phase 7+8)

A dark-only modern dashboard for the complete research and paper-trading pipeline. Built with Next.js 15
(App Router) and React 19, no external UI libraries (Tailwind CSS v4 only).

**11 top-level routes** — `/` (overview), `/research` (6-step pipeline), `/market` (universe), `/strategies` (cards),
`/backtests` (runs), `/risk` (evaluations), `/committee` (debate), `/paper` (fund), `/journal` (audit),
`/learn` (standalone Trading Mastery curriculum: 15 modules, 50 MDX lessons, glossary, resources),
`/settings` (config) — all live and fully functional.

**The 6-step research workflow** (`/research`):
1. Select symbol from NIFTY 50 (searchable)
2. Select strategy (built-in or persisted)
3. Run backtest (persist results, view metrics + equity curve + trades)
4. Evaluate risk (see score, failed rules, veto status)
5. Run AI committee (see six-agent debate, CIO decision, veto override banner if triggered)
6. Create paper order (**HUMAN-ONLY** — button enabled only when risk is APPROVED; form requires thesis,
   stop-loss, quantity; exact rejection reasons shown on veto)

**Design — "The Chamber":** anodized-graphite surfaces under one fixed light source (solid machined
plates with a top-edge highlight and a cast shadow, not blurred glass); a two-channel color system —
warm (muted gold) for authority and consequence (risk verdicts, the CIO decision, the veto seal, ₹
figures) and cool (teal) for the machine (charts, deterministic data) — layered over the semantic
status colors (emerald approved, rose rejected, amber warning/risk-off, sky watchlist); verdicts set
in a high-contrast serif (Fraunces), everything else in sans/mono; the AI committee rendered as an
"opposed chamber" (CIO head, evidence row, a bull-vs-bear debate axis facing across a center line,
risk-narrator floor); the risk veto rendered as a sealed plate (`VetoSeal`) rather than a banner;
grouped bezel sidebar nav with a single traveling active-indicator; a command palette (`⌘K`). Permanent
amber badge "Paper trading only — simulated" in the top bar. Full detail in
[docs/dashboard.md](docs/dashboard.md#design-direction--the-chamber).

**How to run:**

```bash
cd apps/web
npm install
npm run dev
```

Then visit http://localhost:3000 (the API must be running on http://localhost:8000).

**NEXT_PUBLIC_API_URL:** Configure the API base URL at build time via `.env.local` or `.env.example`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Frontend integration:** All 11 top-level routes render end-to-end against a seeded database. No fake
data, no component unit tests (integration tested via API). `npm run build` produces zero TypeScript
errors (82 static pages across 17 route entries once the Learn section's per-module and per-lesson
pages are counted individually).
Two new backend list endpoints support dashboard usability: `GET /backtests?limit=20` and `GET
/risk/evaluations?limit=20`.

Full details in [docs/dashboard.md](docs/dashboard.md).

## Testing

From the repo root (uses `pytest.ini`, which targets `apps/api` and `packages`):

```
pytest
```

The suite needs no network access — all market-data calls are mocked.

## Roadmap

Full details in [docs/development-roadmap.md](docs/development-roadmap.md).

| Phase | Focus | Status |
| ----- | ----- | ------ |
| 1 | Foundation: monorepo, Postgres schema, FastAPI + Next.js skeletons, Docker | Done |
| 2 | Data layer: yfinance connector + validation, Parquet/DuckDB cache, indicator set, market-data API endpoints | Done |
| 3 | Backtesting engine: strategy schema + signals interpreter + deterministic backtester + metrics, first three strategies (SMA crossover, RSI mean reversion, volume breakout), stateless backtest API | Done |
| 3.5 | Persistence: backtest runs + strategy storage + artifacts; Alembic migrations, Postgres OHLCV ingestion + asset seeding, ingestion CLI | Done |
| 4 | Risk engine: versioned policy (YAML), deterministic evaluation, APPROVED/REJECTED/NEEDS_REVIEW verdicts, risk scoring (0–100), hard veto enforcement, snapshot-based reproducibility, API endpoints | Done |
| 5 | Paper trading engine: simulated orders, immediate fills, positions, NAV, risk-off mode, risk-veto enforcement on entries, trade journal | Done |
| 6 | AI agent committee: six agents, five LLM providers (Anthropic, Gemini, OpenRouter, Ollama, MOCK), manual/auto provider selection, zero-credentials default, dual-layer veto binding, persistence | Done |
| 7+8 | Dashboard buildout: 10-route dark-only UI with 6-step research pipeline, human-only order creation, veto visualization; removed MCP from near-term roadmap (far-future idea only) | Done |
| 9 | Daily ops + hardening: daily-cycle endpoint (stop-loss sweep, mark-to-market, NAV snapshot), NAV history for charting, journaled risk-off reset; GitHub publication; live end-to-end shakedown (516 tests, zero product bugs) | Done |
| Backlog | Provider resilience, Docker completeness, strategy UI, multi-symbol batch, parameter sweeps, walk-forward, overfitting detection, sector rotation, and more | Next |

## Documentation index

- [docs/architecture.md](docs/architecture.md) — system architecture and component boundaries
- [docs/development-roadmap.md](docs/development-roadmap.md) — phased build plan
- [docs/dashboard.md](docs/dashboard.md) — web dashboard: 11 top-level routes (incl. `/learn`), 6-step research pipeline, "The Chamber" design system, API client, how to run
- [docs/data-layer.md](docs/data-layer.md) — data sources, universe, validation, cache, indicators, market-data API
- [docs/backtesting-engine.md](docs/backtesting-engine.md) — strategy validation, signals interpreter, backtester, metrics, backtest API
- [docs/persistence.md](docs/persistence.md) — migrations, asset seeding, ingestion CLI, strategy and backtest persistence, retrieval API
- [docs/risk-engine.md](docs/risk-engine.md) — risk policy, deterministic evaluation, scoring, veto enforcement, API, persistence
- [docs/risk-policy.md](docs/risk-policy.md) — risk gates, thresholds, decision logic, policy versioning, hard veto
- [docs/paper-trading-design.md](docs/paper-trading-design.md) — paper portfolio rules and simulation design
- [docs/paper-trading-engine.md](docs/paper-trading-engine.md) — the as-built paper engine: order simulation, veto sequence, positions, NAV/risk-off, journal, API
- [docs/ai-committee.md](docs/ai-committee.md) — AI committee architecture, agent roles, veto binding, API endpoints, persistence, providers
- [docs/llm-providers.md](docs/llm-providers.md) — LLM provider abstraction, five providers (Anthropic, Gemini, OpenRouter, Ollama, MOCK), manual/auto modes, configuration
- [docs/session-handoff.md](docs/session-handoff.md) — current state and next steps for the following session
- [docs/strategy-format.md](docs/strategy-format.md) — strategy definition format and lifecycle
- [docs/non-goals.md](docs/non-goals.md) — what this project will never do
- [docs/assumptions.md](docs/assumptions.md) — documented engineering assumptions

## Disclaimer

QuantCouncil is an educational simulation. It is not investment advice, it does
not manage or touch real money, and it has no real-money trading capability by
design. All results are simulated paper-trading outcomes for learning purposes only.
