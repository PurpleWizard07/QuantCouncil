"""Tests for the deterministic risk evaluation engine (Phase 4).

Hand-constructed metrics/strategy dicts throughout -- realistic shapes per
quant_engine's contract (the 14-field metrics dict; strategy['stop_loss'] /
strategy['position_sizing'] per docs/strategy-format.md), but built directly
rather than run through the real backtester, so each scenario isolates
exactly the gate or warning under test.
"""

from __future__ import annotations

import copy

import pytest

from risk_engine.engine import evaluate
from risk_engine.policy import load_policy

POLICY = load_policy()


def _strategy(**overrides) -> dict:
    base = {
        "name": "test_strategy",
        "universe": ["RELIANCE"],
        "timeframe": "1d",
        "direction": "long_only",
        "entry": {"indicator": "close", "params": {}, "op": "greater_than", "value": 0},
        "exit": {"indicator": "close", "params": {}, "op": "less_than", "value": 0},
        "stop_loss": {"type": "percent", "value": 0.05},
        "position_sizing": {"type": "risk_percent", "value": 0.01},
    }
    base.update(overrides)
    return base


def _metrics(**overrides) -> dict:
    base = {
        "total_return": 0.20,
        "cagr": 0.18,
        "max_drawdown": 0.05,
        "win_rate": 0.55,
        "avg_win": 500.0,
        "avg_loss": -250.0,
        "profit_factor": 2.0,
        "num_trades": 100,
        "exposure_time": 0.5,
        "sharpe": 1.2,
        "best_trade": 900.0,
        "worst_trade": -400.0,
        "starting_capital": 100000.0,
        "final_equity": 120000.0,
    }
    base.update(overrides)
    return base


def _clean_strategy_config(**overrides) -> dict:
    base = {"max_allocation_pct": 0.08}
    base.update(overrides)
    return base


# --- APPROVED --------------------------------------------------------------


