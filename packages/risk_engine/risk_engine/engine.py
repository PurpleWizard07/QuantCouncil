"""Deterministic risk evaluation engine (Phase 4).

Evaluates backtest metrics (and a handful of forward-compatible extras)
against a ``RiskPolicy`` and produces a strict ``RiskEvaluationResult``. Pure
rule-based Python: no LLM involvement, ever. The risk engine holds veto power
over the entire pipeline -- when it does not approve, the CIO agent decision
MUST be NO_TRADE or WATCHLIST, never PAPER_TRADE (that hard rule is codified
in the agents package schema validator).

Percent convention: every ``_pct`` field on ``RiskPolicy`` is a PERCENT
NUMBER (``15`` means 15%), while the metrics coming out of quant_engine are
FRACTIONS (``max_drawdown=0.15`` for a 15% drawdown). This module always
converts the metric fraction to a percent (``* 100``) before comparing
against a policy ``_pct`` threshold -- one direction, consistently.

None handling: quant_engine metrics can be JSON-null. ``profit_factor is
None`` specifically means "no losing trades" (gross_loss == 0), which is
GOOD, not bad -- the ``bt_min_profit_factor`` hard gate is skipped entirely
in that case, and a dedicated warning
(``warn_profit_factor_infinite_small_sample``) fires only when the sample is
also small (``num_trades < policy.warn_if_trade_count_below``). Every OTHER
metric field that is unexpectedly ``None`` (e.g. a stateless caller omitting
``sharpe``) skips just that one gate and records an advisory
``warn_metric_unavailable_<field>`` warning rather than crashing -- these
extra warnings are not part of the eight named warning rules in the project
brief, but participate in the same NEEDS_REVIEW threshold below.

Hard rejection rules (any failure -> REJECTED, all failures recorded):
    bt_min_trades              num_trades < policy.minimum_backtest_trades
    bt_max_drawdown            max_drawdown*100 > policy.max_allowed_drawdown_pct
    bt_min_profit_factor       profit_factor is not None and
                                profit_factor < policy.minimum_profit_factor
    bt_min_total_return        total_return*100 < policy.minimum_total_return_pct
    bt_min_sharpe               sharpe < policy.minimum_sharpe_like
    bt_stop_loss_required      policy.stop_loss_required and no strategy['stop_loss']
    bt_data_quality            policy.reject_if_data_quality_bad and data_quality_bad
    bt_max_position_size       strategy_config given and
                                max_allocation_pct*100 > policy.max_position_size_pct
    bt_max_risk_per_trade      position_sizing.value*100 > policy.max_risk_per_trade_pct

    Forward-compatible, dormant until a caller passes portfolio_context
    (Phase 4 has no live paper portfolio, so nothing calls this today):
    pf_max_open_positions          open_positions > policy.max_open_positions
    pf_max_portfolio_drawdown      portfolio_drawdown_pct > policy.max_portfolio_drawdown_pct

Warning rules (never force rejection alone; see the eight required by the
project brief plus the advisory extras noted above). Every string appended
to ``warnings`` is prefixed with its rule id (``"<rule_id>: <message>"``) --
there is no separate id field on ``RiskEvaluationResult``, so callers/tests
identify which rule fired via that prefix:
    warn_low_trade_count                   num_trades < policy.warn_if_trade_count_below
    warn_low_profit_factor                 profit_factor < policy.warn_if_profit_factor_below
    warn_high_drawdown                     max_drawdown*100 > policy.warn_if_drawdown_pct_above
    warn_high_exposure                     exposure_time*100 > policy.warn_if_exposure_time_pct_above
    warn_loss_win_asymmetry                abs(avg_loss) > 2 * avg_win (both nonzero)
    warn_best_trade_concentration          best winning trade > 50% of total winning pnl
    warn_profit_factor_infinite_small_sample   profit_factor is None and num_trades small
    warn_data_quality                      one entry per string in data_quality_warnings
    warn_position_size_unevaluated         strategy_config was not provided (advisory)
    warn_metric_unavailable_<field>        a metric needed for a gate was None (advisory)

Decision logic (deliberately simple -- no ML, no fitted weights):
    1. Any hard rule failed             -> REJECTED
    2. No hard rule failed, no warnings  -> APPROVED
    3. No hard rule failed, warnings present:
         NEEDS_REVIEW if len(warnings) >= 2, OR the single
         "always needs review" warning (warn_profit_factor_infinite_small_sample)
         fired; otherwise APPROVED with the lone warning surfaced.

Risk score (0-100, deterministic, HIGHER = SAFER -- Phase 4 convention,
inverted from the old provisional "0 is safest" docs). Starts at 100 and
subtracts capped, proportional deductions:
    - drawdown severity:    up to 40 points, scaled by
                             (max_drawdown_pct / policy.max_allowed_drawdown_pct) * 20
    - low profit factor:    up to 20 points, scaled by the fractional shortfall
                             below policy.minimum_profit_factor
    - low trade count:      up to 15 points, scaled by the fractional shortfall
                             below policy.minimum_backtest_trades
    - poor sharpe:          up to 15 points, 10 points per unit shortfall below
                             policy.minimum_sharpe_like (handles sharpe <= 0 safely
                             since it is a simple subtraction, not a ratio)
    - high exposure time:   up to 10 points, scaled by the fractional excess over
                             policy.warn_if_exposure_time_pct_above
    - warnings:             3 flat points per warning, capped at 15
Each deduction is independently capped so no single factor can zero the
score alone; the running total is clamped to [0, 100] at the end
(``max(0, min(100, score))``). A rejected evaluation is not forced below any
threshold -- a low score simply tends to fall out of the same deductions that
drove the rejection.
"""

