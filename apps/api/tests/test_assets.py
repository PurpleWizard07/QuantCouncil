"""Asset endpoint tests -- NO network, NO real cache.

The OHLCV connector dependency (``app.routers.assets.get_ohlcv_service``) is
overridden with an in-memory fake returning a small deterministic DataFrame,
so these tests exercise only the router: symbol resolution, param validation,
error mapping, serialization, and the quant_engine indicator wiring.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import assets
from data_connectors import DataFetchError, DataValidationError, RawFundamentals

client = TestClient(app)

OHLCV_KEYS = {"date", "open", "high", "low", "close", "volume"}
INDICATOR_KEYS = {
    "date",
    "close",
    "sma_20",
    "sma_50",
    "ema_20",
    "rsi_14",
    "atr_14",
    "volume_sma_20",
    "rolling_high_20",
    "rolling_low_20",
    "daily_returns",
    "volatility_20",
}


def _ohlcv_frame(n: int = 60) -> pd.DataFrame:
    """Deterministic n-day OHLCV frame satisfying the connector contract."""
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    closes = [100.0 + i * 0.5 for i in range(n)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": [c - 0.5 for c in closes],
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [1_000 + i for i in range(n)],
        }
    )


class FakeOHLCVService:
    """Counting fake implementing the get_ohlcv interface."""

    def __init__(
        self, df: pd.DataFrame | None = None, error: Exception | None = None
    ) -> None:
        self.df = df if df is not None else _ohlcv_frame()
        self.error = error
        self.calls: list[tuple[str, object, object, str]] = []

    def get_ohlcv(self, symbol, start_date, end_date, timeframe="1d"):
        self.calls.append((symbol, start_date, end_date, timeframe))
        if self.error is not None:
            raise self.error
        return self.df.copy()


@pytest.fixture
def fake_service():
    """Install a FakeOHLCVService as the connector dependency; yield it."""
    fake = FakeOHLCVService()
    app.dependency_overrides[assets.get_ohlcv_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(assets.get_ohlcv_service, None)


def _override_service(fake: FakeOHLCVService) -> None:
    app.dependency_overrides[assets.get_ohlcv_service] = lambda: fake


# --- GET /assets --------------------------------------------------------------


def test_list_assets_returns_50_with_expected_keys():
    response = client.get("/assets")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 50
    assert len(body["assets"]) == 50
    expected_keys = {"symbol", "name", "exchange", "sector", "yfinance_symbol"}
    for record in body["assets"]:
        assert expected_keys <= record.keys()
    symbols = [r["symbol"] for r in body["assets"]]
    assert "RELIANCE" in symbols
    assert "M&M" in symbols


# --- shared param validation ---------------------------------------------------


def test_unknown_symbol_returns_404(fake_service):
    response = client.get("/assets/NOTASYMBOL/ohlcv")
    assert response.status_code == 404
    assert "NIFTY 50" in response.json()["detail"]
    assert fake_service.calls == []


def test_bad_timeframe_returns_400(fake_service):
    response = client.get("/assets/RELIANCE/ohlcv", params={"timeframe": "1h"})
    assert response.status_code == 400
    assert "daily timeframe only in v1" in response.json()["detail"]
    assert fake_service.calls == []


def test_start_after_end_returns_400(fake_service):
    response = client.get(
        "/assets/RELIANCE/ohlcv",
        params={"start_date": "2024-06-01", "end_date": "2024-01-01"},
    )
    assert response.status_code == 400
    assert "on or before" in response.json()["detail"]
    assert fake_service.calls == []


@pytest.mark.parametrize("bad", ["2024/01/01", "not-a-date", "2024-13-01"])
def test_unparseable_date_returns_400(fake_service, bad):
    response = client.get("/assets/RELIANCE/ohlcv", params={"start_date": bad})
    assert response.status_code == 400
    assert "ISO date" in response.json()["detail"]


def test_indicators_endpoint_shares_validation(fake_service):
    assert client.get("/assets/NOTASYMBOL/indicators").status_code == 404
    assert (
        client.get(
            "/assets/RELIANCE/indicators", params={"timeframe": "1wk"}
        ).status_code
        == 400
    )


# --- GET /assets/{symbol}/ohlcv -----------------------------------------------


def test_ohlcv_happy_path_returns_normalized_records(fake_service):
    response = client.get(
        "/assets/RELIANCE/ohlcv",
        params={"start_date": "2024-01-01", "end_date": "2024-03-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "RELIANCE"
    assert body["timeframe"] == "1d"
    assert body["start_date"] == "2024-01-01"
    assert body["end_date"] == "2024-03-31"
    assert body["rows"] == 60
    assert len(body["data"]) == 60
    first = body["data"][0]
    assert set(first.keys()) == OHLCV_KEYS
    assert first["date"] == "2024-01-01"
    assert isinstance(first["open"], float)
    assert isinstance(first["volume"], int)
    # The connector was invoked with the canonical symbol and parsed dates.
    assert fake_service.calls == [
        ("RELIANCE", date(2024, 1, 1), date(2024, 3, 31), "1d")
    ]


def test_ohlcv_defaults_are_applied_when_dates_omitted(fake_service):
    response = client.get("/assets/RELIANCE/ohlcv")
    assert response.status_code == 200
    body = response.json()
    start = date.fromisoformat(body["start_date"])
    end = date.fromisoformat(body["end_date"])
    assert end == date.today()
    assert (end - start).days == 365


def test_ohlcv_symbol_lookup_is_case_insensitive(fake_service):
    response = client.get(
        "/assets/reliance/ohlcv",
        params={"start_date": "2024-01-01", "end_date": "2024-03-31"},
    )
    assert response.status_code == 200
    assert response.json()["symbol"] == "RELIANCE"
    assert fake_service.calls[0][0] == "RELIANCE"


def test_ohlcv_data_fetch_error_returns_502():
    fake = FakeOHLCVService(error=DataFetchError("provider exploded: secret details"))
    _override_service(fake)
    try:
        response = client.get("/assets/RELIANCE/ohlcv")
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "Upstream data source" in detail
        # Internals must not leak to the client.
        assert "secret details" not in detail
    finally:
        app.dependency_overrides.pop(assets.get_ohlcv_service, None)


def test_ohlcv_data_validation_error_returns_502():
    fake = FakeOHLCVService(error=DataValidationError("high < low internals"))
    _override_service(fake)
    try:
        response = client.get("/assets/RELIANCE/ohlcv")
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "validation" in detail
        assert "internals" not in detail
    finally:
        app.dependency_overrides.pop(assets.get_ohlcv_service, None)


# --- GET /assets/{symbol}/indicators --------------------------------------------


def test_indicators_happy_path_keys_and_warmup_nulls(fake_service):
    response = client.get(
        "/assets/TCS/indicators",
        params={"start_date": "2024-01-01", "end_date": "2024-03-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "TCS"
    assert body["rows"] == 60
    records = body["indicators"]
    assert len(records) == 60
    assert set(records[0].keys()) == INDICATOR_KEYS

    first = records[0]
    # Warm-up region: nulls (never NaN, which is invalid JSON anyway).
    assert first["sma_20"] is None
    assert first["sma_50"] is None
    assert first["rsi_14"] is None
    assert first["daily_returns"] is None
    assert first["close"] is not None

    # Row 10: sma_20 (20-bar) still warming up; daily_returns available.
    assert records[10]["sma_20"] is None
    assert isinstance(records[10]["daily_returns"], float)

    # Row 55: all indicators past their warm-up on a 60-row frame.
    warmed = records[55]
    for key in INDICATOR_KEYS - {"date"}:
        assert isinstance(warmed[key], (int, float)) and warmed[key] is not None, key

    # Spot-check one deterministic value against a hand-computed SMA: closes
    # are 100.0, 100.5, ... so sma_20 at row 19 is the mean of rows 0..19.
    expected_sma20 = sum(100.0 + i * 0.5 for i in range(20)) / 20
    assert records[19]["sma_20"] == pytest.approx(expected_sma20)


def test_indicators_data_fetch_error_returns_502():
    fake = FakeOHLCVService(error=DataFetchError("boom"))
    _override_service(fake)
    try:
        response = client.get("/assets/INFY/indicators")
        assert response.status_code == 502
        assert "Upstream data source" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(assets.get_ohlcv_service, None)


# --- GET /assets/{symbol}/fundamentals -----------------------------------------


def _fundamentals_bundle(symbol: str = "RELIANCE") -> RawFundamentals:
    """Deterministic fundamentals bundle satisfying the connector's shape."""
    periods = pd.to_datetime(["2025-03-31", "2024-03-31"])
    info = {
        "longName": "Test Co Ltd",
        "sector": "Energy",
        "industry": "Oil & Gas",
        "currency": "INR",
        "marketCap": 1_000_000.0,
        "trailingPE": 20.0,
        "dividendYield": 2.5,
        "profitMargins": 0.15,
        "debtToEquity": 9.5,
    }
    income_stmt = pd.DataFrame(
        {periods[0]: [900.0, 70.0], periods[1]: [800.0, 60.0]},
        index=["Total Revenue", "Net Income"],
    )
    balance_sheet = pd.DataFrame(
        {periods[0]: [200.0, 100.0, 500.0], periods[1]: [180.0, 90.0, 450.0]},
        index=["Current Assets", "Current Liabilities", "Stockholders Equity"],
    )
    cashflow = pd.DataFrame({periods[0]: [120.0], periods[1]: [110.0]}, index=["Operating Cash Flow"])
    return RawFundamentals(
        symbol=symbol, info=info, income_stmt=income_stmt, balance_sheet=balance_sheet, cashflow=cashflow
    )


