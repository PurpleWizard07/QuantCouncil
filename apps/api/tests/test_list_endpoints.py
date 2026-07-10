"""Tests for the dashboard list endpoints: GET /backtests and GET /risk/evaluations.

Mirrors ``test_risk_api.py``'s fixture style: a per-test in-memory SQLite
engine installed as the ``get_db`` dependency, a deterministic fake OHLCV
connector, and a tmp_path override for ``get_backtests_dir``. Covers, for
each endpoint: empty list, populated newest-first ordering, and limit
respected.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routers import assets, backtests
from quant_engine.strategies import get_builtin_strategies

client = TestClient(app)


# --- fixtures -----------------------------------------------------------------


@pytest.fixture
def engine():
    eng = sa.create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def api_db(session_factory):
    """Install the in-memory database as the app's get_db dependency."""

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


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


@pytest.fixture
def fake_service():
    class FakeOHLCVService:
        def get_ohlcv(self, symbol, start_date, end_date, timeframe="1d"):
            return _sine_trend_frame().copy()

    fake = FakeOHLCVService()
    app.dependency_overrides[assets.get_ohlcv_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(assets.get_ohlcv_service, None)


@pytest.fixture
def artifacts_dir(tmp_path):
    """Point persisted-run artifacts at a throwaway directory."""
    app.dependency_overrides[backtests.get_backtests_dir] = lambda: tmp_path
    yield tmp_path
    app.dependency_overrides.pop(backtests.get_backtests_dir, None)


def _custom_strategy(name: str) -> dict:
    """A schema-valid user strategy (renamed SMA crossover builtin)."""
    for strategy in get_builtin_strategies():
        if strategy["name"] == "sma_crossover_20_50":
            strategy = dict(strategy)
            strategy["name"] = name
            return strategy
    raise AssertionError("SMA crossover built-in missing")


def _run_body(name: str, **overrides) -> dict:
    body = {
        "strategy": _custom_strategy(name),
        "symbol": "RELIANCE",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "persist": True,
    }
    body.update(overrides)
    return body


def _persist_backtest(name: str) -> dict:
    """POST /backtests/run persist=true; returns the JSON response."""
    run = client.post("/backtests/run", json=_run_body(name))
    assert run.status_code == 200, run.text
    return run.json()


# --- GET /backtests -----------------------------------------------------------


def test_list_backtests_empty(api_db):
    response = client.get("/backtests")
    assert response.status_code == 200
    body = response.json()
    assert body == {"count": 0, "backtests": []}


def test_list_backtests_newest_first(api_db, fake_service, artifacts_dir):
    first = _persist_backtest("list_endpoints_first")
    second = _persist_backtest("list_endpoints_second")

    response = client.get("/backtests")
    assert response.status_code == 200
    body = response.json()

    assert body["count"] == 2
    ids = [item["backtest_id"] for item in body["backtests"]]
    assert ids == [second["backtest_id"], first["backtest_id"]]

    item = body["backtests"][0]
    assert item["strategy_name"] == "list_endpoints_second"
    assert item["symbol"] == "RELIANCE"
    assert item["timeframe"] == "1d"
    assert item["status"] == "COMPLETED"
    assert item["created_at"]
    assert set(item["metrics"].keys()) == {
        "total_return",
        "max_drawdown",
        "sharpe",
        "num_trades",
    }


def test_list_backtests_limit_respected(api_db, fake_service, artifacts_dir):
    for i in range(3):
        _persist_backtest(f"list_endpoints_limit_{i}")

    response = client.get("/backtests", params={"limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert len(body["backtests"]) == 2


# --- GET /risk/evaluations -----------------------------------------------------


def test_list_risk_evaluations_empty(api_db):
    response = client.get("/risk/evaluations")
    assert response.status_code == 200
    body = response.json()
    assert body == {"count": 0, "evaluations": []}


def test_list_risk_evaluations_newest_first(api_db, fake_service, artifacts_dir):
    first = _persist_backtest("list_endpoints_risk_first")
    second = _persist_backtest("list_endpoints_risk_second")

    eval_first = client.post(
        "/risk/evaluate", json={"backtest_id": first["backtest_id"]}
    ).json()
    eval_second = client.post(
        "/risk/evaluate", json={"backtest_id": second["backtest_id"]}
    ).json()

    response = client.get("/risk/evaluations")
    assert response.status_code == 200
    body = response.json()

    assert body["count"] == 2
    ids = [item["risk_evaluation_id"] for item in body["evaluations"]]
    assert ids == [
        eval_second["risk_evaluation_id"],
        eval_first["risk_evaluation_id"],
    ]

    item = body["evaluations"][0]
    assert item["backtest_run_id"] == second["backtest_id"]
    assert item["decision"] == eval_second["decision"]
    assert item["approved"] == eval_second["approved"]
    assert item["risk_score"] == eval_second["risk_score"]
    assert item["policy_version"] == eval_second["policy_version"]
    assert item["created_at"]


def test_list_risk_evaluations_limit_respected(api_db, fake_service, artifacts_dir):
    for i in range(3):
        run = _persist_backtest(f"list_endpoints_risk_limit_{i}")
        client.post("/risk/evaluate", json={"backtest_id": run["backtest_id"]})

    response = client.get("/risk/evaluations", params={"limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert len(body["evaluations"]) == 2
