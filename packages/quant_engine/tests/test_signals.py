"""Tests for quant_engine.signals.generate_signals.

Expected outcomes are hand-derived from the indicator formulas documented in
indicators.py (and cross-checked against test_indicators.py's worked
examples), so assertions check the signal-interpretation logic, not just a
re-run of the implementation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from quant_engine.signals import generate_signals
from quant_engine.strategy import StrategyValidationError


def _make_df(
    closes: list[float],
    volumes: list[float] | None = None,
) -> pd.DataFrame:
    n = len(closes)
    close_series = pd.Series(closes, dtype="float64")
    if volumes is None:
        volumes = [1_000.0] * n
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="D"),
            "open": close_series,
            "high": close_series,
            "low": close_series,
            "close": close_series,
            "volume": pd.Series(volumes, dtype="float64"),
        }
    )


def _rules(entry: dict, exit_: dict, stop_loss_value: float = 0.05) -> dict:
    return {
        "name": "test_rules",
        "universe": ["RELIANCE"],
        "timeframe": "1d",
        "direction": "long_only",
        "entry": entry,
        "exit": exit_,
        "stop_loss": {"type": "percent", "value": stop_loss_value},
        "position_sizing": {"type": "risk_percent", "value": 0.01},
    }


def _sma_crossover_rules(fast: int, slow: int, stop_loss_value: float = 0.05) -> dict:
    return _rules(
        entry={
            "all": [
                {
                    "indicator": "sma",
                    "params": {"window": fast},
                    "op": "crosses_above",
                    "target": {"indicator": "sma", "params": {"window": slow}},
                }
            ]
        },
        exit_={
            "all": [
                {
                    "indicator": "sma",
                    "params": {"window": fast},
                    "op": "crosses_below",
                    "target": {"indicator": "sma", "params": {"window": slow}},
                }
            ]
        },
        stop_loss_value=stop_loss_value,
    )


# --------------------------------------------------------------------------
# (a) SMA crossover: hand-computed cross bars, (g) stop_loss_price
# --------------------------------------------------------------------------


def test_sma_crossover_entry_and_exit_bars() -> None:
    # sma(2) vs sma(3) over a flat-up-flat-down-flat price path.
    # Hand-computed (see docstring math below):
    #   idx3: sma2_prev == sma3_prev (10==10), sma2 > sma3 (15 > 13.333) -> crosses_above
    #   idx6: sma2_prev == sma3_prev (20==20), sma2 < sma3 (15 < 16.667) -> crosses_below
    # No other bar satisfies either strict-cross condition.
    closes = [10, 10, 10, 20, 20, 20, 10, 10, 10]
    df = _make_df(closes)
    rules = _sma_crossover_rules(fast=2, slow=3, stop_loss_value=0.05)

    result = generate_signals(df, rules)

    expected_entry = [False, False, False, True, False, False, False, False, False]
    expected_exit = [False, False, False, False, False, False, True, False, False]
    assert result["entry_signal"].tolist() == expected_entry
    assert result["exit_signal"].tolist() == expected_exit

    # Audit columns present with the documented naming scheme.
    assert "sma_2" in result.columns
    assert "sma_3" in result.columns


def test_sma_crossover_above_then_above_does_not_refire() -> None:
    # idx4/idx5 stay above (sma2 > sma3) but never re-cross -- greater_than
    # alone would be True there; crosses_above must not be.
    closes = [10, 10, 10, 20, 20, 20, 10, 10, 10]
    df = _make_df(closes)
    rules = _sma_crossover_rules(fast=2, slow=3)
    result = generate_signals(df, rules)
    assert bool(result["entry_signal"].iloc[4]) is False
    assert bool(result["entry_signal"].iloc[5]) is False


def test_stop_loss_price_on_entry_bars_only() -> None:
    closes = [10, 10, 10, 20, 20, 20, 10, 10, 10]
    df = _make_df(closes)
    rules = _sma_crossover_rules(fast=2, slow=3, stop_loss_value=0.05)
    result = generate_signals(df, rules)

    entry_mask = result["entry_signal"]
    assert entry_mask.sum() == 1
    entry_idx = entry_mask[entry_mask].index[0]

    expected_stop = result.loc[entry_idx, "close"] * (1 - 0.05)
    assert result.loc[entry_idx, "stop_loss_price"] == pytest.approx(expected_stop)
    assert result.loc[entry_idx, "stop_loss_price"] == pytest.approx(20.0 * 0.95)

    non_entry = result.loc[~entry_mask, "stop_loss_price"]
    assert non_entry.isna().all()


# --------------------------------------------------------------------------
# (b) RSI mean reversion + (e) NaN warm-up -> False
# --------------------------------------------------------------------------


def test_rsi_mean_reversion_signals() -> None:
    # window=3, drop then recovery. Hand-derived RSI (Wilder smoothing,
    # alpha=1/3, seeded at the first non-NaN gain/loss observation):
    #   idx0,1,2: NaN (masked warm-up)
    #   idx3: RSI=0     idx4: RSI=0        (all-loss window -> oversold)
    #   idx5: RSI~33.3  (recovering, between thresholds)
    #   idx6: RSI~61.9  idx7: RSI~76.8  idx8: RSI~85.4  (overbought)
    closes = [100, 90, 80, 70, 60, 70, 85, 100, 115]
    df = _make_df(closes)
    rules = _rules(
        entry={"all": [{"indicator": "rsi", "params": {"window": 3}, "op": "less_than", "value": 30}]},
        exit_={"all": [{"indicator": "rsi", "params": {"window": 3}, "op": "greater_than", "value": 55}]},
    )

    result = generate_signals(df, rules)

    expected_entry = [False, False, False, True, True, False, False, False, False]
    expected_exit = [False, False, False, False, False, False, True, True, True]
    assert result["entry_signal"].tolist() == expected_entry
    assert result["exit_signal"].tolist() == expected_exit

    # (e) NaN warm-up region (rsi_3 is NaN for idx 0,1,2) must be False, not NaN.
    assert result["rsi_3"].iloc[:3].isna().all()
    assert result["entry_signal"].iloc[:3].tolist() == [False, False, False]
    assert result["exit_signal"].iloc[:3].tolist() == [False, False, False]
    assert not result["entry_signal"].isna().any()
    assert not result["exit_signal"].isna().any()


# --------------------------------------------------------------------------
# (c) Volume breakout: highest_close shift regression + flat series
# --------------------------------------------------------------------------


def _volume_breakout_rules() -> dict:
    return _rules(
        entry={
            "all": [
                {
                    "indicator": "close",
                    "params": {},
                    "op": "greater_than",
                    "target": {"indicator": "highest_close", "params": {"window": 20}},
                },
                {
                    "indicator": "volume",
                    "params": {},
                    "op": "greater_than",
                    "target": {
                        "indicator": "volume_sma",
                        "params": {"window": 20},
                        "multiplier": 1.5,
                    },
                },
            ]
        },
        exit_={
            "all": [
                {
                    "indicator": "close",
                    "params": {},
                    "op": "less_than",
                    "target": {"indicator": "sma", "params": {"window": 20}},
                }
            ]
        },
        stop_loss_value=0.07,
    )


def test_volume_breakout_fires_on_new_high_with_shift() -> None:
    # 20 flat bars at close=100 (idx 0..19), then a new high at idx20 (110),
    # confirmed by volume well above 1.5x its 20-day average. This is only
    # reachable if highest_close is computed EXCLUDING the current bar
    # (shift(1)); with the raw inclusive indicator, close(t) is always part
    # of its own rolling max, so close(t) > max(...) (including itself)
    # could never be true, and this entry could never fire.
    closes = [100.0] * 20 + [110.0]
    volumes = [1_000.0] * 20
    volumes[19] = 1_000.0  # keep prior window simple
    volumes = volumes + [5_000.0]
    df = _make_df(closes, volumes=volumes)
    rules = _volume_breakout_rules()

    result = generate_signals(df, rules)

    assert bool(result["entry_signal"].iloc[20]) is True
    assert result["entry_signal"].iloc[:20].tolist() == [False] * 20

    # highest_close_20 at idx20 must equal 100 (max of the prior 20 bars,
    # excluding idx20's own close of 110) -- proof the shift was applied.
    assert result["highest_close_20"].iloc[20] == pytest.approx(100.0)
    assert result["close"].iloc[20] == pytest.approx(110.0)

    # Audit columns for the multiplier target.
    assert "volume_sma_20" in result.columns
    assert "volume_sma_20_x1.5" in result.columns
    assert result["volume_sma_20_x1.5"].iloc[20] == pytest.approx(
        result["volume_sma_20"].iloc[20] * 1.5
    )


def test_volume_breakout_flat_series_never_signals() -> None:
    closes = [100.0] * 30
    df = _make_df(closes)
    rules = _volume_breakout_rules()

    result = generate_signals(df, rules)

    assert not result["entry_signal"].any()


# --------------------------------------------------------------------------
# (d) crosses_above requires a strict cross
# --------------------------------------------------------------------------


def test_crosses_above_requires_strict_cross() -> None:
    # close vs a scalar value=5. idx1: 5<=5 (equal) then idx2: 6>5 -> fires
    # (equal-then-above). idx3: 6<=5 is False (already above) -> 7>5 alone
    # does not fire (above-then-above).
    closes = [5, 5, 6, 7, 7]
    df = _make_df(closes)
    rules = _rules(
        entry={"all": [{"indicator": "close", "params": {}, "op": "crosses_above", "value": 5}]},
        exit_={"all": [{"indicator": "close", "params": {}, "op": "crosses_below", "value": 5}]},
    )

    result = generate_signals(df, rules)

    assert result["entry_signal"].tolist() == [False, False, True, False, False]


# --------------------------------------------------------------------------
# (f) bool dtype
# --------------------------------------------------------------------------


def test_signal_columns_are_bool_dtype() -> None:
    df = _make_df([10, 10, 10, 20, 20, 20, 10, 10, 10])
    rules = _sma_crossover_rules(fast=2, slow=3)
    result = generate_signals(df, rules)
    assert result["entry_signal"].dtype == bool
    assert result["exit_signal"].dtype == bool


# --------------------------------------------------------------------------
# (h) input df not mutated
# --------------------------------------------------------------------------


def test_input_df_not_mutated() -> None:
    df = _make_df([10, 10, 10, 20, 20, 20, 10, 10, 10])
    original_columns = list(df.columns)
    original = df.copy()

    generate_signals(df, _sma_crossover_rules(fast=2, slow=3))

    assert list(df.columns) == original_columns
    pd.testing.assert_frame_equal(df, original)


# --------------------------------------------------------------------------
# (i) missing column / empty df raises ValueError
# --------------------------------------------------------------------------


def test_missing_column_raises_value_error() -> None:
    df = _make_df([10, 20, 30]).drop(columns=["volume"])
    with pytest.raises(ValueError, match="volume"):
        generate_signals(df, _sma_crossover_rules(fast=1, slow=2))


def test_empty_df_raises_value_error() -> None:
    df = _make_df([10, 20, 30]).iloc[0:0]
    with pytest.raises(ValueError, match="empty"):
        generate_signals(df, _sma_crossover_rules(fast=1, slow=2))


def test_invalid_rules_raise_strategy_validation_error() -> None:
    df = _make_df([10, 20, 30])
    bad_rules = _sma_crossover_rules(fast=1, slow=2)
    bad_rules["timeframe"] = "1h"
    with pytest.raises(StrategyValidationError):
        generate_signals(df, bad_rules)


# --------------------------------------------------------------------------
# (j) any/all nesting
# --------------------------------------------------------------------------


def test_nested_any_all_combinators() -> None:
    # condA: close > 2 -> [F,F,T,T,T]
    # condB: close < 4 -> [T,T,T,F,F]
    # all(condA, condB) -> [F,F,T,F,F]
    # condC: close > 4 -> [F,F,F,F,T]
    # any(all(condA,condB), condC) -> [F,F,T,F,T]
    closes = [1, 2, 3, 4, 5]
    df = _make_df(closes)
    rules = _rules(
        entry={
            "any": [
                {
                    "all": [
                        {"indicator": "close", "params": {}, "op": "greater_than", "value": 2},
                        {"indicator": "close", "params": {}, "op": "less_than", "value": 4},
                    ]
                },
                {"indicator": "close", "params": {}, "op": "greater_than", "value": 4},
            ]
        },
        exit_={"all": [{"indicator": "close", "params": {}, "op": "less_than", "value": 0}]},
    )

    result = generate_signals(df, rules)

    assert result["entry_signal"].tolist() == [False, False, True, False, True]
    assert result["exit_signal"].tolist() == [False, False, False, False, False]


# --------------------------------------------------------------------------
# (k) multiplier applied
# --------------------------------------------------------------------------


def test_target_multiplier_is_applied() -> None:
    # volume_sma(2): idx0 NaN, idx1=100, idx2=100, idx3=(100+500)/2=300.
    # multiplier=1.5 -> idx1=150, idx2=150, idx3=450.
    # volume > multiplied: idx1:100>150 F, idx2:100>150 F, idx3:500>450 T.
    closes = [10, 10, 10, 10]
    volumes = [100, 100, 100, 500]
    df = _make_df(closes, volumes=volumes)
    rules = _rules(
        entry={
            "all": [
                {
                    "indicator": "volume",
                    "params": {},
                    "op": "greater_than",
                    "target": {
                        "indicator": "volume_sma",
                        "params": {"window": 2},
                        "multiplier": 1.5,
                    },
                }
            ]
        },
        exit_={"all": [{"indicator": "close", "params": {}, "op": "less_than", "value": 0}]},
    )

    result = generate_signals(df, rules)

    assert result["entry_signal"].tolist() == [False, False, False, True]
    assert "volume_sma_2" in result.columns
    assert "volume_sma_2_x1.5" in result.columns
    multiplied = result["volume_sma_2_x1.5"]
    base = result["volume_sma_2"]
    assert multiplied.iloc[1:].tolist() == pytest.approx((base.iloc[1:] * 1.5).tolist())
