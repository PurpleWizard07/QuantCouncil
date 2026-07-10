"""GET /strategies endpoint tests -- no network, no real database.

The endpoint serves code-defined templates straight from
``quant_engine.strategies``; these tests assert the response shape and that
every served definition is schema-valid. Since Phase 3.5 the endpoint also
merges persisted strategies from the database, so ``get_db`` is overridden
with an empty in-memory SQLite session to keep these tests hermetic (an
empty DB means the response is still exactly the three built-ins, matching
the original Phase 3 assertions).
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routers.strategies import STRATEGY_METADATA_KEYS
from quant_engine.strategy import validate_strategy

client = TestClient(app)

EXPECTED_NAMES = {
    "sma_crossover_20_50",
    "rsi_mean_reversion_14",
    "volume_breakout_swing_20",
}


@pytest.fixture(autouse=True)
def empty_sqlite_db():
    """Override get_db with an empty in-memory SQLite DB (hermetic tests).

    StaticPool shares the single in-memory connection across threads --
    TestClient runs sync endpoints in a worker thread, and without it every
    thread would see its own fresh (table-less) database.
    """
    engine = sa.create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def _get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_list_strategies_returns_three_valid_definitions():
    response = client.get("/strategies")
    assert response.status_code == 200
    body = response.json()

    assert body["count"] == 3
    assert len(body["strategies"]) == 3
    assert {s["name"] for s in body["strategies"]} == EXPECTED_NAMES

    # Every served definition must pass the strict v1 schema. Phase 3.5 adds
    # metadata fields (source/id/status/created_at) alongside the definition;
    # strip them first, since the schema rejects unknown keys by design.
    for strategy in body["strategies"]:
        definition = {
            key: value
            for key, value in strategy.items()
            if key not in STRATEGY_METADATA_KEYS
        }
        validate_strategy(definition)


def test_list_strategies_definitions_have_contract_fields():
    body = client.get("/strategies").json()
    required = {
        "name",
        "description",
        "universe",
        "timeframe",
        "direction",
        "entry",
        "exit",
        "stop_loss",
        "position_sizing",
    }
    for strategy in body["strategies"]:
        assert required <= strategy.keys()
        assert strategy["timeframe"] == "1d"
        assert strategy["direction"] == "long_only"
        assert len(strategy["universe"]) == 5


def test_list_strategies_responses_are_independent_copies():
    first = client.get("/strategies").json()
    first["strategies"][0]["name"] = "mutated-client-side"
    second = client.get("/strategies").json()
    assert {s["name"] for s in second["strategies"]} == EXPECTED_NAMES
