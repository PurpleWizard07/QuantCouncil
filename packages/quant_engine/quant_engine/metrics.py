"""Backtest performance metrics (project contract set).

Each function is a pure, deterministic calculation over an equity curve, a
daily returns series, or a closed-trade list. These are the ONLY sources of
the metric values stored on backtest runs -- LLM agents never compute or
adjust them.

Conventions:
    - ``equity_curve``: pd.Series of portfolio equity indexed by ascending,
      tz-naive dates.
    - ``trades``: list of dicts, one per closed round-trip trade, each with at
      least a ``pnl`` key (INR).
    - Fractions are returned as decimals (0.25 == 25%).

Status: implemented (Phase 3).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR: int = 252
"""Annualization factor for daily-bar metrics (NSE trading calendar approx.)."""


def total_return(equity_curve: pd.Series) -> float:
    """Total return over the simulation: ``last / first - 1``.

    Returns:
        0.0 if ``equity_curve`` has fewer than 1 element.
    """
    if len(equity_curve) < 1:
        return 0.0
    first = float(equity_curve.iloc[0])
    last = float(equity_curve.iloc[-1])
    if first == 0.0:
        return 0.0
    return last / first - 1.0


def cagr(equity_curve: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    """Compound annual growth rate of the equity curve.

    ``n_periods`` is ``len(equity_curve) - 1`` bars (the number of bar-to-bar
    steps spanned by the curve). ``cagr = (last / first) ** (periods_per_year
    / n_periods) - 1``.

    Returns:
        0.0 if ``n_periods < 1`` (fewer than 2 points) or ``first <= 0``
        (degenerate/undefined growth rate); documented simplification.
    """
    n_periods = len(equity_curve) - 1
    if n_periods < 1:
        return 0.0
    first = float(equity_curve.iloc[0])
    last = float(equity_curve.iloc[-1])
    if first <= 0.0:
        return 0.0
    return (last / first) ** (periods_per_year / n_periods) - 1.0


def max_drawdown(equity_curve: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a positive fraction (0.2 == 20%).

    Computed as ``max(1 - equity / running_max(equity))``. Returns 0.0 for an
    empty curve or a monotonically non-decreasing curve.
    """
    if len(equity_curve) == 0:
        return 0.0
    running_max = equity_curve.cummax()
    drawdown = 1.0 - equity_curve / running_max
    return float(drawdown.max())


def win_rate(trades: list[dict]) -> float:
    """Fraction of closed trades with positive PnL, in [0, 1].

    Returns:
        0.0 if ``trades`` is empty.
    """
    if len(trades) == 0:
        return 0.0
    wins = sum(1 for t in trades if t["pnl"] > 0)
    return wins / len(trades)


def avg_win(trades: list[dict]) -> float:
    """Average PnL (INR) across winning trades; 0.0 if there are none."""
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    if not wins:
        return 0.0
    return float(np.mean(wins))


def avg_loss(trades: list[dict]) -> float:
    """Average PnL (INR) across losing trades (negative); 0.0 if none."""
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    if not losses:
        return 0.0
    return float(np.mean(losses))


def profit_factor(trades: list[dict]) -> float:
    """Gross profit divided by absolute gross loss.

    Documented edge cases:
        - No losses and no wins (e.g. no trades, or all trades break-even at
          exactly 0 PnL) -> 0.0.
        - No losses but at least one winning trade (gross loss == 0,
          gross profit > 0) -> ``float("inf")`` (unbounded profit factor).
    """
    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = sum(t["pnl"] for t in trades if t["pnl"] < 0)
    if gross_loss == 0:
        if gross_profit > 0:
            return float("inf")
        return 0.0
    return gross_profit / abs(gross_loss)


def num_trades(trades: list[dict]) -> int:
    """Number of closed round-trip trades."""
    return len(trades)


def exposure_time(position_flags: pd.Series) -> float:
    """Fraction of bars with at least one open position, in [0, 1].

    Args:
        position_flags: Boolean Series (per bar) indicating whether any
            position was open on that bar.

    Returns:
        0.0 for an empty Series.
    """
    if len(position_flags) == 0:
        return 0.0
    return float(position_flags.mean())


def sharpe_ratio(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Sharpe-like ratio: annualized mean excess return over annualized volatility.

    ``sharpe = (mean(daily_returns) - risk_free_rate / periods_per_year) /
    std(daily_returns, ddof=1) * sqrt(periods_per_year)``.

    v1 assumes ``risk_free_rate=0.0`` (documented simplification), which is
    why the project contract calls this a "Sharpe-like ratio".

    Returns:
        0.0 if there are fewer than 2 return observations, or the sample
        standard deviation is zero or NaN (flat/degenerate returns).
    """
    returns = daily_returns.dropna()
    if len(returns) < 2:
        return 0.0
    std = float(returns.std(ddof=1))
    if std == 0.0 or np.isnan(std):
        return 0.0
    mean = float(returns.mean())
    excess = mean - risk_free_rate / periods_per_year
    return excess / std * np.sqrt(periods_per_year)


def best_trade(trades: list[dict]) -> float:
    """PnL (INR) of the single best closed trade; 0.0 if there are none."""
    if not trades:
        return 0.0
    return float(max(t["pnl"] for t in trades))


def worst_trade(trades: list[dict]) -> float:
    """PnL (INR) of the single worst closed trade; 0.0 if there are none."""
    if not trades:
        return 0.0
    return float(min(t["pnl"] for t in trades))


def compute_all(
    equity_curve: pd.Series,
    trades: list[dict],
    position_flags: pd.Series,
) -> dict:
    """Compute every contract metric in one call, keyed by name.

    The single entry point the backtester (and later phases) use so that no
    caller inlines metric math -- all numbers flow through this module.

    Args:
        equity_curve: Portfolio equity Series (see module docstring).
        trades: Closed round-trip trade dicts (see module docstring).
        position_flags: Boolean Series, one per bar, True when a position was
            open on that bar (for ``exposure_time``).

    Returns:
        A dict with keys ``total_return, cagr, max_drawdown, win_rate,
        avg_win, avg_loss, profit_factor, num_trades, exposure_time, sharpe,
        best_trade, worst_trade``.
    """
    daily_rets = equity_curve.pct_change()
    return {
        "total_return": total_return(equity_curve),
        "cagr": cagr(equity_curve),
        "max_drawdown": max_drawdown(equity_curve),
        "win_rate": win_rate(trades),
        "avg_win": avg_win(trades),
        "avg_loss": avg_loss(trades),
        "profit_factor": profit_factor(trades),
        "num_trades": num_trades(trades),
        "exposure_time": exposure_time(position_flags),
        "sharpe": sharpe_ratio(daily_rets),
        "best_trade": best_trade(trades),
        "worst_trade": worst_trade(trades),
    }
