# QuantCouncil Web Dashboard (Phase 7+8)

Modern, dark-only dashboard for the complete research and paper-trading pipeline. Built with Next.js 15 (App Router) and React 19.

## Design Direction

- **Dark-only mode.** No light mode. The visual language is "AI quant command center": glassmorphism panels, cyan/teal accents, semantic status colors, soft glows, and motion-enabled page transitions.
- **Status colors (semantic):**
  - Emerald: approved/positive verdicts (risk APPROVED, successful trades)
  - Rose: rejected/negative verdicts (risk REJECTED, failed trades)
  - Amber: warning/needs-review state (NEEDS_REVIEW decisions, risk-off latch)
  - Sky: watchlist status (secondary decisions)
- **Tabular numbers** via `font-variant-numeric: tabular-nums` for unambiguous data alignment.
- **No shadcn, no external UI libraries.** Tailwind CSS v4 only (`@tailwindcss/postcss`).
- **Frontend dependencies:** recharts (charts), motion (animations), no others.

## The 10 Routes

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | Dashboard | Overview: NAV/cash/positions/risk-mode cards, latest backtest, latest risk evaluation, latest committee verdict, recent journal entries, quick actions (mark-to-market, create-default-portfolio) |
| `/research` | The 6-Step Pipeline | Guided workflow: select symbol → select strategy → run backtest → evaluate risk → run committee → create paper order |
| `/market` | Universe View | NIFTY 50 searchable table with sector filters; per-asset price chart, recent OHLCV, indicator preview with warm-up hints |
| `/strategies` | Strategy Cards | View strategy definitions with lifecycle badges (DRAFT/BACKTESTED/etc.), JSON viewers, links into research workflow |
| `/backtests` | Persisted Runs | List all stored backtest runs (newest-first, metric subset). Detail view: metrics grid, equity curve chart, trade list, veto status chip |
| `/risk` | Risk Evaluations | List recent evaluations (newest-first). Console: evaluate-by-backtest_id, score gauge, failed rules, policy/metrics snapshots |
| `/committee` | Committee Decisions | Run console with provider selector (mock/auto/anthropic/gemini/openrouter/ollama); six-agent debate cards; CIO final decision; override banner when code-level veto fired |
| `/paper` | Paper Fund Cockpit | NAV/cash/unrealized/realized P&L/risk-mode metrics; NAV history chart (Phase 9); RISK_OFF rose banner when active with inline reset form (Phase 9); "Run daily cycle" action (Phase 9: stop-loss sweep → mark-to-market → NAV snapshot); mark-to-market button; positions table with Open/Closed filters; full order form with veto-aware error handling; recent orders; permanent simulated-only footer |
| `/journal` | Trade Journal | Filterable audit timeline: portfolio/type/search filters; per-type badges; refs chips (thesis/rejection reasons/linked ids); expandable JSON; show-more pagination |
| `/settings` | Configuration (read-only) | API base URL, LLM provider env-var reference table, paper-trading-only safety statement. No broker settings exist. |

## The 6-Step Research Workflow (`/research`)

The guided pipeline walks a user from idea to simulated execution:

1. **Select Symbol**
   - Searchable dropdown populated from `GET /assets`
   - All 50 NIFTY constituents available

2. **Select Strategy**
   - Built-in templates (SMA crossover, RSI mean reversion, volume breakout) plus persisted custom strategies
   - JSON viewer for inspection; edit deferred to Phase 8+

3. **Run Backtest**
   - Form: symbol (pre-filled), strategy (pre-filled), start_date, end_date, optional costs override
   - Calls `POST /backtests/run` with `persist: true`
   - Results: metrics grid, equity curve chart (recharts), trade list
   - Copyable `backtest_id` for next steps
   - Shows persisted backtest immediately; no hard refresh needed

4. **Evaluate Risk**
   - Automatically called via `POST /risk/evaluate` with the backtest_id
   - Decision badge + score gauge (0–100, higher=safer)
   - Lists failed rules and warnings
   - **Unmistakable veto banner if rejected.** Rose background, bold text, blocks progression to step 5

5. **Run AI Committee**
   - Provider selector: Mock (default, offline), Auto (fallback cascade), or specific cloud provider
   - Shows "requested provider" vs "selected provider" (auto mode fallback)
   - Six agent cards with reasoning (each scrollable)
   - CIO final decision card with `approved_by_risk` indicator
   - **Override banner** (amber, prominent) if code-level veto fired (raw CIO said PAPER_TRADE but risk rejected)
   - Copy `backtest_id` + `risk_evaluation_id` for step 6

