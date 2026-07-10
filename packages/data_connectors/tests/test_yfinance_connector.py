"""Tests for YFinanceConnector.fetch_daily with yfinance fully mocked.

No network access: every test monkeypatches
``data_connectors.yfinance_connector.yf.download`` with a fake that returns
(or raises) a controlled, in-memory DataFrame shaped like a real yfinance
response.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

import data_connectors.yfinance_connector as yfc
from data_connectors.exceptions import DataFetchError

_FIELDS = ["Adj Close", "Close", "High", "Low", "Open", "Volume"]


def _multiindex_frame(dates: list[str], ticker: str, data: dict[str, list[float]]) -> pd.DataFrame:
    """Build a frame shaped like yf.download's default MultiIndex output."""
    index = pd.DatetimeIndex(pd.to_datetime(dates), name="Date")
    columns = pd.MultiIndex.from_product([_FIELDS, [ticker]], names=["Price", "Ticker"])
    df = pd.DataFrame(index=index, columns=columns, dtype="float64")
    for field in _FIELDS:
        key = field if field != "Adj Close" else "Close"  # reuse close for adj close in fixtures
        df[(field, ticker)] = data[key.lower().replace(" ", "_")]
    return df


def _flat_frame(dates: list[str], data: dict[str, list[float]]) -> pd.DataFrame:
    """Build a frame with plain (non-MultiIndex) columns, as older/alternate
    yfinance call shapes can return for a single ticker."""
    index = pd.DatetimeIndex(pd.to_datetime(dates), name="Date")
    df = pd.DataFrame(index=index)
    df["Open"] = data["open"]
    df["High"] = data["high"]
    df["Low"] = data["low"]
    df["Close"] = data["close"]
    df["Adj Close"] = data["close"]
    df["Volume"] = data["volume"]
    return df


def test_fetch_daily_normal_multiindex_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    data = {
        "open": [100.0, 101.0, 102.0],
        "high": [105.0, 106.0, 107.0],
        "low": [99.0, 100.0, 101.0],
        "close": [104.0, 105.0, 106.0],
        "volume": [1000, 1100, 1200],
    }

    def fake_download(*args, **kwargs):
        return _multiindex_frame(dates, "RELIANCE.NS", data)

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    connector = yfc.YFinanceConnector()
    out = connector.fetch_daily("RELIANCE", date(2024, 1, 1), date(2024, 1, 3))

    assert list(out.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(out) == 3
    assert out["date"].is_monotonic_increasing
    assert out.loc[0, "open"] == 100.0
    assert out.loc[2, "close"] == 106.0
    # tz-naive
    assert out["date"].dt.tz is None


def test_fetch_daily_flat_column_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    dates = ["2024-01-01", "2024-01-02"]
    data = {
        "open": [10.0, 11.0],
        "high": [12.0, 13.0],
        "low": [9.0, 10.0],
        "close": [11.5, 12.5],
        "volume": [500, 600],
    }

    def fake_download(*args, **kwargs):
        return _flat_frame(dates, data)

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    connector = yfc.YFinanceConnector()
    out = connector.fetch_daily("INFY", date(2024, 1, 1), date(2024, 1, 2))

    assert list(out.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(out) == 2


def test_fetch_daily_end_date_is_made_inclusive(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs = {}

    def fake_download(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return _multiindex_frame(
            ["2024-01-01"],
            "TCS.NS",
            {"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1]},
        )

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    connector = yfc.YFinanceConnector()
    connector.fetch_daily("TCS", date(2024, 1, 1), date(2024, 1, 10))

    # yfinance's `end` is exclusive; the connector must pass end + 1 day so
    # 2024-01-10 is actually included in the fetched range.
    assert captured_kwargs["end"] == date(2024, 1, 11)
    assert captured_kwargs["start"] == date(2024, 1, 1)
    assert captured_kwargs["auto_adjust"] is False


def test_fetch_daily_empty_response_raises_data_fetch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download(*args, **kwargs):
        return pd.DataFrame()

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    connector = yfc.YFinanceConnector()
    with pytest.raises(DataFetchError, match="no data"):
        connector.fetch_daily("NOTAREALSYMBOL", date(2024, 1, 1), date(2024, 1, 3))


def test_fetch_daily_download_raising_exception_becomes_data_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_download(*args, **kwargs):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    connector = yfc.YFinanceConnector()
    with pytest.raises(DataFetchError, match="simulated network failure"):
        connector.fetch_daily("RELIANCE", date(2024, 1, 1), date(2024, 1, 3))


def test_fetch_daily_drops_duplicate_dates_and_nan_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    # Row 0 and row 1 share the same date (duplicate); row 2 has a NaN close.
    dates = ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"]
    data = {
        "open": [100.0, 999.0, 101.0, 102.0],
        "high": [105.0, 999.0, 106.0, 107.0],
        "low": [99.0, 999.0, 100.0, 101.0],
        "close": [104.0, 999.0, float("nan"), 106.0],
        "volume": [1000, 999, 1100, 1200],
    }

    def fake_download(*args, **kwargs):
        return _multiindex_frame(dates, "WIPRO.NS", data)

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    connector = yfc.YFinanceConnector()
    out = connector.fetch_daily("WIPRO", date(2024, 1, 1), date(2024, 1, 3))

    # Keeps the first of the duplicate-date rows (2024-01-01, open=100.0),
    # drops the NaN-close row (2024-01-02), keeps 2024-01-03.
    assert len(out) == 2
    assert list(out["date"].dt.strftime("%Y-%m-%d")) == ["2024-01-01", "2024-01-03"]
    assert out.loc[0, "open"] == 100.0
    assert not out[["open", "high", "low", "close", "volume"]].isna().any().any()


def test_fetch_daily_uses_yfinance_symbol_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_download(ticker, *args, **kwargs):
        captured["ticker"] = ticker
        return _multiindex_frame(
            ["2024-01-01"],
            "M&M.NS",
            {"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1]},
        )

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    connector = yfc.YFinanceConnector()
    connector.fetch_daily("M&M", date(2024, 1, 1), date(2024, 1, 1))

    assert captured["ticker"] == "M&M.NS"
