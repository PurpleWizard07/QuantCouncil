"""Risk evaluation endpoints: run the deterministic risk engine and persist verdicts.

POST /risk/evaluate -- evaluate EITHER a persisted backtest run
(``{"backtest_id": "<uuid>"}``) OR an inline, never-persisted backtest
payload (``{"metrics": {...}, "strategy": {...}, "trades": [...]?, "config":
{...}?}``), mutually exclusive with ``backtest_id`` (same 400-on-both-or-
neither pattern as ``backtests.py``'s ``strategy``/``strategy_id``).

    - ``backtest_id`` path: loads the persisted ``BacktestRun`` and its
      ``StrategyDefinition`` (404 if either is missing -- the FK guarantees
      the strategy exists once the run does), reads the metrics straight off
      the row (already JSON-safe) and the trade list from the same
      artifact-on-disk pattern ``backtests.py`` uses (``_read_artifact`` /
      ``get_backtests_dir``, imported and reused here, not duplicated).
      ``config`` comes from ``row.params["config"]``. The evaluation is
      ALWAYS persisted (a risk evaluation of a persisted backtest is itself
      worth keeping, and the ``risk_evaluations`` FK columns are NOT NULL, so
      this path is the only one that CAN persist).
    - inline-payload path: nothing is looked up and nothing is persisted (no
      ``backtest_run_id`` exists to satisfy the NOT NULL FK); the response
      carries ``persisted: false`` with a note explaining that persistence
      requires a ``backtest_id``.

Both paths call ``risk_engine.engine.evaluate`` under the packaged DEFAULT
policy (``risk_engine.policy.load_policy()``) -- Phase 4 does not expose a
custom-policy override via the API; that is a deliberate simplification
documented here, not an oversight.

GET /risk/evaluations/{id} -- load a persisted risk evaluation by id.

Auto-evaluation on backtest persistence is DEFERRED: ``POST /backtests/run``
is unchanged by this router (no ``evaluate_risk`` flag) -- call
``POST /risk/evaluate`` explicitly after a persisted run. The brief calls
this integration optional; deferring it keeps ``backtests.py``'s persist
flow (and its default behavior for both ``persist=false`` and
``persist=true``) exactly as it was before Phase 4.

See ``apps.api.app.routers.backtests`` for the nested
``GET /backtests/{id}/risk`` convenience route (lives there, not here, since
it is nested under ``/backtests``).

Error mapping (mirrors backtests.py):
    400 -- malformed UUID, both/neither of backtest_id and inline payload given.
    404 -- unknown backtest_id, unknown risk_evaluation id.
    500 -- persisted backtest's trades artifact missing on disk (via _read_artifact).
    503 -- database unreachable while a DB operation was required.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from risk_engine.engine import evaluate as risk_evaluate
from risk_engine.policy import load_policy
from risk_engine.schemas import RiskEvaluationResult

from app.db import repositories
from app.db.session import get_db
from app.routers.backtests import DB_UNAVAILABLE_DETAIL, _parse_uuid, _read_artifact

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["risk"])

INLINE_NOT_PERSISTED_NOTE = (
    "results not persisted; persistence requires a persisted 'backtest_id' "
    "(the risk_evaluations.backtest_run_id/strategy_id columns are NOT NULL "
    "foreign keys, so an inline evaluation has nothing to attach a row to)"
)


class RiskEvaluateRequest(BaseModel):
    """Request body for POST /risk/evaluate.

    Attributes:
        backtest_id: UUID of a persisted backtest run to evaluate and
            persist. Mutually exclusive with the inline fields below.
        metrics: Inline metrics dict (the 14-field quant_engine contract
            set). Mutually exclusive with ``backtest_id``.
        strategy: Inline FULL validated strategy definition dict. Required
            alongside ``metrics`` for the inline path.
        trades: Optional inline trade list, used for warning heuristics.
        config: Optional inline backtest config dict (e.g.
            ``{"max_allocation_pct": 0.10}``).
    """

    backtest_id: str | None = None
    metrics: dict | None = None
    strategy: dict | None = None
    trades: list[dict] | None = None
    config: dict | None = None


def _is_inline_payload(request: RiskEvaluateRequest) -> bool:
    return request.metrics is not None or request.strategy is not None


def _result_body(
    result: RiskEvaluationResult, *, risk_evaluation_id: str | None, backtest_id: str | None
) -> dict[str, Any]:
    """The full RiskEvaluationResult contract plus the two echo fields."""
    return {
        "decision": result.decision,
        "approved": result.approved,
        "risk_score": result.risk_score,
        "policy_version": result.policy_version,
        "reasons": result.reasons,
        "failed_rules": result.failed_rules,
        "warnings": result.warnings,
        "metrics_snapshot": result.metrics_snapshot,
        "policy_snapshot": result.policy_snapshot,
        "risk_evaluation_id": risk_evaluation_id,
        "backtest_id": backtest_id,
    }


@router.post("/evaluate")
def evaluate_risk(
    request: RiskEvaluateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run the deterministic risk engine against a backtest, inline or persisted.

    Exactly one of ``backtest_id`` or an inline payload (``metrics`` +
    ``strategy``) must be provided. See the module docstring for the full
    persistence semantics.
    """
    has_backtest_id = request.backtest_id is not None
    has_inline = _is_inline_payload(request)
    if has_backtest_id == has_inline:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide exactly one of 'backtest_id' (a persisted backtest "
                "UUID) or an inline payload ('metrics' + 'strategy')."
            ),
        )

    policy = load_policy()

    if has_backtest_id:
        run_uuid = _parse_uuid(request.backtest_id, "backtest_id")
        try:
            row = repositories.get_backtest_run(db, run_uuid)
            strategy_row = (
                repositories.get_strategy(db, row.strategy_id) if row is not None else None
            )
        except OperationalError:
            logger.exception("POST /risk/evaluate: database unavailable")
            raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"No persisted backtest run with id {request.backtest_id!r}.",
            )
        if strategy_row is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Backtest run {request.backtest_id!r} references strategy "
                    f"{row.strategy_id!s}, which no longer exists."
                ),
            )

        trades = _read_artifact(row.trades_path, "trades.json")
        params = row.params or {}
        strategy_config = params.get("config")

        result = risk_evaluate(
            metrics=row.metrics or {},
            strategy=strategy_row.rules,
            policy=policy,
            trades=trades,
            strategy_config=strategy_config,
        )

        try:
            saved = repositories.create_risk_evaluation(
                db,
                backtest_run_id=row.id,
                strategy_id=strategy_row.id,
                decision=result.decision,
                approved=result.approved,
                risk_score=result.risk_score,
                policy_version=result.policy_version,
                reasons=result.reasons,
                failed_rules=result.failed_rules,
                warnings=result.warnings,
                metrics_snapshot=result.metrics_snapshot,
                policy_snapshot=result.policy_snapshot,
            )
        except OperationalError:
            logger.exception("POST /risk/evaluate: database unavailable (persist)")
            raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

        body = _result_body(
            result, risk_evaluation_id=str(saved.id), backtest_id=str(row.id)
        )
        body["persisted"] = True
        return body

    # Inline payload: never persisted (no backtest_run_id to satisfy the FK).
    if request.metrics is None or request.strategy is None:
        raise HTTPException(
            status_code=400,
            detail="Inline evaluation requires both 'metrics' and 'strategy'.",
        )

    result = risk_evaluate(
        metrics=request.metrics,
        strategy=request.strategy,
        policy=policy,
        trades=request.trades,
        strategy_config=request.config,
    )

    body = _result_body(result, risk_evaluation_id=None, backtest_id=None)
    body["persisted"] = False
    body["note"] = INLINE_NOT_PERSISTED_NOTE
    return body


