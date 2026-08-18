# QuantCouncil Assumptions and Engineering Decisions Log

Running log of engineering decisions and documented assumptions. Append new entries with a
date; do not rewrite history. Cross-references:
[architecture.md](architecture.md), [development-roadmap.md](development-roadmap.md),
[paper-trading-design.md](paper-trading-design.md), [risk-policy.md](risk-policy.md).

## 2026-07-06 — Foundation Phase Decisions

1. **Schema bootstrap via SQLAlchemy `create_all`; Alembic in Phase 2.** The foundation ships
   typed SQLAlchemy 2.x models plus an init script calling `create_all`. Alembic migrations
   arrive in Phase 2 once the schema is exercised by real data; until then
   `infra/migrations/` holds a README placeholder. Rationale: avoid migration ceremony while
   the schema is greenfield.

2. **Portable SQLAlchemy `JSON` column type instead of Postgres `JSONB`.** Models must also
   run against SQLite in tests; the portable `JSON` type works on both. Rationale: fast,
   dependency-free unit testing. Revisit JSONB (indexing, containment queries) only if query
   patterns demand it.

3. **`String` columns constrained by Python `StrEnum` constants instead of native DB enums.**
   Status/enum-ish columns (strategy lifecycle, order status, journal entry type, decisions)
   are plain strings validated in Python. Rationale: native Postgres enums make future
   migrations (adding/renaming members) painful; string columns keep Alembic diffs trivial.

4. **Paper fills simulated at the NEXT trading day's open price with zero slippage (v1).**
   Documented in [paper-trading-design.md](paper-trading-design.md). Rationale: simple,
   deterministic, unambiguous with daily bars; avoids pretending to intraday precision the
   data does not have. Slippage becomes a configurable fill-model parameter in a later phase.

5. **Market data via yfinance (free) with the `.NS` suffix for NSE symbols; Phase 2.** Symbols
   are stored plain (e.g. `RELIANCE`) in `assets`; the data connector appends `.NS` when
   querying yfinance. OpenBB is optional later. No paid data in v1 (local-first principle,
   see [non-goals.md](non-goals.md)).

6. **LLM provider for the AI committee: Anthropic Claude API, from Phase 5 onward.**
   `ANTHROPIC_API_KEY` is optional and never required for the foundation; the system must be
   fully functional without it except for the committee itself.

7. **PostgreSQL driver: `psycopg2-binary`.** Canonical connection string:
   `postgresql+psycopg2://quant:quant@localhost:5432/quantcouncil`. Rationale: mature,
   well-supported with SQLAlchemy 2.x; the `-binary` wheel avoids a local build toolchain.

8. **Monorepo Python setup via editable installs.** Each `packages/*` directory is an
   installable setuptools package. The root `requirements-dev.txt` installs the API
   requirements plus all packages editable plus pytest and httpx. Root `pytest.ini` sets
   `testpaths = apps/api packages`. Rationale: one virtualenv, real package boundaries,
   imports identical in tests and runtime.

9. **Repository location:** created at `C:\Users\motop\Desktop\quantcouncil` (Windows,
   local-first; no hosted deployment in v1).

10. **Strategy-format extension — `target.multiplier`.** The condition grammar in
    [strategy-format.md](strategy-format.md) allows an optional numeric `multiplier` on a
    `target` indicator reference (default 1.0), so rules like "volume > 1.5x volume_sma(20)"
    are expressible without a general expression language. `highest_close(window)` is defined
    over the prior `window` bars excluding the current bar, so breakout conditions are
    satisfiable.

11. **Provisional risk gates.** The default backtest gates in [risk-policy.md](risk-policy.md)
    (max_drawdown <= 20%, profit_factor >= 1.2, num_trades >= 20, win_rate >= 35%,
    sharpe >= 0.5) are starting points for a learning lab, not tuned values; every revision
    bumps `policy_version`.

## 2026-07-07 — Phase 2 (Data Layer) Decisions

12. **Unadjusted prices: yfinance called with `auto_adjust=False`.** Raw OHLC is kept as
    reported; splits and bonus issues appear as sharp price jumps on the ex-date rather than a
    smoothly adjusted series. Rationale: v1 prioritizes simplicity over a fully
    split/dividend-adjusted pipeline. `validate_ohlcv_report` flags >40% single-day
    close-to-close moves as "possible corporate action" warnings so the jumps are at least
    visible. See [data-layer.md](data-layer.md).

13. **Cache coverage decided by min/max-date containment, not a trading calendar.** A cached
    Parquet file covers a requested `[start, end]` range iff `min(date) <= start` and
    `max(date) >= end`. A requested boundary falling on a non-trading day can therefore
    under-cover and trigger a redundant re-fetch — accepted, since a redundant fetch merges
    harmlessly (idempotently) back into the same file. Exact calendar coverage tracking is a
    later refinement if it ever matters.

14. **Universe JSON located by walk-up path resolution; package not wheel-installable.**
    `data_connectors.universe` finds `data/nifty50_symbols.json` by walking up from its own
    source file (up to 8 parents), so it works from any working directory inside the monorepo
    checkout but NOT as a standalone wheel install (the data file would not be bundled).
    Accepted v1 simplification for a personal, local-first project developed via editable
    installs.