6. **Create Paper Order** (HUMAN-ONLY, NEVER AUTOMATIC)
   - Button enabled only when:
     - Risk evaluation is APPROVED
     - User explicitly clicks "Create Order"
   - Form fields (required):
     - Symbol (pre-filled)
     - Quantity
     - Thesis (free-form text, audit trail)
     - Stop-loss price (enforced < entry reference, or < current close)
   - Calls `POST /paper/orders`
   - **Veto-aware error handling:** If risk changed or was vetoed, shows exact server rejection reason
   - Success: order fill summary (filled qty, fill price, NAV impact, P&L)

## API Client + NEXT_PUBLIC_API_URL

**Location:** `apps/web/app/lib/api.ts`

Typed async helpers for every backend endpoint. All routes pass:
- `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`)
- Normalized error handling (no retries)
- No fake data anywhere

Environment setup in `.env.local` or `.env.example`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The API base URL is baked at Next.js build time (no runtime fallback).

## How to Run

### Backend (from repo root or `apps/api`)

```bash
# 1. Ensure Postgres is running
docker compose --env-file .env -f infra/docker-compose.yml up -d postgres

# 2. Migrations
alembic -c infra/alembic.ini upgrade head

# 3. Seed assets and ingest data (optional; skips if already loaded)
python apps/api/scripts/seed_assets.py
python apps/api/scripts/ingest_ohlcv.py --all --start 2022-01-01 --end 2024-12-31

# 4. Start API
cd apps/api
uvicorn app.main:app --reload --port 8000
```

### Frontend (from repo root)

```bash
cd apps/web

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev

# Production build
npm run build

# Run production build locally
npm run start
```

Then navigate to:
- Dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs

**NEXT_PUBLIC_API_URL matters:** The frontend makes HTTP calls to the API. Default is `http://localhost:8000` (set in `.env.example`). In Docker or remote deployments, override it at build time or in `.env.local`.

## Empty-State Philosophy

**No fake data anywhere.** Every widget shows either:
- Real API data (charts, metrics, lists)
- An honest empty state (gray text, helpful copy)
- A loading spinner
- An error message with server details

Examples:
- No "sample backtest" if the user has run zero backtests
- No "mock positions" if the portfolio is empty
- No pre-filled journal entries

## What's Deferred (Backlog)

Explicitly NOT implemented in Phase 7+8 (note: Phase 9 completed stop-loss auto-monitoring, risk-off reset, and daily NAV snapshots):

- **Strategy-level P&L:** P&L shown only at portfolio level, not per-strategy.
- **Provider quality improvements:** Real Anthropic/Gemini/OpenRouter/Ollama refinements, retry-on-malformed-JSON. Phase 6 is single-shot, no auto-retry.
- **Parameter sweeps:** Manual strategy tweaking only; no grid search or optimization UI.
- **Walk-forward testing:** Single-window backtests only.
- **Overfitting detection:** No out-of-sample validation display.
- **Sector rotation:** Global market-level strategy; not yet implemented.
- **Multi-symbol batch research:** One symbol at a time in the pipeline.
- **Strategy authoring/editor UI:** JSON viewer only; no form-based strategy builder yet.
- **Global committee-list endpoint:** No list of all committee runs (only by backtest_id).
- **Light mode:** Dark-only by design.
- **Frontend component tests:** Integration tested only (E2E via API).
- **Docker image completeness:** Dockerfile excludes `packages/*` (local dev only).

## Safety Statements

**This is paper trading only.** Every page carries:
- Permanent amber badge in the top bar: "Paper trading only — simulated"
- Read-only footer on `/settings` and `/paper`: "All orders are simulated. No real money, no broker connectivity."
- Rose banner on `/paper` when risk-off is active

**Zero real-order capability.** No broker APIs, no live connections, no production secrets in the codebase.

## Testing

Frontend integration tests are in `apps/api/tests/test_routes.py` (API integration) and apps/web routes are exercised end-to-end via API. Unit test coverage of React components deferred.

**Current state:** 508 pytest tests passing (backend only). Frontend verified via `npm run build` (13 routes, all live; zero TypeScript errors).