def test_approved_clean_case() -> None:
    result = evaluate(
        metrics=_metrics(),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "APPROVED"
    assert result.approved is True
    assert result.failed_rules == []
    assert result.risk_score >= 70


# --- REJECTED: hard gates ----------------------------------------------------


def test_rejected_min_trades() -> None:
    result = evaluate(
        metrics=_metrics(num_trades=5),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "REJECTED"
    assert result.approved is False
    assert "bt_min_trades" in result.failed_rules


def test_rejected_max_drawdown() -> None:
    result = evaluate(
        metrics=_metrics(max_drawdown=0.25),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "REJECTED"
    assert "bt_max_drawdown" in result.failed_rules


def test_rejected_min_profit_factor() -> None:
    result = evaluate(
        metrics=_metrics(profit_factor=0.8),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "REJECTED"
    assert "bt_min_profit_factor" in result.failed_rules


def test_rejected_min_total_return() -> None:
    result = evaluate(
        metrics=_metrics(total_return=-0.05),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "REJECTED"
    assert "bt_min_total_return" in result.failed_rules


def test_rejected_min_sharpe() -> None:
    result = evaluate(
        metrics=_metrics(sharpe=-0.5),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "REJECTED"
    assert "bt_min_sharpe" in result.failed_rules


def test_rejected_missing_stop_loss() -> None:
    strategy = _strategy()
    del strategy["stop_loss"]
    result = evaluate(
        metrics=_metrics(),
        strategy=strategy,
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "REJECTED"
    assert "bt_stop_loss_required" in result.failed_rules


def test_rejected_data_quality_bad() -> None:
    result = evaluate(
        metrics=_metrics(),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
        data_quality_bad=True,
    )
    assert result.decision == "REJECTED"
    assert "bt_data_quality" in result.failed_rules


def test_rejected_max_position_size() -> None:
    result = evaluate(
        metrics=_metrics(),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config={"max_allocation_pct": 0.25},
    )
    assert result.decision == "REJECTED"
    assert "bt_max_position_size" in result.failed_rules


def test_rejected_max_risk_per_trade() -> None:
    strategy = _strategy(position_sizing={"type": "risk_percent", "value": 0.05})
    result = evaluate(
        metrics=_metrics(),
        strategy=strategy,
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "REJECTED"
    assert "bt_max_risk_per_trade" in result.failed_rules


def test_rejected_multiple_failures_all_recorded() -> None:
    strategy = _strategy(position_sizing={"type": "risk_percent", "value": 0.05})
    del strategy["stop_loss"]
    result = evaluate(
        metrics=_metrics(num_trades=5, max_drawdown=0.30),
        strategy=strategy,
        policy=POLICY,
        strategy_config={"max_allocation_pct": 0.25},
    )
    assert result.decision == "REJECTED"
    for rule_id in (
        "bt_min_trades",
        "bt_max_drawdown",
        "bt_stop_loss_required",
        "bt_max_position_size",
        "bt_max_risk_per_trade",
    ):
        assert rule_id in result.failed_rules
    assert len(result.reasons) >= len(result.failed_rules)


# --- NEEDS_REVIEW ------------------------------------------------------------


def test_needs_review_two_warnings() -> None:
    result = evaluate(
        metrics=_metrics(num_trades=40, profit_factor=1.3),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "NEEDS_REVIEW"
    assert result.approved is False
    assert result.failed_rules == []
    assert any("warn_low_trade_count" in w for w in result.warnings)
    assert any("warn_low_profit_factor" in w for w in result.warnings)


def test_needs_review_when_always_review_warning_present() -> None:
    """The 'always needs review' warning forces NEEDS_REVIEW.

    (In practice warn_profit_factor_infinite_small_sample and
    warn_low_trade_count share the same num_trades condition and co-fire --
    either one alone already satisfies a NEEDS_REVIEW trigger: the
    always-review subset, or the len(warnings) >= 2 rule.)
    """
    result = evaluate(
        metrics=_metrics(profit_factor=None, num_trades=35),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.decision == "NEEDS_REVIEW"
    assert result.failed_rules == []
    assert any("warn_profit_factor_infinite_small_sample" in w for w in result.warnings)


# --- individual warning rules -------------------------------------------------


def test_warn_low_trade_count_isolated() -> None:
    result = evaluate(
        metrics=_metrics(num_trades=40),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert any("warn_low_trade_count" in w for w in result.warnings)
    # A single non-always-review warning still resolves to APPROVED (see
    # engine.py:394-404) -- assert the outcome, not just the warning text.
    assert result.decision == "APPROVED"
    assert result.approved is True


def test_warn_low_profit_factor_isolated() -> None:
    result = evaluate(
        metrics=_metrics(profit_factor=1.3),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert any("warn_low_profit_factor" in w for w in result.warnings)
    # Single non-always-review warning -> still APPROVED (engine.py:394-404).
    assert result.decision == "APPROVED"
    assert result.approved is True


def test_warn_high_drawdown_isolated() -> None:
    result = evaluate(
        metrics=_metrics(max_drawdown=0.12),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert any("warn_high_drawdown" in w for w in result.warnings)
    # Single non-always-review warning -> still APPROVED (engine.py:394-404).
    assert result.decision == "APPROVED"
    assert result.approved is True


def test_warn_high_exposure_isolated() -> None:
    result = evaluate(
        metrics=_metrics(exposure_time=0.9),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert any("warn_high_exposure" in w for w in result.warnings)
    # Single non-always-review warning -> still APPROVED (engine.py:394-404).
    assert result.decision == "APPROVED"
    assert result.approved is True


def test_warn_loss_win_asymmetry_isolated() -> None:
    result = evaluate(
        metrics=_metrics(avg_win=100.0, avg_loss=-300.0),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert any("warn_loss_win_asymmetry" in w for w in result.warnings)
    # Single non-always-review warning -> still APPROVED (engine.py:394-404).
    assert result.decision == "APPROVED"
    assert result.approved is True


def test_needs_review_two_warnings_drawdown_and_exposure() -> None:
    """Two simultaneous non-always-review warnings flip APPROVED -> NEEDS_REVIEW.

    Complements test_needs_review_two_warnings (which pairs
    warn_low_trade_count + warn_low_profit_factor) with a different pair
    (warn_high_drawdown + warn_high_exposure), directly exercising the
    len(warnings) >= 2 boundary at engine.py:394 -- a regression to a >= 1
    threshold would flip the single-warning isolated tests above to
    NEEDS_REVIEW, and a regression the other way (e.g. requiring > 2) would
    leave this case at APPROVED.
    """
    result = evaluate(
        metrics=_metrics(max_drawdown=0.12, exposure_time=0.9),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.failed_rules == []
    assert any("warn_high_drawdown" in w for w in result.warnings)
    assert any("warn_high_exposure" in w for w in result.warnings)
    assert len(result.warnings) == 2
    assert result.decision == "NEEDS_REVIEW"
    assert result.approved is False


def test_warn_best_trade_concentration_isolated() -> None:
    trades = [
        {"pnl": 1000.0},
        {"pnl": 50.0},
        {"pnl": 50.0},
        {"pnl": -200.0},
    ]
    result = evaluate(
        metrics=_metrics(),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
        trades=trades,
    )
    assert any("warn_best_trade_concentration" in w for w in result.warnings)


def test_warn_profit_factor_infinite_small_sample_isolated() -> None:
    result = evaluate(
        metrics=_metrics(profit_factor=None, num_trades=10),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert any("warn_profit_factor_infinite_small_sample" in w for w in result.warnings)


def test_warn_data_quality_isolated() -> None:
    result = evaluate(
        metrics=_metrics(),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
        data_quality_warnings=["stale bar detected on 2024-03-01"],
    )
    matches = [w for w in result.warnings if w.startswith("warn_data_quality")]
    assert len(matches) == 1
    assert "stale bar detected on 2024-03-01" in matches[0]


# --- profit_factor None handling ---------------------------------------------


def test_profit_factor_none_high_trade_count_no_reject_no_small_sample_warning() -> None:
    result = evaluate(
        metrics=_metrics(profit_factor=None, num_trades=200),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert "bt_min_profit_factor" not in result.failed_rules
    assert not any("warn_profit_factor_infinite_small_sample" in w for w in result.warnings)
    assert result.decision == "APPROVED"


# --- metric unavailable (None) handling: hard gate skipped, advisory warning fires ---
#
# Per the module docstring (engine.py, "None handling"), when one of these
# four metrics is None the corresponding hard gate is skipped entirely (not
# treated as a failure) and a warn_metric_unavailable_<field> advisory
# warning is emitted instead. Each test below sets exactly one metric to
# None, keeps every other metric at an otherwise-clean (base) value, and
# asserts all three documented consequences: the hard gate did not fire, the
# specific advisory warning did fire, and the overall decision is still
# APPROVED (a single advisory warning does not force NEEDS_REVIEW).


def test_num_trades_none_skips_gate_warns_and_approves() -> None:
    result = evaluate(
        metrics=_metrics(num_trades=None),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert "bt_min_trades" not in result.failed_rules
    assert result.failed_rules == []
    assert any("warn_metric_unavailable_num_trades" in w for w in result.warnings)
    assert result.decision == "APPROVED"
    assert result.approved is True


def test_max_drawdown_none_skips_gate_warns_and_approves() -> None:
    result = evaluate(
        metrics=_metrics(max_drawdown=None),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert "bt_max_drawdown" not in result.failed_rules
    assert result.failed_rules == []
    assert any("warn_metric_unavailable_max_drawdown" in w for w in result.warnings)
    assert result.decision == "APPROVED"
    assert result.approved is True


def test_total_return_none_skips_gate_warns_and_approves() -> None:
    result = evaluate(
        metrics=_metrics(total_return=None),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert "bt_min_total_return" not in result.failed_rules
    assert result.failed_rules == []
    assert any("warn_metric_unavailable_total_return" in w for w in result.warnings)
    assert result.decision == "APPROVED"
    assert result.approved is True


def test_sharpe_none_skips_gate_warns_and_approves() -> None:
    result = evaluate(
        metrics=_metrics(sharpe=None),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert "bt_min_sharpe" not in result.failed_rules
    assert result.failed_rules == []
    assert any("warn_metric_unavailable_sharpe" in w for w in result.warnings)
    assert result.decision == "APPROVED"
    assert result.approved is True


# --- risk score clamping ------------------------------------------------------


def test_risk_score_clamped_for_pathologically_bad_metrics() -> None:
    strategy = _strategy(position_sizing={"type": "risk_percent", "value": 0.20})
    del strategy["stop_loss"]
    result = evaluate(
        metrics=_metrics(
            num_trades=1,
            max_drawdown=0.95,
            profit_factor=0.1,
            total_return=-0.80,
            sharpe=-5.0,
            exposure_time=1.0,
        ),
        strategy=strategy,
        policy=POLICY,
        strategy_config={"max_allocation_pct": 0.90},
        data_quality_bad=True,
    )
    assert result.decision == "REJECTED"
    assert 0 <= result.risk_score <= 100
    assert result.risk_score < 40


# --- snapshots -----------------------------------------------------------------


def test_metrics_and_policy_snapshots_are_verbatim_copies() -> None:
    metrics = _metrics()
    result = evaluate(
        metrics=metrics,
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
    )
    assert result.metrics_snapshot == metrics
    assert result.policy_snapshot == POLICY.model_dump()


# --- portfolio_context is dormant while None ----------------------------------


def test_portfolio_context_none_never_adds_portfolio_gates() -> None:
    strategy = _strategy(position_sizing={"type": "risk_percent", "value": 0.20})
    del strategy["stop_loss"]
    result = evaluate(
        metrics=_metrics(num_trades=1, max_drawdown=0.95),
        strategy=strategy,
        policy=POLICY,
        strategy_config={"max_allocation_pct": 0.90},
        data_quality_bad=True,
        portfolio_context=None,
    )
    assert "pf_max_open_positions" not in result.failed_rules
    assert "pf_max_portfolio_drawdown" not in result.failed_rules
    assert not any("pf_max_open_positions" in w for w in result.warnings)
    assert not any("pf_max_portfolio_drawdown" in w for w in result.warnings)


def test_portfolio_context_provided_evaluates_gates() -> None:
    result = evaluate(
        metrics=_metrics(),
        strategy=_strategy(),
        policy=POLICY,
        strategy_config=_clean_strategy_config(),
        portfolio_context={"open_positions": 20, "portfolio_drawdown_pct": 15},
    )
    assert "pf_max_open_positions" in result.failed_rules
    assert "pf_max_portfolio_drawdown" in result.failed_rules
    assert result.decision == "REJECTED"


# --- determinism ---------------------------------------------------------------


def test_determinism_identical_inputs_identical_results() -> None:
    metrics = _metrics(num_trades=40, profit_factor=1.3)
    strategy = _strategy()
    config = _clean_strategy_config()

    first = evaluate(
        metrics=copy.deepcopy(metrics),
        strategy=copy.deepcopy(strategy),
        policy=POLICY,
        strategy_config=copy.deepcopy(config),
    )
    second = evaluate(
        metrics=copy.deepcopy(metrics),
        strategy=copy.deepcopy(strategy),
        policy=POLICY,
        strategy_config=copy.deepcopy(config),
    )
    assert first == second
