"""Alembic environment for QuantCouncil.

Bootstraps ``sys.path`` so ``import app`` resolves to ``apps/api/app``
regardless of the working directory Alembic is invoked from, registers all
ten models on ``Base.metadata``, and resolves the database URL at runtime:

1. ``ALEMBIC_DATABASE_URL`` environment variable, if set (used by tests to
   point migrations at a scratch SQLite file).
2. Otherwise ``app.core.config.get_settings().database_url`` (which loads the
   repo-root ``.env``).

``sqlalchemy.url`` in ``infra/alembic.ini`` is intentionally empty.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- sys.path bootstrap: make apps/api importable ---------------------------
# This file lives at <repo_root>/infra/migrations/env.py; walk up from here
# until a directory containing apps/api is found (robust to repo relocation).


def _find_api_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "apps" / "api"
        if (candidate / "app").is_dir():
            return candidate
    raise RuntimeError(
        f"Could not locate apps/api by walking up from {here}; "
        "run Alembic from within the QuantCouncil repo checkout."
    )


_API_DIR = _find_api_dir()
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

from app.db import models  # noqa: F401,E402  (registers all models on Base)
from app.db.base import Base  # noqa: E402

config = context.config
target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """ALEMBIC_DATABASE_URL env var if set, else the app settings URL."""
    override = os.environ.get("ALEMBIC_DATABASE_URL", "").strip()
    if override:
        return override
    from app.core.config import get_settings

    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DBAPI)."""
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect and execute)."""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolve_database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
