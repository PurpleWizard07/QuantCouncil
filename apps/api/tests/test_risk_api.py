"""Phase 4 risk API tests -- in-memory SQLite, no network, no Postgres.

Mirrors ``test_persistence_smoke.py``'s fixture style: a per-test in-memory
SQLite engine installed as the ``get_db`` dependency, a deterministic fake
OHLCV connector, and a tmp_path override for ``get_backtests_dir``. Covers:
    - POST /risk/evaluate against a persisted backtest_id: full result
      contract, persisted risk_evaluation_id, and the GET round-trip.
    - POST /risk/evaluate against an inline payload: never persisted.
    - Error mapping: 404 unknown backtest_id / unknown risk_evaluation_id,
      400 malformed UUID, 400 both/neither of backtest_id and inline payload.
    - GET /backtests/{id}/risk: latest-evaluation lookup and its two distinct
      404s (unknown backtest vs. no evaluation yet).
    - Database-unreachable -> 503 for one representative endpoint.
"""

from __future__ import annotations

import uuid

import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routers import assets, backtests
from quant_engine.strategies import get_builtin_strategies
from risk_engine.policy import load_policy

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


def _custom_strategy(name: str = "risk_api_sma_crossover") -> dict:
    """A schema-valid user strategy (renamed SMA crossover builtin)."""
    for strategy in get_builtin_strategies():
        if strategy["name"] == "sma_crossover_20_50":
            strategy["name"] = name
            return strategy
    raise AssertionError("SMA crossover built-in missing")


def _run_body(**overrides) -> dict:
    body = {
        "symbol": "RELIANCE",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
    }
    body.update(overrides)
    return body


def _persist_backtest(**strategy_overrides) -> dict:
    """POST /backtests/run persist=true; returns the JSON response."""
    run = client.post(
        "/backtests/run",
        json=_run_body(strategy=_custom_strategy(**strategy_overrides), persist=True),
    )
    assert run.status_code == 200, run.text
    return run.json()


_RESULT_KEYS = {
    "decision",
    "approved",
    "risk_score",
    "policy_version",
    "reasons",
    "failed_rules",
    "warnings",
    "metrics_snapshot",
    "policy_snapshot",
    "risk_evaluation_id",
    "backtest_id",
    "persisted",
}


# --- POST /risk/evaluate: backtest_id path ------------------------------------


def test_evaluate_persisted_backtest_returns_full_result_and_persists(
    api_db, fake_service, artifacts_dir
):
    posted = _persist_backtest()
    backtest_id = posted["backtest_id"]

    response = client.post("/risk/evaluate", json={"backtest_id": backtest_id})
    assert response.status_code == 200, response.text
    body = response.json()

    assert _RESULT_KEYS <= set(body.keys())
    assert body["decision"] in {"APPROVED", "REJECTED", "NEEDS_REVIEW"}
    assert body["approved"] == (body["decision"] == "APPROVED")
    assert 0 <= body["risk_score"] <= 100
    assert body["persisted"] is True
    assert body["backtest_id"] == backtest_id
    uuid.UUID(body["risk_evaluation_id"])  # valid UUID string
    assert body["metrics_snapshot"] == posted["metrics"]
    assert body["policy_snapshot"] == load_policy().model_dump()
    assert body["policy_version"] == load_policy().policy_version


def test_get_risk_evaluation_round_trips(api_db, fake_service, artifacts_dir):
    posted = _persist_backtest()
    evaluated = client.post(
        "/risk/evaluate", json={"backtest_id": posted["backtest_id"]}
    ).json()

    fetched = client.get(f"/risk/evaluations/{evaluated['risk_evaluation_id']}")
    assert fetched.status_code == 200
    body = fetched.json()

    assert body["risk_evaluation_id"] == evaluated["risk_evaluation_id"]
    assert body["backtest_id"] == posted["backtest_id"]
    assert body["decision"] == evaluated["decision"]
    assert body["approved"] == evaluated["approved"]
    assert body["risk_score"] == evaluated["risk_score"]
    assert body["policy_version"] == evaluated["policy_version"]
    assert body["reasons"] == evaluated["reasons"]
    assert body["failed_rules"] == evaluated["failed_rules"]
    assert body["warnings"] == evaluated["warnings"]
    assert body["metrics_snapshot"] == evaluated["metrics_snapshot"]
    assert body["policy_snapshot"] == evaluated["policy_snapshot"]
    assert body["created_at"]
    assert body["persisted"] is True


