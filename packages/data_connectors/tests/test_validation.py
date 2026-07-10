"""Tests for the shared OHLCV validation module."""

from __future__ import annotations

import pandas as pd
import pytest

from data_connectors.validation import (
    DataValidationError,
    validate_ohlcv,
    validate_ohlcv_report,
)


def _good_df(n: int = 5) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    rows = []
    price = 100.0
    for d in dates:
        rows.append(
            {
                "date": d,
                "open": price,
                "high": price + 2,
                "low": price - 2,
                "close": price + 1,
                "volume": 1000,
            }
        )
        price += 1
    return pd.DataFrame(rows)


def test_validate_ohlcv_happy_path_returns_same_shape() -> None:
    df = _good_df()
    out = validate_ohlcv(df)
    assert list(out.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(out) == len(df)
    assert out["date"].is_monotonic_increasing


def test_missing_columns_raises() -> None:
    df = _good_df().drop(columns=["volume"])
    with pytest.raises(DataValidationError, match="missing required column"):
        validate_ohlcv(df)


def test_duplicate_dates_raises() -> None:
    df = _good_df()
    df.loc[1, "date"] = df.loc[0, "date"]
    with pytest.raises(DataValidationError, match="duplicate"):
        validate_ohlcv(df)


def test_high_less_than_low_raises() -> None:
    df = _good_df()
    df.loc[2, "high"] = df.loc[2, "low"] - 1
    with pytest.raises(DataValidationError, match="high < low"):
        validate_ohlcv(df)


def test_open_above_high_beyond_tolerance_raises() -> None:
    df = _good_df()
    df.loc[0, "open"] = df.loc[0, "high"] + 5
    with pytest.raises(DataValidationError, match="high/low bounds"):
        validate_ohlcv(df)


def test_close_below_low_beyond_tolerance_raises() -> None:
    df = _good_df()
    df.loc[0, "close"] = df.loc[0, "low"] - 5
    with pytest.raises(DataValidationError, match="high/low bounds"):
        validate_ohlcv(df)


def test_open_high_within_tiny_tolerance_is_accepted() -> None:
    df = _good_df()
    # A rounding-noise-sized overshoot (well within the 1e-6 relative
    # tolerance) must not raise.
    df.loc[0, "open"] = df.loc[0, "high"] + 1e-9
    out = validate_ohlcv(df)
    assert len(out) == len(df)


def test_negative_volume_raises() -> None:
    df = _good_df()
    df.loc[1, "volume"] = -100
    with pytest.raises(DataValidationError, match="negative volume"):
        validate_ohlcv(df)


def test_nan_rows_are_dropped_not_raised() -> None:
    df = _good_df()
    df.loc[1, "close"] = None
    out = validate_ohlcv(df)
    assert len(out) == len(df) - 1
    assert not out["close"].isna().any()


def test_unsorted_input_gets_sorted_not_raised() -> None:
    df = _good_df().iloc[::-1].reset_index(drop=True)
    assert not df["date"].is_monotonic_increasing
    out = validate_ohlcv(df)
    assert out["date"].is_monotonic_increasing
    assert len(out) == len(df)


def test_min_rows_failure_raises() -> None:
    df = _good_df(n=3)
    with pytest.raises(DataValidationError, match="Not enough rows"):
        validate_ohlcv(df, min_rows=10)


def test_min_rows_success_when_enough_rows() -> None:
    df = _good_df(n=10)
    out = validate_ohlcv(df, min_rows=5)
    assert len(out) == 10


def test_unparseable_date_raises() -> None:
    df = _good_df()
    # pandas>=3 raises immediately on assigning a string into a datetime64
    # column; go through object dtype first so the bad value actually lands
    # in the frame for validate_ohlcv to catch.
    df["date"] = df["date"].astype(object)
    df.loc[0, "date"] = "not-a-date"
    with pytest.raises(DataValidationError, match="date"):
        validate_ohlcv(df)


def test_report_variant_returns_clean_df_and_warning_list() -> None:
    df = _good_df()
    clean, warnings = validate_ohlcv_report(df)
    assert len(clean) == len(df)
    assert warnings == []


def test_report_variant_flags_large_close_to_close_move() -> None:
    df = _good_df(n=4)
    # Simulate an unadjusted split/bonus: close roughly doubles overnight,
    # with high/low widened so the row still satisfies the OHLC bounds.
    df.loc[2, ["open", "high", "low", "close"]] = [
        df.loc[1, "close"] * 2.0,
        df.loc[1, "close"] * 2.2,
        df.loc[1, "close"] * 1.8,
        df.loc[1, "close"] * 2.0,
    ]
    clean, warnings = validate_ohlcv_report(df)
    assert len(clean) == len(df)
    assert any("corporate action" in w for w in warnings)


def test_report_variant_includes_nan_drop_warning() -> None:
    df = _good_df()
    df.loc[0, "open"] = None
    clean, warnings = validate_ohlcv_report(df)
    assert len(clean) == len(df) - 1
    assert any("Dropped" in w for w in warnings)
