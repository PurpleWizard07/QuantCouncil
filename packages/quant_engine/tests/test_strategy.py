"""Tests for quant_engine.strategy (strategy definition schema validation)."""

from __future__ import annotations

import pytest

from quant_engine.strategies import (
    RSI_MEAN_REVERSION,
    SMA_CROSSOVER,
    VOLUME_BREAKOUT,
    get_builtin_strategies,
)
from quant_engine.strategy import StrategyValidationError, validate_strategy


def _minimal_strategy(**overrides) -> dict:
    base = {
        "name": "test_strategy",
        "universe": ["RELIANCE"],
        "timeframe": "1d",
        "direction": "long_only",
        "entry": {"all": [{"indicator": "close", "params": {}, "op": "greater_than", "value": 100}]},
        "exit": {"all": [{"indicator": "close", "params": {}, "op": "less_than", "value": 90}]},
        "stop_loss": {"type": "percent", "value": 0.05},
        "position_sizing": {"type": "risk_percent", "value": 0.01},
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# Built-in strategies
# --------------------------------------------------------------------------


@pytest.mark.parametrize("strategy", [SMA_CROSSOVER, RSI_MEAN_REVERSION, VOLUME_BREAKOUT])
def test_builtin_strategies_validate(strategy: dict) -> None:
    validate_strategy(strategy)


def test_get_builtin_strategies_returns_three() -> None:
    strategies = get_builtin_strategies()
    assert len(strategies) == 3
    names = {s["name"] for s in strategies}
    assert names == {"sma_crossover_20_50", "rsi_mean_reversion_14", "volume_breakout_swing_20"}


def test_get_builtin_strategies_returns_deep_copies() -> None:
    strategies = get_builtin_strategies()
    strategies[0]["name"] = "mutated"
    strategies[0]["entry"]["all"][0]["op"] = "mutated"
    assert SMA_CROSSOVER["name"] == "sma_crossover_20_50"
    assert SMA_CROSSOVER["entry"]["all"][0]["op"] == "crosses_above"


# --------------------------------------------------------------------------
# Minimal valid strategy / normalization
# --------------------------------------------------------------------------


def test_minimal_strategy_validates() -> None:
    validate_strategy(_minimal_strategy())


def test_normalized_copy_does_not_alias_input() -> None:
    original = _minimal_strategy()
    normalized = validate_strategy(original)

    normalized["name"] = "mutated"
    normalized["universe"].append("TCS")
    normalized["entry"]["all"][0]["op"] = "mutated"

    assert original["name"] == "test_strategy"
    assert original["universe"] == ["RELIANCE"]
    assert original["entry"]["all"][0]["op"] == "greater_than"


# --------------------------------------------------------------------------
# Top-level field rules
# --------------------------------------------------------------------------


def test_rejects_unknown_top_level_key() -> None:
    strategy = _minimal_strategy(bogus_field=123)
    with pytest.raises(StrategyValidationError, match="bogus_field"):
        validate_strategy(strategy)


def test_rejects_missing_required_top_level_key() -> None:
    strategy = _minimal_strategy()
    del strategy["stop_loss"]
    with pytest.raises(StrategyValidationError, match="stop_loss"):
        validate_strategy(strategy)


def test_rejects_empty_name() -> None:
    with pytest.raises(StrategyValidationError):
        validate_strategy(_minimal_strategy(name=""))


def test_rejects_empty_universe() -> None:
    with pytest.raises(StrategyValidationError, match="universe"):
        validate_strategy(_minimal_strategy(universe=[]))


def test_rejects_empty_string_in_universe() -> None:
    with pytest.raises(StrategyValidationError, match="universe"):
        validate_strategy(_minimal_strategy(universe=["RELIANCE", ""]))


def test_rejects_bad_timeframe() -> None:
    with pytest.raises(StrategyValidationError, match="daily only in v1"):
        validate_strategy(_minimal_strategy(timeframe="1h"))


def test_rejects_bad_direction() -> None:
    with pytest.raises(StrategyValidationError, match="direction"):
        validate_strategy(_minimal_strategy(direction="long_short"))


def test_description_optional_and_accepted() -> None:
    validate_strategy(_minimal_strategy(description="a description"))


def test_rejects_non_string_description() -> None:
    with pytest.raises(StrategyValidationError, match="description"):
        validate_strategy(_minimal_strategy(description=123))


# --------------------------------------------------------------------------
# stop_loss / position_sizing
# --------------------------------------------------------------------------


def test_rejects_missing_stop_loss() -> None:
    strategy = _minimal_strategy()
    del strategy["stop_loss"]
    with pytest.raises(StrategyValidationError):
        validate_strategy(strategy)


def test_rejects_atr_stop_loss() -> None:
    with pytest.raises(StrategyValidationError, match="reserved for a later phase"):
        validate_strategy(_minimal_strategy(stop_loss={"type": "atr", "value": 2.0}))


def test_rejects_unknown_stop_loss_type() -> None:
    with pytest.raises(StrategyValidationError, match="stop_loss"):
        validate_strategy(_minimal_strategy(stop_loss={"type": "fixed", "value": 0.05}))


def test_rejects_stop_loss_value_out_of_range() -> None:
    with pytest.raises(StrategyValidationError):
        validate_strategy(_minimal_strategy(stop_loss={"type": "percent", "value": 1.5}))


def test_rejects_bad_position_sizing_type() -> None:
    with pytest.raises(StrategyValidationError, match="position_sizing"):
        validate_strategy(_minimal_strategy(position_sizing={"type": "fixed_lot", "value": 0.01}))


def test_rejects_position_sizing_value_out_of_range() -> None:
    with pytest.raises(StrategyValidationError):
        validate_strategy(_minimal_strategy(position_sizing={"type": "risk_percent", "value": 0.0}))


# --------------------------------------------------------------------------
# Condition tree rules
# --------------------------------------------------------------------------


def test_rejects_unknown_operator() -> None:
    strategy = _minimal_strategy(
        entry={"all": [{"indicator": "close", "params": {}, "op": "equals", "value": 100}]}
    )
    with pytest.raises(StrategyValidationError, match="equals"):
        validate_strategy(strategy)


def test_rejects_unknown_indicator() -> None:
    strategy = _minimal_strategy(
        entry={"all": [{"indicator": "macd", "params": {}, "op": "greater_than", "value": 100}]}
    )
    with pytest.raises(StrategyValidationError, match="macd"):
        validate_strategy(strategy)


def test_rejects_unknown_combinator_key() -> None:
    strategy = _minimal_strategy(
        entry={"none": [{"indicator": "close", "params": {}, "op": "greater_than", "value": 100}]}
    )
    with pytest.raises(StrategyValidationError):
        validate_strategy(strategy)


def test_rejects_both_value_and_target() -> None:
    strategy = _minimal_strategy(
        entry={
            "all": [
                {
                    "indicator": "close",
                    "params": {},
                    "op": "greater_than",
                    "value": 100,
                    "target": {"indicator": "sma", "params": {"window": 20}},
                }
            ]
        }
    )
    with pytest.raises(StrategyValidationError, match="both"):
        validate_strategy(strategy)


def test_rejects_neither_value_nor_target() -> None:
    strategy = _minimal_strategy(
        entry={"all": [{"indicator": "close", "params": {}, "op": "greater_than"}]}
    )
    with pytest.raises(StrategyValidationError, match="neither"):
        validate_strategy(strategy)


def test_rejects_empty_combinator_list() -> None:
    strategy = _minimal_strategy(entry={"all": []})
    with pytest.raises(StrategyValidationError):
        validate_strategy(strategy)


def test_rejects_bad_window_zero() -> None:
    strategy = _minimal_strategy(
        entry={"all": [{"indicator": "sma", "params": {"window": 0}, "op": "greater_than", "value": 100}]}
    )
    with pytest.raises(StrategyValidationError):
        validate_strategy(strategy)


def test_rejects_non_integer_window() -> None:
    strategy = _minimal_strategy(
        entry={
            "all": [
                {"indicator": "sma", "params": {"window": 20.5}, "op": "greater_than", "value": 100}
            ]
        }
    )
    with pytest.raises(StrategyValidationError):
        validate_strategy(strategy)


def test_rejects_params_for_paramless_indicator() -> None:
    strategy = _minimal_strategy(
        entry={"all": [{"indicator": "close", "params": {"window": 20}, "op": "greater_than", "value": 100}]}
    )
    with pytest.raises(StrategyValidationError):
        validate_strategy(strategy)


def test_rejects_missing_window_param() -> None:
    strategy = _minimal_strategy(
        entry={"all": [{"indicator": "sma", "params": {}, "op": "greater_than", "value": 100}]}
    )
    with pytest.raises(StrategyValidationError):
        validate_strategy(strategy)


def test_rejects_negative_multiplier() -> None:
    strategy = _minimal_strategy(
        entry={
            "all": [
                {
                    "indicator": "volume",
                    "params": {},
                    "op": "greater_than",
                    "target": {
                        "indicator": "volume_sma",
                        "params": {"window": 20},
                        "multiplier": -1.5,
                    },
                }
            ]
        }
    )
    with pytest.raises(StrategyValidationError, match="multiplier"):
        validate_strategy(strategy)


def test_multiplier_defaults_to_one() -> None:
    strategy = _minimal_strategy(
        entry={
            "all": [
                {
                    "indicator": "volume",
                    "params": {},
                    "op": "greater_than",
                    "target": {"indicator": "volume_sma", "params": {"window": 20}},
                }
            ]
        }
    )
    normalized = validate_strategy(strategy)
    assert normalized["entry"]["all"][0]["target"]["multiplier"] == 1.0


def test_nested_combinators_validate() -> None:
    strategy = _minimal_strategy(
        entry={
            "any": [
                {"all": [{"indicator": "close", "params": {}, "op": "greater_than", "value": 100}]},
                {"indicator": "close", "params": {}, "op": "less_than", "value": 50},
            ]
        }
    )
    validate_strategy(strategy)


# --------------------------------------------------------------------------
# Phase 3 optional fields: max_holding_days / costs
# --------------------------------------------------------------------------


def test_max_holding_days_valid() -> None:
    normalized = validate_strategy(_minimal_strategy(max_holding_days=10))
    assert normalized["max_holding_days"] == 10


def test_max_holding_days_omitted_by_default() -> None:
    normalized = validate_strategy(_minimal_strategy())
    assert "max_holding_days" not in normalized


def test_rejects_bad_max_holding_days_zero() -> None:
    with pytest.raises(StrategyValidationError, match="max_holding_days"):
        validate_strategy(_minimal_strategy(max_holding_days=0))


def test_rejects_bad_max_holding_days_type() -> None:
    with pytest.raises(StrategyValidationError, match="max_holding_days"):
        validate_strategy(_minimal_strategy(max_holding_days=10.5))


def test_costs_valid() -> None:
    normalized = validate_strategy(
        _minimal_strategy(costs={"transaction_cost_pct": 0.001, "slippage_pct": 0.0005})
    )
    assert normalized["costs"] == {"transaction_cost_pct": 0.001, "slippage_pct": 0.0005}


def test_costs_partial_keys_allowed() -> None:
    normalized = validate_strategy(_minimal_strategy(costs={"transaction_cost_pct": 0.001}))
    assert normalized["costs"] == {"transaction_cost_pct": 0.001}


def test_costs_empty_dict_allowed() -> None:
    normalized = validate_strategy(_minimal_strategy(costs={}))
    assert normalized["costs"] == {}


def test_costs_omitted_by_default() -> None:
    normalized = validate_strategy(_minimal_strategy())
    assert "costs" not in normalized


def test_rejects_unknown_costs_key() -> None:
    with pytest.raises(StrategyValidationError, match="costs"):
        validate_strategy(_minimal_strategy(costs={"bogus": 0.01}))


def test_rejects_bad_costs_value() -> None:
    with pytest.raises(StrategyValidationError, match="costs"):
        validate_strategy(_minimal_strategy(costs={"transaction_cost_pct": 1.5}))


def test_costs_boundary_zero_allowed() -> None:
    normalized = validate_strategy(_minimal_strategy(costs={"transaction_cost_pct": 0.0}))
    assert normalized["costs"] == {"transaction_cost_pct": 0.0}
