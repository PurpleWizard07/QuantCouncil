"""Health endpoints.

GET /health    -- liveness, never touches the database.
GET /health/db -- readiness, runs SELECT 1 through the engine.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; intentionally does not touch the database."""
    return {"status": "ok", "service": "quantcouncil-api", "version": "0.1.0"}


@router.get("/health/db")
def health_db():
    """Readiness probe: SELECT 1 against the configured database.

    Returns 503 with a generic body on failure; the exception is logged
    server-side and never leaked to the client.
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        return JSONResponse(status_code=503, content={"database": "unreachable"})
    return {"database": "ok"}
