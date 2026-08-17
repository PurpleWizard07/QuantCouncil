# QuantCouncil Web Dashboard (Phase 7+8)

Modern, dark-only dashboard for the complete research and paper-trading pipeline. Built with Next.js 15 (App Router) and React 19.

## Design Direction — "The Chamber"

The dashboard went through a full visual re-architecture (git history: "The Chamber, Phase 1-2" and
"Phase 3-4") that replaced the original glassmorphism/cyan-teal look described in earlier drafts of
this document. What ships today (verified against `apps/web/app/globals.css` and the component tree):

- **Dark-only mode, one fixed light source.** No light mode, no toggle. Every panel is a solid
  machined-graphite plate (`.surface`) lit from one consistent top-left source: a specular highlight
  along the top edge plus a shadow cast down-right, rather than independently blurred glass rectangles.
  Real translucency/blur (`.glass`) is reserved for things that genuinely float above the page — the
  mobile nav drawer backdrop, the command palette, tooltips, modals — not structural chrome.
- **Two-channel color system**, layered on top of the semantic status colors:
  - **Warm channel** (`--color-warm`, a muted gold) marks authority and consequence — risk verdicts,
    the CIO decision, the veto seal, rupee figures. Used sparingly (a single `.metal-edge` hairline
    per screen, the `VetoSeal` component, warm accents on money).
  - **Cool channel** (`--color-accent`, teal/cyan) marks the machine — charts, deterministic data,
    the active-nav indicator, the API health lamp.
  - **Semantic status colors** remain underneath both channels: positive/emerald (approved, bullish,
    filled, gains), negative/rose (rejected, bearish, losses), warning/amber (needs-review, risk-off),
    watchlist/sky (secondary/neutral-informative decisions).
- **Three typographic voices, not one.** Sans (Geist) for UI chrome, labels, body, and tables; mono
  (Geist Mono) for tabular figures — tickers, ids, money — via `.font-mono-ui` /
  `.tabular-nums` (`font-variant-numeric: tabular-nums slashed-zero`); and a high-contrast serif
  (Fraunces) reserved exclusively for verdict moments (risk/CIO decisions, hero numerals) — never
  for body copy or UI chrome.
- **The committee as an "opposed chamber."** `/committee`'s `ChamberLayout` renders a presiding CIO
  head, an evidence row (Technical Analyst + Quant Researcher), a bull-vs-bear debate axis with the
  two cases facing each other across a shared center line (`DebateAxis`/`OpposedBar`, mirrored
  progress bars growing outward from the axis), and the Risk Narrator as the floor beneath it —
  each role settling into place with a per-card landing flash as the verdict resolves.
- **The veto as a sealed plate, not a banner.** `VetoSeal` renders a REJECTED or NEEDS_REVIEW
  decision as a locked plate with animated corner brackets and a warm metal-edge hairline — REJECTED
  gets the full warm glow and seal, NEEDS_REVIEW the same construction half-committed (fainter
  brackets, no glow). A `.veto-scope` filter (desaturate + reduced contrast) drains color from the
  specific metric block being overridden, scoped to that block, not the whole page.
- **Grouped bezel nav with a single traveling indicator.** The sidebar groups routes into three
  rooms — Council (research/market/strategies/backtests/risk/committee/paper/journal), Library
  (Learn), System (Settings) — and the active item's indicator (`ActiveTravelingLight`) is one
  shared Motion `layoutId` element that slides between positions on navigation rather than fading
  out and back in.
- **Command palette** (`⌘K`, `CommandPalette` in the top command bar) for fast navigation across
  every route.
- **Tabular numbers** via `font-variant-numeric: tabular-nums slashed-zero` for unambiguous data
  alignment.
- **No shadcn, no external UI libraries.** Tailwind CSS v4 only (`@tailwindcss/postcss`).
- **Frontend dependencies:** recharts (charts), motion (animations), no others.
- **The Learn section reskins the same material system** rather than diverging from it: `.learn-room`
  (scoped to `/learn/**`) swaps the token values for warmer, lower-chroma "reading room" paper tones,
  but every structural class (`.surface`, `.metal-edge`, `GlassCard`, etc.) is untouched, so existing
  components retint automatically.

