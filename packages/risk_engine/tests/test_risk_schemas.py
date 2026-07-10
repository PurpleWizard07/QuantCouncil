"""Phase 4 tests for the risk engine schemas and the YAML-backed policy.

Superseding note: this file previously asserted against the provisional
fraction-based ``RiskPolicy`` (``max_drawdown_limit``, ``min_profit_factor``,
``min_trades``, ``min_win_rate``, ``min_sharpe``, ``policy_version == "v1"``).
That shape is deliberately superseded in Phase 4 by the YAML-backed policy in
``risk_policy.yaml`` (percent-based fields, see ``risk_engine.policy``) --
these assertions are intentionally updated, not "broken". Policy-loading
behavior (malformed YAML, missing keys, wrong types) is covered in
``test_policy.py``; engine decision/scoring behavior is covered in
``test_engine.py``.
"""

import pytest
from pydantic import ValidationError

from risk_engine.policy import RiskPolicy, load_policy
from risk_engine.schemas import RiskEvaluationResult


def test_valid_approved_payload_parses() -> None:
    result = RiskEvaluationResult(
        decision="APPROVED",
        approved=True,
        risk_score=95,
        policy_version="1.0.0",
        reasons=["All policy rules passed"],
        failed_rules=[],
        warnings=[],
    )
    assert result.decision == "APPROVED"
    assert result.approved is True
    assert result.risk_score == 95
    assert result.policy_version == "1.0.0"


def test_list_and_dict_fields_default_to_empty() -> None:
    result = RiskEvaluationResult(
        decision="REJECTED",
        approved=False,
        risk_score=10,
        policy_version="1.0.0",
        failed_rules=["bt_min_trades"],
    )
    assert result.reasons == []
    assert result.warnings == []
    assert result.metrics_snapshot == {}
    assert result.policy_snapshot == {}


def test_rejected_with_approved_true_raises() -> None:
    with pytest.raises(ValidationError):
        RiskEvaluationResult(
            decision="REJECTED",
            approved=True,
            risk_score=80,
            policy_version="1.0.0",
            failed_rules=["bt_min_trades"],
        )


def test_approved_decision_with_approved_false_raises() -> None:
    with pytest.raises(ValidationError):
        RiskEvaluationResult(
            decision="APPROVED", approved=False, risk_score=10, policy_version="1.0.0"
        )


def test_needs_review_with_approved_false_parses() -> None:
    result = RiskEvaluationResult(
        decision="NEEDS_REVIEW", approved=False, risk_score=55, policy_version="1.0.0"
    )
    assert result.approved is False


def test_risk_score_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        RiskEvaluationResult(
            decision="REJECTED",
            approved=False,
            risk_score=150,
            policy_version="1.0.0",
            failed_rules=["bt_min_trades"],
        )


def test_extra_field_raises() -> None:
    with pytest.raises(ValidationError):
        RiskEvaluationResult(
            decision="APPROVED",
            approved=True,
            risk_score=10,
            policy_version="1.0.0",
            unexpected_field="not allowed",
        )


def test_rejected_requires_at_least_one_failed_rule() -> None:
    with pytest.raises(ValidationError):
        RiskEvaluationResult(
            decision="REJECTED",
            approved=False,
            risk_score=10,
            policy_version="1.0.0",
            failed_rules=[],
        )


def test_approved_requires_zero_failed_rules() -> None:
    with pytest.raises(ValidationError):
        RiskEvaluationResult(
            decision="APPROVED",
            approved=True,
            risk_score=90,
            policy_version="1.0.0",
            failed_rules=["bt_min_trades"],
        )


def test_metrics_and_policy_snapshot_round_trip() -> None:
    metrics = {"num_trades": 42, "sharpe": 1.1}
    policy = load_policy()
    result = RiskEvaluationResult(
        decision="APPROVED",
        approved=True,
        risk_score=88,
        policy_version=policy.policy_version,
        metrics_snapshot=metrics,
        policy_snapshot=policy.model_dump(),
    )
    assert result.metrics_snapshot == metrics
    assert result.policy_snapshot == policy.model_dump()


def test_risk_policy_defaults_match_yaml() -> None:
    """The default RiskPolicy matches risk_policy.yaml exactly (Phase 4)."""
    policy = RiskPolicy(
        policy_version="1.0.0",
        minimum_backtest_trades=30,
        max_allowed_drawdown_pct=15,
        minimum_profit_factor=1.2,
        minimum_total_return_pct=0,
        minimum_sharpe_like=0,
        max_position_size_pct=10,
        max_risk_per_trade_pct=1,
        max_open_positions=10,
        max_portfolio_drawdown_pct=8,
        stop_loss_required=True,
        reject_if_data_quality_bad=True,
        warn_if_exposure_time_pct_above=80,
        warn_if_trade_count_below=50,
        warn_if_profit_factor_below=1.5,
        warn_if_drawdown_pct_above=10,
    )
    loaded = load_policy()
    assert loaded == policy


def test_risk_policy_rejects_unknown_extra_key() -> None:
    with pytest.raises(ValidationError):
        RiskPolicy(
            policy_version="1.0.0",
            minimum_backtest_trades=30,
            max_allowed_drawdown_pct=15,
            minimum_profit_factor=1.2,
            minimum_total_return_pct=0,
            minimum_sharpe_like=0,
            max_position_size_pct=10,
            max_risk_per_trade_pct=1,
            max_open_positions=10,
            max_portfolio_drawdown_pct=8,
            stop_loss_required=True,
            reject_if_data_quality_bad=True,
            warn_if_exposure_time_pct_above=80,
            warn_if_trade_count_below=50,
            warn_if_profit_factor_below=1.5,
            warn_if_drawdown_pct_above=10,
            unknown_field=1,
        )
