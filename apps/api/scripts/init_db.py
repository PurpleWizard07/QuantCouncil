"""Create all QuantCouncil tables against the configured database.

DEPRECATED for real databases (Phase 3.5): schema is now managed by Alembic
-- run ``alembic -c infra/alembic.ini upgrade head`` from the repo root
instead (see infra/migrations/README.md). This script creates tables WITHOUT
stamping an Alembic revision, so a database initialized here will confuse
future ``upgrade`` runs. It is kept only as a convenience for throwaway /
test databases.

Idempotent: Base.metadata.create_all only creates tables that do not exist.

Usage (from apps/api, with the venv active and Postgres running):

    python scripts/init_db.py
"""

import sys
from pathlib import Path

# Path bootstrap so "import app" works when this file is run directly.
API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.db import models  # noqa: F401,E402  (registers all models on Base)
from app.db.base import Base  # noqa: E402
from app.db.session import get_engine  # noqa: E402


def main() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    print(f"Ensured {len(Base.metadata.tables)} tables on {engine.url.render_as_string(hide_password=True)}:")
    for table_name in sorted(Base.metadata.tables):
        print(f"  - {table_name}")


if __name__ == "__main__":
    main()