## The 11 Top-Level Routes

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | Dashboard | Overview: NAV/cash/positions/risk-mode cards, latest backtest, latest risk evaluation, latest committee verdict, recent journal entries, quick actions (mark-to-market, create-default-portfolio) |
| `/research` | The 6-Step Pipeline | Guided workflow: select symbol → select strategy → run backtest → evaluate risk → run committee → create paper order |
| `/market` | Universe View | NIFTY 50 searchable table with sector filters; per-asset price chart, recent OHLCV, indicator preview with warm-up hints |
| `/strategies` | Strategy Cards | View strategy definitions with lifecycle badges (DRAFT/BACKTESTED/etc.), JSON viewers, links into research workflow |
| `/backtests` | Persisted Runs | List all stored backtest runs (newest-first, metric subset). Detail view: metrics grid, equity curve chart, trade list, veto status chip |
| `/risk` | Risk Evaluations | List recent evaluations (newest-first). Console: evaluate-by-backtest_id, score gauge, failed rules, policy/metrics snapshots |
| `/committee` | Committee Decisions | Run console with provider selector (mock/auto/anthropic/gemini/openrouter/ollama); six-agent debate cards laid out as the "opposed chamber" (CIO head, evidence row, bull-vs-bear axis, risk-narrator floor); override banner when code-level veto fired |
| `/paper` | Paper Fund Cockpit | NAV/cash/unrealized/realized P&L/risk-mode metrics; NAV history chart (Phase 9); RISK_OFF rose banner when active with inline reset form (Phase 9); "Run daily cycle" action (Phase 9: stop-loss sweep → mark-to-market → NAV snapshot); mark-to-market button; positions table with Open/Closed filters; full order form with veto-aware error handling; recent orders; permanent simulated-only footer |
| `/journal` | Trade Journal | Filterable audit timeline: portfolio/type/search filters; per-type badges; refs chips (thesis/rejection reasons/linked ids); expandable JSON; show-more pagination |
| `/learn` | Learning Center | Standalone "Trading Mastery" curriculum, unrelated to the research pipeline: a landing page (curriculum grid, 15 modules), module pages (`/learn/[moduleSlug]`), and lesson pages (`/learn/[moduleSlug]/[lessonSlug]`) rendering 50 MDX lessons (margin notes, quizzes, payoff diagrams, table of contents, prev/next nav, reading-time estimate, localStorage-backed completion tracking), plus `/learn/glossary` (client-side searchable glossary) and `/learn/resources` (books/papers/data/library reference page). Retints to warm "reading room" paper tones via `.learn-room`; educational only, not wired to the paper-trading engine. |
| `/settings` | Configuration (read-only) | API base URL, LLM provider env-var reference table, paper-trading-only safety statement. No broker settings exist. |

`/learn`'s five page templates (landing, module, lesson, glossary, resources) plus `/learn/[moduleSlug]`
and `/learn/[moduleSlug]/[lessonSlug]` expanding via `generateStaticParams` account for the bulk of
the difference between "11 top-level routes" above and the much larger static-page count `npm run
build` reports (see "Testing" below) — 15 modules and 50 lesson pages in total.

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

Explicitly NOT implemented in Phase 7+8 (note: Phase 9 completed stop-loss auto-monitoring, risk-off
reset, and daily NAV snapshots; commit `be22217` later resolved Docker image completeness, listed
below the "deferred" items rather than in them since it's no longer outstanding):

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

**Resolved since (not deferred anymore): Docker image completeness.** `apps/api/Dockerfile` (commit
`be22217`) now installs `packages/quant_engine`, `packages/risk_engine`, `packages/agents`, and
`packages/data_connectors` editable, plus `data/nifty50_symbols.json`. Only `packages/mcp_server`
stays excluded from the image, since nothing under `apps/api` imports it.

## Safety Statements

**This is paper trading only.** Every page carries:
- Permanent amber badge in the top bar: "Paper trading only — simulated"
- Read-only footer on `/settings` and `/paper`: "All orders are simulated. No real money, no broker connectivity."
- Rose banner on `/paper` when risk-off is active

**Zero real-order capability.** No broker APIs, no live connections, no production secrets in the codebase.

## Testing

Frontend integration tests are in `apps/api/tests/test_routes.py` (API integration) and apps/web routes are exercised end-to-end via API. Unit test coverage of React components deferred.

**Current state:** 508 pytest tests passing (backend only). Frontend verified via `npm run build`:
zero TypeScript errors, 82 static pages generated across 17 route entries in the build's route
list (11 top-level app routes, `/_not-found`, the `/dashboard` alias, and the Learn section's 5
templates — `/learn`, `/learn/glossary`, `/learn/resources`, `/learn/[moduleSlug]` expanding to 15
module pages, and `/learn/[moduleSlug]/[lessonSlug]` expanding to 50 lesson pages).
