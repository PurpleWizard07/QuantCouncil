"""AI committee endpoints: run the six-role committee over a persisted backtest.

THE COMMITTEE PROPOSES ONLY -- it NEVER creates paper orders. Paper order
creation stays exclusively manual, via ``POST /paper/orders`` (Phase 5),
which enforces the persisted risk evaluation's veto again, independently.
Nothing in this router (or ``app.services.committee_service``) writes to
``paper_orders``, ``paper_positions``, or ``paper_portfolios``.

POST /committee/evaluate -- run the committee (technical analyst, quant
researcher, bull, bear, risk narrator, CIO) against a persisted
``BacktestRun`` + the ``RiskEvaluation`` that was computed against it, using
either the requested provider or (when ``provider`` is omitted) the
configured default (``settings.agent_provider``, itself defaulting to
``"mock"``). Manual provider selection NEVER silently falls back to mock: an
unconfigured named provider (e.g. ``"anthropic"`` with no API key) is a
controlled 503 failure, not a degraded mock run. Persists seven
``agent_decisions`` rows per call -- see ``app.services.committee_service``
for the exact seven-row scheme.

GET /committee/backtests/{backtest_id} -- list persisted committee
evaluations (``agent_decisions`` rows) for a backtest, newest first. Inputs
are omitted from this list response to keep it small; they remain in the
database and retrievable directly if needed.

Error mapping:
    400 -- malformed UUID; risk evaluation belongs to a different backtest
           than the one supplied; unknown ``provider`` name (message lists
           the allowed values).
    404 -- unknown ``backtest_id``; unknown ``risk_evaluation_id``.
    502 -- the selected provider responded but its output failed schema
           validation, or the provider call failed upstream (network, auth
           rejected mid-call, refusal, ...); logged server-side.
    503 -- a manually selected provider is not configured/reachable (names
           the missing env var or unreachable URL -- NOT a fallback); or the
           database is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from agents import ProviderError, ProviderNotConfiguredError, ProviderResponseError

from app.core.config import get_settings
from app.db import repositories
from app.db.session import get_db
from app.routers.backtests import DB_UNAVAILABLE_DETAIL, _parse_uuid
from app.services import committee_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/committee", tags=["committee"])


class CommitteeEvaluateRequest(BaseModel):
    """Request body for POST /committee/evaluate.

    Attributes:
        backtest_id: UUID of a persisted backtest run.
        risk_evaluation_id: UUID of a persisted risk evaluation computed
            against that same backtest run.
        provider: Provider name ("mock", "auto", "anthropic", "gemini",
            "openrouter", "ollama"). Omitted or null uses
            ``settings.agent_provider`` (default "mock").
    """

    backtest_id: str
    risk_evaluation_id: str
    provider: str | None = None


@router.post("/evaluate")
def evaluate_committee(
    request: CommitteeEvaluateRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Run the AI committee against a persisted backtest + risk evaluation.

    See the module docstring for the full error mapping. The response
    carries: both echoed ids, ``requested_provider`` / ``selected_provider``
    (they differ only when ``requested_provider`` is ``"auto"``), each of the
    five non-CIO role outputs, ``cio`` (the FINAL, veto-checked decision --
    authoritative), ``cio_raw`` (the untrusted raw CIO call, for audit only),
    ``override_warning``, and ``agent_decision_ids`` (all seven persisted row
    ids, in the order documented in ``committee_service``).
    """
    backtest_uuid = _parse_uuid(request.backtest_id, "backtest_id")
    risk_evaluation_uuid = _parse_uuid(request.risk_evaluation_id, "risk_evaluation_id")
    provider_name = (
        request.provider if request.provider is not None else get_settings().agent_provider
    )

    try:
        return committee_service.evaluate_committee(
            db,
            backtest_id=backtest_uuid,
            risk_evaluation_id=risk_evaluation_uuid,
            provider_name=provider_name,
        )
    except committee_service.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except committee_service.ValidationFailure as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except ValueError as exc:
        # get_provider() raises this for an unknown provider name; its
        # message already lists the allowed values.
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except ProviderNotConfiguredError as exc:
        # A controlled failure of manual provider selection -- NEVER a
        # silent fallback to mock.
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except (ProviderResponseError, ProviderError) as exc:
        # Log the full exception (with traceback) server-side for debugging,
        # but NEVER put its text in the client-facing response: a provider's
        # exception message can carry sensitive request detail (e.g. the
        # Gemini provider's underlying URL embeds GEMINI_API_KEY as a query
        # parameter, which httpx's own error formatting does not redact).
        # The client gets only a generic, static message.
        logger.exception("POST /committee/evaluate: provider failure")
        raise HTTPException(
            status_code=502,
            detail=f"AI committee provider {provider_name!r} failed. See server logs for details.",
        ) from None
    except OperationalError:
        logger.exception("POST /committee/evaluate: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None


@router.get("/backtests/{backtest_id}")
def list_committee_evaluations(
    backtest_id: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """List persisted committee agent_decisions rows for a backtest, newest first.

    ``input`` is intentionally omitted here to keep the list response small;
    it remains in the database (query ``agent_decisions`` directly, or add a
    detail endpoint later, if a UI ever needs it).
    """
    run_uuid = _parse_uuid(backtest_id, "backtest_id")

    try:
        backtest = repositories.get_backtest_run(db, run_uuid)
        decisions = (
            repositories.list_agent_decisions_for_backtest(db, run_uuid)
            if backtest is not None
            else []
        )
    except OperationalError:
        logger.exception(
            "GET /committee/backtests/%s: database unavailable", backtest_id
        )
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if backtest is None:
        raise HTTPException(
            status_code=404,
            detail=f"No persisted backtest run with id {backtest_id!r}.",
        )

    return {
        "backtest_id": str(run_uuid),
        "count": len(decisions),
        "decisions": [
            {
                "id": str(row.id),
                "agent_role": row.agent_role,
                "model": row.model,
                "output": row.output,
                "created_at": row.created_at.isoformat(),
            }
            for row in decisions
        ],
    }