15. **Sector labels in `data/nifty50_symbols.json` are best-effort.** They are descriptive
    tags for display/grouping (manually assigned in the snapshot), not an official NSE or GICS
    classification; do not build logic that depends on their exact strings.

16. **Duplicate dates are a hard error at the validation layer.** `validate_ohlcv` raises
    `DataValidationError` on any duplicate date rather than silently deduplicating — a
    duplicate reaching validation indicates an upstream bug. Individual connectors may dedup
    their own raw provider responses (yfinance does, keeping the first row) before the shared
    validation runs, and the cache dedups on merge by design (newest fetch wins).

17. **EMA warm-up masked to NaN.** A recursive EMA (`ewm(span=window, adjust=False)`) is
    technically defined from the first bar, but `quant_engine.indicators.ema` masks its first
    `window - 1` values to NaN so every lookback indicator shares the same "leading values
    NaN" convention. Rationale: cross-indicator consistency beats squeezing a few extra
    early-but-unstable EMA values out of short histories.

18. **Wilder smoothing implemented as `ewm(alpha=1/window, adjust=False)`, not the classic
    seed.** RSI and ATR share one smoothing primitive: a full-history recursion seeded with the
    first observation, rather than the textbook simple-average-of-first-window seed. Values are
    deterministic and internally consistent but may differ slightly from third-party TA
    libraries. Both indicators mask their first `window` values to NaN. RSI boundary cases are
    explicit: zero-loss window -> 100, zero-gain -> 0, flat -> 50 (no division errors).

19. **`volatility` takes a PRICE series, not returns.** It computes daily simple returns
    internally (`pct_change`), takes the rolling standard deviation over `window`, and
    multiplies by `sqrt(periods_per_year)` (default 252, reusing
    `quant_engine.metrics.TRADING_DAYS_PER_YEAR`) when `annualize=True`. Rationale: one
    obvious call signature for API/strategy code, no ambiguity about whether returns were
    simple or log.

20. **API serves the universe from JSON, not the database.** `GET /assets` reads
    `get_universe()` directly; Postgres asset seeding, `ohlcv_daily` ingestion, the ingestion
    CLI, and Alembic migrations are deferred to Phase 3. The project owner's Phase 2
    specification superseded the original roadmap (which had placed those items in Phase 2 and
    the indicators in Phase 3); the deviation is recorded in
    [development-roadmap.md](development-roadmap.md).

## 2026-07-07 — Phase 3 (Quant Engine + Backtesting) Decisions

21. **Backtest cost defaults: 0.05% slippage per fill (adverse) and 0.05% transaction cost per
    side.** This supersedes the Phase 1 zero-slippage assumption (entry 4) *for the
    backtester*: `BacktestConfig` replaced `slippage_bps: float = 0.0` with
    `slippage_pct: float = 0.0005` and added `transaction_cost_pct: float = 0.0005`. Slippage
    is always adverse — buys fill at `price * (1 + slippage_pct)`, sells at
    `price * (1 - slippage_pct)`; costs are charged on both legs' notional. Rationale:
    zero-cost backtests systematically flatter high-turnover strategies; small non-zero
    defaults keep results honest while remaining overridable (including back to zero) per
    strategy via the new optional `costs` field. Note: [paper-trading-design.md](paper-trading-design.md)
    still specifies zero slippage for the Phase 6 paper engine — reconcile when it lands.

22. **Execution model: next-day-open fills only.** Signals computed on bar t's close fill at
    bar t+1's open; `next_day_open_fills=False` raises `NotImplementedError` rather than
    silently simulating same-close fills. An entry signal on the last bar of data is ignored
    (there is no next open). Rationale: one unambiguous, non-lookahead fill model, consistent
    with the daily-bar data.

23. **Position sizing precedence: `min(risk quantity, allocation quantity, cash quantity)`,
    whole shares, one position max.** At fill time (equity = cash, since the engine holds at
    most one position and no leverage exists) the traded quantity is the floor-minimum of:
    risk-percent sizing (`sizing.value * equity / (fill * stop.value)`), the 10% allocation cap
    (`max_allocation_pct * equity / fill`), and affordability including the entry cost. A
    result below 1 share means no trade (silently skipped). Rationale: mirrors the paper
    portfolio rules (1% risk, 10% allocation) and keeps every fill hand-checkable.

24. **Stops are recomputed from the actual fill price, never taken from the signal frame.**
    `generate_signals` emits a `stop_loss_price` column (`close * (1 - stop.value)` on entry
    bars) for auditability, but it is indicative only: the fill happens at the next open, so
    the backtester sets `stop = entry_fill * (1 - stop.value)`, fixed for the trade's life.
    The stop check is gap-aware: an open at/below the stop exits at the open (you cannot fill
    at a price the market gapped past); otherwise a low at/below the stop exits at the stop
    price — both with adverse slippage. The stop may trigger on the entry bar itself.