class FakeFundamentalsService:
    """Counting fake implementing the fetch_fundamentals interface."""

    def __init__(self, bundle: RawFundamentals | None = None, error: Exception | None = None) -> None:
        self.bundle = bundle if bundle is not None else _fundamentals_bundle()
        self.error = error
        self.calls: list[str] = []

    def fetch_fundamentals(self, symbol):
        self.calls.append(symbol)
        if self.error is not None:
            raise self.error
        return self.bundle


@pytest.fixture
def fake_fundamentals_service():
    fake = FakeFundamentalsService()
    app.dependency_overrides[assets.get_fundamentals_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(assets.get_fundamentals_service, None)


def test_fundamentals_unknown_symbol_returns_404(fake_fundamentals_service):
    response = client.get("/assets/NOTASYMBOL/fundamentals")
    assert response.status_code == 404
    assert fake_fundamentals_service.calls == []


def test_fundamentals_happy_path_returns_expected_shape(fake_fundamentals_service):
    response = client.get("/assets/RELIANCE/fundamentals")
    assert response.status_code == 200
    body = response.json()

    assert body["symbol"] == "RELIANCE"
    assert set(body.keys()) == {
        "symbol",
        "profile",
        "valuation",
        "per_share",
        "dividends",
        "profitability",
        "growth",
        "financial_health",
        "annual_history",
        "as_of",
    }
    assert body["profile"]["name"] == "Test Co Ltd"
    assert body["valuation"]["trailing_pe"] == 20.0
    assert body["dividends"]["dividend_yield_pct"] == 2.5
    assert body["financial_health"]["current_ratio"] == pytest.approx(2.0)
    assert len(body["annual_history"]) == 2
    assert body["annual_history"][0]["fiscal_year_end"] == "2025-03-31"
    assert fake_fundamentals_service.calls == ["RELIANCE"]


def test_fundamentals_symbol_lookup_is_case_insensitive(fake_fundamentals_service):
    response = client.get("/assets/reliance/fundamentals")
    assert response.status_code == 200
    assert response.json()["symbol"] == "RELIANCE"
    assert fake_fundamentals_service.calls == ["RELIANCE"]


def test_fundamentals_data_fetch_error_returns_502():
    fake = FakeFundamentalsService(error=DataFetchError("provider exploded: secret details"))
    app.dependency_overrides[assets.get_fundamentals_service] = lambda: fake
    try:
        response = client.get("/assets/RELIANCE/fundamentals")
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "Upstream data source" in detail
        assert "secret details" not in detail
    finally:
        app.dependency_overrides.pop(assets.get_fundamentals_service, None)
