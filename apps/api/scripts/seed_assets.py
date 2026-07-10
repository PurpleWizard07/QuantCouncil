"""Seed the assets table from the NIFTY 50 universe snapshot.

Source of truth: ``data/nifty50_symbols.json`` via
``data_connectors.get_universe()``. Idempotent -- running twice changes
nothing the second time (the repository upsert only writes rows that are new
or whose name/exchange/sector actually changed).

Usage (from the repo root, venv active, database migrated):

    python apps/api/scripts/seed_assets.py

Prerequisite: the schema must exist -- run
``alembic -c infra/alembic.ini upgrade head`` first.
"""

import sys
from pathlib import Path

# Path bootstrap so "import app" works when this file is run directly.
API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy.exc import OperationalError  # noqa: E402

from data_connectors import get_universe  # noqa: E402

from app.db.repositories import upsert_assets  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

DB_UNREACHABLE_HINT = (
    "ERROR: could not connect to the database.\n"
    "Is Postgres running? Start it with:  docker compose -f "
    "infra/docker-compose.yml up -d\n"
    "Also check DATABASE_URL in your repo-root .env (see .env.example)."
)


def main() -> int:
    records = get_universe()
    db = SessionLocal()
    try:
        counts = upsert_assets(db, records)
    except OperationalError as exc:
        print(DB_UNREACHABLE_HINT, file=sys.stderr)
        print(f"(driver error: {exc.orig})", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(
        f"Seeded NIFTY 50 universe ({len(records)} symbols): "
        f"{counts['created']} created, {counts['updated']} updated, "
        f"{counts['unchanged']} unchanged."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
