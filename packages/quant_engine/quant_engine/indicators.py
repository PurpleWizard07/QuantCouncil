"""Technical indicators.

Pure, deterministic functions over pandas Series. All functions operate on a
price (or volume) Series indexed by ascending, tz-naive dates and return a
Series aligned to the input index. Leading values that lack a full lookback
window are NaN. No function mutates its input.

Conventions:
    - ``window`` / ``periods_per_year`` arguments are validated to be >= 1
      (``ValueError`` otherwise).
    - Empty input Series return an empty Series (same dtype/index), never an
      error.
    - EMA is masked to NaN for its first ``window - 1`` values so that all
      "moving average" style indicators share the same warm-up convention,
      even though the underlying recursive EMA is technically defined from
      the first observation onward (see ``ema`` docstring for detail).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_engine.metrics import TRADING_DAYS_PER_YEAR


def _validate_window(window: int) -> None:
    """Raise ValueError if ``window`` is not a positive integer lookback."""
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average.

    Args:
        series: Price series (typically daily close), ascending date index.
        window: Lookback window in trading days. Must be >= 1.

    Returns:
        Series of the rolling arithmetic mean over ``window`` periods, aligned
        to ``series.index``. The first ``window - 1`` values are NaN.

    Raises:
        ValueError: If ``window < 1``.
    """
    _validate_window(window)
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """Exponential moving average.

    Uses the standard smoothing factor ``alpha = 2 / (window + 1)`` via
    ``pandas.Series.ewm(span=window, adjust=False)``.

    Note on warm-up: a recursive EMA (``adjust=False``) is technically
    defined starting at the very first observation (seeded with that
    observation as the initial value), so pandas would return non-NaN values
    from index 0. For consistency with the other lookback-based indicators in
    this module (whose first ``window - 1`` values are NaN), this function
    explicitly masks the first ``window - 1`` values to NaN before returning.

    Args:
        series: Price series (typically daily close), ascending date index.
        window: Span in trading days. Must be >= 1.

    Returns:
        Series of the exponentially weighted mean, aligned to
        ``series.index``. The first ``window - 1`` values are NaN.

    Raises:
        ValueError: If ``window < 1``.
    """
    _validate_window(window)
    result = series.ewm(span=window, adjust=False).mean()
    if len(result) > 0:
        result.iloc[: window - 1] = np.nan
    return result


