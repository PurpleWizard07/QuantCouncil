"""THE foundational test of QuantCouncil.

"AI can propose. Math can approve. Risk can veto."

If the risk engine did not approve, a CIO decision of PAPER_TRADE must be
structurally impossible -- rejected by schema validation, not by prompt text.
If this file fails, nothing else in the project matters.
"""

import pytest
from pydantic import ValidationError

from agents.schemas import AuditRefs, CIODecision


def _audit_refs() -> AuditRefs:
    return AuditRefs(
        backtest_id="bt-001",
        risk_evaluation_id="re-001",
        agent_decision_ids=["ad-001", "ad-002"],
    )


def test_risk_veto_blocks_paper_trade() -> None:
    """approved_by_risk=False + PAPER_TRADE must raise. The hard rule."""
    with pytest.raises(ValidationError) as exc_info:
        CIODecision(
            decision="PAPER_TRADE",
            approved_by_risk=False,
            summary="Committee is bullish",
            reason="Strong momentum setup",
            audit_refs=_audit_refs(),
        )
    assert "Risk veto" in str(exc_info.value)


def test_risk_rejected_no_trade_parses() -> None:
    decision = CIODecision(
        decision="NO_TRADE",
        approved_by_risk=False,
        summary="Risk engine rejected the proposal",
        reason="Backtest max drawdown exceeded policy limit",
        audit_refs=_audit_refs(),
    )
    assert decision.decision == "NO_TRADE"
    assert decision.approved_by_risk is False


def test_risk_rejected_watchlist_parses() -> None:
    decision = CIODecision(
        decision="WATCHLIST",
        approved_by_risk=False,
        summary="Interesting setup but risk engine rejected it",
        reason="Too few backtest trades for statistical confidence",
        conditions_to_reconsider=["Re-run backtest once 20+ trades accumulate"],
        audit_refs=_audit_refs(),
    )
    assert decision.decision == "WATCHLIST"
    assert decision.approved_by_risk is False


def test_risk_approved_paper_trade_parses() -> None:
    decision = CIODecision(
        decision="PAPER_TRADE",
        approved_by_risk=True,
        summary="Committee and risk engine aligned",
        reason="All policy rules passed with margin",
        audit_refs=_audit_refs(),
    )
    assert decision.decision == "PAPER_TRADE"
    assert decision.approved_by_risk is True


def test_invalid_decision_literal_raises() -> None:
    with pytest.raises(ValidationError):
        CIODecision(
            decision="REAL_TRADE",
            approved_by_risk=True,
            summary="",
            reason="",
            audit_refs=_audit_refs(),
        )


def test_extra_field_raises() -> None:
    with pytest.raises(ValidationError):
        CIODecision(
            decision="NO_TRADE",
            approved_by_risk=False,
            summary="",
            reason="",
            audit_refs=_audit_refs(),
            broker_order_id="never",
        )


def test_conditions_default_to_empty_list() -> None:
    decision = CIODecision(
        decision="NO_TRADE",
        approved_by_risk=False,
        summary="s",
        reason="r",
        audit_refs=_audit_refs(),
    )
    assert decision.conditions_to_reconsider == []
