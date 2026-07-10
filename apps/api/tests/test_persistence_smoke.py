"""Phase 3.5 persistence smoke tests -- in-memory SQLite, no network.

Covers the persistence surface end to end without Postgres:
    - POST /strategies + GET /strategies builtin/persisted merge and the
      database-unavailable degradation path.
    - POST /backtests/run with persist=true (artifacts to a tmp dir via the
      ``get_backtests_dir`` dependency override) and the GET round-trip.
    - Repository idempotency: upsert_assets and upsert_ohlcv_bars.

The ``get_db`` dependency is overridden with sessions bound to a per-test
in-memory SQLite engine (StaticPool, so every thread -- TestClient runs sync
endpoints in a worker thread -- sees the same database). The OHLCV connector
is the deterministic fake from the Phase 3 tests; the real cache and network
are never touched.
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

from app.db import repositories
from app.db.base import Base
from app.db.models import StrategyStatus
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
def db(session_factory):
    """A direct session for repository-level tests."""
    session = session_factory()
    yield session
    session.close()


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


def _custom_strategy(name: str = "my_sma_crossover") -> dict:
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


# --- strategies: POST + merge in GET --------------------------------------------


def test_post_then_get_strategies_shows_builtins_plus_persisted(api_db):
    created = client.post("/strategies", json=_custom_strategy())
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "my_sma_crossover"
    assert body["status"] == StrategyStatus.DRAFT.value
    assert body["source"] == "persisted"
    uuid.UUID(body["id"])  # valid UUID string
    assert body["created_at"]

    listed = client.get("/strategies").json()
    assert listed["count"] == 4
    assert "warning" not in listed
    sources = [s["source"] for s in listed["strategies"]]
    assert sources == ["builtin", "builtin", "builtin", "persisted"]
    persisted = listed["strategies"][-1]
    assert persisted["id"] == body["id"]
    assert persisted["status"] == StrategyStatus.DRAFT.value
    # Full definition round-trips out of the rules JSON.
    assert persisted["name"] == "my_sma_crossover"
    assert persisted["entry"] and persisted["exit"] and persisted["stop_loss"]


def test_post_strategy_invalid_returns_400(api_db):
    bad = _custom_strategy()
    del bad["stop_loss"]
    response = client.post("/strategies", json=bad)
    assert response.status_code == 400
    assert "Invalid strategy definition" in response.json()["detail"]


def test_post_strategy_name_conflicts_return_409(api_db):
    builtin_clash = _custom_strategy(name="sma_crossover_20_50")
    assert client.post("/strategies", json=builtin_clash).status_code == 409

    assert client.post("/strategies", json=_custom_strategy()).status_code == 201
    duplicate = client.post("/strategies", json=_custom_strategy())
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


def test_get_strategies_degrades_when_db_unavailable():
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", None, Exception("db down"))

        def close(self):
            pass

    def _broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = _broken_db
    try:
        response = client.get("/strategies")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert body["warning"] == "database unavailable; persisted strategies not shown"


# --- backtests: persist=true round trip ------------------------------------------


def test_backtest_persist_roundtrip(api_db, fake_service, artifacts_dir):
    run = client.post(
        "/backtests/run",
        json=_run_body(strategy=_custom_strategy(), persist=True),
    )
    assert run.status_code == 200
    posted = run.json()
    assert posted["persisted"] is True
    backtest_id = posted["backtest_id"]
    run_uuid = uuid.UUID(backtest_id)

    # Artifacts landed in the overridden directory.
    run_dir = artifacts_dir / str(run_uuid)
    assert (run_dir / "equity_curve.json").is_file()
    assert (run_dir / "trades.json").is_file()

    # The strategy was created and promoted DRAFT -> BACKTESTED.
    listed = client.get("/strategies").json()
    persisted = [s for s in listed["strategies"] if s["source"] == "persisted"]
    assert len(persisted) == 1
    assert persisted[0]["name"] == "my_sma_crossover"
    assert persisted[0]["status"] == StrategyStatus.BACKTESTED.value

    # GET round-trips everything the POST returned.
    fetched = client.get(f"/backtests/{backtest_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["backtest_id"] == backtest_id
    assert body["strategy_id"] == persisted[0]["id"]
    assert body["strategy_name"] == "my_sma_crossover"
    assert body["symbol"] == "RELIANCE"
    assert body["timeframe"] == "1d"
    assert body["config"] == posted["config"]
    assert body["start_date"] == posted["start_date"]
    assert body["end_date"] == posted["end_date"]
    assert body["status"] == "COMPLETED"
    assert body["created_at"] and body["completed_at"]
    assert body["metrics"] == posted["metrics"]
    assert body["equity_curve"] == posted["equity_curve"]
    assert body["trades"] == posted["trades"]
    assert body["persisted"] is True


def test_backtest_persist_false_writes_nothing(api_db, fake_service, artifacts_dir):
    run = client.post(
        "/backtests/run", json=_run_body(strategy=_custom_strategy())
    )
    assert run.status_code == 200
    body = run.json()
    assert body["persisted"] is False
    assert body["backtest_id"] is None
    assert "Phase 3.5" in body["note"]

    assert client.get("/strategies").json()["count"] == 3  # nothing persisted
    assert list(artifacts_dir.iterdir()) == []  # no artifacts


def test_backtest_requires_exactly_one_strategy_source(api_db, fake_service):
    neither = client.post("/backtests/run", json=_run_body())
    assert neither.status_code == 400
    both = client.post(
        "/backtests/run",
        json=_run_body(strategy=_custom_strategy(), strategy_id=str(uuid.uuid4())),
    )
    assert both.status_code == 400


def test_backtest_by_strategy_id(api_db, fake_service, artifacts_dir):
    created = client.post("/strategies", json=_custom_strategy()).json()

    run = client.post(
        "/backtests/run",
        json=_run_body(strategy_id=created["id"], persist=True),
    )
    assert run.status_code == 200
    assert run.json()["strategy_name"] == "my_sma_crossover"

    fetched = client.get(f"/backtests/{run.json()['backtest_id']}").json()
    assert fetched["strategy_id"] == created["id"]

    assert (
        client.post(
            "/backtests/run", json=_run_body(strategy_id="not-a-uuid")
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/backtests/run", json=_run_body(strategy_id=str(uuid.uuid4()))
        ).status_code
        == 404
    )


def test_backtest_persist_name_conflict_with_different_rules_409(
    api_db, fake_service, artifacts_dir
):
    assert client.post("/strategies", json=_custom_strategy()).status_code == 201

    changed = _custom_strategy()
    changed["stop_loss"]["value"] = 0.09  # same name, different rules
    conflict = client.post(
        "/backtests/run", json=_run_body(strategy=changed, persist=True)
    )
    assert conflict.status_code == 409
    assert "strategy_id" in conflict.json()["detail"]

    # Identical rules reuse the existing row instead of conflicting.
    rerun = client.post(
        "/backtests/run",
        json=_run_body(strategy=_custom_strategy(), persist=True),
    )
    assert rerun.status_code == 200
    persisted = [
        s
        for s in client.get("/strategies").json()["strategies"]
        if s["source"] == "persisted"
    ]
    assert len(persisted) == 1


def test_get_backtest_error_paths(api_db, fake_service, artifacts_dir):
    assert client.get("/backtests/not-a-uuid").status_code == 400
    assert client.get(f"/backtests/{uuid.uuid4()}").status_code == 404

    run = client.post(
        "/backtests/run",
        json=_run_body(strategy=_custom_strategy(), persist=True),
    ).json()
    run_dir = artifacts_dir / run["backtest_id"]
    (run_dir / "trades.json").unlink()

    broken = client.get(f"/backtests/{run['backtest_id']}")
    assert broken.status_code == 500
    assert "artifact missing on disk" in broken.json()["detail"]


# --- repositories: idempotent upserts -------------------------------------------


def test_upsert_assets_idempotent(db):
    records = [
        {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "exchange": "NSE", "sector": "Energy"},
        {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE", "sector": "IT"},
    ]
    first = repositories.upsert_assets(db, records)
    assert first == {"created": 2, "updated": 0, "unchanged": 0}

    second = repositories.upsert_assets(db, records)
    assert second == {"created": 0, "updated": 0, "unchanged": 2}

    # Metadata change -> exactly one update; lookup is case-insensitive.
    records[0]["sector"] = "Energy (Oil & Gas)"
    third = repositories.upsert_assets(db, records)
    assert third == {"created": 0, "updated": 1, "unchanged": 1}
    assert repositories.get_asset_by_symbol(db, "reliance").sector == "Energy (Oil & Gas)"


def test_upsert_ohlcv_bars_idempotent(db):
    repositories.upsert_assets(
        db,
        [{"symbol": "INFY", "name": "Infosys Ltd", "exchange": "NSE", "sector": "IT"}],
    )
    asset = repositories.get_asset_by_symbol(db, "INFY")
    frame = _sine_trend_frame(30)

    first = repositories.upsert_ohlcv_bars(db, asset.id, frame)
    assert first == {"inserted": 30, "skipped": 0}

    second = repositories.upsert_ohlcv_bars(db, asset.id, frame)
    assert second == {"inserted": 0, "skipped": 30}

    # Overlapping wider range: only the genuinely new rows are inserted.
    wider = _sine_trend_frame(40)
    third = repositories.upsert_ohlcv_bars(db, asset.id, wider)
    assert third == {"inserted": 10, "skipped": 30}
