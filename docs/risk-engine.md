# QuantCouncil Risk Engine (Phase 4)

The authoritative reference for the Phase 4 Rule-Based Risk Engine: policy configuration,
deterministic evaluation, risk scoring, hard veto enforcement, and API surface. Component
boundaries are defined in [architecture.md](architecture.md); the delivery history and
deviations from the original plan are in [development-roadmap.md](development-roadmap.md); the
underlying engineering decisions are logged in [assumptions.md](assumptions.md).

Everything in this layer is deterministic Python (`packages/risk_engine`) with **binding veto
power** over the entire pipeline. **No LLM touches, adjusts, or produces any number here** —
every verdict is computed from deterministic policy gates applied to backtest metrics and
portfolio constraints. LLM agents (Phase 6) may narrate risk; they never compute or decide it.

## Philosophy: "AI Can Propose. Math Can Approve. Risk Can Veto."

The risk engine is the **hard gate** between proposed strategies and paper trading. When the
engine returns `approved=false`, the CIO agent decision **must not** be `PAPER_TRADE` — this
constraint is **enforced in code** (a Pydantic validator in `packages/agents`), not just in
prompts. Non-approved evaluations block paper trading exactly like rejections until a human
re-runs or overrides with a journaled note.

## Risk Policy Configuration (Versioned)

The policy is a versioned YAML file `packages/risk_engine/risk_policy.yaml` loaded at engine
startup via `risk_engine.policy.load_policy()`. Malformed YAML or schema violations raise
`RiskPolicyError` with a clear message. Pydantic enforces `extra="forbid"` — no unknown fields.

### Current Policy (v1.0.0)

```yaml
policy_version: "1.0.0"

hard_gates:
  minimum_backtest_trades: 30
  max_allowed_drawdown_pct: 15
  minimum_profit_factor: 1.2
  minimum_total_return_pct: 0
  minimum_sharpe_like: 0
  max_position_size_pct: 10
  max_risk_per_trade_pct: 1
  stop_loss_required: true
  reject_if_data_quality_bad: true

portfolio_gates:
  max_open_positions: 10
  max_portfolio_drawdown_pct: 8

warning_thresholds:
  warn_if_exposure_time_pct_above: 80
  warn_if_trade_count_below: 50
  warn_if_profit_factor_below: 1.5
  warn_if_drawdown_pct_above: 10
```

**Convention:** All `_pct` fields are **PERCENT numbers** (e.g., `15` means 15%, not 0.15).
The engine converts metric fractions to percent (`metric × 100`) for comparison.

**Versioning:** `policy_version: "1.0.0"` supersedes the old provisional "v1" draft. This
redesign includes a score-direction flip (higher = safer, not 0 safest) and changes to hard
gates (e.g., `minimum_backtest_trades: 30` instead of `bt_num_trades >= 20`). Every change to
gates, thresholds, or weights bumps the version. Every `risk_evaluations` row stores the
`policy_version` it was evaluated under, so historical verdicts remain reproducible against
the policy that produced them.

## Engine (`packages/risk_engine/risk_engine/engine.py`)

### API Entry Point

```python
evaluate(
    metrics: Dict,
    strategy: Dict,
    policy: Policy,
    trades: Optional[List[Dict]] = None,
    data_quality_bad: Optional[bool] = None,
    data_quality_warnings: Optional[List[str]] = None,
    portfolio_context: Optional[Dict] = None,
    strategy_config: Optional[Dict] = None
) -> RiskEvaluationResult
```

Returns a pydantic `RiskEvaluationResult` (contract below). **No per-request policy override**
in Phase 4 — always uses the packaged default policy.

### Hard-Gate Rule IDs (Any Failure → REJECTED)

