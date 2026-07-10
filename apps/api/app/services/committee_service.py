"""AI committee orchestration: build context, run the committee, persist it.

This module is pure glue between the database and the (complete, tested,
unmodified) ``agents`` package: it loads a persisted backtest run and risk
evaluation, shapes them into the plain context dict ``agents.run_committee``
expects, runs the six-role committee against an injected provider, and
persists every agent's input/output for audit.

THE COMMITTEE NEVER CREATES PAPER ORDERS. It only proposes a decision
(``CIODecision``); creating a paper order remains exclusively
``POST /paper/orders`` (Phase 5), which enforces the risk veto again,
independently, against the persisted ``RiskEvaluation`` row.

THE RISK VETO is enforced entirely inside ``agents.committee.run_committee``
(a model validator on ``CIODecision`` plus a deterministic override step) --
this module does not re-implement or second-guess it. It merely reads the
already-persisted ``RiskEvaluation.approved`` column and hands it to the
committee verbatim; ``approved_by_risk`` on the final decision is always that
same persisted value.

PERSISTENCE: SEVEN ``agent_decisions`` rows per evaluation, in this order:
    1-5. technical_analyst, quant_researcher, bull, bear, risk_narrator --
         each row's ``input`` is the exact JSON-safe payload
         (``agents.build_agent_payload``) that role received (context fields
         plus prior roles' summaries), and ``output`` is that role's
         validated raw output (``model_dump()``).
    6.   cio -- the RAW, UNTRUSTED CIO output (``CIORawOutput.model_dump()``)
         BEFORE the deterministic veto step. ``input`` is that role's payload
         like the others.
    7.   cio (again) -- the AUTHORITATIVE final decision: the veto-checked
         ``CIODecision`` (with ``audit_refs.agent_decision_ids`` filled in
         with the SIX raw-role row ids from steps 1-6 -- this seventh row
         cannot reference its own id before it exists) plus
         ``override_warning`` folded into the stored JSON. ``model`` is
         ``"{provider}:final"`` (vs. plain ``"{provider}"`` for rows 1-6) so
         the two CIO rows for one evaluation are distinguishable at a glance.
         Row 6 is kept purely for audit ("what did the raw agent say");
         downstream code must always prefer row 7 (or the API response's
         ``cio`` field, never ``cio_raw``) as the decision of record. The
         API response's own ``agent_decision_ids`` list (returned to the
         caller, NOT the same list as ``cio.audit_refs.agent_decision_ids``)
         has all SEVEN ids, row 7's own id last.

``build_context`` and ``evaluate_committee`` raise the local ``NotFound`` /
``ValidationFailure`` exceptions (mirroring
``app.services.paper_engine``'s convention) for the router to map to
404/400; ``sqlalchemy.exc.OperationalError`` and any ``agents.ProviderError``
subclass are left to propagate unchanged for the router to map.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents import AgentRole, build_agent_payload, get_provider, run_committee

from app.db import repositories
from app.routers.backtests import _read_artifact


class CommitteeServiceError(Exception):
    """Base class for every typed error this module raises."""


class NotFound(CommitteeServiceError):
    """A referenced entity (backtest run, risk evaluation, strategy) is missing."""


class ValidationFailure(CommitteeServiceError):
    """A pure input error, e.g. a risk evaluation that belongs to a different backtest."""


def build_context(
    db: Session, backtest_id: uuid.UUID, risk_evaluation_id: uuid.UUID
) -> dict[str, Any]:
    """Load and shape the plain context dict ``agents.run_committee`` expects.

    Raises:
        NotFound: unknown ``backtest_id``, unknown ``risk_evaluation_id``, or
            (defensively) a backtest whose strategy row no longer exists.
        ValidationFailure: the risk evaluation was computed against a
            DIFFERENT backtest run than ``backtest_id`` (names both ids).

    The returned dict carries one extra, non-``agents``-contract key,
    ``strategy_id`` (a ``uuid.UUID``, not stringified) -- used internally by
    ``evaluate_committee`` to persist ``agent_decisions.strategy_id`` without
    a second database round trip. ``agents.build_agent_payload`` only reads
    the documented context keys (strategy/metrics/risk_evaluation/
    trades_summary/symbol/dates), so this extra key never leaks into a
    provider payload.
    """
    backtest = repositories.get_backtest_run(db, backtest_id)
    if backtest is None:
        raise NotFound(f"No persisted backtest run with id {backtest_id!s}.")

    risk_eval = repositories.get_risk_evaluation(db, risk_evaluation_id)
    if risk_eval is None:
        raise NotFound(
            f"No persisted risk evaluation with id {risk_evaluation_id!s}."
        )

    if risk_eval.backtest_run_id != backtest.id:
        raise ValidationFailure(
            f"Risk evaluation {risk_evaluation_id!s} was evaluated against "
            f"backtest {risk_eval.backtest_run_id!s}, not the supplied "
            f"backtest_id {backtest_id!s}; the AI committee may only run "
            "against a risk evaluation of its own backtest."
        )

    strategy = repositories.get_strategy(db, backtest.strategy_id)
    if strategy is None:
        raise NotFound(
            f"Backtest run {backtest_id!s} references strategy "
            f"{backtest.strategy_id!s}, which no longer exists."
        )

    trades = _read_artifact(backtest.trades_path, "trades.json")
    trades_summary = {
        "count": len(trades),
        "first": trades[:3],
        "last": trades[-3:],
    }

    params = backtest.params or {}

    return {
        "strategy": {
            "name": strategy.name,
            "universe": strategy.universe,
            "timeframe": strategy.timeframe,
            "direction": strategy.direction,
        },
        "metrics": backtest.metrics or {},
        "risk_evaluation": {
            "decision": risk_eval.decision,
            "approved": risk_eval.approved,
            "risk_score": risk_eval.risk_score,
            "failed_rules": risk_eval.failed_rules,
            "warnings": risk_eval.warnings,
            "policy_version": risk_eval.policy_version,
        },
        "trades_summary": trades_summary,
        "symbol": params.get("symbol"),
        "dates": {
            "start": backtest.start_date.isoformat(),
            "end": backtest.end_date.isoformat(),
        },
        "backtest_id": str(backtest_id),
        "risk_evaluation_id": str(risk_evaluation_id),
        # Internal only -- see docstring above.
        "strategy_id": backtest.strategy_id,
    }


def evaluate_committee(
    db: Session,
    *,
    backtest_id: uuid.UUID,
    risk_evaluation_id: uuid.UUID,
    provider_name: str,
) -> dict[str, Any]:
    """Run the six-role committee and persist all seven audit rows.

    Args:
        provider_name: The provider name AS REQUESTED (e.g. "mock", "auto",
            "anthropic"). Resolved via ``agents.get_provider`` -- manual
            selection of an unconfigured provider raises
            ``ProviderNotConfiguredError`` and NEVER falls back to mock.

    Raises:
        NotFound, ValidationFailure: see ``build_context``.
        ValueError: ``provider_name`` is not a known provider name.
        agents.ProviderNotConfiguredError: manual provider not usable.
        agents.ProviderResponseError, agents.ProviderError: provider failed.
        sqlalchemy.exc.OperationalError: database unavailable.

    Returns:
        The full API response dict (see ``app.routers.committee`` for the
        documented shape) -- also directly usable as the POST
        /committee/evaluate 200 response body.
    """
    context = build_context(db, backtest_id, risk_evaluation_id)
    strategy_id: uuid.UUID = context["strategy_id"]

    provider = get_provider(provider_name)
    result = run_committee(provider, context)

    decision_ids: list[str] = []
    role_dumps: dict[AgentRole, dict[str, Any]] = {}
    prior_outputs: dict[AgentRole, BaseModel] = {}
    for role, output in result.ordered_outputs():
        payload = build_agent_payload(role, context, prior_outputs)
        row = repositories.create_agent_decision(
            db,
            agent_role=role.value,
            model=result.provider_name,
            input=payload,
            output=output.model_dump(),
            backtest_run_id=backtest_id,
            strategy_id=strategy_id,
        )
        decision_ids.append(str(row.id))
        prior_outputs[role] = output
        role_dumps[role] = output.model_dump()

    final_decision = result.final_decision.model_copy(
        update={
            "audit_refs": result.final_decision.audit_refs.model_copy(
                update={"agent_decision_ids": list(decision_ids)}
            )
        }
    )
    final_output = final_decision.model_dump()
    final_output["override_warning"] = result.override_warning

    final_row = repositories.create_agent_decision(
        db,
        agent_role=AgentRole.CIO.value,
        model=f"{result.provider_name}:final",
        input={
            "cio_raw": role_dumps[AgentRole.CIO],
            "risk_evaluation_approved": bool(context["risk_evaluation"]["approved"]),
        },
        output=final_output,
        backtest_run_id=backtest_id,
        strategy_id=strategy_id,
    )
    decision_ids.append(str(final_row.id))

    return {
        "backtest_id": str(backtest_id),
        "risk_evaluation_id": str(risk_evaluation_id),
        "requested_provider": provider_name,
        "selected_provider": result.provider_name,
        "technical_analyst": role_dumps[AgentRole.TECHNICAL_ANALYST],
        "quant_researcher": role_dumps[AgentRole.QUANT_RESEARCHER],
        "bull_case": role_dumps[AgentRole.BULL],
        "bear_case": role_dumps[AgentRole.BEAR],
        "risk_narrator": role_dumps[AgentRole.RISK_NARRATOR],
        "cio": final_decision.model_dump(),
        "cio_raw": role_dumps[AgentRole.CIO],
        "override_warning": result.override_warning,
        # Documented order: technical_analyst, quant_researcher, bull, bear,
        # risk_narrator, cio_raw (row 6, untrusted), cio final (row 7,
        # authoritative) -- exactly agents.ROLE_ORDER followed by the final
        # decision row.
        "agent_decision_ids": decision_ids,
    }
