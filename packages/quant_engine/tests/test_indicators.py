"""Tests for quant_engine.indicators.

Expected values are hand-derived (or derived from the same closed-form
Wilder/EMA recursion documented in indicators.py) for small series, so each
assertion is checking the math, not just re-running the implementation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_engine import indicators as ind


def _dates(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="D")


# --------------------------------------------------------------------------
# sma
# --------------------------------------------------------------------------


def test_sma_values() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=_dates(5))
    result = ind.sma(series, window=3)
    expected = [np.nan, np.nan, 2.0, 3.0, 4.0]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_sma_nan_warmup_length() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = ind.sma(series, window=3)
    assert result.iloc[:2].isna().all()
    assert result.iloc[2:].notna().all()


def test_sma_index_alignment() -> None:
    idx = _dates(5)
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=idx)
    result = ind.sma(series, window=3)
    assert result.index.equals(idx)


def test_sma_window_one_is_identity() -> None:
    series = pd.Series([1.0, 2.0, 3.0])
    result = ind.sma(series, window=1)
    assert result.tolist() == pytest.approx(series.tolist())


def test_sma_window_less_than_one_raises() -> None:
    series = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        ind.sma(series, window=0)


def test_sma_empty_series() -> None:
    result = ind.sma(pd.Series([], dtype=float), window=3)
    assert len(result) == 0


# --------------------------------------------------------------------------
# ema
# --------------------------------------------------------------------------


def test_ema_values() -> None:
    # span=3 -> alpha=0.5; adjust=False recursion seeded at x0=1.0:
    # y0=1, y1=0.5*2+0.5*1=1.5, y2=0.5*3+0.5*1.5=2.25,
    # y3=0.5*4+0.5*2.25=3.125, y4=0.5*5+0.5*3.125=4.0625
    # then first (window-1)=2 values masked to NaN.
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = ind.ema(series, window=3)
    expected = [np.nan, np.nan, 2.25, 3.125, 4.0625]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_ema_nan_warmup_length() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = ind.ema(series, window=3)
    assert result.iloc[:2].isna().all()
    assert result.iloc[2:].notna().all()


def test_ema_index_alignment() -> None:
    idx = _dates(5)
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=idx)
    result = ind.ema(series, window=3)
    assert result.index.equals(idx)


def test_ema_window_one_is_identity() -> None:
    # alpha = 2/(1+1) = 1 -> each output equals the current input, and there
    # is no warm-up to mask (window - 1 == 0).
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = ind.ema(series, window=1)
    assert result.tolist() == pytest.approx(series.tolist())


def test_ema_window_less_than_one_raises() -> None:
    series = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        ind.ema(series, window=0)


def test_ema_empty_series() -> None:
    result = ind.ema(pd.Series([], dtype=float), window=3)
    assert len(result) == 0


# --------------------------------------------------------------------------
# rsi
# --------------------------------------------------------------------------


def test_rsi_values() -> None:
    # prices = [10, 12, 11, 13, 16], window=3
    # diffs:  NaN,  2, -1,  2,  3 -> gain: NaN,2,0,2,3 ; loss: NaN,0,1,0,0
    # Wilder smoothing (alpha=1/3) seeded at index1:
    #   avg_gain: 2, 4/3, 14/9, 55/27
    #   avg_loss: 0, 1/3, 2/9, 4/27
    # index3: rs=14/9 / 2/9=7      -> rsi=100-100/8=87.5
    # index4: rs=55/27 / 4/27=13.75 -> rsi=100-100/14.75=93.220338983...
    # First `window`=3 values are masked to NaN.
    series = pd.Series([10.0, 12.0, 11.0, 13.0, 16.0])
    result = ind.rsi(series, window=3)
    expected = [np.nan, np.nan, np.nan, 87.5, 93.22033898305085]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_rsi_nan_warmup_length() -> None:
    series = pd.Series([10.0, 12.0, 11.0, 13.0, 16.0])
    result = ind.rsi(series, window=3)
    assert result.iloc[:3].isna().all()
    assert result.iloc[3:].notna().all()


def test_rsi_index_alignment() -> None:
    idx = _dates(5)
    series = pd.Series([10.0, 12.0, 11.0, 13.0, 16.0], index=idx)
    result = ind.rsi(series, window=3)
    assert result.index.equals(idx)


def test_rsi_all_gains_is_100() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    result = ind.rsi(series, window=3)
    assert result.iloc[3:].tolist() == pytest.approx([100.0, 100.0, 100.0])


def test_rsi_all_losses_is_0() -> None:
    series = pd.Series([6.0, 5.0, 4.0, 3.0, 2.0, 1.0])
    result = ind.rsi(series, window=3)
    assert result.iloc[3:].tolist() == pytest.approx([0.0, 0.0, 0.0])


def test_rsi_flat_series_no_division_error() -> None:
    # Zero gain AND zero loss throughout: avg_gain == avg_loss == 0, RS is
    # undefined (0/0) -- the implementation treats this as neutral (50) and
    # must not raise or emit a division warning.
    series = pd.Series([5.0, 5.0, 5.0, 5.0, 5.0])
    result = ind.rsi(series, window=3)
    assert result.iloc[3:].tolist() == pytest.approx([50.0, 50.0])


def test_rsi_window_less_than_one_raises() -> None:
    series = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        ind.rsi(series, window=0)


def test_rsi_empty_series() -> None:
    result = ind.rsi(pd.Series([], dtype=float), window=14)
    assert len(result) == 0


# --------------------------------------------------------------------------
# atr
# --------------------------------------------------------------------------


def test_atr_values() -> None:
    # bar0: H=10 L=8  C=9    -> TR0 = H-L = 2 (no prior close)
    # bar1: H=11 L=9  C=10.5 -> TR1 = max(2, |11-9|=2, |9-9|=0) = 2
    # bar2: H=13 L=11 C=12   -> TR2 = max(2, |13-10.5|=2.5, |11-10.5|=0.5) = 2.5
    # bar3: H=12 L=9  C=10   -> TR3 = max(3, |12-12|=0, |9-12|=3) = 3
    # Wilder smoothing (window=2, alpha=0.5) seeded at TR0=2:
    #   avg0=2, avg1=2+0.5*(2-2)=2, avg2=2+0.5*(2.5-2)=2.25,
    #   avg3=2.25+0.5*(3-2.25)=2.625
    # First `window`=2 values masked to NaN.
    high = pd.Series([10.0, 11.0, 13.0, 12.0])
    low = pd.Series([8.0, 9.0, 11.0, 9.0])
    close = pd.Series([9.0, 10.5, 12.0, 10.0])
    result = ind.atr(high, low, close, window=2)
    expected = [np.nan, np.nan, 2.25, 2.625]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_atr_nan_warmup_length() -> None:
    high = pd.Series([10.0, 11.0, 13.0, 12.0])
    low = pd.Series([8.0, 9.0, 11.0, 9.0])
    close = pd.Series([9.0, 10.5, 12.0, 10.0])
    result = ind.atr(high, low, close, window=2)
    assert result.iloc[:2].isna().all()
    assert result.iloc[2:].notna().all()


def test_atr_index_alignment() -> None:
    idx = _dates(4)
    high = pd.Series([10.0, 11.0, 13.0, 12.0], index=idx)
    low = pd.Series([8.0, 9.0, 11.0, 9.0], index=idx)
    close = pd.Series([9.0, 10.5, 12.0, 10.0], index=idx)
    result = ind.atr(high, low, close, window=2)
    assert result.index.equals(idx)


def test_atr_window_less_than_one_raises() -> None:
    high = pd.Series([10.0, 11.0])
    low = pd.Series([8.0, 9.0])
    close = pd.Series([9.0, 10.0])
    with pytest.raises(ValueError):
        ind.atr(high, low, close, window=0)


def test_atr_empty_series() -> None:
    empty = pd.Series([], dtype=float)
    result = ind.atr(empty, empty, empty, window=14)
    assert len(result) == 0


# --------------------------------------------------------------------------
# rolling_high / rolling_low
# --------------------------------------------------------------------------


def test_rolling_high_values() -> None:
    series = pd.Series([3.0, 7.0, 2.0, 9.0, 4.0])
    result = ind.rolling_high(series, window=3)
    expected = [np.nan, np.nan, 7.0, 9.0, 9.0]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_rolling_low_values() -> None:
    series = pd.Series([3.0, 7.0, 2.0, 9.0, 4.0])
    result = ind.rolling_low(series, window=3)
    expected = [np.nan, np.nan, 2.0, 2.0, 2.0]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_rolling_high_window_one_is_identity() -> None:
    series = pd.Series([3.0, 7.0, 2.0])
    assert ind.rolling_high(series, window=1).tolist() == pytest.approx(series.tolist())


def test_rolling_low_window_one_is_identity() -> None:
    series = pd.Series([3.0, 7.0, 2.0])
    assert ind.rolling_low(series, window=1).tolist() == pytest.approx(series.tolist())


def test_rolling_high_window_less_than_one_raises() -> None:
    with pytest.raises(ValueError):
        ind.rolling_high(pd.Series([1.0, 2.0]), window=0)


def test_rolling_low_window_less_than_one_raises() -> None:
    with pytest.raises(ValueError):
        ind.rolling_low(pd.Series([1.0, 2.0]), window=0)


def test_rolling_high_empty_series() -> None:
    assert len(ind.rolling_high(pd.Series([], dtype=float), window=3)) == 0


def test_rolling_low_empty_series() -> None:
    assert len(ind.rolling_low(pd.Series([], dtype=float), window=3)) == 0


# --------------------------------------------------------------------------
# volume_sma
# --------------------------------------------------------------------------


def test_volume_sma_values() -> None:
    series = pd.Series([100.0, 200.0, 300.0, 400.0])
    result = ind.volume_sma(series, window=2)
    expected = [np.nan, 150.0, 250.0, 350.0]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_volume_sma_window_less_than_one_raises() -> None:
    with pytest.raises(ValueError):
        ind.volume_sma(pd.Series([1.0, 2.0]), window=0)


def test_volume_sma_empty_series() -> None:
    assert len(ind.volume_sma(pd.Series([], dtype=float), window=3)) == 0


# --------------------------------------------------------------------------
# highest_close
# --------------------------------------------------------------------------


def test_highest_close_values() -> None:
    series = pd.Series([10.0, 15.0, 12.0, 20.0, 18.0])
    result = ind.highest_close(series, window=2)
    expected = [np.nan, 15.0, 15.0, 20.0, 20.0]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_highest_close_matches_rolling_high() -> None:
    series = pd.Series([10.0, 15.0, 12.0, 20.0, 18.0])
    assert ind.highest_close(series, window=3).tolist() == pytest.approx(
        ind.rolling_high(series, window=3).tolist(), nan_ok=True
    )


def test_highest_close_window_less_than_one_raises() -> None:
    with pytest.raises(ValueError):
        ind.highest_close(pd.Series([1.0, 2.0]), window=0)


def test_highest_close_empty_series() -> None:
    assert len(ind.highest_close(pd.Series([], dtype=float), window=3)) == 0


# --------------------------------------------------------------------------
# daily_returns
# --------------------------------------------------------------------------


def test_daily_returns_values() -> None:
    series = pd.Series([100.0, 110.0, 99.0, 108.9])
    result = ind.daily_returns(series)
    expected = [np.nan, 0.10, -0.10, 0.10]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_daily_returns_first_value_nan() -> None:
    series = pd.Series([100.0, 110.0])
    result = ind.daily_returns(series)
    assert pd.isna(result.iloc[0])
    assert not pd.isna(result.iloc[1])


def test_daily_returns_index_alignment() -> None:
    idx = _dates(4)
    series = pd.Series([100.0, 110.0, 99.0, 108.9], index=idx)
    result = ind.daily_returns(series)
    assert result.index.equals(idx)


def test_daily_returns_empty_series() -> None:
    assert len(ind.daily_returns(pd.Series([], dtype=float))) == 0


# --------------------------------------------------------------------------
# volatility
# --------------------------------------------------------------------------


def test_volatility_values_not_annualized() -> None:
    # prices = [100, 102, 101, 105, 103], window=3
    # returns = [NaN, 0.02, -0.0098039216, 0.0396039604, -0.0190476190]
    # rolling std (ddof=1) of returns[1:4] -> index3, and returns[2:5] -> index4.
    series = pd.Series([100.0, 102.0, 101.0, 105.0, 103.0])
    result = ind.volatility(series, window=3, annualize=False)
    expected = [np.nan, np.nan, np.nan, 0.024878798886846264, 0.03153461726038387]
    assert result.tolist() == pytest.approx(expected, nan_ok=True)


def test_volatility_zero_for_constant_growth() -> None:
    # Constant per-day growth rate -> identical daily returns -> zero
    # rolling standard deviation.
    series = pd.Series([100.0, 110.0, 121.0, 133.1, 146.41])
    result = ind.volatility(series, window=3, annualize=False)
    assert result.iloc[3:].tolist() == pytest.approx([0.0, 0.0], abs=1e-9)


def test_volatility_annualization_factor() -> None:
    series = pd.Series([100.0, 102.0, 101.0, 105.0, 103.0, 107.0, 104.0, 110.0])
    raw = ind.volatility(series, window=3, annualize=False)
    annualized = ind.volatility(series, window=3, annualize=True)
    ratio = (annualized / raw).dropna()
    assert len(ratio) > 0
    assert ratio.tolist() == pytest.approx([np.sqrt(252)] * len(ratio))


def test_volatility_custom_periods_per_year() -> None:
    series = pd.Series([100.0, 102.0, 101.0, 105.0, 103.0, 107.0, 104.0, 110.0])
    raw = ind.volatility(series, window=3, annualize=False)
    annualized = ind.volatility(series, window=3, annualize=True, periods_per_year=52)
    ratio = (annualized / raw).dropna()
    assert ratio.tolist() == pytest.approx([np.sqrt(52)] * len(ratio))


def test_volatility_nan_warmup_length() -> None:
    series = pd.Series([100.0, 102.0, 101.0, 105.0, 103.0])
    result = ind.volatility(series, window=3)
    # Need window+1 price observations for the first valid value: indices
    # 0..window-1 are NaN, index `window` is the first valid entry.
    assert result.iloc[:3].isna().all()
    assert not pd.isna(result.iloc[3])


def test_volatility_index_alignment() -> None:
    idx = _dates(5)
    series = pd.Series([100.0, 102.0, 101.0, 105.0, 103.0], index=idx)
    result = ind.volatility(series, window=3)
    assert result.index.equals(idx)


def test_volatility_window_less_than_one_raises() -> None:
    with pytest.raises(ValueError):
        ind.volatility(pd.Series([1.0, 2.0, 3.0]), window=0)


def test_volatility_periods_per_year_less_than_one_raises() -> None:
    with pytest.raises(ValueError):
        ind.volatility(pd.Series([1.0, 2.0, 3.0]), window=1, periods_per_year=0)


def test_volatility_empty_series() -> None:
    assert len(ind.volatility(pd.Series([], dtype=float), window=3)) == 0
