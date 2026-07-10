# QuantCouncil API

FastAPI backend for QuantCouncil, a personal AI quant research and
PAPER-TRADING-ONLY lab (NIFTY 50, daily timeframe, long-only). It exposes
health endpoints and owns the SQLAlchemy schema for the 10 core tables.
There is no real-money trading, no broker connectivity, and no financial
advice anywhere in this service.

## Run locally

From the repo root, create and activate a virtualenv, then install dev deps:

```
python -m venv .venv
.venv\Scripts\activate          # Windows (source .venv/bin/activate on Unix)
pip install -r requirements-dev.txt
```

Start the API from `apps/api`:

```
cd apps/api
uvicorn app.main:app --reload --port 8000
```

- API root: http://localhost:8000/
- OpenAPI docs: http://localhost:8000/docs
- Health: http://localhost:8000/health and http://localhost:8000/health/db

Configuration comes from environment variables (or a repo-root `.env`):
`APP_ENV`, `DATABASE_URL`, `API_HOST`, `API_PORT`, `CORS_ORIGINS`,
`ANTHROPIC_API_KEY` (optional, unused in the foundation phase).

## Initialize the database

With PostgreSQL running (see `infra/` for Docker Compose) and `DATABASE_URL`
pointing at it, run from `apps/api`:

```
python scripts/init_db.py
```

The script is idempotent: it creates any missing tables via
`Base.metadata.create_all` and prints the table names it ensured. Alembic
migrations replace this in Phase 2.

## Tests

Tests do not require a live database (`/health/db` is asserted to return
200 or 503; schema DDL is validated against in-memory SQLite). Run from the
repo root (root `pytest.ini` sets `testpaths = apps/api packages`):

```
pytest
```

or only this app's tests:

```
pytest apps/api
```
