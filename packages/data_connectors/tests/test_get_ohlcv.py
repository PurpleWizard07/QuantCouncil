"""Tests for OHLCVConnector.get_ohlcv: input validation and the fetch/validate pipeline.

Uses a minimal in-memory fake connector rather than a real one, so these
tests exercise only ``base.py``'s ``get_ohlcv`` logic (date coercion,
timeframe check, ordering check, delegation to ``fetch_daily`` and then
``validate_ohlcv``) without any network or provider-specific code.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from data_connectors.base import OHLCVConnector
from data_connectors.validation import DataValidationError


class _FakeConnector(OHLCVConnector):
    """Returns a fixed, valid OHLCV frame regardless of the requested range."""

    def __init__(self) -> None:
        self.fetch_daily_calls: list[tuple[str, date, date]] = []

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        self.fetch_daily_calls.append((symbol, start, end))
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        return pd.DataFrame(
            {
                "date": dates,
                "open": [100.0] * 5,
                "high": [102.0] * 5,
                "low": [98.0] * 5,
                "close": [101.0] * 5,
                "volume": [1000] * 5,
            }
        )


class _MalformedConnector(OHLCVConnector):
    """Returns data violating the OHLCV contract (high < low)."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=2, freq="D"),
                "open": [100.0, 100.0],
                "high": [90.0, 102.0],  # first row: high < low
                "low": [98.0, 98.0],
                "close": [99.0, 101.0],
                "volume": [1000, 1000],
            }
        )


def test_get_ohlcv_happy_path_with_date_objects() -> None:
    connector = _FakeConnector()
    out = connector.get_ohlcv("RELIANCE", date(2024, 1, 1), date(2024, 1, 5))
    assert list(out.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(out) == 5
    assert connector.fetch_daily_calls == [("RELIANCE", date(2024, 1, 1), date(2024, 1, 5))]


def test_get_ohlcv_happy_path_with_iso_strings() -> None:
    connector = _FakeConnector()
    out = connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-01-05")
    assert len(out) == 5
    assert connector.fetch_daily_calls == [("RELIANCE", date(2024, 1, 1), date(2024, 1, 5))]


def test_get_ohlcv_rejects_non_daily_timeframe() -> None:
    connector = _FakeConnector()
    with pytest.raises(ValueError, match="daily"):
        connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-01-05", timeframe="1h")


@pytest.mark.parametrize("bad_date", ["2024/01/01", "not-a-date", "2024-13-01", ""])
def test_get_ohlcv_rejects_unparseable_dates(bad_date: str) -> None:
    connector = _FakeConnector()
    with pytest.raises(ValueError):
        connector.get_ohlcv("RELIANCE", bad_date, "2024-01-05")


def test_get_ohlcv_rejects_wrong_typed_dates() -> None:
    connector = _FakeConnector()
    with pytest.raises(ValueError):
        connector.get_ohlcv("RELIANCE", 12345, "2024-01-05")  # type: ignore[arg-type]


def test_get_ohlcv_rejects_start_after_end() -> None:
    connector = _FakeConnector()
    with pytest.raises(ValueError, match="on or before"):
        connector.get_ohlcv("RELIANCE", "2024-01-10", "2024-01-01")


def test_get_ohlcv_allows_start_equal_end() -> None:
    connector = _FakeConnector()
    out = connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-01-01")
    assert not out.empty


def test_get_ohlcv_propagates_validation_errors_from_malformed_data() -> None:
    connector = _MalformedConnector()
    with pytest.raises(DataValidationError):
        connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-01-02")
