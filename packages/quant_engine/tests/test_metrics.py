"""Tests for quant_engine.metrics.

Expected values are hand-computed (or derived directly from the documented
formula using plain Python arithmetic, cross-checked against a manual
derivation in comments) so each assertion checks the math, not just re-runs
the implementation.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant_engine import metrics


def _dates(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="D")


# --------------------------------------------------------------------------
# total_return
# --------------------------------------------------------------------------


def test_total_return_basic() -> None:
    curve = pd.Series([100.0, 150.0, 200.0], index=_dates(3))
    assert metrics.total_return(curve) == pytest.approx(1.0)


def test_total_return_loss() -> None:
    curve = pd.Series([200.0, 150.0, 100.0], index=_dates(3))
    assert metrics.total_return(curve) == pytest.approx(-0.5)


def test_total_return_single_point_is_zero() -> None:
    curve = pd.Series([100.0], index=_dates(1))
    assert metrics.total_return(curve) == 0.0


def test_total_return_empty_is_zero() -> None:
    assert metrics.total_return(pd.Series([], dtype=float)) == 0.0


def test_total_return_zero_first_is_zero() -> None:
    curve = pd.Series([0.0, 100.0], index=_dates(2))
    assert metrics.total_return(curve) == 0.0


# --------------------------------------------------------------------------
# cagr
# --------------------------------------------------------------------------


def test_cagr_doubling_over_252_bars_is_approximately_one() -> None:
    # n_periods = len(curve) - 1 = 252 -> cagr = (200/100)**(252/252) - 1 = 1.0
    curve = pd.Series(np.linspace(100.0, 200.0, 253), index=_dates(253))
    assert metrics.cagr(curve) == pytest.approx(1.0, rel=1e-9)


def test_cagr_doubling_over_half_year_annualizes_to_3x() -> None:
    # n_periods = 126 -> cagr = (2)**(252/126) - 1 = 2**2 - 1 = 3.0
    curve = pd.Series(np.linspace(100.0, 200.0, 127), index=_dates(127))
    assert metrics.cagr(curve) == pytest.approx(3.0, rel=1e-9)


def test_cagr_single_point_is_zero() -> None:
    curve = pd.Series([100.0], index=_dates(1))
    assert metrics.cagr(curve) == 0.0


def test_cagr_non_positive_first_is_zero() -> None:
    curve = pd.Series([0.0, 100.0, 200.0], index=_dates(3))
    assert metrics.cagr(curve) == 0.0
    curve_neg = pd.Series([-10.0, 100.0], index=_dates(2))
    assert metrics.cagr(curve_neg) == 0.0


# --------------------------------------------------------------------------
# max_drawdown
# --------------------------------------------------------------------------


def test_max_drawdown_known_zigzag() -> None:
    # running max: 100,120,120,120,120,130
    # drawdown:      0,  0,.25,.0833..,.3333..,0
    curve = pd.Series([100.0, 120.0, 90.0, 110.0, 80.0, 130.0], index=_dates(6))
    expected = 1.0 - 80.0 / 120.0
    assert metrics.max_drawdown(curve) == pytest.approx(expected)


def test_max_drawdown_monotonic_rise_is_zero() -> None:
    curve = pd.Series([100.0, 110.0, 120.0, 150.0], index=_dates(4))
    assert metrics.max_drawdown(curve) == 0.0


def test_max_drawdown_empty_is_zero() -> None:
    assert metrics.max_drawdown(pd.Series([], dtype=float)) == 0.0


# --------------------------------------------------------------------------
# win_rate / avg_win / avg_loss / profit_factor / num_trades / best / worst
# --------------------------------------------------------------------------

_TRADES = [
    {"pnl": 100.0},
    {"pnl": -50.0},
    {"pnl": 30.0},
    {"pnl": -10.0},
]


def test_win_rate_basic() -> None:
    assert metrics.win_rate(_TRADES) == pytest.approx(0.5)


def test_win_rate_no_trades_is_zero() -> None:
    assert metrics.win_rate([]) == 0.0


def test_avg_win_basic() -> None:
    assert metrics.avg_win(_TRADES) == pytest.approx((100.0 + 30.0) / 2)


def test_avg_win_no_winners_is_zero() -> None:
    assert metrics.avg_win([{"pnl": -5.0}, {"pnl": -10.0}]) == 0.0


def test_avg_loss_basic() -> None:
    assert metrics.avg_loss(_TRADES) == pytest.approx((-50.0 + -10.0) / 2)


def test_avg_loss_no_losers_is_zero() -> None:
    assert metrics.avg_loss([{"pnl": 5.0}, {"pnl": 10.0}]) == 0.0


def test_profit_factor_basic() -> None:
    gross_profit = 100.0 + 30.0
    gross_loss = 50.0 + 10.0
    assert metrics.profit_factor(_TRADES) == pytest.approx(gross_profit / gross_loss)


def test_profit_factor_no_losses_with_wins_is_inf() -> None:
    assert metrics.profit_factor([{"pnl": 10.0}, {"pnl": 20.0}]) == float("inf")


def test_profit_factor_no_trades_is_zero() -> None:
    assert metrics.profit_factor([]) == 0.0


def test_profit_factor_all_breakeven_is_zero() -> None:
    assert metrics.profit_factor([{"pnl": 0.0}, {"pnl": 0.0}]) == 0.0


def test_num_trades() -> None:
    assert metrics.num_trades(_TRADES) == 4
    assert metrics.num_trades([]) == 0


def test_best_trade() -> None:
    assert metrics.best_trade(_TRADES) == 100.0


def test_worst_trade() -> None:
    assert metrics.worst_trade(_TRADES) == -50.0


def test_best_worst_trade_empty_is_zero() -> None:
    assert metrics.best_trade([]) == 0.0
    assert metrics.worst_trade([]) == 0.0


# --------------------------------------------------------------------------
# exposure_time
# --------------------------------------------------------------------------


def test_exposure_time_basic() -> None:
    flags = pd.Series([True, True, False, True])
    assert metrics.exposure_time(flags) == pytest.approx(0.75)


def test_exposure_time_empty_is_zero() -> None:
    assert metrics.exposure_time(pd.Series([], dtype=bool)) == 0.0


def test_exposure_time_never_open_is_zero() -> None:
    flags = pd.Series([False, False, False])
    assert metrics.exposure_time(flags) == 0.0


# --------------------------------------------------------------------------
# sharpe_ratio
# --------------------------------------------------------------------------


def test_sharpe_ratio_hand_derived() -> None:
    # returns: 0.01, 0.03, 0.01, 0.03 -> mean=0.02
    # deviations: -0.01, +0.01, -0.01, +0.01 -> sample variance (ddof=1)
    #   = (4 * 0.01**2) / 3 = 4e-4/3; std = sqrt(4e-4/3)
    returns = pd.Series([0.01, 0.03, 0.01, 0.03])
    mean = 0.02
    std = math.sqrt(4e-4 / 3)
    expected = mean / std * math.sqrt(252)
    assert metrics.sharpe_ratio(returns) == pytest.approx(expected, rel=1e-9)


def test_sharpe_ratio_drops_leading_nan() -> None:
    returns = pd.Series([np.nan, 0.01, 0.03, 0.01, 0.03])
    mean = 0.02
    std = math.sqrt(4e-4 / 3)
    expected = mean / std * math.sqrt(252)
    assert metrics.sharpe_ratio(returns) == pytest.approx(expected, rel=1e-9)


def test_sharpe_ratio_flat_curve_returns_is_zero() -> None:
    returns = pd.Series([0.0, 0.0, 0.0, 0.0])
    assert metrics.sharpe_ratio(returns) == 0.0


def test_sharpe_ratio_fewer_than_two_returns_is_zero() -> None:
    assert metrics.sharpe_ratio(pd.Series([0.02])) == 0.0
    assert metrics.sharpe_ratio(pd.Series([], dtype=float)) == 0.0


def test_sharpe_ratio_risk_free_rate_shifts_numerator() -> None:
    returns = pd.Series([0.01, 0.03, 0.01, 0.03])
    mean = 0.02
    std = math.sqrt(4e-4 / 3)
    rf = 0.05
    periods = 252
    expected = (mean - rf / periods) / std * math.sqrt(periods)
    assert metrics.sharpe_ratio(returns, risk_free_rate=rf) == pytest.approx(expected, rel=1e-9)


# --------------------------------------------------------------------------
# compute_all
# --------------------------------------------------------------------------


def test_compute_all_matches_individual_functions() -> None:
    curve = pd.Series([100.0, 120.0, 90.0, 110.0, 80.0, 130.0], index=_dates(6))
    trades = _TRADES
    flags = pd.Series([True, True, False, True, False, False])

    result = metrics.compute_all(curve, trades, flags)

    assert result["total_return"] == metrics.total_return(curve)
    assert result["cagr"] == metrics.cagr(curve)
    assert result["max_drawdown"] == metrics.max_drawdown(curve)
    assert result["win_rate"] == metrics.win_rate(trades)
    assert result["avg_win"] == metrics.avg_win(trades)
    assert result["avg_loss"] == metrics.avg_loss(trades)
    assert result["profit_factor"] == metrics.profit_factor(trades)
    assert result["num_trades"] == metrics.num_trades(trades)
    assert result["exposure_time"] == metrics.exposure_time(flags)
    assert result["sharpe"] == metrics.sharpe_ratio(curve.pct_change())
    assert result["best_trade"] == metrics.best_trade(trades)
    assert result["worst_trade"] == metrics.worst_trade(trades)


def test_compute_all_zero_trades_edge_case() -> None:
    curve = pd.Series([1_000_000.0] * 4, index=_dates(4))
    flags = pd.Series([False, False, False, False])

    result = metrics.compute_all(curve, [], flags)

    assert result["num_trades"] == 0
    assert result["win_rate"] == 0.0
    assert result["avg_win"] == 0.0
    assert result["avg_loss"] == 0.0
    assert result["profit_factor"] == 0.0
    assert result["best_trade"] == 0.0
    assert result["worst_trade"] == 0.0
    assert result["sharpe"] == 0.0
    assert result["exposure_time"] == 0.0
    assert result["total_return"] == 0.0
    assert result["max_drawdown"] == 0.0
