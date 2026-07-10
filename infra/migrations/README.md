# Database migrations (Alembic)

Schema changes flow through Alembic from Phase 3.5 onward. The ten
foundation tables are created by the initial migration
(`versions/356085dfc427_initial_schema.py`), which exactly matches
`apps/api/app/db/models.py` (`Base.metadata`) — equivalence is enforced by
`apps/api/tests/test_migrations.py`.

## Running migrations

From the **repo root**, with the venv active (or via `.venv/Scripts/python.exe -m alembic`):

```bash
# Apply all migrations
alembic -c infra/alembic.ini upgrade head

# Show current revision / history
alembic -c infra/alembic.ini current
alembic -c infra/alembic.ini history

# Roll everything back (drops all tables)
alembic -c infra/alembic.ini downgrade base
```

## Database URL resolution

`sqlalchemy.url` in `infra/alembic.ini` is intentionally **empty**;
`env.py` resolves the URL at runtime, in this order:

1. `ALEMBIC_DATABASE_URL` environment variable, if set (used by tests to
   target scratch SQLite files, and handy for one-off runs against another
   database).
2. Otherwise `app.core.config.get_settings().database_url`, i.e. the
   `DATABASE_URL` from your environment or the repo-root `.env` file
   (default: local Postgres, see `.env.example`).

No credentials are ever stored in the ini or in migration files.

## Creating a new migration

```bash
# Autogenerate against the configured database (must be at head first)
alembic -c infra/alembic.ini revision --autogenerate -m "describe the change"
```

Review the generated file before committing — autogenerate output is a
starting point, not a finished migration. Keep migrations portable
(SQLite + PostgreSQL): plain `sa.JSON`, `String` statuses, `sa.Uuid`, no
dialect-specific constructs.

## init_db.py (deprecated for real databases)

`apps/api/scripts/init_db.py` (a `Base.metadata.create_all` script) is
**deprecated for real databases** — it creates tables without stamping an
Alembic revision, so a database initialized that way will confuse future
`upgrade` runs. It is kept only as a convenience for throwaway/test
databases (tests use `create_all` on in-memory SQLite directly). For any
database you intend to keep, use `alembic -c infra/alembic.ini upgrade head`.