| Rule ID | Gate | Source |
|---|---|---|
| `bt_min_trades` | `num_trades >= policy.hard_gates.minimum_backtest_trades` | `metrics.num_trades` |
| `bt_max_drawdown` | `max_drawdown <= policy.hard_gates.max_allowed_drawdown_pct` | `metrics.max_drawdown * 100` |
| `bt_min_profit_factor` | `profit_factor >= policy.hard_gates.minimum_profit_factor` OR `profit_factor` is `null` (infinite) | `metrics.profit_factor` |
| `bt_min_total_return` | `total_return >= policy.hard_gates.minimum_total_return_pct / 100` | `metrics.total_return * 100` |
| `bt_min_sharpe` | `sharpe >= policy.hard_gates.minimum_sharpe_like` | `metrics.sharpe` |
| `bt_stop_loss_required` | Strategy rule defines a stop-loss | `strategy.stop_loss.type` (must exist) |
| `bt_data_quality` | `data_quality_bad != true` | passed input; Phase 4 does not wire live data-quality detection |
| `bt_max_position_size` | `strategy_config.max_allocation_pct <= policy.hard_gates.max_position_size_pct` | requires `strategy_config` input; skipped with advisory warning if absent |
| `bt_max_risk_per_trade` | `strategy.position_sizing.value * 100 <= policy.hard_gates.max_risk_per_trade_pct` | `strategy.position_sizing.value` |

**Special case: `profit_factor` null (JSON `null`).** When a backtest has no losing trades,
`profit_factor` is `null` (infinite). This is treated as **GOOD**: the `bt_min_profit_factor`
gate is skipped; only the small-sample warning can fire if triggered.

### Warning Rules (Never Force Rejection Alone)

Warning rule IDs are machine-readable strings: `"<rule_id>: <message>"` so they remain parseable
by downstream code.

| Rule ID | Condition | Severity |
|---|---|---|
| `warn_low_trade_count` | `num_trades < policy.warning_thresholds.warn_if_trade_count_below` | Statistical unreliability |
| `warn_low_profit_factor` | `profit_factor < policy.warning_thresholds.warn_if_profit_factor_below` AND `profit_factor` is finite | Weak margin of safety |
| `warn_high_drawdown` | `max_drawdown > policy.warning_thresholds.warn_if_drawdown_pct_above` | Large peak-to-trough loss |
| `warn_high_exposure` | `exposure_time > policy.warning_thresholds.warn_if_exposure_time_pct_above` | Nearly always in market |
| `warn_loss_win_asymmetry` | `abs(avg_loss) > 2 × avg_win` | Risk uncompensated by reward |
| `warn_best_trade_concentration` | `best_trade > 0.5 × gross_winning_pnl` | Strategy overly dependent on one win |
| `warn_profit_factor_infinite_small_sample` | `profit_factor` is `null` (infinite) AND `num_trades < 50` | No losses observed, limited sample |
| `warn_position_size_unevaluated` | `strategy_config` input is missing (so `bt_max_position_size` could not be checked) | Incomplete input |
| `warn_metric_unavailable_<field>` | Required metric field is missing/None | Data input issue |
| (passthrough) `warn_data_quality` | `data_quality_warnings` list supplied at input (Phase 4 placeholder) | Input flag |

### Decision Logic

```
if any hard gate failed:
    decision = REJECTED
    approved = false
else if (0 to 1 minor warnings) OR no failures:
    decision = APPROVED
    approved = true
else if ≥2 warnings OR warn_profit_factor_infinite_small_sample present:
    decision = NEEDS_REVIEW
    approved = false
```

- **APPROVED:** All hard gates passed. Strategy may proceed toward paper trading (still subject to CIO decision). `approved = true`.
- **REJECTED:** At least one hard gate failed. Paper trading is blocked. `approved = false`.
- **NEEDS_REVIEW:** No hard gates failed, but ≥2 warnings or an infinite-profit-factor small-sample flag exists. A human must review. `approved = false` — blocks paper trading exactly like REJECTED until override.

`approved` is derivable but stored explicitly for auditability: `approved == (decision == "APPROVED")`. A Pydantic validator enforces this invariant.

### Risk Score (0–100, Higher = Safer)

The score is **informational only** — it never overrides the gates. A low score with a passing
hard gate is still APPROVED.

**Composition:**

Start at 100, then apply capped proportional deductions:

