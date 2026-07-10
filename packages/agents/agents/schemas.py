"""Strict output schemas for the AI committee (project contract).

The CIO agent output contract is exactly:

    {
        "decision": "PAPER_TRADE" | "NO_TRADE" | "WATCHLIST",
        "approved_by_risk": true,
        "summary": "",
        "reason": "",
        "conditions_to_reconsider": [],
        "audit_refs": {
            "backtest_id": "",
            "risk_evaluation_id": "",
            "agent_decision_ids": []
        }
    }

THE HARD RULE, codified here as a model validator rather than trusted to
prompt text: if ``approved_by_risk`` is False, the decision must NEVER be
PAPER_TRADE. The risk engine has veto power; a CIO output that violates the
veto fails validation and is rejected before it can reach execution.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.roles import AgentRole


class AuditRefs(BaseModel):
    """References tying a CIO decision back to its deterministic evidence.

    Every CIO decision must be traceable to a concrete backtest run and a
    concrete risk evaluation (no paper trade without both, per the paper
    portfolio rules), plus the individual committee agent decisions that fed
    into it.
    """

    model_config = ConfigDict(extra="forbid")

    backtest_id: str
    risk_evaluation_id: str
    agent_decision_ids: list[str] = Field(default_factory=list)


class CIODecision(BaseModel):
    """Final decision of the CIO agent, bounded by the risk engine's veto.

    Attributes:
        decision: PAPER_TRADE, NO_TRADE, or WATCHLIST.
        approved_by_risk: Verbatim outcome of the deterministic risk engine
            (RiskEvaluationResult.approved). Not an LLM judgment.
        summary: Short human-readable summary of the committee's view.
        reason: The decisive rationale for this decision.
        conditions_to_reconsider: Concrete conditions under which the
            decision should be revisited.
        audit_refs: Links to the backtest, risk evaluation, and agent
            decisions behind this call.
    """

    model_config = ConfigDict(extra="forbid")

    decision: Literal["PAPER_TRADE", "NO_TRADE", "WATCHLIST"]
    approved_by_risk: bool
    summary: str
    reason: str
    conditions_to_reconsider: list[str] = Field(default_factory=list)
    audit_refs: AuditRefs

    @model_validator(mode="after")
    def _enforce_risk_veto(self) -> "CIODecision":
        if not self.approved_by_risk and self.decision == "PAPER_TRADE":
            raise ValueError(
                "Risk veto: risk engine did not approve; CIO decision must be "
                "NO_TRADE or WATCHLIST"
            )
        return self


class TechnicalAnalystOutput(BaseModel):
    """Technical read of the setup, derived from precomputed indicator context.

    The analyst never computes indicators itself; it describes what the
    (deterministic) indicator/signal context already shows.
    """

    model_config = ConfigDict(extra="forbid")

    view: Literal["BULLISH", "BEARISH", "NEUTRAL", "MIXED"]
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str


class QuantResearcherOutput(BaseModel):
    """Interpretation of backtest metrics computed by quant_engine.

    The researcher interprets the numbers it is given; it never recomputes
    them.
    """

    model_config = ConfigDict(extra="forbid")

    strategy_quality: Literal["STRONG", "ACCEPTABLE", "WEAK", "INVALID"]
    rule_interpretation: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvement_ideas: list[str] = Field(default_factory=list)
    summary: str


class BullCaseOutput(BaseModel):
    """The strongest good-faith case FOR the proposed paper trade."""

    model_config = ConfigDict(extra="forbid")

    case_strength: float = Field(ge=0.0, le=1.0)
    arguments: list[str] = Field(default_factory=list)
    best_case_scenario: str
    summary: str


class BearCaseOutput(BaseModel):
    """The strongest good-faith case AGAINST the proposed paper trade."""

    model_config = ConfigDict(extra="forbid")

    case_strength: float = Field(ge=0.0, le=1.0)
    risks: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    worst_case_scenario: str
    summary: str


class RiskNarratorOutput(BaseModel):
    """Plain-language narration of the deterministic risk engine verdict.

    Narration only: the verdict itself (decision/approved/failed_rules/...)
    comes from ``risk_engine`` and is never altered here.
    """

    model_config = ConfigDict(extra="forbid")

    risk_summary: str
    failed_rules_explained: list[str] = Field(default_factory=list)
    warnings_explained: list[str] = Field(default_factory=list)
    plain_english_verdict: str


class CIORawOutput(BaseModel):
    """Raw (untrusted) CIO agent output, before the deterministic veto step.

    Deliberately has NO ``approved_by_risk`` field -- the raw agent is never
    trusted with that flag. Deterministic code in ``agents.committee``
    combines this with the actual risk evaluation to construct the final,
    veto-validated ``CIODecision``.
    """

    model_config = ConfigDict(extra="forbid")

    decision: Literal["PAPER_TRADE", "NO_TRADE", "WATCHLIST"]
    summary: str
    reason: str
    conditions_to_reconsider: list[str] = Field(default_factory=list)


ROLE_OUTPUT_SCHEMAS: dict[AgentRole, type[BaseModel]] = {
    AgentRole.TECHNICAL_ANALYST: TechnicalAnalystOutput,
    AgentRole.QUANT_RESEARCHER: QuantResearcherOutput,
    AgentRole.BULL: BullCaseOutput,
    AgentRole.BEAR: BearCaseOutput,
    AgentRole.RISK_NARRATOR: RiskNarratorOutput,
    AgentRole.CIO: CIORawOutput,
}
"""Maps each committee role to the schema its raw agent output must satisfy.

Note the CIO maps to ``CIORawOutput`` (no ``approved_by_risk``), not to the
veto-validated ``CIODecision`` -- that final object is built by deterministic
code in ``agents.committee.run_committee``, never returned directly by a
provider.
"""
