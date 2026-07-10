"""End-to-end integration tests: Backtester.run() over the full pipeline.

Exercises rules validation -> signal generation -> simulation -> metrics via
``Backtester.run`` (never ``run_from_signals``) with the three built-in
strategies plus purpose-built minimal strategies for the max-holding and
stop-loss paths. All data is synthetic and fully deterministic (closed-form
series; no randomness).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant_engine.backtest import Backtester, BacktestConfig
from quant_engine.strategies import get_builtin_strategies

VALID_EXIT_REASONS = {"signal", "stop_loss", "max_holding", "end_of_data"}

TRADE_KEYS = {
    "symbol",
    "entry_date",
    "entry_price",
    "exit_date",
    "exit_price",
    "quantity",
    "pnl",
    "return_pct",
    "holding_days",
    "exit_reason",
    "entry_cost",
    "exit_cost",
}


def _builtin(name: str) -> dict:
    for strategy in get_builtin_strategies():
        if strategy["name"] == name:
            return strategy
    raise AssertionError(f"no built-in strategy named {name!r}")


def _frame_from_closes(closes: np.ndarray | list[float]) -> pd.DataFrame:
    """OHLCV frame where each bar opens at the prior close (bar 0 at its own).

    Highs/lows bracket the open/close so the frame satisfies the connector
    contract without ever piercing far below the closes (keeps stop-loss
    behavior driven by the close path, not artificial lows).
    """
    closes = np.asarray(closes, dtype="float64")
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = np.maximum(opens, closes) + 0.25
    lows = np.minimum(opens, closes) - 0.25
    n = len(closes)
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(n, 1_000.0),
        }
    )


def _explicit_frame(rows: list[tuple[float, float, float, float, float]]) -> pd.DataFrame:
    """Frame from explicit (open, high, low, close, volume) tuples."""
    opens, highs, lows, closes, volumes = (list(col) for col in zip(*rows))
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(rows), freq="B"),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


def _minimal_strategy(entry_above: float, **overrides) -> dict:
    """A schema-valid single-symbol strategy: enter when close > entry_above."""
    strategy = {
        "name": "integration_minimal",
        "universe": ["RELIANCE"],
        "timeframe": "1d",
        "direction": "long_only",
        "entry": {
            "all": [
                {"indicator": "close", "params": {}, "op": "greater_than", "value": entry_above}
            ]
        },
        "exit": {
            "all": [{"indicator": "close", "params": {}, "op": "less_than", "value": 0.5}]
        },
        "stop_loss": {"type": "percent", "value": 0.05},
        "position_sizing": {"type": "risk_percent", "value": 0.01},
    }
    strategy.update(overrides)
    return strategy


def _sine_trend_frame(n: int = 250, amplitude: float = 10.0, period: float = 80.0) -> pd.DataFrame:
    i = np.arange(n)
    closes = 100.0 + amplitude * np.sin(2.0 * np.pi * i / period) + 0.02 * i
    return _frame_from_closes(closes)


# --------------------------------------------------------------------------
# (a) SMA crossover end to end
# --------------------------------------------------------------------------


def test_sma_crossover_end_to_end() -> None:
    df = _sine_trend_frame()
    result = Backtester().run(df, _builtin("sma_crossover_20_50"), symbol="RELIANCE")

    assert result.num_trades >= 1
    assert len(result.trades) == result.num_trades
    assert result.equity_curve is not None
    assert list(result.equity_curve.columns) == ["date", "equity"]
    assert len(result.equity_curve) == len(df)
    assert result.equity_curve["equity"].iloc[0] == pytest.approx(1_000_000.0)
    assert result.starting_capital == pytest.approx(1_000_000.0)
    assert result.final_equity == pytest.approx(result.equity_curve["equity"].iloc[-1])

    for trade in result.trades:
        assert set(trade.keys()) == TRADE_KEYS
        assert trade["symbol"] == "RELIANCE"
        assert trade["exit_reason"] in VALID_EXIT_REASONS
        assert trade["quantity"] >= 1
        assert trade["holding_days"] >= 1
        assert trade["entry_cost"] > 0
        assert trade["exit_cost"] > 0


# --------------------------------------------------------------------------
# (b) RSI mean reversion end to end
# --------------------------------------------------------------------------


def test_rsi_mean_reversion_end_to_end() -> None:
    # Big slow oscillation: 30-bar sustained downswings push RSI(14) well
    # below 30; upswings push it back above 55.
    i = np.arange(240)
    closes = 100.0 + 30.0 * np.sin(2.0 * np.pi * i / 60.0)
    df = _frame_from_closes(closes)

    result = Backtester().run(df, _builtin("rsi_mean_reversion_14"), symbol="TCS")

    assert result.num_trades >= 1
    assert len(result.equity_curve) == len(df)
    for trade in result.trades:
        assert trade["exit_reason"] in VALID_EXIT_REASONS
        assert trade["symbol"] == "TCS"


# --------------------------------------------------------------------------
# (c) Volume breakout: engineered single trade, fill price, allocation cap
# --------------------------------------------------------------------------


def _breakout_frame() -> pd.DataFrame:
    rows: list[tuple[float, float, float, float, float]] = []
    # 20 flat warm-up bars.
    for _ in range(20):
        rows.append((100.0, 100.0, 100.0, 100.0, 1_000.0))
    # Bar 20: 20-day closing-high breakout (110 > prior max 100) on 2.5x
    # volume (2500 > 1.5 * volume_sma_20 = 1.5 * 1075 = 1612.5).
    rows.append((100.0, 110.0, 100.0, 110.0, 2_500.0))
    # Bar 21: entry fills at this open (104). Decay begins; lows stay above
    # the 7% stop (0.93 * 104.052 = 96.77).
    rows.append((104.0, 104.0, 103.0, 103.0, 1_000.0))
    rows.append((103.0, 103.0, 101.0, 101.0, 1_000.0))
    # Bar 23: close 100 < sma_20 (100.7) -> exit signal; fills at bar 24 open.
    rows.append((101.0, 101.0, 100.0, 100.0, 1_000.0))
    rows.append((100.0, 100.0, 100.0, 100.0, 1_000.0))
    # Flat tail: no re-entry (110 stays inside the highest_close window).
    for _ in range(3):
        rows.append((100.0, 100.0, 100.0, 100.0, 1_000.0))
    return _explicit_frame(rows)


def test_volume_breakout_single_engineered_trade() -> None:
    df = _breakout_frame()
    config = BacktestConfig()  # defaults: slippage 0.0005, alloc cap 10%
    result = Backtester(config).run(df, _builtin("volume_breakout_swing_20"), symbol="RELIANCE")

    assert result.num_trades == 1
    trade = result.trades[0]

    # Entry: signal on bar 20 -> fill at bar 21's open with default slippage.
    expected_fill = 104.0 * (1.0 + 0.0005)
    assert trade["entry_date"] == df["date"].iloc[21]
    assert trade["entry_price"] == pytest.approx(expected_fill)

    # Sizing: the 10%-allocation cap binds (risk-based sizing with a 7% stop
    # allows ~14.3% of equity, cash allows far more).
    expected_qty = math.floor(0.10 * 1_000_000.0 / expected_fill)
    assert trade["quantity"] == expected_qty
    assert trade["quantity"] == 961  # floor(100_000 / 104.052), hand-checked

    # Exit: signal on bar 23 (close 100 < sma_20 100.7) -> bar 24's open.
    assert trade["exit_reason"] == "signal"
    assert trade["exit_date"] == df["date"].iloc[24]
    assert trade["exit_price"] == pytest.approx(100.0 * (1.0 - 0.0005))

    assert len(result.equity_curve) == len(df)


# --------------------------------------------------------------------------
# (d) Determinism
# --------------------------------------------------------------------------


def test_backtest_is_deterministic() -> None:
    df = _sine_trend_frame()
    rules = _builtin("sma_crossover_20_50")

    first = Backtester().run(df, rules, symbol="RELIANCE")
    second = Backtester().run(df, rules, symbol="RELIANCE")

    assert first.trades == second.trades
    pd.testing.assert_frame_equal(first.equity_curve, second.equity_curve)
    assert first.final_equity == second.final_equity
    assert first.num_trades == second.num_trades


# --------------------------------------------------------------------------
# (e) max_holding_days through the full pipeline
# --------------------------------------------------------------------------


def test_max_holding_days_exit_reason() -> None:
    # Always-in strategy (entry always true, exit never) capped at 3 bars.
    # Gently rising closes keep the 5% stop out of play.
    closes = [100.0 + 0.1 * i for i in range(15)]
    df = _frame_from_closes(closes)
    rules = _minimal_strategy(entry_above=1.0, max_holding_days=3)

    result = Backtester().run(df, rules, symbol="RELIANCE")

    assert result.num_trades >= 1
    reasons = [t["exit_reason"] for t in result.trades]
    assert "max_holding" in reasons
    assert set(reasons) <= {"max_holding", "end_of_data"}
    for trade in result.trades:
        if trade["exit_reason"] == "max_holding":
            assert trade["holding_days"] == 3


# --------------------------------------------------------------------------
# (f) stop_loss through the full pipeline
# --------------------------------------------------------------------------


def test_stop_loss_exit_reason_on_crash() -> None:
    rows: list[tuple[float, float, float, float, float]] = []
    # Bars 0..4: flat below the 105 entry trigger.
    for _ in range(5):
        rows.append((100.0, 100.0, 100.0, 100.0, 1_000.0))
    # Bar 5: close 106 > 105 -> entry signal.
    rows.append((100.0, 106.0, 100.0, 106.0, 1_000.0))
    # Bar 6: entry fills at open 106 (fill 106.053, stop = 0.95x = 100.75);
    # low stays above the stop, so no same-bar stop-out.
    rows.append((106.0, 106.5, 105.5, 106.0, 1_000.0))
    # Bar 7: crash. Open 101 is still above the stop (no gap-down fill), but
    # the low pierces it -> stop-loss fill at stop_price * (1 - slippage).
    rows.append((101.0, 101.0, 95.0, 96.0, 1_000.0))
    # Tail: below the trigger, no re-entry.
    for _ in range(3):
        rows.append((96.0, 96.0, 96.0, 96.0, 1_000.0))
    df = _explicit_frame(rows)

    rules = _minimal_strategy(entry_above=105.0)
    result = Backtester().run(df, rules, symbol="RELIANCE")

    assert result.num_trades == 1
    trade = result.trades[0]
    assert trade["exit_reason"] == "stop_loss"
    assert trade["entry_date"] == df["date"].iloc[6]
    assert trade["exit_date"] == df["date"].iloc[7]

    entry_fill = 106.0 * (1.0 + 0.0005)
    stop_price = entry_fill * (1.0 - 0.05)
    assert trade["entry_price"] == pytest.approx(entry_fill)
    assert trade["exit_price"] == pytest.approx(stop_price * (1.0 - 0.0005))
    assert trade["pnl"] < 0