| Component | Max Deduction | Applied When |
|---|---|---|
| Drawdown severity | 40 | `max_drawdown` approaches/exceeds gate; scales from 0 to 40 as drawdown rises from 0 to 15% |
| Low profit factor | 20 | `profit_factor` near minimum gate; scales linearly from 1.2 to 0 |
| Low trade count | 15 | `num_trades` below recommendation; scales from 50 to 30 |
| Poor Sharpe | 15 | `sharpe` below gate; scales linearly |
| High exposure | 10 | `exposure_time` near 100% (busy portfolio) |
| Warning penalty | 3 per warning | For each warning up to 5 warnings (max 15 total) |

**Formula:** (exact deductions documented in `engine.py` module docstring)

```
score = 100
score -= drawdown_deduction(max_drawdown, gate=15)
score -= profit_factor_deduction(profit_factor, gate=1.2)
score -= trade_count_deduction(num_trades)
score -= sharpe_deduction(sharpe, gate=0)
score -= exposure_deduction(exposure_time)
score -= min(num_warnings * 3, 15)
score = max(0, min(score, 100))  # clamp to [0, 100]
```

**Interpretation:**

- **80–100:** Low risk. Strong metrics across all dimensions; strategy shows genuine promise.
- **60–79:** Moderate risk. Most gates pass, but some metrics warrant watching (e.g., exposure or concentration).
- **40–59:** Material risk. Multiple warning flags or borderline gate performance. Likely triggers NEEDS_REVIEW.
- **0–39:** High risk. Many warnings, thin margin of safety, or small sample. Expect REJECTED or NEEDS_REVIEW.

## Output Contract (Pydantic, `extra="forbid"`)

```json
{
  "decision": "APPROVED" | "REJECTED" | "NEEDS_REVIEW",
  "approved": true | false,
  "risk_score": 0,
  "policy_version": "1.0.0",
  "reasons": ["Human-readable explanation"],
  "failed_rules": ["bt_max_drawdown", "bt_min_profit_factor"],
  "warnings": [
    "warn_high_drawdown: max_drawdown 18% > gate 15%",
    "warn_low_trade_count: 42 < threshold 50"
  ],
  "metrics_snapshot": {
    "total_return": 0.25,
    "max_drawdown": 0.18,
    "num_trades": 42,
    ...
  },
  "policy_snapshot": {
    "policy_version": "1.0.0",
    "hard_gates": { ... },
    "warning_thresholds": { ... },
    ...
  }
}
```

| Field | Type | Meaning |
|---|---|---|
| `decision` | Enum | One of `APPROVED`, `REJECTED`, `NEEDS_REVIEW` |
| `approved` | bool | `true` iff `decision == "APPROVED"` (enforced by validator) |
| `risk_score` | int [0,100] | Higher = safer (higher is good); informational, never overrides gates |
| `policy_version` | str | The policy version this evaluation used (e.g., `"1.0.0"`) |
| `reasons` | [str] | Human-readable list of why the decision was made |
| `failed_rules` | [str] | Machine-readable rule ids of every gate that failed (empty if APPROVED/NEEDS_REVIEW) |
| `warnings` | [str] | Machine-readable warnings (never empty unless no warnings); formatted `"<rule_id>: <message>"` |
| `metrics_snapshot` | Dict | Verbatim copy of the input metrics dict for reproducibility |
| `policy_snapshot` | Dict | Verbatim copy of `policy.model_dump()` for reproducibility |

**Snapshots enable standalone reproduction:** any historical `risk_evaluations` row can be
re-evaluated in isolation against the policy that produced it, byte-for-byte identical.

## API Endpoints (`apps/api/app/routers/risk.py`)

### POST /risk/evaluate

Evaluate backtest metrics against the risk policy. Body is **mutually exclusive:**

**Path A: Evaluate a persisted backtest**

