# QuantCouncil Risk Policy

The risk engine (`packages/risk_engine`) is deterministic Python with **binding veto power**
over the entire pipeline. It evaluates backtest metrics and portfolio constraints against a
versioned policy and emits a strict JSON verdict. LLM agents may narrate risk; they never
compute or decide it. See [architecture.md](architecture.md) for the propose/approve/veto
hierarchy. Full implementation details, API surface, and testing are in [risk-engine.md](risk-engine.md).

## Output Contract (Verbatim, Phase 4)

Every risk evaluation produces exactly this JSON shape:

```json
{
  "decision": "APPROVED" | "REJECTED" | "NEEDS_REVIEW",
  "approved": true | false,
  "risk_score": 0,
  "policy_version": "1.0.0",
  "reasons": [],
  "failed_rules": [],
  "warnings": [],
  "metrics_snapshot": {},
  "policy_snapshot": {}
}
```

| Field | Meaning |
|---|---|
| `decision` | One of `APPROVED`, `REJECTED`, `NEEDS_REVIEW`. |
| `approved` | Boolean. `true` **iff** `decision == "APPROVED"`. Validator-enforced invariant. |
| `risk_score` | Integer 0-100; **higher = safer** (e.g., 80 is safer than 20). Informational only; never overrides gates. |
| `policy_version` | The policy version this evaluation used (e.g., `"1.0.0"`). Enables reproducibility. |
| `reasons` | Human-readable explanations for the decision. |
| `failed_rules` | Machine-readable ids of every hard gate that failed; empty if no failures. |
| `warnings` | Non-blocking concerns (never empty unless no warnings); formatted `"<rule_id>: <message>"`. |
| `metrics_snapshot` | Verbatim copy of input metrics for full reproducibility of this verdict. |
| `policy_snapshot` | Verbatim copy of the policy that produced this verdict. |

## Decision Semantics

- **APPROVED** — all hard gates passed; `approved = true`. The strategy may proceed toward paper
  trading (still subject to the CIO decision).
- **REJECTED** — at least one hard gate failed; `approved = false`. Paper trading is blocked.
- **NEEDS_REVIEW** — no hard gates failed, but ≥2 warnings or an infinite-profit-factor
  small-sample flag exists; `approved = false`. **The pipeline treats NEEDS_REVIEW as
  not-approved**: it blocks paper trading exactly like REJECTED until a human re-runs or
  overrides with a journaled note.

`approved` is derivable but stored explicitly for auditability. The engine enforces the
invariant via Pydantic validation; a row violating it is a bug.

## Risk Score (0–100, Higher = Safer)

**Phase 4 change:** Score direction flipped from the old draft. In the draft, 0 was safest
and 100 was riskiest. In Phase 4 (policy v1.0.0), **higher scores are safer**. This is a
deliberate, versioned change; old draft scores are not comparable.

**Composition:**

Start at 100, then apply capped proportional deductions:

| Component | Max Deduction | Applied When |
|---|---|---|
| Drawdown severity | 40 | `max_drawdown` approaches/exceeds 15%; scales from 0 to 40 as drawdown rises. |
| Low profit factor | 20 | `profit_factor` near minimum gate (1.2); scales linearly. |
| Low trade count | 15 | `num_trades` below recommendation (50); scales logarithmically. |
| Poor Sharpe | 15 | `sharpe` below gate (0); scales linearly. |
| High exposure | 10 | `exposure_time` approaches 100% (always in market). |
| Warning penalty | 3 per warning | Per warning up to 5 (max 15 total). |

**Result:** Clamped to [0, 100].

**Interpretation:**

- **80–100:** Low risk. Strong metrics across all dimensions.
- **60–79:** Moderate risk. Some warning flags; most gates pass.
- **40–59:** Material risk. Multiple warnings or borderline gate performance.
- **0–39:** High risk. Many warnings or poor margin of safety.

The score is informational. It never overrides the gates: a low score with a failed hard gate
is still REJECTED.

## Hard Gates (Phase 4)

All gates apply to the metrics of a persisted `backtest_runs` row or inline backtest inputs
(metric definitions in [backtesting-engine.md](backtesting-engine.md), Phase 3):

