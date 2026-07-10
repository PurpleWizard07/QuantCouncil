# QuantCouncil Persistence (Phase 3.5)

The authoritative reference for the Phase 3.5 persistence layer: environment setup, database migrations,
asset seeding, OHLCV ingestion, strategy persistence, backtest persistence, and the retrieval API.
Component boundaries are defined in [architecture.md](architecture.md); the delivery history and
deviations from the original plan are in [development-roadmap.md](development-roadmap.md); the
underlying engineering decisions are logged in [assumptions.md](assumptions.md).

Everything in this layer is deterministic Python (pandas/numpy/SQLAlchemy/Alembic). **No LLM touches,
adjusts, or produces any number here** — persistence records results already computed by the
deterministic backtesting engine.

## Environment Setup

### Configuration

The `.env` file at the repo root holds the single source of truth for database connection:

```
DATABASE_URL=postgresql+psycopg2://quant:quant@localhost:5432/quantcouncil
BACKTESTS_DIR=                    # optional; empty = default <repo_root>/data/backtests
```

`BACKTESTS_DIR` is the only new optional var (Phase 3.5). When empty, artifacts and artifact paths
default to `data/backtests/` relative to the repo root.

**Never commit `.env` — it contains local dev credentials.**

### Starting PostgreSQL

From the repo root with Docker Desktop running:

```
docker compose --env-file .env -f infra/docker-compose.yml up -d postgres
```

The `--env-file .env` flag is critical: Docker Compose otherwise looks for `.env` in `infra/` instead
of at the repo root.

PostgreSQL 16 listens on port 5432; the database is created and ready for migrations immediately.

## Migrations (Alembic)

Alembic is now the schema authority, replacing the `create_all` bootstrap.

### Configuration

- **Config file:** `infra/alembic.ini`
- **Script location:** `infra/migrations` (upgrade/downgrade Python scripts)
- **sqlalchemy.url:** left intentionally empty; URL is resolved at runtime

### URL Resolution

`infra/migrations/env.py` resolves the database URL at runtime with this precedence:

1. If `ALEMBIC_DATABASE_URL` environment variable is set, use it.
2. Otherwise, read `DATABASE_URL` from the `.env` file via the app's settings module.

This allows migrations to be run from any directory without hardcoding credentials into
`alembic.ini`.

### Running Migrations

From the repo root with the virtual environment activated:

```
.venv/Scripts/alembic.exe -c infra/alembic.ini upgrade head
```

Or, with the venv active, the shorter form:

```
alembic -c infra/alembic.ini upgrade head
```

**Downgrade** (rare, destructive):

```
alembic -c infra/alembic.ini downgrade base
```

This safely drops all tables (respects foreign key constraints). Use only for debugging a corrupted
development database.

### Initial Migration

The single migration `356085dfc427_initial_schema` creates:

- All 10 contract tables: `assets`, `ohlcv_daily`, `strategy_definitions`, `backtest_runs`,
  `risk_evaluations`, `agent_decisions`, `paper_portfolios`, `paper_orders`, `paper_positions`,
  `trade_journal`
- Unique constraint `uq_ohlcv_daily_asset_date` on `(asset_id, date)` in `ohlcv_daily` — no duplicate
  (asset, date) pairs.
- Indexes for query efficiency on foreign keys and date ranges.

Downgrade drops all tables FK-safely.

### Deprecation of `create_all`

`apps/api/scripts/init_db.py` is **deprecated for real databases** after Phase 3.5 and kept only
as a test convenience (SQLite in-memory unit tests still use it). For any development or deployment
using PostgreSQL, use Alembic migrations exclusively. The script will be removed or marked no-op in
a later phase.

**Permanent test:** `apps/api/tests/test_migrations.py` proves that:

- `alembic upgrade head` produces a schema identical to what `create_all` would produce.
- `alembic downgrade base` then `upgrade head` is safe and idempotent.

## Asset Seeding

Populates the `assets` table with the NIFTY 50 constituents from `data/nifty50_symbols.json`.

```
.venv/Scripts/python.exe apps/api/scripts/seed_assets.py
```

**Idempotent upsert:** runs any number of times with the same result (no duplicates).

**On first run:** 50 rows created.

**On rerun:** 50 rows unchanged.

**Console output example:**

```
Seeding assets from data/nifty50_symbols.json...
✓ Created: 50
✓ Updated: 0
✓ Unchanged: 0
```

**Requirements:**