def _wilder_smooth(series: pd.Series, window: int) -> pd.Series:
    """Wilder's smoothing: ``ewm(alpha=1/window, adjust=False)`` over ``series``.

    Equivalent to the classic recursive formula
    ``avg[t] = (avg[t-1] * (window - 1) + value[t]) / window``, seeded with
    the first observation. Used as the shared smoothing primitive for RSI and
    ATR so both indicators warm up identically.
    """
    return series.ewm(alpha=1.0 / window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's RSI).

    Gains and losses of consecutive closes are smoothed independently via
    Wilder smoothing (equivalent to ``ewm(alpha=1/window, adjust=False)``),
    then combined as ``RS = avg_gain / avg_loss`` and
    ``RSI = 100 - 100 / (1 + RS)``. Windows with zero average loss (all gains)
    yield RSI = 100; windows with zero average gain (all losses) yield RSI =
    0; both are handled explicitly to avoid division by zero.

    Args:
        series: Price series (typically daily close), ascending date index.
        window: Lookback window in trading days. Defaults to the conventional 14.

    Returns:
        Series of RSI values in the range [0, 100], aligned to
        ``series.index``. Values before the first full window are NaN.

    Raises:
        ValueError: If ``window < 1``.
    """
    _validate_window(window)
    if len(series) == 0:
        return series.astype(float).copy()

    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = _wilder_smooth(gain, window)
    avg_loss = _wilder_smooth(loss, window)

    # Avoid divide-by-zero warnings: NaN out zero denominators before
    # dividing, then explicitly fill in the boundary cases below.
    avg_loss_safe = avg_loss.where(avg_loss != 0.0)
    rs = avg_gain / avg_loss_safe
    result = 100.0 - (100.0 / (1.0 + rs))
    result = result.where(avg_loss != 0.0, 100.0)  # zero loss -> RSI 100
    result = result.where(~((avg_loss == 0.0) & (avg_gain == 0.0)), 50.0)  # flat -> RSI 50

    # Warm-up: need `window` prior diffs, i.e. `window` observations after the
    # first (which produces no diff), so the first `window` values are NaN.
    result.iloc[:window] = np.nan
    return result


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Average True Range (Wilder's ATR).

    True Range for bar ``t`` is
    ``max(high[t] - low[t], |high[t] - close[t-1]|, |low[t] - close[t-1]|)``.
    True Range is smoothed with the same Wilder smoothing used by ``rsi``
    (``ewm(alpha=1/window, adjust=False)``).

    Args:
        high: High price series, ascending date index.
        low: Low price series, aligned to ``high``.
        close: Close price series, aligned to ``high`` (used for the prior
            close in the true range calculation).
        window: Lookback window in trading days. Defaults to the conventional 14.

    Returns:
        Series of ATR values, aligned to ``high.index``. Values before the
        first full window are NaN.

    Raises:
        ValueError: If ``window < 1``.
    """
    _validate_window(window)
    if len(high) == 0:
        return high.astype(float).copy()

    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result = _wilder_smooth(true_range, window)
    # First bar has no prior close, so True Range there is undefined for the
    # gap terms; the first full ATR needs `window` true-range observations
    # starting from bar 1 (bar 0 has no prior close), matching `rsi`'s warm-up.
    result.iloc[:window] = np.nan
    return result


def rolling_high(series: pd.Series, window: int) -> pd.Series:
    """Rolling maximum over a lookback window.

    Typically applied to the high price series for classic Donchian-style
    breakout levels.

    Args:
        series: Price series, ascending date index.
        window: Lookback window in trading days. Must be >= 1.

    Returns:
        Series of the rolling maximum over ``window`` periods, aligned to
        ``series.index``. The first ``window - 1`` values are NaN.

    Raises:
        ValueError: If ``window < 1``.
    """
    _validate_window(window)
    return series.rolling(window=window, min_periods=window).max()


def rolling_low(series: pd.Series, window: int) -> pd.Series:
    """Rolling minimum over a lookback window.

    Typically applied to the low price series for classic Donchian-style
    breakout levels.

    Args:
        series: Price series, ascending date index.
        window: Lookback window in trading days. Must be >= 1.

    Returns:
        Series of the rolling minimum over ``window`` periods, aligned to
        ``series.index``. The first ``window - 1`` values are NaN.

    Raises:
        ValueError: If ``window < 1``.
    """
    _validate_window(window)
    return series.rolling(window=window, min_periods=window).min()


def volume_sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average of volume.

    Used by the volume breakout strategy to compare current volume against
    its recent average.

    Args:
        series: Volume series, ascending date index.
        window: Lookback window in trading days. Must be >= 1.

    Returns:
        Series of the rolling mean volume over ``window`` periods, aligned to
        ``series.index``. The first ``window - 1`` values are NaN.

    Raises:
        ValueError: If ``window < 1``.
    """
    _validate_window(window)
    return sma(series, window)


def highest_close(series: pd.Series, window: int) -> pd.Series:
    """Rolling highest close over a lookback window.

    Used by breakout-style strategies (e.g. close breaking above the highest
    close of the prior N days). A thin wrapper around ``rolling_high``.

    Args:
        series: Close price series, ascending date index.
        window: Lookback window in trading days. Must be >= 1.

    Returns:
        Series of the rolling maximum close over ``window`` periods, aligned
        to ``series.index``. The first ``window - 1`` values are NaN.

    Raises:
        ValueError: If ``window < 1``.
    """
    _validate_window(window)
    return rolling_high(series, window)


def daily_returns(series: pd.Series) -> pd.Series:
    """Simple close-to-close percentage returns.

    Args:
        series: Price series (typically daily close), ascending date index.

    Returns:
        Series of ``series.pct_change()`` (i.e. ``(price[t] / price[t-1]) -
        1``), aligned to ``series.index``. The first value is NaN.
    """
    return series.pct_change()


def volatility(
    series: pd.Series,
    window: int = 20,
    annualize: bool = True,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> pd.Series:
    """Rolling volatility of daily returns.

    Takes a PRICE series (not a returns series): daily simple returns are
    computed internally via ``daily_returns``, then the rolling standard
    deviation of those returns is taken over ``window`` periods. When
    ``annualize`` is True, the rolling standard deviation is multiplied by
    ``sqrt(periods_per_year)``.

    Args:
        series: Price series (typically daily close), ascending date index.
        window: Lookback window (in return observations) for the rolling
            standard deviation. Must be >= 1. Defaults to 20.
        annualize: If True (default), scale by ``sqrt(periods_per_year)``.
        periods_per_year: Annualization factor. Must be >= 1. Defaults to
            ``quant_engine.metrics.TRADING_DAYS_PER_YEAR`` (252).

    Returns:
        Series of rolling return volatility, aligned to ``series.index``.
        Because the first return observation is NaN (from ``daily_returns``),
        the first full rolling window of volatility is only available once
        ``window + 1`` price observations exist; values before that are NaN.

    Raises:
        ValueError: If ``window < 1`` or ``periods_per_year < 1``.
    """
    _validate_window(window)
    _validate_window(periods_per_year)
    returns = daily_returns(series)
    result = returns.rolling(window=window, min_periods=window).std()
    if annualize:
        result = result * np.sqrt(periods_per_year)
    return result