| Rule id | Gate | Source |
|---|---|---|
| `bt_min_trades` | `num_trades >= 30` | `metrics.num_trades` |
| `bt_max_drawdown` | `max_drawdown <= 15%` | `metrics.max_drawdown * 100` |
| `bt_min_profit_factor` | `profit_factor >= 1.2` OR `profit_factor` is `null` (infinite) | `metrics.profit_factor` |
| `bt_min_total_return` | `total_return >= 0%` | `metrics.total_return * 100` |
| `bt_min_sharpe` | `sharpe >= 0` | `metrics.sharpe` |
| `bt_stop_loss_required` | Strategy rule defines a stop-loss | `strategy.stop_loss.type` must exist |
| `bt_data_quality` | `data_quality_bad != true` | Placeholder input; Phase 4 does not wire live detection |
| `bt_max_position_size` | `strategy_config.max_allocation_pct <= 10%` | Requires `strategy_config` input; skipped with warning if absent |
| `bt_max_risk_per_trade` | `strategy.position_sizing.value * 100 <= 1%` | `strategy.position_sizing.value` |

**Special cases:**

- **Profit factor null (infinite):** When a backtest has no losing trades, `profit_factor` is
  `null` (JSON). This is treated as GOOD: the gate is skipped, only the small-sample warning fires.
- **Position size unevaluated:** If `strategy_config` is missing, `bt_max_position_size` is
  skipped and an advisory warning issued.

These thresholds supersede the old draft provisional values (e.g., old 20% drawdown gate →
new 15%). Versioning enables policy evolution with experience.

## Warning Rules (Phase 4)

| Rule ID | Condition |
|---|---|
| `warn_low_trade_count` | `num_trades < 50` |
| `warn_low_profit_factor` | `profit_factor < 1.5` AND `profit_factor` is finite |
| `warn_high_drawdown` | `max_drawdown > 10%` |
| `warn_high_exposure` | `exposure_time > 80%` |
| `warn_loss_win_asymmetry` | `abs(avg_loss) > 2 × avg_win` |
| `warn_best_trade_concentration` | `best_trade > 50%` of gross winning PnL (requires trade list) |
| `warn_profit_factor_infinite_small_sample` | `profit_factor` is `null` AND `num_trades < 50` |
| `warn_position_size_unevaluated` | `strategy_config` input missing |
| `warn_metric_unavailable_<field>` | Required metric field is missing/None |
| (passthrough) `warn_data_quality` | `data_quality_warnings` list supplied at input |

Warnings never force rejection alone. ≥2 warnings or the infinite-small-sample flag → NEEDS_REVIEW.

## Portfolio Gates (Dormant Until Phase 6)

The paper-portfolio rules from the project contract, evaluated **only** when a `portfolio_context`
is passed (Phase 4 does not pass one; Phase 6 paper trading will):

| Rule id | Gate | Status |
|---|---|---|
| `pf_max_open_positions` | Open positions <= 10 | Dormant; implemented, awaits portfolio context |
| `pf_max_portfolio_drawdown` | Portfolio drawdown <= 8% | Dormant; implemented, awaits portfolio context |

Full portfolio semantics in [paper-trading-design.md](paper-trading-design.md).

## The Hard Veto (Verbatim)

> The risk engine has veto power: if `approved_by_risk=false`, the CIO agent decision MUST be
> `NO_TRADE` or `WATCHLIST` — never `PAPER_TRADE`.

This constraint is **enforced in code, not just in prompts**: a Pydantic model validator in
`packages/agents` rejects any CIO output where `approved_by_risk` is `false` and `decision`
is `PAPER_TRADE`, before it can be persisted or acted on. The prompt also states the rule,
but the validator is the enforcement mechanism. For reference, the CIO agent output contract:

```json
{
  "decision": "PAPER_TRADE" | "NO_TRADE" | "WATCHLIST",
  "approved_by_risk": true | false,
  "summary": "",
  "reason": "",
  "conditions_to_reconsider": [],
  "audit_refs": {"backtest_id": "", "risk_evaluation_id": "", "agent_decision_ids": []}
}
```

`approved_by_risk` is **copied by code** from the risk evaluation's `approved` field — the CIO
agent cannot set it.

## Policy Versioning

- The risk policy (gates, thresholds, score weights) is a versioned YAML configuration
  (`packages/risk_engine/risk_policy.yaml`).
- **Phase 4 ships policy v1.0.0**, which supersedes the old provisional "v1" draft. The v1.0.0
  redesign includes the score-direction flip (higher = safer) and hard-gate changes
  (e.g., 15% drawdown vs. old 20%, 30 trades vs. old 20). These are **deliberate, breaking changes**.
- Every `risk_evaluations` row stores the `policy_version` it was evaluated under, enabling
  reproducibility: any historical verdict can be re-evaluated against the exact policy that
  produced it.
- Any future change to gates, thresholds, or weights bumps the version (e.g., v1.0.0 → v1.1.0).
  Re-evaluation under a new version writes a new row; history is never mutated.
- Policy load errors (malformed YAML, schema violations) raise `RiskPolicyError` with a clear
  message.