- PostgreSQL must be running and reachable via `DATABASE_URL`.
- Migrations must have been run (`alembic upgrade head`).

**Failure modes:**

- Database unreachable → prints `"Database unreachable. Is PostgreSQL running?"` and exits with code 1.
- JSON file missing or malformed → fails with a clear error message.

## OHLCV Ingestion

Fetches daily OHLCV data for one or more NIFTY 50 symbols and writes only missing (asset_id, date)
rows to `ohlcv_daily`.

### Command

```
.venv/Scripts/python.exe apps/api/scripts/ingest_ohlcv.py [options]
```

### Options

| Option | Meaning | Example |
|---|---|---|
| `--symbol SYMBOL` | Ingest one symbol; repeatable. | `--symbol RELIANCE --symbol INFY` |
| `--all` | Ingest all 50 NIFTY constituents. | `--all` |
| `--start START_DATE` | Start date (ISO 8601, inclusive). | `--start 2024-01-01` |
| `--end END_DATE` | End date (ISO 8601, inclusive); default: today. | `--end 2024-12-31` |
| `--refresh` | Force re-download (bypass local cache, still merge idempotently). | `--refresh` |

### Execution

The script:

1. Resolves symbol(s) against the seeded `assets` table.
2. Fetches OHLCV via the existing Phase 2 `CachedConnector` (uses Parquet cache, no bypass).
3. Validates all data (same checks as the Phase 2 data layer; warnings are logged).
4. Inserts only rows where `(asset_id, date)` does not already exist in `ohlcv_daily`.

**Idempotent:** re-running the same command with identical dates skips all rows (no duplicates).

**Per-symbol console summary:**

```
RELIANCE [2024-01-01 to 2024-12-31]: 252 bars fetched → 248 inserted (4 skipped as duplicates)
```

**`--all` with mixed success:**

If any symbol fails (e.g., network error, invalid data), the script continues with the remaining
symbols and prints a summary table at the end:

```
Ingestion summary:
  RELIANCE:     248 inserted
  INFY:         251 inserted
  TCS:          ERROR - DataFetchError
  ...
Exit code: 1 (at least one failure)
```

**Exit codes:**

- `0`: all symbols succeeded.
- `1`: at least one symbol failed; check the summary table for details.

**Requirements and failure modes:**

- PostgreSQL must be running; unreachable → helpful `"Is Postgres running?"` message, exit 1.
- Assets must be seeded first; run `seed_assets.py` once before ingesting. Missing symbols produce
  a clear error.
- The Parquet cache in `data/processed/ohlcv/` is assumed valid (Phase 2 validation ran on fetch);
  if corrupted, delete the file(s) and re-run with `--refresh`.

**Example workflow:**

```bash
# One-time setup
alembic -c infra/alembic.ini upgrade head
python apps/api/scripts/seed_assets.py

# First ingest: 3 years of daily data for the full NIFTY 50
python apps/api/scripts/ingest_ohlcv.py --all --start 2022-01-01 --end 2024-12-31

# Later: refresh recent data in case of provider revisions
python apps/api/scripts/ingest_ohlcv.py --symbol RELIANCE --start 2024-10-01 --end today --refresh
```

## Strategy Persistence

### Model

Strategies exist in three states:

| Source | State | Created By | Editing | Lifecycle |
|---|---|---|---|---|
| Code-defined | immutable | Phase 1 | Cannot edit | Starts lifecycle at DRAFT (v1 design choice) |
| Persisted | mutable | `POST /strategies` | Can update | Starts at DRAFT |

**Key asymmetry (v1 design):** POST `/strategies` **blocks** custom strategies with the same name as a
builtin (e.g., cannot create a second `"SMA_CROSSOVER"`). However, running a builtin strategy with
`persist=true` and finding that no persisted strategy matches creates a new row sharing the builtin's
name. This is an accepted v1 simplification pending strategy versioning in a later phase.

### POST /strategies

**Request:**

```json
{
  "name": "Custom SMA 10/30",
  "rules": { ... },
  "status": "DRAFT"
}
```

The `rules` object is validated strictly against [strategy-format.md](strategy-format.md) via
`quant_engine.strategy.validate_strategy`.

**Responses:**

| Code | Meaning |
|---|---|
| `201` | Created; response body contains `{id, name, status, source: "persisted", created_at}`. |
| `400` | Invalid JSON or strategy rules fail validation; error body names the offending field. |
| `409` | Name conflict: a builtin or persisted strategy with this name already exists. |
| `503` | Database unreachable; error body explains. |