```json
{
  "backtest_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

- Loads the backtest row's metrics and strategy; fetches trades from disk artifact.
- **Always persists** the evaluation to `risk_evaluations` with a new row and `risk_evaluation_id`.
- Returns full `RiskEvaluationResult` + `risk_evaluation_id`.

**Path B: Evaluate inline (never persisted)**

```json
{
  "metrics": { "total_return": 0.25, "max_drawdown": 0.15, ... },
  "strategy": { "name": "sma_20_50", "stop_loss": { "type": "percent", "value": 0.02 }, ... },
  "trades": [ { "entry_date": "2024-01-15", "exit_date": "2024-01-20", ... }, ... ],
  "config": { "max_allocation_pct": 0.10 }
}
```

- Evaluates the supplied inputs.
- **Never persisted** — no `risk_evaluation_id`, no database row.
- Returns `RiskEvaluationResult` with `persisted: false` flag.

**Response (200):**

```json
{
  "risk_evaluation_id": "550e8400-e29b-41d4-a716-446655440001",
  "backtest_id": "550e8400-e29b-41d4-a716-446655440000",
  "persisted": true,
  "decision": "APPROVED",
  "approved": true,
  "risk_score": 72,
  "policy_version": "1.0.0",
  ...full RiskEvaluationResult...
  "created_at": "2026-07-07T10:30:00Z"
}
```

**Error responses:**

| Code | Meaning |
|---|---|
| `400` | Malformed JSON; both `backtest_id` and inline payload supplied; neither supplied; invalid UUID |
| `404` | Backtest ID not found in database |
| `503` | Database unreachable |

### GET /risk/evaluations/{id}

Retrieve a persisted risk evaluation by id.

**Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "backtest_id": "550e8400-e29b-41d4-a716-446655440000",
  "strategy_id": "550e8400-e29b-41d4-a716-446655440002",
  "decision": "APPROVED",
  "approved": true,
  "risk_score": 72,
  "policy_version": "1.0.0",
  "reasons": [...],
  "failed_rules": [],
  "warnings": [],
  "metrics_snapshot": {...},
  "policy_snapshot": {...},
  "created_at": "2026-07-07T10:30:00Z"
}
```

**Error responses:**

| Code | Meaning |
|---|---|
| `400` | Malformed UUID |
| `404` | ID not found |
| `503` | Database unreachable |

### GET /backtests/{id}/risk

Latest risk evaluation for a backtest.

**Response (200):**

Same as `GET /risk/evaluations/{id}`, but sourced from the backtest.

**Response (404, two flavors):**

- Backtest not found: `"Backtest <id> not found"`
- Backtest found, but no evaluation yet: `"Backtest <id> has no risk evaluation yet"`

## Persistence

### Schema Change (Alembic Migration)

New migration `853ec0ddce66_risk_evaluation_snapshots` (down_revision = `356085dfc427`)
adds two nullable JSON columns to `risk_evaluations`:

- `metrics_snapshot` (JSON): Verbatim copy of input metrics for reproducibility.
- `policy_snapshot` (JSON): Verbatim copy of the policy that produced this verdict.

**Upgrade:** Adds columns; existing rows have NULL snapshots (safe).
**Downgrade:** Drops the columns.

Verified against scratch SQLite; schema-equivalence test confirms Alembic produces
the same schema as `create_all` would.

### Evaluation Persistence

**Always-persist on backtest_id path:** When `POST /risk/evaluate` receives
`{"backtest_id": "..."}`, the evaluation is **always** stored in `risk_evaluations`,
creating a new row with a unique `risk_evaluation_id`.

**Never-persist on inline path:** Inline payloads (no `backtest_id`) are evaluated
but **not stored** — no database write, no `risk_evaluation_id`.

### Repository Functions

`apps/api/app/db/repository/risk.py`:

- `create_risk_evaluation(...)` — insert a new row; return the id and full result.
- `get_risk_evaluation(id)` — fetch by id; return full result with snapshots.
- `get_latest_risk_evaluation_for_backtest(backtest_id)` — most recent evaluation
  for a backtest; return full result or None.

## Typical Workflow

1. **Run a backtest and persist it:**
   ```bash
   curl -X POST http://localhost:8000/backtests/run \
     -H "Content-Type: application/json" \
     -d '{
       "strategy": {...full strategy JSON...},
       "symbol": "RELIANCE",
       "start_date": "2023-01-01",
       "end_date": "2024-12-31",
       "persist": true
     }'
   # Returns: {"backtest_id": "550e8400-...", "persisted": true, ...}
   ```

