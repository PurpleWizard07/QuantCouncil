"""Alembic migration tests -- run against scratch SQLite files, no Postgres.

Two guarantees:

1. ``alembic upgrade head`` (via the command API, driven through
   ``ALEMBIC_DATABASE_URL``) creates exactly the ten foundation tables, and
   ``downgrade base`` removes them all.
2. Schema equivalence: a database built by ``alembic upgrade head`` matches a
   database built by ``Base.metadata.create_all`` -- same table names, and per
   table the same column names, type strings, and nullability -- so the static
   initial migration can never silently drift from the models.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

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
}


def _repo_root() -> Path:
    """Walk up from this file to the repo root (marker: infra/alembic.ini)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "infra" / "alembic.ini").is_file():
            return parent
    raise AssertionError(f"could not find infra/alembic.ini above {here}")


def _alembic_config() -> Config:
    root = _repo_root()
    cfg = Config(str(root / "infra" / "alembic.ini"))
    # script_location in the ini is relative to the invocation cwd; make it
    # absolute so these tests pass regardless of where pytest was started.
    cfg.set_main_option("script_location", str(root / "infra" / "migrations"))
    return cfg


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _upgrade_head(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", _sqlite_url(db_path))
    command.upgrade(_alembic_config(), "head")


def _user_tables(engine: sa.Engine) -> set[str]:
    return set(sa.inspect(engine).get_table_names()) - {"alembic_version"}


def _schema_snapshot(engine: sa.Engine) -> dict[str, dict[str, dict]]:
    """{table: {column: {type, nullable}}} as rendered by the dialect."""
    inspector = sa.inspect(engine)
    snapshot: dict[str, dict[str, dict]] = {}
    for table in sorted(_user_tables(engine)):
        snapshot[table] = {
            col["name"]: {
                "type": str(col["type"]).upper(),
                "nullable": col["nullable"],
            }
            for col in inspector.get_columns(table)
        }
    return snapshot


def test_upgrade_head_creates_all_ten_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "migrated.db"
    _upgrade_head(db_path, monkeypatch)

    engine = sa.create_engine(_sqlite_url(db_path))
    try:
        assert _user_tables(engine) == EXPECTED_TABLES

        # The ohlcv idempotency guard must exist in the migrated schema too.
        uqs = sa.inspect(engine).get_unique_constraints("ohlcv_daily")
        assert {
            "name": "uq_ohlcv_daily_asset_date",
            "column_names": ["asset_id", "date"],
        } in [{"name": u["name"], "column_names": u["column_names"]} for u in uqs]
    finally:
        engine.dispose()


def test_downgrade_base_drops_all_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "roundtrip.db"
    _upgrade_head(db_path, monkeypatch)
    command.downgrade(_alembic_config(), "base")

    engine = sa.create_engine(_sqlite_url(db_path))
    try:
        assert _user_tables(engine) == set()
    finally:
        engine.dispose()


def test_migrated_schema_matches_create_all(tmp_path, monkeypatch):
    migrated_path = tmp_path / "via_alembic.db"
    created_path = tmp_path / "via_create_all.db"

    _upgrade_head(migrated_path, monkeypatch)

    created_engine = sa.create_engine(_sqlite_url(created_path))
    migrated_engine = sa.create_engine(_sqlite_url(migrated_path))
    try:
        Base.metadata.create_all(created_engine)

        migrated = _schema_snapshot(migrated_engine)
        created = _schema_snapshot(created_engine)

        assert set(migrated) == set(created) == EXPECTED_TABLES
        for table in EXPECTED_TABLES:
            assert migrated[table] == created[table], (
                f"schema drift in table {table!r}: "
                f"alembic={migrated[table]} create_all={created[table]}"
            )
    finally:
        created_engine.dispose()
        migrated_engine.dispose()