from __future__ import annotations

from risk_engine.policy import RiskPolicy
from risk_engine.schemas import RiskEvaluationResult

# The one warning that alone (even without a second warning) is serious
# enough to force NEEDS_REVIEW rather than APPROVED-with-a-warning.
_ALWAYS_NEEDS_REVIEW_WARNINGS = {"warn_profit_factor_infinite_small_sample"}

# Loss/win asymmetry multiplier for warn_loss_win_asymmetry: a simple,
# documented, non-overfit threshold (avg_loss more than 2x avg_win).
_LOSS_WIN_ASYMMETRY_MULTIPLIER = 2.0

# Best-trade concentration threshold for warn_best_trade_concentration: a
# simple, documented, non-overfit threshold (one trade > half of total
# winning pnl).
_BEST_TRADE_CONCENTRATION_FRACTION = 0.5


def evaluate(
    *,
    metrics: dict,
    strategy: dict,
    policy: RiskPolicy,
    trades: list[dict] | None = None,
    data_quality_bad: bool = False,
    data_quality_warnings: list[str] | None = None,
    portfolio_context: dict | None = None,
    strategy_config: dict | None = None,
) -> RiskEvaluationResult:
    """Evaluate backtest metrics (and strategy config) against a risk policy.

    Deterministic and auditable: identical inputs always produce an
    identical (by value) result. Every failed hard gate is recorded in
    ``failed_rules`` (with an explanation appended to ``reasons``) -- ALL
    failures are recorded, not just the first. Non-blocking concerns are
    surfaced in ``warnings``. See the module docstring for the exact gate
    list, warning list, decision logic, and risk-score formula.

    Args:
        metrics: The 14-field metrics dict produced by quant_engine /
            persisted on a ``BacktestRun`` row (total_return, cagr,
            max_drawdown, win_rate, avg_win, avg_loss, profit_factor,
            num_trades, exposure_time, sharpe, best_trade, worst_trade,
            starting_capital, final_equity). Values may be ``None``
            (JSON-null) -- handled per-field as documented above.
        strategy: The FULL validated strategy definition dict (i.e. the
            output of ``quant_engine.strategy.validate_strategy``, or a
            persisted row's ``.rules``). Used to read ``stop_loss`` and
            ``position_sizing.value``.
        policy: The ``RiskPolicy`` to evaluate against.
        trades: Optional trade list (dicts with at least ``pnl``) used only
            for the ``warn_best_trade_concentration`` heuristic.
        data_quality_bad: Hard-gate trigger for ``bt_data_quality``.
        data_quality_warnings: Optional pre-computed warning strings (e.g.
            from a future ``validate_ohlcv_report``) folded verbatim into
            ``warnings`` as ``warn_data_quality`` entries. Phase 4 does not
            wire actual data-quality detection into the backtest flow -- this
            parameter is a pass-through for a future phase; this layer never
            inspects raw OHLCV data itself.
        portfolio_context: Optional ``{"open_positions": int,
            "portfolio_drawdown_pct": float}``-shaped dict. Phase 4 has no
            live paper portfolio, so every caller today passes ``None`` and
            the two portfolio gates (``pf_max_open_positions``,
            ``pf_max_portfolio_drawdown``) are skipped entirely (no warning,
            no failure -- there is nothing to evaluate yet). Implemented now,
            simply, for forward compatibility.
        strategy_config: Optional backtest config dict (e.g.
            ``BacktestConfig`` as persisted in ``params.config``) carrying
            ``max_allocation_pct``, needed for ``bt_max_position_size`` since
            that value lives on the backtest config, not the strategy
            definition. If omitted, that one gate is skipped with an
            advisory warning rather than assuming a default.

    Returns:
        A ``RiskEvaluationResult`` with decision APPROVED, REJECTED, or
        NEEDS_REVIEW; a risk_score in [0, 100] (higher = safer); and full
        reasoning, including verbatim ``metrics_snapshot`` and
        ``policy_snapshot`` copies for audit.
    """
    failed_rules: list[str] = []
    reasons: list[str] = []
    warning_entries: list[tuple[str, str]] = []

    def fail(rule_id: str, message: str) -> None:
        failed_rules.append(rule_id)
        reasons.append(message)

    def warn(rule_id: str, message: str) -> None:
        # Each warning string is prefixed with its rule id (e.g.
        # "warn_low_trade_count: num_trades (5) is below ...") since
        # RiskEvaluationResult.warnings is a flat list[str] with no separate
        # id field -- callers identify which rule fired via this prefix.
        warning_entries.append((rule_id, f"{rule_id}: {message}"))

    num_trades = metrics.get("num_trades")
    max_drawdown = metrics.get("max_drawdown")
    profit_factor = metrics.get("profit_factor")
    total_return = metrics.get("total_return")
    sharpe = metrics.get("sharpe")
    exposure_time = metrics.get("exposure_time")
    avg_win = metrics.get("avg_win")
    avg_loss = metrics.get("avg_loss")

    # --- hard rejection gates -------------------------------------------

    if num_trades is None:
        warn(
            "warn_metric_unavailable_num_trades",
            "metric 'num_trades' is null; skipping bt_min_trades gate.",
        )
    elif num_trades < policy.minimum_backtest_trades:
        fail(
            "bt_min_trades",
            f"num_trades ({num_trades}) is below the policy minimum "
            f"({policy.minimum_backtest_trades}).",
        )

    if max_drawdown is None:
        warn(
            "warn_metric_unavailable_max_drawdown",
            "metric 'max_drawdown' is null; skipping bt_max_drawdown gate.",
        )
    else:
        drawdown_pct = max_drawdown * 100
        if drawdown_pct > policy.max_allowed_drawdown_pct:
            fail(
                "bt_max_drawdown",
                f"max_drawdown ({drawdown_pct:.2f}%) exceeds the policy limit "
                f"({policy.max_allowed_drawdown_pct}%).",
            )

    # profit_factor is None -> "no losing trades" (good); the hard gate is
    # skipped entirely (see module docstring), not treated as missing data.
    if profit_factor is not None and profit_factor < policy.minimum_profit_factor:
        fail(
            "bt_min_profit_factor",
            f"profit_factor ({profit_factor:.2f}) is below the policy minimum "
            f"({policy.minimum_profit_factor}).",
        )

    if total_return is None:
        warn(
            "warn_metric_unavailable_total_return",
            "metric 'total_return' is null; skipping bt_min_total_return gate.",
        )
    else:
        total_return_pct = total_return * 100
        if total_return_pct < policy.minimum_total_return_pct:
            fail(
                "bt_min_total_return",
                f"total_return ({total_return_pct:.2f}%) is below the policy "
                f"minimum ({policy.minimum_total_return_pct}%).",
            )

    if sharpe is None:
        warn(
            "warn_metric_unavailable_sharpe",
            "metric 'sharpe' is null; skipping bt_min_sharpe gate.",
        )
    elif sharpe < policy.minimum_sharpe_like:
        fail(
            "bt_min_sharpe",
            f"sharpe ({sharpe:.2f}) is below the policy minimum "
            f"({policy.minimum_sharpe_like}).",
        )

    if policy.stop_loss_required and not strategy.get("stop_loss"):
        fail(
            "bt_stop_loss_required",
            "strategy defines no stop_loss, and policy.stop_loss_required is true.",
        )

    if policy.reject_if_data_quality_bad and data_quality_bad:
        fail(
            "bt_data_quality",
            "data_quality_bad is true and policy.reject_if_data_quality_bad is true.",
        )

    if strategy_config is not None:
        max_allocation_pct = strategy_config.get("max_allocation_pct", 0) * 100
        if max_allocation_pct > policy.max_position_size_pct:
            fail(
                "bt_max_position_size",
                f"max_allocation_pct ({max_allocation_pct:.2f}%) exceeds the "
                f"policy limit ({policy.max_position_size_pct}%).",
            )
    else:
        warn(
            "warn_position_size_unevaluated",
            "strategy_config not provided; cannot evaluate bt_max_position_size "
            "(max_allocation_pct unknown).",
        )

    risk_per_trade_pct = strategy.get("position_sizing", {}).get("value", 0) * 100
    if risk_per_trade_pct > policy.max_risk_per_trade_pct:
        fail(
            "bt_max_risk_per_trade",
            f"position_sizing.value ({risk_per_trade_pct:.2f}%) exceeds the "
            f"policy limit ({policy.max_risk_per_trade_pct}%).",
        )

    # --- portfolio gates: dormant until a caller supplies portfolio_context ---
    if portfolio_context is not None:
        open_positions = portfolio_context.get("open_positions")
        if open_positions is not None and open_positions > policy.max_open_positions:
            fail(
                "pf_max_open_positions",
                f"open_positions ({open_positions}) exceeds the policy limit "
                f"({policy.max_open_positions}).",
            )
        portfolio_drawdown_pct = portfolio_context.get("portfolio_drawdown_pct")
        if (
            portfolio_drawdown_pct is not None
            and portfolio_drawdown_pct > policy.max_portfolio_drawdown_pct
        ):
            fail(
                "pf_max_portfolio_drawdown",
                f"portfolio_drawdown_pct ({portfolio_drawdown_pct:.2f}%) exceeds "
                f"the policy limit ({policy.max_portfolio_drawdown_pct}%).",
            )

    # --- warning rules ---------------------------------------------------

    if num_trades is not None and num_trades < policy.warn_if_trade_count_below:
        warn(
            "warn_low_trade_count",
            f"num_trades ({num_trades}) is below the warning threshold "
            f"({policy.warn_if_trade_count_below}).",
        )

    if profit_factor is not None and profit_factor < policy.warn_if_profit_factor_below:
        warn(
            "warn_low_profit_factor",
            f"profit_factor ({profit_factor:.2f}) is below the warning threshold "
            f"({policy.warn_if_profit_factor_below}).",
        )

    if max_drawdown is not None and max_drawdown * 100 > policy.warn_if_drawdown_pct_above:
        warn(
            "warn_high_drawdown",
            f"max_drawdown ({max_drawdown * 100:.2f}%) exceeds the warning "
            f"threshold ({policy.warn_if_drawdown_pct_above}%).",
        )

    if (
        exposure_time is not None
        and exposure_time * 100 > policy.warn_if_exposure_time_pct_above
    ):
        warn(
            "warn_high_exposure",
            f"exposure_time ({exposure_time * 100:.2f}%) exceeds the warning "
            f"threshold ({policy.warn_if_exposure_time_pct_above}%).",
        )

    if avg_win and avg_loss and abs(avg_loss) > _LOSS_WIN_ASYMMETRY_MULTIPLIER * avg_win:
        warn(
            "warn_loss_win_asymmetry",
            f"avg_loss ({avg_loss:.2f}) is more than "
            f"{_LOSS_WIN_ASYMMETRY_MULTIPLIER:.0f}x avg_win ({avg_win:.2f}).",
        )

    if trades:
        winning_pnls = [pnl for t in trades if (pnl := t.get("pnl", 0)) > 0]
        total_positive_pnl = sum(winning_pnls)
        if total_positive_pnl > 0:
            best_trade_pnl = max(winning_pnls)
            if best_trade_pnl > _BEST_TRADE_CONCENTRATION_FRACTION * total_positive_pnl:
                warn(
                    "warn_best_trade_concentration",
                    f"best trade pnl ({best_trade_pnl:.2f}) exceeds "
                    f"{_BEST_TRADE_CONCENTRATION_FRACTION * 100:.0f}% of total "
                    f"winning pnl ({total_positive_pnl:.2f}).",
                )

    if (
        profit_factor is None
        and num_trades is not None
        and num_trades < policy.warn_if_trade_count_below
    ):
        warn(
            "warn_profit_factor_infinite_small_sample",
            "profit_factor is infinite due to zero losing trades, but "
            f"num_trades ({num_trades}) is below the warning threshold "
            f"({policy.warn_if_trade_count_below}); treat as statistically thin.",
        )

    for dq_warning in data_quality_warnings or []:
        warn("warn_data_quality", f"data_quality: {dq_warning}")

    warnings = [message for _, message in warning_entries]
    warning_ids = {rule_id for rule_id, _ in warning_entries}

    # --- decision ---------------------------------------------------------

    if failed_rules:
        decision = "REJECTED"
        approved = False
    elif not warnings:
        decision = "APPROVED"
        approved = True
        reasons.append("All hard risk policy gates passed; no warnings.")
    elif len(warnings) >= 2 or (warning_ids & _ALWAYS_NEEDS_REVIEW_WARNINGS):
        decision = "NEEDS_REVIEW"
        approved = False
        reasons.append(
            "No hard risk policy gate failed, but warnings require human review "
            "before approval."
        )
    else:
        decision = "APPROVED"
        approved = True
        reasons.append("All hard risk policy gates passed; one minor warning noted.")

    # --- risk score (see module docstring for the formula) ----------------

    score = 100.0

    if max_drawdown is not None and policy.max_allowed_drawdown_pct > 0:
        drawdown_pct = max_drawdown * 100
        score -= min(40.0, max(0.0, drawdown_pct / policy.max_allowed_drawdown_pct) * 20.0)

    if profit_factor is not None and policy.minimum_profit_factor > 0:
        shortfall_ratio = (policy.minimum_profit_factor - profit_factor) / policy.minimum_profit_factor
        score -= min(20.0, max(0.0, shortfall_ratio) * 20.0)

    if num_trades is not None and policy.minimum_backtest_trades > 0:
        shortfall_ratio = (policy.minimum_backtest_trades - num_trades) / policy.minimum_backtest_trades
        score -= min(15.0, max(0.0, shortfall_ratio) * 15.0)

    if sharpe is not None:
        shortfall = policy.minimum_sharpe_like - sharpe
        score -= min(15.0, max(0.0, shortfall) * 10.0)

    if exposure_time is not None and policy.warn_if_exposure_time_pct_above > 0:
        exposure_pct = exposure_time * 100
        excess_ratio = (
            exposure_pct - policy.warn_if_exposure_time_pct_above
        ) / policy.warn_if_exposure_time_pct_above
        score -= min(10.0, max(0.0, excess_ratio) * 10.0)

    score -= min(15.0, 3.0 * len(warnings))

    risk_score = int(round(max(0.0, min(100.0, score))))

    metrics_snapshot = dict(metrics)
    policy_snapshot = policy.model_dump()

    return RiskEvaluationResult(
        decision=decision,
        approved=approved,
        risk_score=risk_score,
        policy_version=policy.policy_version,
        reasons=reasons,
        failed_rules=failed_rules,
        warnings=warnings,
        metrics_snapshot=metrics_snapshot,
        policy_snapshot=policy_snapshot,
    )
