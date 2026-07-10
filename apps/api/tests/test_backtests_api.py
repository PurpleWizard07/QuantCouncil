"""POST /backtests/run endpoint tests -- NO network, NO real cache.

The OHLCV connector dependency (shared with the assets router via
``app.routers.assets.get_ohlcv_service``) is overridden with an in-memory
fake serving a deterministic synthetic frame, so these tests exercise only
the router: strategy validation, symbol/universe checks, error mapping, and
JSON-safe serialization of the backtester's output.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import assets
from data_connectors import DataFetchError, DataValidationError
from quant_engine.strategies import get_builtin_strategies

client = TestClient(app)

METRIC_KEYS = {
    "total_return",
    "cagr",
    "max_drawdown",
    "win_rate",
    "avg_win",
    "avg_loss",
    "profit_factor",
    "num_trades",
    "exposure_time",
    "sharpe",
    "best_trade",
    "worst_trade",
    "starting_capital",
    "final_equity",
}

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


def _sma_strategy() -> dict:
    for strategy in get_builtin_strategies():
        if strategy["name"] == "sma_crossover_20_50":
            return strategy
    raise AssertionError("SMA crossover built-in missing")


def _sine_trend_frame(n: int = 200) -> pd.DataFrame:
    """Deterministic frame with SMA(20)/SMA(50) crossovers (sine + drift)."""
    i = np.arange(n)
    closes = 100.0 + 10.0 * np.sin(2.0 * np.pi * i / 80.0) + 0.02 * i
    opens = np.concatenate([[closes[0]], closes[:-1]])
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": opens,
            "high": np.maximum(opens, closes) + 0.25,
            "low": np.minimum(opens, closes) - 0.25,
            "close": closes,
            "volume": np.full(n, 1_000.0),
        }
    )


class FakeOHLCVService:
    """Counting fake implementing the get_ohlcv interface."""

    def __init__(
        self, df: pd.DataFrame | None = None, error: Exception | None = None
    ) -> None:
        self.df = df if df is not None else _sine_trend_frame()
        self.error = error
        self.calls: list[tuple[str, object, object, str]] = []

    def get_ohlcv(self, symbol, start_date, end_date, timeframe="1d"):
        self.calls.append((symbol, start_date, end_date, timeframe))
        if self.error is not None:
            raise self.error
        return self.df.copy()


@pytest.fixture
def fake_service():
    """Install a FakeOHLCVService as the shared connector dependency."""
    fake = FakeOHLCVService()
    app.dependency_overrides[assets.get_ohlcv_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(assets.get_ohlcv_service, None)


def _override_service(fake: FakeOHLCVService) -> None:
    app.dependency_overrides[assets.get_ohlcv_service] = lambda: fake


def _run(strategy: dict, symbol: str = "RELIANCE", **extra):
    body = {
        "strategy": strategy,
        "symbol": symbol,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
    }
    body.update(extra)
    return client.post("/backtests/run", json=body)


# --- happy path -----------------------------------------------------------------


def test_run_happy_path_sma_crossover(fake_service):
    response = _run(_sma_strategy())
    assert response.status_code == 200
    body = response.json()

    assert body["strategy_name"] == "sma_crossover_20_50"
    assert body["symbol"] == "RELIANCE"
    assert body["timeframe"] == "1d"
    assert body["start_date"] == "2024-01-01"
    assert body["end_date"] == "2024-12-31"
    assert body["persisted"] is False
    assert "Phase 3.5" in body["note"]

    assert set(body["config"].keys()) == {
        "initial_capital",
        "slippage_pct",
        "transaction_cost_pct",
        "max_allocation_pct",
    }
    assert body["config"]["initial_capital"] == 1_000_000.0

    # All 14 scalar metrics present.
    assert set(body["metrics"].keys()) == METRIC_KEYS
    assert body["metrics"]["starting_capital"] == 1_000_000.0
    assert isinstance(body["metrics"]["final_equity"], float)
    assert body["metrics"]["num_trades"] >= 1

    # Equity curve: one point per input bar, ISO dates, numeric equity.
    assert len(body["equity_curve"]) == 200
    first_point = body["equity_curve"][0]
    assert set(first_point.keys()) == {"date", "equity"}
    assert first_point["date"] == "2024-01-01"
    assert first_point["equity"] == 1_000_000.0

    # Trades: JSON-safe records with ISO dates (already JSON round-tripped
    # via response.json(); re-dumping proves serializability explicitly).
    assert len(body["trades"]) == body["metrics"]["num_trades"]
    json.dumps(body["trades"])
    for trade in body["trades"]:
        assert set(trade.keys()) == TRADE_KEYS
        assert trade["symbol"] == "RELIANCE"
        assert len(trade["entry_date"]) == 10 and trade["entry_date"][4] == "-"
        assert len(trade["exit_date"]) == 10 and trade["exit_date"][4] == "-"

    # The connector received the canonical symbol and the parsed range.
    assert fake_service.calls[0][0] == "RELIANCE"
    assert fake_service.calls[0][3] == "1d"


def test_run_symbol_is_case_insensitive(fake_service):
    response = _run(_sma_strategy(), symbol="reliance")
    assert response.status_code == 200
    assert response.json()["symbol"] == "RELIANCE"


def test_run_date_defaults_applied_when_omitted(fake_service):
    response = client.post(
        "/backtests/run", json={"strategy": _sma_strategy(), "symbol": "RELIANCE"}
    )
    assert response.status_code == 200
    body = response.json()
    from datetime import date

    end = date.fromisoformat(body["end_date"])
    start = date.fromisoformat(body["start_date"])
    assert end == date.today()
    assert (end - start).days == 365


# --- validation errors ------------------------------------------------------------


def test_run_invalid_strategy_returns_400_with_message(fake_service):
    strategy = _sma_strategy()
    del strategy["stop_loss"]
    response = _run(strategy)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Invalid strategy definition" in detail
    assert "stop_loss" in detail
    assert fake_service.calls == []


def test_run_bad_timeframe_in_strategy_returns_400(fake_service):
    strategy = _sma_strategy()
    strategy["timeframe"] = "1h"
    response = _run(strategy)
    assert response.status_code == 400
    assert "daily only in v1" in response.json()["detail"]


def test_run_unknown_symbol_returns_404(fake_service):
    response = _run(_sma_strategy(), symbol="NOTASYMBOL")
    assert response.status_code == 404
    assert "NIFTY 50" in response.json()["detail"]
    assert fake_service.calls == []


def test_run_symbol_not_in_strategy_universe_returns_400(fake_service):
    # SBIN is a valid NIFTY 50 symbol but not in the built-in sample universe.
    response = _run(_sma_strategy(), symbol="SBIN")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "SBIN" in detail
    assert "sma_crossover_20_50" in detail
    assert "universe" in detail
    assert fake_service.calls == []


def test_run_bad_date_returns_400(fake_service):
    response = _run(_sma_strategy(), start_date="not-a-date")
    assert response.status_code == 400
    assert "ISO date" in response.json()["detail"]


def test_run_start_after_end_returns_400(fake_service):
    response = _run(_sma_strategy(), start_date="2024-12-31", end_date="2024-01-01")
    assert response.status_code == 400
    assert "on or before" in response.json()["detail"]


# --- upstream / data errors --------------------------------------------------------


def test_run_data_fetch_error_returns_502():
    fake = FakeOHLCVService(error=DataFetchError("provider exploded: secrets"))
    _override_service(fake)
    try:
        response = _run(_sma_strategy())
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert "Upstream data source" in detail
        assert "secrets" not in detail
    finally:
        app.dependency_overrides.pop(assets.get_ohlcv_service, None)


def test_run_data_validation_error_returns_502():
    fake = FakeOHLCVService(error=DataValidationError("bad rows internals"))
    _override_service(fake)
    try:
        response = _run(_sma_strategy())
        assert response.status_code == 502
        assert "validation" in response.json()["detail"]
        assert "internals" not in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(assets.get_ohlcv_service, None)


def test_run_empty_data_returns_400():
    fake = FakeOHLCVService(df=_sine_trend_frame().iloc[0:0])
    _override_service(fake)
    try:
        response = _run(_sma_strategy())
        assert response.status_code == 400
        assert "empty" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(assets.get_ohlcv_service, None)