2. **Evaluate the backtest's risk:**
   ```bash
   curl -X POST http://localhost:8000/risk/evaluate \
     -H "Content-Type: application/json" \
     -d '{"backtest_id": "550e8400-..."}'
   # Returns: {"risk_evaluation_id": "550e8400-...", "persisted": true, "decision": "APPROVED", ...}
   ```

3. **Retrieve the risk evaluation:**
   ```bash
   curl http://localhost:8000/risk/evaluations/550e8400-...
   # Returns: full evaluation details + snapshots
   ```

4. **Check risk status for a backtest:**
   ```bash
   curl http://localhost:8000/backtests/550e8400-.../risk
   # Returns: latest evaluation or 404 with a helpful message
   ```

5. **Phase 6 (AI Committee) onwards:** The CIO agent checks the persisted evaluation's
   `approved` field. If `false`, `PAPER_TRADE` is impossible (enforced by validator).
   **Phase 6 is now live.** See [ai-committee.md](ai-committee.md) for the implemented wiring.

## How This Connects to Paper Trading (Phase 5) and the AI Committee (Phase 6)

The risk veto is **hard-wired into the CIO agent decision** (implemented in Phase 6):

1. Before the CIO issues a decision, a persisted risk evaluation exists for the backtest
   (`GET /backtests/{id}/risk` returns it).
2. The evaluation's `approved` field is copied by code into the CIO agent's input
   (`approved_by_risk = evaluation.approved`).
3. The CIO agent cannot set `approved_by_risk` — it is computed, not a decision.
4. A Pydantic validator in `packages/agents` enforces the rule: if `approved_by_risk=false`
   and `decision=PAPER_TRADE`, the output is rejected with an error — no persistence, no
   downstream action.
5. Code in `packages/agents/agents/committee.py` also overrides raw CIO decisions that violate
   the veto (dual-layer enforcement). See [ai-committee.md](ai-committee.md) for details.
6. Only `approved=true` evaluations allow `PAPER_TRADE`; rejected/needs-review evaluations
   force the CIO to `NO_TRADE` or `WATCHLIST`.

## Limitations (Phase 4)

1. **No per-request policy override.** Always uses the default packaged policy. Dynamic policy
   selection arrives in a later phase.
2. **Data-quality detection not wired.** The `data_quality_bad` and `data_quality_warnings`
   inputs are placeholders; Phase 4 does not integrate live data-quality checks into the
   backtest flow. Placeholder for a later phase.
3. **Portfolio gates dormant.** `pf_max_open_positions` and `pf_max_portfolio_drawdown` are
   defined and evaluated **only** when a `portfolio_context` is passed. Nothing passes one
   yet: the Phase 5 paper engine enforces those limits itself from the portfolio's settings
   JSON instead (see paper-trading-engine.md); wiring a `portfolio_context` into risk
   evaluations remains a possible later refinement.
4. **No auto-evaluation on backtest run.** `POST /backtests/run` does not automatically call
   `POST /risk/evaluate` — it is a manual step. This is deliberate: deferred to keep Phase 4
   scope tight. Typical flow: run backtest → get `backtest_id` → evaluate risk explicitly.

## Running the Tests

From the repo root (uses `pytest.ini`; `testpaths = apps/api packages`):

```
.venv/Scripts/python.exe -m pytest -q        # or plain `pytest` inside the activated venv
```

Phase 4 test suites:

- `packages/risk_engine/tests/test_policy.py` — 12 tests: policy loading, YAML validation,
  schema enforcement.
- `packages/risk_engine/tests/test_engine.py` — 27 tests: gate evaluation, decision logic,
  risk score computation, warning rules, snapshot reproducibility.
- `apps/api/tests/test_risk.py` — 14 tests: API endpoints, backtest_id path, inline path,
  error cases, persistence.
- `apps/api/tests/test_schema.py` — 12 updated schema tests (replaced 9 old provisional ones).

All SQLite/offline; 366 tests passing repo-wide.
