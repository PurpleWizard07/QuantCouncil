"""Schema tests: table inventory and DDL portability to SQLite."""

import sqlalchemy as sa

from app.db import models  # noqa: F401  (registers all models on Base)
from app.db.base import Base

EXPECTED_TABLES = {
    "assets",
    "ohlcv_daily",
    "strategy_definitions",
    "backtest_runs",
    "risk_evaluations",
    "agent_decisions",
    "paper_portfolios",
    "paper_orders",
    "paper_positions",
    "trade_journal",
    "nav_snapshots",
}


def test_metadata_contains_exactly_the_eleven_expected_tables():
    assert set(Base.metadata.tables.keys()) == EXPECTED_TABLES


def test_ddl_is_portable_to_sqlite():
    # The contract mandates portable types (sqlalchemy JSON, String statuses,
    # Uuid) precisely so the schema also works on SQLite in tests.
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = sa.inspect(engine)
    assert set(inspector.get_table_names()) == EXPECTED_TABLES