**Success example:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Custom SMA 10/30",
  "status": "DRAFT",
  "source": "persisted",
  "created_at": "2026-07-07T10:30:00Z",
  "rules": { ... }
}
```

## Backtest Persistence

### Persist Flag

`POST /backtests/run` gains a `persist` flag (default `false`):

```json
{
  "strategy": { "name": "sma_crossover_20_50", "universe": ["RELIANCE", "..."], "entry": { "...": "full definition per strategy-format.md" } },
  "symbol": "RELIANCE",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "persist": true
}
```

`strategy` must be the **full strategy JSON** (e.g. copied from `GET /strategies`, minus the
`source`/`id`/`status`/`created_at` metadata keys) — not just a strategy name. Alternatively,
pass `"strategy_id": "<uuid>"` (and omit `strategy`) to run a persisted strategy by reference.

- `persist=false` (default): exactly the Phase 3 stateless behavior; results computed, not stored.
- `persist=true`: results stored in `backtest_runs` plus artifacts on disk.

**Mutual exclusivity:**

- `strategy` and `strategy_id` are mutually exclusive. Supply exactly one.
- If both or neither: `400` error.
- If `strategy_id` is malformed (not a valid UUID): `400`.
- If `strategy_id` does not exist: `404`.

### Artifact Storage

When `persist=true`, a successful run writes two files:

1. **Equity curve:** `<backtests_dir>/<run_id>/equity_curve.json` — array of `[date, equity]` pairs.
2. **Trade list:** `<backtests_dir>/<run_id>/trades.json` — array of trade records (same schema as Phase 3).

Where `<backtests_dir>` is `BACKTESTS_DIR` from `.env` (or `data/backtests/` if empty).

Paths stored in the `backtest_runs` row are **repo-relative** (e.g., `data/backtests/...`) for
portability.

### Strategy Lifecycle (Persist Mode)

When `persist=true` and the backtest **succeeds**:

1. If a `strategy` name is given: resolve or create the strategy row.
   - If a persisted strategy has the same name **and identical rules**, reuse it (no change to its status).
   - If a persisted strategy has the same name but **different rules**, `409` conflict.
   - Otherwise, create a new DRAFT row.
2. Promote the strategy from DRAFT → BACKTESTED (idempotent; if already BACKTESTED, no change).
3. Store the run in `backtest_runs` referencing the strategy.

**Side-effect-free failures:** if persistence fails (e.g., disk full, SQL error), the strategy row
**is not created** — no partial state.

**Only successful runs persisted (v1 simplification):** if the backtest engine raises an error or
returns `None`, no row is written. The trade-off: simplifies the API (no `FAILED` state) but
means you cannot query why a run did not work from the database.

### Response

Success (`201`):

```json
{
  "backtest_id": "550e8400-e29b-41d4-a716-446655440000",
  "persisted": true,
  "strategy": { "id": "...", "name": "...", ... },
  "total_return": 0.25,
  "max_drawdown": 0.15,
  "num_trades": 42,
  ...
}
```

Failure scenarios:

| Code | Meaning |
|---|---|
| `400` | Invalid request (both/neither strategy+strategy_id, malformed UUID, invalid dates). |
| `404` | strategy_id references an unknown strategy. |
| `409` | persist=true and strategy name conflicts with a persisted row (different rules). |
| `503` | Database unreachable or persistence failed (disk, SQL error). |

## Retrieval API

### GET /backtests/{id}

**Request:**

```
GET /backtests/550e8400-e29b-41d4-a716-446655440000
```

**Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "persisted": true,
  "strategy_id": "...",
  "symbol": "RELIANCE",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 1000000.0,
  "status": "COMPLETED",
  "completed_at": "2026-07-07T10:30:00Z",
  "total_return": 0.25,
  "cagr": 0.18,
  "max_drawdown": 0.15,
  "win_rate": 0.52,
  "avg_win": 5000.0,
  "avg_loss": -3200.0,
  "profit_factor": 1.8,
  "num_trades": 42,
  "exposure_time": 0.65,
  "sharpe": 0.75,
  "best_trade": 12000.0,
  "worst_trade": -8500.0,
  "starting_capital": 1000000.0,
  "final_equity": 1250000.0,
  "equity_curve": [ [date1, equity1], [date2, equity2], ... ],
  "trades": [ { ... }, ... ]
}
```