@router.get("/evaluations")
def list_risk_evaluations(
    limit: int = 20, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """List persisted risk evaluations, newest first.

    Declared before ``GET /evaluations/{risk_evaluation_id}`` on this router
    so the literal ``/evaluations`` path is matched first -- FastAPI resolves
    routes in declaration order and a dynamic ``{risk_evaluation_id}``
    segment would otherwise be tried against the literal "evaluations"
    path too (unlike the ``/backtests`` vs. ``/backtests/{id}`` case, here
    both routes share the ``/evaluations`` prefix, so declaration order
    matters).
    """
    try:
        rows = repositories.list_risk_evaluations(db, limit=limit)
    except OperationalError:
        logger.exception("GET /risk/evaluations: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    items = [
        {
            "risk_evaluation_id": str(row.id),
            "backtest_run_id": str(row.backtest_run_id),
            "decision": row.decision,
            "approved": row.approved,
            "risk_score": row.risk_score,
            "policy_version": row.policy_version,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return {"count": len(items), "evaluations": items}


@router.get("/evaluations/{risk_evaluation_id}")
def get_risk_evaluation(
    risk_evaluation_id: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Load a persisted risk evaluation by id."""
    eval_uuid = _parse_uuid(risk_evaluation_id, "risk_evaluation_id")

    try:
        row = repositories.get_risk_evaluation(db, eval_uuid)
    except OperationalError:
        logger.exception(
            "GET /risk/evaluations/%s: database unavailable", risk_evaluation_id
        )
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No persisted risk evaluation with id {risk_evaluation_id!r}.",
        )

    return {
        "risk_evaluation_id": str(row.id),
        "backtest_id": str(row.backtest_run_id),
        "strategy_id": str(row.strategy_id),
        "decision": row.decision,
        "approved": row.approved,
        "risk_score": row.risk_score,
        "policy_version": row.policy_version,
        "reasons": row.reasons,
        "failed_rules": row.failed_rules,
        "warnings": row.warnings,
        "metrics_snapshot": row.metrics_snapshot,
        "policy_snapshot": row.policy_snapshot,
        "created_at": row.created_at.isoformat(),
        "persisted": True,
    }
