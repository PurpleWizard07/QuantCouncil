"""Strategy endpoints: built-in templates plus persisted user strategies.

GET  /strategies -- built-in templates merged with persisted strategies.
POST /strategies -- validate and persist a user-authored strategy (DRAFT).

Built-ins are CODE-DEFINED templates served from
``quant_engine.strategies.get_builtin_strategies()`` (deep copies, so
responses can never mutate the module constants). Persisted strategies live
in the ``strategy_definitions`` table (Phase 3.5) and are stored as the FULL
validated definition JSON in the ``rules`` column.

Response shape (GET): each strategy record is the full definition plus
metadata fields -- ``source: "builtin"`` for templates (no id, no status) or
``source: "persisted"`` with ``id`` (str UUID), ``status``, ``created_at``
for rows. Consumers that want to re-validate a record against the strict v1
schema must strip the metadata keys first (the schema rejects unknown
top-level keys by design; see ``STRATEGY_METADATA_KEYS``).

Local-first degradation: if the database is unreachable, GET /strategies
still returns 200 with the built-ins only, plus a ``warning`` field
("database unavailable; persisted strategies not shown") -- browsing
templates must never require Postgres. POST, being a write, returns 503 when
the database is down.

Error mapping (POST):
    400 -- definition fails ``quant_engine.strategy.validate_strategy``.
    409 -- name collides with a built-in template or a persisted strategy.
    503 -- database unreachable.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from quant_engine.strategies import get_builtin_strategies
from quant_engine.strategy import StrategyValidationError, validate_strategy

from app.db import repositories
from app.db.models import StrategyDefinition
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])

DB_UNAVAILABLE_WARNING = "database unavailable; persisted strategies not shown"
DB_UNAVAILABLE_DETAIL = (
    "Database unavailable. Is Postgres running? Start it with "
    "'docker compose -f infra/docker-compose.yml up -d' and check "
    "DATABASE_URL in the repo-root .env."
)

# Metadata keys the API adds alongside the raw definition fields in GET
# responses; strip these before re-validating a record against the schema.
STRATEGY_METADATA_KEYS = {"source", "id", "status", "created_at"}


def _builtin_record(definition: dict) -> dict[str, Any]:
    """A built-in template as a response record (no id, no status)."""
    return {**definition, "source": "builtin"}


def _persisted_record(row: StrategyDefinition) -> dict[str, Any]:
    """A persisted row as a response record: full definition + metadata."""
    return {
        **dict(row.rules),
        "source": "persisted",
        "id": str(row.id),
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    }


@router.get("")
def list_strategies(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Built-in templates first, then persisted strategies (oldest first).

    Degrades gracefully when the database is unreachable: returns the
    built-ins only, plus a ``warning`` field (see module docstring) -- the
    endpoint never 5xxes just because Postgres is down.
    """
    strategies = [_builtin_record(d) for d in get_builtin_strategies()]
    warning: str | None = None
    try:
        rows = repositories.list_strategies(db)
    except OperationalError:
        logger.warning("GET /strategies: database unavailable; serving builtins only")
        warning = DB_UNAVAILABLE_WARNING
    else:
        strategies.extend(_persisted_record(row) for row in rows)

    body: dict[str, Any] = {"count": len(strategies), "strategies": strategies}
    if warning is not None:
        body["warning"] = warning
    return body


@router.post("", status_code=201)
def create_strategy(
    definition: dict, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Validate and persist a user-authored strategy definition (DRAFT).

    The request body is the full strategy JSON per docs/strategy-format.md.
    The normalized output of ``validate_strategy`` (not the raw input) is
    what gets stored, so every persisted ``rules`` document is schema-valid
    by construction.
    """
    try:
        validated = validate_strategy(definition)
    except StrategyValidationError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid strategy definition: {exc}"
        ) from None

    name = validated["name"]
    builtin_names = {d["name"] for d in get_builtin_strategies()}
    if name in builtin_names:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Strategy name {name!r} collides with a built-in template; "
                "choose a different name."
            ),
        )

    try:
        if repositories.find_strategy_by_name(db, name) is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A persisted strategy named {name!r} already exists.",
            )
        row = repositories.create_strategy(db, validated)
    except OperationalError:
        logger.exception("POST /strategies: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    return {
        "id": str(row.id),
        "name": row.name,
        "status": row.status,
        "source": "persisted",
        "created_at": row.created_at.isoformat(),
    }