def test_evaluate_unknown_backtest_id_returns_404(api_db, fake_service, artifacts_dir):
    response = client.post("/risk/evaluate", json={"backtest_id": str(uuid.uuid4())})
    assert response.status_code == 404


def test_evaluate_malformed_backtest_id_returns_400(api_db):
    response = client.post("/risk/evaluate", json={"backtest_id": "not-a-uuid"})
    assert response.status_code == 400


def test_evaluate_both_backtest_id_and_inline_returns_400(api_db, fake_service, artifacts_dir):
    posted = _persist_backtest()
    response = client.post(
        "/risk/evaluate",
        json={
            "backtest_id": posted["backtest_id"],
            "metrics": posted["metrics"],
            "strategy": _custom_strategy(),
        },
    )
    assert response.status_code == 400


def test_evaluate_neither_backtest_id_nor_inline_returns_400(api_db):
    response = client.post("/risk/evaluate", json={})
    assert response.status_code == 400


def test_get_risk_evaluation_unknown_id_returns_404(api_db):
    response = client.get(f"/risk/evaluations/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_risk_evaluation_malformed_uuid_returns_400(api_db):
    response = client.get("/risk/evaluations/not-a-uuid")
    assert response.status_code == 400


# --- POST /risk/evaluate: inline payload path (never persisted) ---------------


def test_evaluate_inline_payload_is_not_persisted(api_db):
    strategy = _custom_strategy()
    metrics = {
        "total_return": 0.20,
        "cagr": 0.18,
        "max_drawdown": 0.05,
        "win_rate": 0.55,
        "avg_win": 500.0,
        "avg_loss": -250.0,
        "profit_factor": 2.0,
        "num_trades": 100,
        "exposure_time": 0.5,
        "sharpe": 1.2,
        "best_trade": 900.0,
        "worst_trade": -400.0,
        "starting_capital": 100000.0,
        "final_equity": 120000.0,
    }

    response = client.post(
        "/risk/evaluate", json={"metrics": metrics, "strategy": strategy}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["persisted"] is False
    assert body["risk_evaluation_id"] is None
    assert body["backtest_id"] is None
    assert "note" in body
    assert body["decision"] == "APPROVED"
    assert body["metrics_snapshot"] == metrics


def test_evaluate_inline_payload_missing_strategy_returns_400(api_db):
    response = client.post("/risk/evaluate", json={"metrics": {"num_trades": 10}})
    assert response.status_code == 400


# --- GET /backtests/{id}/risk --------------------------------------------------


def test_get_backtest_risk_returns_latest_evaluation(api_db, fake_service, artifacts_dir):
    posted = _persist_backtest()
    evaluated = client.post(
        "/risk/evaluate", json={"backtest_id": posted["backtest_id"]}
    ).json()

    response = client.get(f"/backtests/{posted['backtest_id']}/risk")
    assert response.status_code == 200
    body = response.json()
    assert body["risk_evaluation_id"] == evaluated["risk_evaluation_id"]
    assert body["decision"] == evaluated["decision"]


def test_get_backtest_risk_404_when_backtest_unknown(api_db):
    response = client.get(f"/backtests/{uuid.uuid4()}/risk")
    assert response.status_code == 404
    assert "No persisted backtest run" in response.json()["detail"]


def test_get_backtest_risk_404_when_no_evaluation_yet(api_db, fake_service, artifacts_dir):
    posted = _persist_backtest()
    response = client.get(f"/backtests/{posted['backtest_id']}/risk")
    assert response.status_code == 404
    assert "no persisted risk evaluation yet" in response.json()["detail"]


# --- database unreachable -------------------------------------------------------


def test_evaluate_returns_503_when_db_unavailable():
    class BrokenSession:
        def get(self, *args, **kwargs):
            raise OperationalError("SELECT 1", None, Exception("db down"))

        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", None, Exception("db down"))

        def close(self):
            pass

    def _broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = _broken_db
    try:
        response = client.post("/risk/evaluate", json={"backtest_id": str(uuid.uuid4())})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