All 14 metrics are included (infinity serialized as `null`). Artifact files are loaded from disk and
embedded in the response (for browser viewing and API clients).

**Errors:**

| Code | Meaning |
|---|---|
| `400` | Malformed UUID. |
| `404` | ID not found in `backtest_runs`. |
| `500` | Artifact file missing on disk (indicates corruption; error body explains). |
| `503` | Database unreachable. |

## Error Behavior and Degradation

### GET /strategies (Database Down)

Returns `200` with the built-in templates only:

```json
{
  "count": 3,
  "strategies": [ ... ],
  "warning": "Database unavailable; showing built-in strategies only"
}
```

Local-first degradation: the API remains usable for backtesting and indicators even if Postgres is
offline.

### Ingestion and Seeding (Database Down)

Both scripts detect database unreachability and exit with code 1 and a helpful message:

```
Database unreachable. Is PostgreSQL running?
```

No partial state is left behind.

## Testing Strategy

### Unit Tests (SQLite)

`apps/api/tests/` and `packages/` unit tests use SQLite in-memory for speed (models are portable by
design). The persistence layer (strategy/backtest CRUD) is exercised in this mode. Mocked:
yfinance, filesystem operations (artifacts written to temp directories).

### Integration Tests (Manual via CLI)

Postgres-based integration is exercised manually via the CLI commands documented above. A working
session:

```bash
# 1. Start Postgres
docker compose --env-file .env -f infra/docker-compose.yml up -d postgres

# 2. Migrate schema
alembic -c infra/alembic.ini upgrade head

# 3. Seed assets
python apps/api/scripts/seed_assets.py

# 4. Ingest data
python apps/api/scripts/ingest_ohlcv.py --symbol RELIANCE --start 2024-01-01 --end 2024-12-31

# 5. Save a custom strategy (my_strategy.json = full JSON per strategy-format.md;
#    builtin names are reserved, so give your copy its own name). Returns {"id": "<uuid>", ...}
curl -X POST http://localhost:8000/strategies \
  -H "Content-Type: application/json" -d @my_strategy.json

# 6. Run and persist a backtest of it by reference
curl -X POST http://localhost:8000/backtests/run \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "<uuid>", "symbol": "RELIANCE", "start_date": "2024-01-01", "end_date": "2024-12-31", "persist": true}'

# 7. Retrieve persisted run
curl http://localhost:8000/backtests/{backtest_id}

# 8. Query database directly
psql -h localhost -U quant -d quantcouncil -c "SELECT COUNT(*) FROM backtest_runs;"
```

### Reproducibility

Every persisted run stores:

- All inputs: strategy definition (rules), symbol, date window, initial capital, slippage/cost overrides.
- All outputs: the 14 metrics, equity curve, trades.

Re-running the same backtest with the same inputs **must** reproduce the same metrics (foundation
for Phase 8 reproducibility audit, per [development-roadmap.md](development-roadmap.md)).

## Limitations (v1)

1. **No strategy editing or versioning.** Strategies are immutable after creation. To modify, create
   a new strategy with a different name. Version tracking arrives in a later phase.
2. **Builtin-name asymmetry.** Cannot create a custom strategy named after a builtin (e.g.,
   `"sma_crossover_20_50"`), but running a builtin with `persist=true` creates a persisted row
   sharing the builtin's name. Documented v1 design choice pending future versioning.
3. **Only successful runs persisted.** Failed backtests do not create `backtest_runs` rows — no
   `FAILED` state. Simplifies the API but prevents querying failure reasons from the database.
4. **No backtest parameterization beyond what's in strategy rules and backtest request.** Custom
   slippage/costs per strategy via the `costs` field; per-run overrides via the
   `POST /backtests/run` request body. Param-sweep automation is deferred.
5. **Artifact files are git-ignored and not backed up.** `data/backtests/` is in `.gitignore`.
   Long-term persistence requires external backup.

## Running the Tests

From the repo root (uses `pytest.ini`; `testpaths = apps/api packages`):

```
.venv/Scripts/python.exe -m pytest -q        # or plain `pytest` inside the activated venv
```

Persistence-related tests are in:

- `apps/api/tests/test_persistence.py` — strategy/backtest CRUD via the API, SQLite in-memory.
- `apps/api/tests/test_migrations.py` — Alembic upgrade/downgrade safety and schema identity.

The repo-wide suite (310 tests) runs offline; no test touches the network or real Postgres.