25. **Positions still open at the end of data are force-closed at the last bar's close**
    (with slippage and transaction cost), `exit_reason = "end_of_data"`. Rationale: metrics
    always reflect fully realized trades — no ambiguity about open-position accounting in
    win-rate/profit-factor style metrics. Documented v1 simplification; the trade record's
    reason field keeps such trades distinguishable.

26. **Metric conventions.** `profit_factor` is `float("inf")` when there are winning trades
    and zero losing trades, and `0.0` when there are neither; `sharpe` (Sharpe-like, risk-free
    rate 0 in v1, computed from the equity curve's daily returns with `ddof=1`) is `0.0` for
    fewer than 2 returns or zero/NaN volatility; `cagr` uses `n_periods = len(curve) - 1` bars
    against 252 trading days/year and returns `0.0` when `n_periods < 1` or the first equity
    value is `<= 0`; the zero-trade case yields 0.0 for all trade metrics rather than NaN or
    an error. All metric values flow through `quant_engine.metrics.compute_all` — the
    backtester inlines no metric math.

27. **`highest_close` exclusive-window semantics implemented in the interpreter, not the
    indicator.** `indicators.highest_close` stays a general-purpose inclusive rolling max;
    `signals.py` applies `.shift(1)` when evaluating strategy conditions, matching the
    strategy-format definition (prior `window` bars excluding the current bar). This closes
    the open thread recorded in the Phase 2 handoff. Rationale: keeps the indicator library
    free of strategy-format-specific conventions.

28. **Phase 3 API is stateless; persistence split into Phase 3.5.** `GET /strategies` serves
    the code-defined built-in templates and `POST /backtests/run` computes and returns results
    with `"persisted": false` — no `backtest_runs` or `strategy_definitions` rows, no
    artifacts on disk. The project owner's decision groups persistence, `GET /backtests/{id}`,
    `POST /strategies`, Alembic, Postgres ingestion/seeding, and the ingestion CLI into
    Phase 3.5; recorded in [development-roadmap.md](development-roadmap.md).

## 2026-07-07 — Phase 3.5 (Persistence) Decisions

29. **Alembic migrations are the schema authority; `create_all` is deprecated for real
    databases.** `infra/alembic.ini` and `infra/migrations/` hold production schema code;
    `apps/api/scripts/init_db.py` is kept only for SQLite unit tests. URL resolution happens at
    runtime in `infra/migrations/env.py`: `ALEMBIC_DATABASE_URL` env var if set, else
    `DATABASE_URL` from `.env` via app settings. Rationale: standard Alembic workflow, supports
    any deployment model, and decouples schema versioning from runtime code.

30. **Larger artifacts (equity curve, trade list) live on disk under `data/backtests/`,
    referenced from the DB row by repo-relative paths.** Keeps `backtest_runs` rows small and
    avoids bloating the database with JSON. Paths are stored repo-relative (e.g.,
    `data/backtests/...`) for portability across deployments. Rationale: artifacts are
    retrieval-oriented (read-heavy, rarely updated), and direct I/O is faster and cheaper than
    serialization.

31. **Persist-path failures are side-effect-free: the strategy row is only created after a
    successful run.** If backtest persistence fails (disk full, SQL error), the strategy row
    is not created — the next attempt will re-evaluate and create if needed. Rationale: no
    orphaned rows, no inconsistent state; clients can safely retry.

32. **Persisting a run of an unmodified builtin creates a persisted row sharing the builtin's
    name.** `POST /strategies` blocks custom strategies named after builtins, but
    `POST /backtests/run` with `persist=true` and a builtin strategy creates a new DRAFT row
    with the same name. This is an accepted v1 asymmetry; versioning and edit history arrive
    in a later phase. Rationale: simplifies the Phase 3.5 scope — all persistence code paths
    treat strategy identity uniformly (no special builtin handling in the backtest flow).

33. **Tests use SQLite in-memory (models are portable by design); Postgres-based integration
    is exercised manually via the CLI commands.** Unit tests run fast and offline via
    `pytest`; the persistence layer (strategy/backtest CRUD, migrations) is exercised this
    way. Alembic upgrade/downgrade safety and schema identity (vs. `create_all`) are proven by
    `apps/api/tests/test_migrations.py`. Real Postgres integration is manual: start Docker,
    run migrations, seed, ingest, hit the API. Rationale: keeps CI fast; Postgres-specific
    issues caught by explicit integration testing (not regression risk).

34. **Only successful runs are persisted (v1 simplification — no FAILED state).** If a backtest
    engine raises an error or returns None, no `backtest_runs` row is written. The tradeoff:
    simplifies the API schema and avoids querying why a run failed from the DB (run
    introspection deferred). Rationale: for a learning lab, deterministic successful runs are
    the value; failure diagnosis is typically via logs or re-running with debugging flags.

## 2026-07-07 — Phase 4 (Risk Engine) Decisions

35. **Risk score direction: higher = safer (inverted from draft).** Phase 4 ships with policy v1.0.0,
    which deliberately flips the old draft convention (0 = safest, 100 = riskiest) to the inverse:
    higher scores now mean safer strategies. Rationale: intuitive alignment with investment
    language ("higher quality = higher score") and to prevent confusion between score interpretation
    and decision signals. Old draft scores are not comparable; every evaluation stores `policy_version`
    for reproducibility.

36. **Percent-vs-fraction convention: all `_pct` fields in policy are PERCENT numbers, not fractions.**
    Policy YAML uses `15` to mean 15%, not 0.15. The engine converts metric fractions to percent
    (`metric × 100`) for comparison. Rationale: policy YAML readability and consistency with
    human-facing thresholds (e.g., "max 15% drawdown" reads more naturally than 0.15).

37. **NEEDS_REVIEW trigger: ≥2 warnings or profit_factor infinite with small sample (<50 trades).**
    No hard gates failed, but multiple warning flags or low-sample-size infinite profit-factor
    → NEEDS_REVIEW. Rationale: distinguishes borderline/suspicious cases from outright rejections,
    requiring human review before paper trading proceeds. The decision still blocks trading (like
    REJECTED) until override.

38. **Profit factor null (infinite) is treated as GOOD for gate purposes.** When a backtest has
    no losing trades, `profit_factor` is `null` (JSON). The hard gate `bt_min_profit_factor` is
    skipped; only the small-sample warning can fire. Rationale: infinite profit factor is
    theoretically excellent (no losses), but on thin sample evidence it is suspicious — the warning
    surfaces this without an outright rejection.

39. **Always-persist on backtest_id path; never on inline.** `POST /risk/evaluate` with
    `{"backtest_id": "..."}` always stores the evaluation in `risk_evaluations`. Inline payloads
    (no backtest_id) are evaluated but not persisted — no database row, no `risk_evaluation_id`.
    Rationale: backtest evaluations are permanent audit trails; inline evaluations are exploratory
    and ephemeral.

40. **Portfolio gates dormant until Phase 6.** `pf_max_open_positions` and `pf_max_portfolio_drawdown`
    are defined in policy YAML and implemented in the engine, but evaluated **only** when a
    `portfolio_context` dict is passed. Phase 4 backtests do not pass one; Phase 6 paper trading
    will. Rationale: gates require real portfolio state (live positions, NAV) that does not exist
    in Phase 4; deferring keeps Phase 4 scope tight.

41. **Data-quality detection not wired into backtest flow (Phase 4 placeholder).** The
    `data_quality_bad` and `data_quality_warnings` inputs to `evaluate()` are accepted but
    Phase 4 does not populate them automatically. The `bt_data_quality` gate checks the input flag;
    `warn_data_quality` passes through supplied warnings. Full data-quality detection (corruption,
    gaps, suspicious moves) integrates in Phase 5+.

42. **No per-request policy override in Phase 4.** Evaluation always uses the default packaged
    policy (`packages/risk_engine/risk_policy.yaml`). Dynamic policy selection (e.g., different
    thresholds per strategy type) deferred. Rationale: v1 simplification; policy versioning in
    the evaluation row enables A/B testing via separate runs.

43. **Auto-evaluation deferred: `POST /backtests/run` does not call `POST /risk/evaluate`.** The
    typical flow is manual: run backtest → get `backtest_id` → explicitly evaluate risk. Rationale:
    decouples backtesting from risk evaluation, allowing independent optimization of each. Auto-eval
    is a UX convenience deferred to a later phase.

44. **Snapshots enable reproducibility: every evaluation stores verbatim copies of inputs and
    policy.** `metrics_snapshot` and `policy_snapshot` fields contain the exact dict/YAML that
    produced the verdict. Any historical row can be re-evaluated in isolation, bit-for-bit identical.
    Rationale: audit trail, debugging, and policy evolution audit (comparing verdicts across
    policy versions).

## 2026-07-08 — Phase 5 (Paper Portfolio Engine) Decisions

45. **Immediate fills at a price reference (deviation from the next-day-open design).** The
    paper engine fills orders immediately at the request's `price_reference`, else the latest
    available cached close (via the shared OHLCV service, ~10-day lookback; 502 if
    unavailable) — orders go straight to FILLED or REJECTED, so PENDING is effectively
    transient and next-open fills remain a possible future refinement. This supersedes the
    next-day-open PENDING model in [paper-trading-design.md](paper-trading-design.md) (and
    entry 4) *for the paper engine as delivered*. The backtester's cost model is reused:
    BUY fill = `ref × (1 + 0.0005)`, SELL fill = `ref × (1 − 0.0005)`, transaction cost
    `qty × fill × 0.0005` per side — same defaults as the backtester, for comparability.
    Whole shares only; no partial fills, no order book, no intraday. Rationale: a versioned
    simplification that keeps Phase 5 scope tight without a bar-scheduling subsystem.

46. **SELL orders never require risk approval (no veto on exits).** BUY creation requires a
    persisted, approved risk evaluation; SELLs check only that an open position with enough
    quantity exists (plus thesis/exit_reason). Exits are risk-reducing and are always
    allowed — including during risk-off. Rationale: a veto that traps the portfolio in losing
    positions would increase risk, not reduce it.

47. **Add-on BUYs use weighted-average entry, and the new order's stop replaces the
    position's stop.** Adding to an existing position recomputes `avg_entry` as the
    quantity-weighted average of old and new fills, and the incoming order's
    `stop_loss_price` overwrites the position's previous stop. Rationale: one stop per
    position keeps the model simple; the most recent, risk-approved order carries the
    current exit intent.

48. **Realized P&L charges only the sell-side cost.** Per sale,
    `realized = (fill − avg_entry) × qty − sell-side cost`; entry-side costs were already
    debited from cash at BUY time and are not double-counted in realized P&L. Rationale:
    cash accounting stays exact, and P&L per sale remains hand-checkable.

49. **Positions are marked at average entry until the first mark-to-market.** NAV is
    `cash + Σ qty × mark`, where mark is `last_price` if the position has been
    marked-to-market and `avg_entry` otherwise. Rationale: marking is on demand (an explicit
    endpoint), not automatic; cost basis is the only honest mark before the first
    revaluation.

50. **Risk-off is a one-way latch with no reset endpoint in Phase 5.** Drawdown ≥ 8% at
    mark-to-market sets `risk_off=true` (with a RISK_EVENT journal entry) and it never
    auto-clears on NAV recovery; no reset endpoint exists yet (manual, journaled reset
    arrives later — documented limitation). Rationale: recovering NAV alone is not evidence
    the underlying problem is resolved; a human review must precede re-entry.

51. **Business rejections leave an audit trail; pure input errors do not.** On veto, limit,
    insufficient-cash, and oversell rejections, a `paper_orders` row with status REJECTED is
    persisted AND a RISK_EVENT trade_journal entry is written before the error returns; the
    HTTP error detail includes the rejected order id. Pure input errors (bad quantity,
    missing thesis, unknown ids) create no rows. Rationale: decisions the engine made are
    auditable; malformed requests are not decisions.

52. **Stop-losses are stored but not auto-triggered in Phase 5.** Every BUY requires a
    `stop_loss_price` (< reference price) and it is persisted on the position, but no
    monitoring evaluates stops against daily closes — exits are manual SELLs. Stop-loss
    evaluation on daily closes remains future work. Rationale: auto-triggering needs a
    scheduled evaluation loop that Phase 5 deliberately excludes.

53. **No schema changes for the paper engine.** The Phase 1 models (`paper_portfolios`,
    `paper_orders`, `paper_positions`, `trade_journal`) fit the delivered engine as-is — no
    new Alembic migration in Phase 5. Money is floats internally, stored rounded: 2 decimals
    for cash/NAV/P&L, 4 for prices. Rationale: the Phase 1 contract anticipated this layer;
    validating it unchanged is evidence the schema design was right-sized.

## 2026-07-08 — Phase 6 (AI Committee) Decisions

54. **Mock as the default provider, not auto.** Environment variable `QUANTCOUNCIL_AGENT_PROVIDER`
    defaults to `"mock"` (deterministic, offline), not `"auto"`. The system is fully functional
    with zero LLM credentials. When a user wants a premium provider, they explicitly set
    `ANTHROPIC_API_KEY` (or another key) and optionally override `QUANTCOUNCIL_AGENT_PROVIDER`
    or request `provider="auto"` per-request. Rationale: explicit is better than implicit;
    defaulting to auto would mask configuration errors (user sets a key but forgets to enable
    auto mode, system silently uses mock). Mock-first also keeps tests offline and repeatable.

55. **Provider priority order: Anthropic → Gemini → OpenRouter → Ollama → Mock.** In auto mode,
    the system tries providers in this order and picks the first `is_configured() == true`.
    Rationale: Anthropic (quality, official SDK), Gemini (free-tier cloud option), OpenRouter
    (flexible routing, free-model support), Ollama (local, privacy, no API keys), Mock
    (always available fallback).

56. **Raw CIO schema has no `approved_by_risk` field; final CIO has it (set by code).** The
    `cio_raw` agent output is a plain decision without risk context — it is deliberately
    untrusted. The final `CIODecision` schema includes `approved_by_risk` (copied by code from
    the persisted risk evaluation, not set by the agent) and `override_warning` (populated if
    code overrode a PAPER_TRADE). Rationale: strict separation of concerns; the agent debates
    and proposes; code applies the deterministic veto.

57. **Dual enforcement of the risk veto (code override + schema validator).** Layer 1: code in
    `run_committee()` detects raw CIO PAPER_TRADE + `approved_by_risk=false` → overrides to
    NO_TRADE with audit warning, then builds final CIODecision. Layer 2: Pydantic validator on
    `CIODecision` rejects any instance with `approved_by_risk=false` + `decision=PAPER_TRADE`
    before persistence. Both are independent (either could catch the error alone). Rationale:
    defense in depth; prevents accidental veto bypass via either code path or schema path.

58. **Seven-row persistence per committee run (5 analysts + raw CIO + final CIO).** One row per
    agent in `agent_decisions` table: technical_analyst (1), quant_researcher (2), bull (3),
    bear (4), risk_narrator (5), cio_raw (6), cio final (7). Rows 1–5 are trusted analysts;
    row 6 is the raw CIO (untrusted, no approved_by_risk); row 7 is the final CIO (with
    approved_by_risk + override_warning if veto fired). Rationale: full traceability; rows
    1–6 can be audited independently; row 7 is the authoritative decision.

59. **Mock CIO deliberately ignores risk approval for veto testability.** The mock provider's raw
    CIO agent always decides PAPER_TRADE if total_return > 0, WATCHLIST if == 0, NO_TRADE if
    < 0 — ignoring `approved_by_risk`. This means tests can verify that the code-level veto
    (Layer 1) works by checking that an approved_by_risk=false backtest triggers the override
    and produces NO_TRADE (from the mock's raw PAPER_TRADE). Rationale: deterministic test
    coverage of the veto mechanism; validates both layers are enforced.

60. **No committee-triggered paper orders (by design, permanent for Phase 6+).** The committee
    endpoint `POST /committee/evaluate` runs agents and returns a decision; it never calls
    `POST /paper/orders`. Paper order creation is manual: a human reads the decision and creates
    an order via `POST /paper/orders`, where the veto is enforced a second time (the evaluation
    is loaded again and its approved field checked). Rationale: keeps Phase 6 scope tight; human
    review between decision and execution is a feature (oversight); the veto being enforced twice
    (in the committee, in the order endpoint) increases confidence.

61. **Anthropic via official SDK (`anthropic.Anthropic` + `messages.parse()`).** The Anthropic
    provider uses `anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.parse()` for structured
    outputs. Other providers use REST + `httpx` for transport. Rationale: official SDK is mature,
    type-safe, and handles retries/errors; REST is simpler to implement for stateless cloud APIs
    and avoids dependency bloat (Anthropic SDK is not installed unless needed).

62. **Single-shot agent responses; no retry on malformed output (Phase 6 plumbing).** If a provider
    returns invalid JSON or fails schema validation, the error is 502 without automatic retry.
    Future phases may add resilience (exponential backoff, fallback to mock). Rationale: Phase 6
    focuses on plumbing verification; resilience logic arrives in Phase 7+.

63. **Agent context payload includes `committee_so_far` (outputs of prior agents).** Agents 2–6
    receive the previous agents' outputs in `committee_so_far` so the committee can debate and
    build consensus. Inputs also include deterministic context (strategy, metrics, risk verdict,
    trade summary). Rationale: agents can reference each other's reasoning without recomputing.

64. **Mock provider determinism extends to all six roles.** Every role has hardcoded deterministic
    logic based on metrics (e.g., Technical Analyst view based on total_return; Quant Researcher
    quality based on profit_factor and trade count). This makes mock outputs reproducible and
    tests verifiable. Rationale: the mock is a deterministic test double, not a simplified LLM.

## 2026-07-09 — Phase 7+8 (Dashboard) Decisions

65. **Dark-only UI design; no light mode.** The dashboard is dark-only by design: "AI quant command
    center" visual language with glassmorphism panels, cyan/teal accents, semantic status colors
    (emerald approved, rose rejected, amber warning/risk-off, sky watchlist), soft glows, tabular
    numbers, motion-enabled page transitions. Light mode is explicitly deferred. Rationale: coherent
    visual identity for a learning lab; reduces scope; can be revisited in a future phase if needed.

66. **No external UI libraries; Tailwind CSS v4 only (plus recharts and motion).** The frontend uses
    no shadcn, no Material UI, no other component libraries. Rationale: keep bundle size small,
    design system fully under control, no dependency sprawl. Recharts for charts (composable,
    responsive); motion for animations (compact, performant).

67. **Human-only paper order creation from the research pipeline.** The `/research` route's step 6
    ("Create Paper Order") button is disabled until risk evaluation is APPROVED and the user
    explicitly clicks; it is never automatic, never triggered by committee decisions, never
    triggered by backtest success. The form requires: symbol, quantity, thesis (free text),
    stop-loss price (enforced < reference). The `POST /paper/orders` endpoint rejects with the
    exact server reason on any veto. Rationale: keeps human oversight in the loop; a veto that
    silently blocks an automatic order is a user-hostile experience; explicit human click ensures
    intentionality.

68. **No fake data anywhere in the dashboard.** Every widget shows real API data or an honest
    empty/loading/error state. No sample backtests, no mock positions, no pre-filled journal
    entries, no placeholder cards. Rationale: truth-first design; users immediately see what data
    exists and what's missing; avoids confusion between real and simulated state.

69. **Two new list endpoints for dashboard usability.** `GET /backtests?limit=20` (newest-first
    persisted runs with metric subset) and `GET /risk/evaluations?limit=20` (newest-first
    evaluations) are simple query endpoints added to Phase 7+8. The backtest list omits large
    artifacts (equity curve, trade list); `/backtests/{id}` still returns them. Rationale: dashboards
    need fast, paginated lists; fat payloads are deferred to detail views.

70. **Veto visualization is unmistakable.** When risk evaluation is REJECTED (step 4 of the
    pipeline), a rose-background banner states "Risk: REJECTED — Paper trading blocked" (or similar),
    and the "Proceed to Committee" button is visually disabled. When the code-level veto fires
    (raw CIO says PAPER_TRADE but `approved_by_risk=false`), an amber-background banner states
    "CIO Decision Overridden — Risk veto enforced" with an explanation. Rationale: the veto is a
    critical safety feature; a dismissed or ambiguous visual breaks safety; color + text + button
    state + modal all signal the same message.

71. **MCP server removed from near-term roadmap.** The original Phase 8 proposed an MCP server
    exposing paper-trading tools. The project owner decision redirects Phase 8 scope elsewhere and
    demotes MCP to a far-future idea (zero priority, no committed timeline). The placeholder
    `packages/mcp_server` directory remains for future work but is not built or shipped. Rationale:
    keeps Phase 7+8 scope focused on the dashboard (the more urgent UX gap); MCP is useful only after
    the dashboard proves the research workflow works end-to-end; can be revisited when ROI is clear.

## 2026-07-11 — Phase 9 (Daily Ops) Decisions

72. **Stop-loss auto-triggered on daily closes, full-quantity exits only (Phase 9).** The daily-cycle
    endpoint (`POST /paper/portfolios/{id}/daily-cycle`) evaluates every open position's latest cached
    close against its stop-loss. If `latest_close ≤ stop_loss_price`, the entire position exits
    immediately at the breaching close via the normal SELL pipeline (slippage, costs, journaled).
    This is daily-close granularity only — intraday or next-open fills remain future refinements.
    Full-quantity-only exits simplify accounting; partial-position stops are deferred. Rationale:
    daily closes are the natural resolution for a daily-bar backtest engine; the v1 model keeps
    scope tight without an intraday bar or order-scheduling subsystem.

73. **Fetch-all-prices-first atomicity (Phase 9).** The daily-cycle endpoint fetches the latest close
    for every open position **before** evaluating stops or running mark-to-market. If any fetch fails
    (price unavailable, OHLCV service 502), the endpoint returns 502 and makes zero state changes —
    no partial fills, no partial marks, no snapshot. Rationale: preserves consistency; a fetch failure
    is transient and can be retried idempotently; a half-executed cycle would corrupt audit trails.

74. **One snapshot per portfolio per day, upsertable (Phase 9).** The `nav_snapshots` table has a
    unique constraint on `(portfolio_id, date)`. The daily-cycle endpoint upserts: if a row for today
    exists, it updates NAV/cash/drawdown/risk_off; if not, it inserts. Rationale: a portfolio's
    daily-cycle may be re-run multiple times on the same day for testing or recovery; the idempotent
    upsert avoids duplicates and permits safe retries.

75. **Risk-off reset is manual and journaled, with required note (Phase 9).** A new endpoint
    (`POST /paper/portfolios/{id}/risk-off/reset`) allows manual, explicit recovery from risk-off.
    Request body must include a non-empty `note` field (the reason for reset). The endpoint returns
    400 if the portfolio is not currently `risk_off=true` or if the note is empty. On success, the
    flag clears and a RISK_EVENT journal entry records the note. Rationale: risk-off latch is a
    critical safety feature (prevents new entries during drawdown); manual reset with a logged
    reason ensures human review and full audit trail before re-entry is permitted.

76. **Min-30-trades gate rejecting real sparse daily data is expected behavior (Phase 9).** The live
    shakedown seeded 50 assets, ingested 3 years of daily data (1118 bars), and ran 6 backtests on
    real data. All 6 evaluations were REJECTED by the risk engine's `bt_min_num_trades >= 30` hard
    gate. This is expected: real NIFTY 50 stock strategies on daily bars naturally produce
    20–15 trades per 3-year window, falling short of the 30-trade minimum. The gate correctly identifies
    sparse trading patterns as risky (high estimation error, regime-dependent luck). The live test
    confirmed the gate functions as designed; lowering the threshold for daily-bar strategies is a
    future policy refinement, not a bug. Rationale: the policy is conservative by design; tuning gates
    to historical data will be done when the next tranche of backtests matures.

## Post-Phase-9 — Un-numbered dashboard work (Learn section + "The Chamber" redesign)

77. **Entry 65 (2026-07-09, "Dark-only UI design") describes the dashboard's original look, since
    superseded.** Two changes shipped after Phase 9 closed, outside any numbered phase: (1) the
    `/learn` route, a standalone "Trading Mastery" curriculum (15 modules, 50 MDX lessons, a
    searchable glossary, a resources page, localStorage-backed lesson-completion tracking) bringing
    the dashboard to 11 top-level routes; and (2) "The Chamber," a full visual re-architecture
    (git history: "The Chamber, Phase 1-2" and "Phase 3-4") that replaced the glassmorphism/cyan-teal
    look entry 65 describes with anodized-graphite surfaces under one fixed light source, a
    two-channel warm/cool color system (warm for authority/consequence — verdicts, CIO, veto, ₹
    figures; cool for the machine — charts, deterministic data), a high-contrast serif reserved for
    verdict typography, the AI committee rendered as an "opposed chamber" (bull vs. bear across a
    shared axis), the risk veto rendered as a sealed plate (`VetoSeal`) instead of a banner, grouped
    bezel nav with a single traveling active-indicator, and a command palette. Entry 65 is left
    unedited per this log's append-only convention; [dashboard.md](dashboard.md) is the current
    source of truth for the shipped design. Rationale: the redesign and the Learn section were
    project-owner-directed additions delivered between sessions, outside the phase-gated roadmap;
    logging them here (rather than silently letting entry 65 go stale) keeps the assumptions log
    itself honest about what it does and doesn't still describe.

## Post-Phase-9 — Fundamental analysis

78. **Fundamentals were added on yfinance rather than OpenBB, after an empirical data-quality
    spike.** The project owner asked whether in-depth fundamental analysis was possible, and
    whether OpenBB should replace yfinance for it. OpenBB was rejected: it is an aggregator, and
    its stronger fundamentals providers are both paid and US-market-focused with thin NSE
    coverage — so with paid data permanently off the table (entry below), the only usable OpenBB
    backend for NIFTY-50 names is its own yfinance connector, i.e. identical data behind a much
    heavier dependency tree. `OpenBBConnector` therefore remains the inactive placeholder it has
    been since Phase 2. A spike against five deliberately different NIFTY-50 names (RELIANCE
    conglomerate, HDFCBANK bank, INFY IT services, ITC FMCG, ETERNAL young internet company)
    found free yfinance fundamentals substantially better than expected: 4–5 years of annual
    income statement / balance sheet / cash flow (41–92 line items each), 5–7 quarters of
    quarterly data, current through FY2026 and Q1 FY2027. Rationale: the decision rested on
    measured coverage for actual NSE symbols rather than on OpenBB's general reputation, since
    the aggregator's breadth is irrelevant when every non-free backend is out of scope.

79. **Ratio math lives in `quant_engine`, not in the connector, and prefers `.info` over
    recomputation.** `data_connectors.fundamentals` fetches raw data only; all ratios are
    computed in `quant_engine.fundamentals`, preserving the rule that quant_engine is the sole
    source of truth for numbers. Where yfinance's `.info` already reports a ratio (ROE, ROA),
    that value is used and statement-based computation is only a fallback — `.info` is TTM-based
    and likely more precise than an annual approximation. Current and quick ratios are always
    computed locally because yfinance never populates them for NSE symbols. yfinance's ratio
    units are inconsistent (`debtToEquity` and `dividendYield` are percentage points while
    margins and growth are fractions), which was verified by cross-checking `debtToEquity`
    against raw `Total Debt / Stockholders Equity` for RELIANCE/INFY/ITC rather than assumed from
    field naming. Rationale: silent unit errors in valuation ratios are the kind of bug that
    survives a passing test suite, so the units are pinned by measurement and documented in
    [data-layer.md](data-layer.md#fundamentals-post-phase-9-addition).

80. **Some fundamentals nulls are correct absences, not missing data, and `.info` can return
    partially populated.** Banks and similar financials report no classified (current vs.
    non-current) balance sheet, so `current_ratio`/`quick_ratio` are legitimately `null` for
    HDFCBANK — verified live. A company with no `Inventory` line (IT services) is treated as
    zero-inventory so its quick ratio correctly equals its current ratio, rather than being
    reported as unavailable. Separately, yfinance assembles `.info` from several upstream Yahoo
    modules and under rate limiting can return it partially populated: during live testing
    `priceToSalesTrailing12Months` came back `null` for RELIANCE from the running API while the
    same field returned 1.58 on a direct call moments later. A `null` therefore means "absent
    from this response," which is usually but not always "not reported." Rationale: recorded
    because a reader debugging a `null` field would otherwise reasonably suspect the extraction
    code, which was verified correct via the real code path.

81. **Fundamentals are not cached, unlike OHLCV.** Every request re-fetches from yfinance.
    Company fundamentals change at most quarterly, so the Parquet/DuckDB caching layer built for
    daily bars was not extended here. Rationale: a deliberate v1 simplification — the cache
    exists to avoid re-hitting the provider for long historical bar ranges, a pressure that does
    not apply to a single per-company snapshot; adding a cache mirroring `data_connectors.cache`
    remains straightforward if request volume ever warrants it.

82. **No paid data or paid services, ever — stronger than the "v1" framing in non-goals.md.** The
    project owner stated that never paying is the most important rule of the project.
    [non-goals.md](non-goals.md) #11 ("No premium or paid data in v1") is phrased as a v1-scoped
    decision, which understates this: it is permanent and not something a v2 revisits. Rationale:
    recorded explicitly because several non-goals are deliberately marked "v1" to signal they are
    amendable, and this one must not be read that way — it constrains every future data-source,
    hosting, and dependency decision, and it is why OpenBB's paid backends were never weighed
    against yfinance on quality grounds (entry 78).
