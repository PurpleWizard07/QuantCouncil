"""Tests for the YAML-backed risk policy loader (Phase 4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from risk_engine.policy import RiskPolicy, RiskPolicyError, default_policy, load_policy

_VALID_YAML = """\
policy_version: "1.0.0"
minimum_backtest_trades: 30
max_allowed_drawdown_pct: 15
minimum_profit_factor: 1.2
minimum_total_return_pct: 0
minimum_sharpe_like: 0
max_position_size_pct: 10
max_risk_per_trade_pct: 1
max_open_positions: 10
max_portfolio_drawdown_pct: 8
stop_loss_required: true
reject_if_data_quality_bad: true
warn_if_exposure_time_pct_above: 80
warn_if_trade_count_below: 50
warn_if_profit_factor_below: 1.5
warn_if_drawdown_pct_above: 10
"""


def test_load_default_policy_matches_yaml_values() -> None:
    policy = load_policy()
    assert policy.policy_version == "1.0.0"
    assert policy.minimum_backtest_trades == 30
    assert policy.max_allowed_drawdown_pct == 15
    assert policy.minimum_profit_factor == 1.2
    assert policy.minimum_total_return_pct == 0
    assert policy.minimum_sharpe_like == 0
    assert policy.max_position_size_pct == 10
    assert policy.max_risk_per_trade_pct == 1
    assert policy.max_open_positions == 10
    assert policy.max_portfolio_drawdown_pct == 8
    assert policy.stop_loss_required is True
    assert policy.reject_if_data_quality_bad is True
    assert policy.warn_if_exposure_time_pct_above == 80
    assert policy.warn_if_trade_count_below == 50
    assert policy.warn_if_profit_factor_below == 1.5
    assert policy.warn_if_drawdown_pct_above == 10


def test_default_policy_wrapper_matches_load_policy_none() -> None:
    assert default_policy() == load_policy(None)


def test_load_policy_returns_equal_but_independent_objects() -> None:
    first = load_policy()
    second = load_policy()
    assert first == second
    assert first is not second


def test_load_policy_from_explicit_path(tmp_path: Path) -> None:
    custom = tmp_path / "custom_policy.yaml"
    custom.write_text(_VALID_YAML, encoding="utf-8")
    policy = load_policy(custom)
    assert policy.policy_version == "1.0.0"
    assert policy.minimum_backtest_trades == 30


def test_missing_file_raises_risk_policy_error(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(RiskPolicyError):
        load_policy(missing)


def test_malformed_yaml_raises_risk_policy_error(tmp_path: Path) -> None:
    bad = tmp_path / "malformed.yaml"
    bad.write_text("policy_version: '1.0.0'\n  bad_indent: [1, 2\n", encoding="utf-8")
    with pytest.raises(RiskPolicyError, match="Malformed YAML"):
        load_policy(bad)


def test_non_mapping_yaml_raises_risk_policy_error(tmp_path: Path) -> None:
    listy = tmp_path / "listy.yaml"
    listy.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(RiskPolicyError, match="mapping"):
        load_policy(listy)


def test_missing_required_key_raises_risk_policy_error(tmp_path: Path) -> None:
    incomplete = tmp_path / "incomplete.yaml"
    lines = _VALID_YAML.splitlines()
    without_version = "\n".join(line for line in lines if not line.startswith("policy_version"))
    incomplete.write_text(without_version, encoding="utf-8")
    with pytest.raises(RiskPolicyError, match="schema validation"):
        load_policy(incomplete)


def test_wrong_type_raises_risk_policy_error(tmp_path: Path) -> None:
    wrong_type = tmp_path / "wrong_type.yaml"
    wrong_type.write_text(
        _VALID_YAML.replace("minimum_backtest_trades: 30", "minimum_backtest_trades: not_a_number"),
        encoding="utf-8",
    )
    with pytest.raises(RiskPolicyError, match="schema validation"):
        load_policy(wrong_type)


def test_unknown_extra_key_raises_risk_policy_error(tmp_path: Path) -> None:
    extra_key = tmp_path / "extra_key.yaml"
    extra_key.write_text(_VALID_YAML + "unknown_extra_field: 1\n", encoding="utf-8")
    with pytest.raises(RiskPolicyError, match="schema validation"):
        load_policy(extra_key)


def test_risk_policy_error_is_a_value_error() -> None:
    assert issubclass(RiskPolicyError, ValueError)


def test_loading_same_file_twice_gives_equal_independent_objects(tmp_path: Path) -> None:
    custom = tmp_path / "policy.yaml"
    custom.write_text(_VALID_YAML, encoding="utf-8")
    first = load_policy(custom)
    second = load_policy(custom)
    assert first == second
    assert first is not second
    assert isinstance(first, RiskPolicy)
