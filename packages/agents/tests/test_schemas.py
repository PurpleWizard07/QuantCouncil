"""Tests for the non-CIO strict output schemas and ROLE_OUTPUT_SCHEMAS.

``test_cio_veto.py`` already covers ``AuditRefs``/``CIODecision`` exhaustively
and must stay untouched; this file covers the five schemas added for the
other committee roles plus the CIO's *raw* (untrusted) output schema.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.roles import AgentRole
from agents.schemas import (
    BearCaseOutput,
    BullCaseOutput,
    CIORawOutput,
    QuantResearcherOutput,
    RiskNarratorOutput,
    ROLE_OUTPUT_SCHEMAS,
    TechnicalAnalystOutput,
)


class TestTechnicalAnalystOutput:
    def test_valid_payload(self) -> None:
        out = TechnicalAnalystOutput(
            view="BULLISH",
            confidence=0.8,
            signals=["total_return=0.10"],
            warnings=[],
            summary="Bullish setup.",
        )
        assert out.view == "BULLISH"
        assert out.confidence == 0.8

    def test_invalid_view_literal_raises(self) -> None:
        with pytest.raises(ValidationError):
            TechnicalAnalystOutput(
                view="SIDEWAYS",
                confidence=0.5,
                signals=[],
                warnings=[],
                summary="s",
            )

    @pytest.mark.parametrize("confidence", [-0.01, 1.01])
    def test_confidence_out_of_range_raises(self, confidence: float) -> None:
        with pytest.raises(ValidationError):
            TechnicalAnalystOutput(
                view="NEUTRAL",
                confidence=confidence,
                signals=[],
                warnings=[],
                summary="s",
            )

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            TechnicalAnalystOutput(
                view="NEUTRAL",
                confidence=0.5,
                signals=[],
                warnings=[],
                summary="s",
                extra_field="nope",
            )


class TestQuantResearcherOutput:
    def test_valid_payload(self) -> None:
        out = QuantResearcherOutput(
            strategy_quality="STRONG",
            rule_interpretation="Consistent trend-following edge.",
            strengths=["profit_factor=1.8"],
            weaknesses=[],
            improvement_ideas=[],
            summary="Strong evidence.",
        )
        assert out.strategy_quality == "STRONG"

    def test_invalid_quality_literal_raises(self) -> None:
        with pytest.raises(ValidationError):
            QuantResearcherOutput(
                strategy_quality="GREAT",
                rule_interpretation="x",
                strengths=[],
                weaknesses=[],
                improvement_ideas=[],
                summary="s",
            )

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            QuantResearcherOutput(
                strategy_quality="WEAK",
                rule_interpretation="x",
                strengths=[],
                weaknesses=[],
                improvement_ideas=[],
                summary="s",
                sharpe=1.5,
            )


class TestBullCaseOutput:
    def test_valid_payload(self) -> None:
        out = BullCaseOutput(
            case_strength=0.6,
            arguments=["win_rate=0.55"],
            best_case_scenario="Momentum continues.",
            summary="Reasonable bull case.",
        )
        assert out.case_strength == 0.6

    @pytest.mark.parametrize("case_strength", [-0.5, 1.5])
    def test_case_strength_out_of_range_raises(self, case_strength: float) -> None:
        with pytest.raises(ValidationError):
            BullCaseOutput(
                case_strength=case_strength,
                arguments=[],
                best_case_scenario="s",
                summary="s",
            )

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            BullCaseOutput(
                case_strength=0.5,
                arguments=[],
                best_case_scenario="s",
                summary="s",
                confidence=0.9,
            )


class TestBearCaseOutput:
    def test_valid_payload(self) -> None:
        out = BearCaseOutput(
            case_strength=0.4,
            risks=["max_drawdown=0.2"],
            failure_modes=["losing streak"],
            worst_case_scenario="Drawdown recurs.",
            summary="Reasonable bear case.",
        )
        assert out.case_strength == 0.4

    @pytest.mark.parametrize("case_strength", [-0.1, 1.1])
    def test_case_strength_out_of_range_raises(self, case_strength: float) -> None:
        with pytest.raises(ValidationError):
            BearCaseOutput(
                case_strength=case_strength,
                risks=[],
                failure_modes=[],
                worst_case_scenario="s",
                summary="s",
            )

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            BearCaseOutput(
                case_strength=0.5,
                risks=[],
                failure_modes=[],
                worst_case_scenario="s",
                summary="s",
                arguments=["nope"],
            )


class TestRiskNarratorOutput:
    def test_valid_payload(self) -> None:
        out = RiskNarratorOutput(
            risk_summary="Risk engine decision: REJECTED.",
            failed_rules_explained=["Failed rule: max_drawdown_exceeded"],
            warnings_explained=[],
            plain_english_verdict="The risk engine did not approve this proposal.",
        )
        assert "REJECTED" in out.risk_summary

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            RiskNarratorOutput(
                risk_summary="s",
                failed_rules_explained=[],
                warnings_explained=[],
                plain_english_verdict="v",
                risk_score=50,
            )

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            RiskNarratorOutput(
                failed_rules_explained=[],
                warnings_explained=[],
                plain_english_verdict="v",
            )


class TestCIORawOutput:
    def test_valid_payload(self) -> None:
        out = CIORawOutput(
            decision="PAPER_TRADE",
            summary="s",
            reason="r",
            conditions_to_reconsider=[],
        )
        assert out.decision == "PAPER_TRADE"

    def test_invalid_decision_literal_raises(self) -> None:
        with pytest.raises(ValidationError):
            CIORawOutput(decision="BUY", summary="s", reason="r")

    def test_has_no_approved_by_risk_field(self) -> None:
        """The raw CIO output must never carry approved_by_risk -- extra='forbid'
        rejects it even if a misbehaving provider tries to slip it in."""
        with pytest.raises(ValidationError):
            CIORawOutput(
                decision="NO_TRADE",
                summary="s",
                reason="r",
                approved_by_risk=True,
            )

    def test_conditions_default_to_empty_list(self) -> None:
        out = CIORawOutput(decision="WATCHLIST", summary="s", reason="r")
        assert out.conditions_to_reconsider == []


class TestRoleOutputSchemasCompleteness:
    def test_all_six_roles_present(self) -> None:
        assert set(ROLE_OUTPUT_SCHEMAS.keys()) == set(AgentRole)
        assert len(ROLE_OUTPUT_SCHEMAS) == 6

    def test_cio_maps_to_raw_output_not_final_decision(self) -> None:
        assert ROLE_OUTPUT_SCHEMAS[AgentRole.CIO] is CIORawOutput

    @pytest.mark.parametrize(
        ("role", "schema"),
        [
            (AgentRole.TECHNICAL_ANALYST, TechnicalAnalystOutput),
            (AgentRole.QUANT_RESEARCHER, QuantResearcherOutput),
            (AgentRole.BULL, BullCaseOutput),
            (AgentRole.BEAR, BearCaseOutput),
            (AgentRole.RISK_NARRATOR, RiskNarratorOutput),
            (AgentRole.CIO, CIORawOutput),
        ],
    )
    def test_each_role_maps_to_expected_schema(self, role: AgentRole, schema: type) -> None:
        assert ROLE_OUTPUT_SCHEMAS[role] is schema
