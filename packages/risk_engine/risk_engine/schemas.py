"""Strict output schema for risk evaluations (Phase 4 project contract).

The risk engine's output contract is exactly:

    {
        "decision": "APPROVED" | "REJECTED" | "NEEDS_REVIEW",
        "approved": true,
        "risk_score": 100,
        "policy_version": "1.0.0",
        "reasons": [],
        "failed_rules": [],
        "warnings": [],
        "metrics_snapshot": {},
        "policy_snapshot": {}
    }

The ``approved`` flag is redundant with ``decision`` by design (it is the
single boolean downstream consumers key off), so consistency between the two
is enforced by a model validator: ``approved`` must be True if and only if
``decision == "APPROVED"``.

``risk_score`` convention (Phase 4, INVERTED from the old provisional
docs/risk-policy.md convention of "0 is safest"): higher is safer. 100 is the
safest possible score; 0 is the riskiest. See ``risk_engine.engine`` for the
exact scoring formula.

Auditability is further enforced by a second validator: a ``REJECTED``
decision must always name at least one failed rule (``failed_rules``
non-empty), and an ``APPROVED`` decision must never carry a failed rule.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskEvaluationResult(BaseModel):
    """Result of a deterministic risk evaluation.

    Attributes:
        decision: One of APPROVED, REJECTED, NEEDS_REVIEW.
        approved: True if and only if ``decision == "APPROVED"`` (enforced).
        risk_score: Integer risk score in [0, 100]; HIGHER means SAFER
            (100 = safest, 0 = riskiest -- Phase 4 convention).
        policy_version: The ``RiskPolicy.policy_version`` this evaluation was
            produced under (auditability: reproduce any historical verdict
            against the policy that produced it).
        reasons: Human-readable explanations for the decision.
        failed_rules: Identifiers of hard-gate policy rules that failed.
        warnings: Non-blocking concerns worth surfacing.
        metrics_snapshot: Verbatim copy of the ``metrics`` dict the engine was
            evaluated against (JSON-safe: floats/None only, no NaN).
        policy_snapshot: ``policy.model_dump()`` at evaluation time.
    """

    model_config = ConfigDict(extra="forbid")

    decision: Literal["APPROVED", "REJECTED", "NEEDS_REVIEW"]
    approved: bool
    risk_score: int = Field(ge=0, le=100)
    policy_version: str
    reasons: list[str] = Field(default_factory=list)
    failed_rules: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metrics_snapshot: dict = Field(default_factory=dict)
    policy_snapshot: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _approved_must_match_decision(self) -> "RiskEvaluationResult":
        expected = self.decision == "APPROVED"
        if self.approved != expected:
            raise ValueError(
                "Inconsistent risk evaluation: approved must be True if and only if "
                f"decision == 'APPROVED' (got decision={self.decision!r}, "
                f"approved={self.approved!r})"
            )
        return self

    @model_validator(mode="after")
    def _failed_rules_must_match_decision(self) -> "RiskEvaluationResult":
        if self.decision == "REJECTED" and len(self.failed_rules) < 1:
            raise ValueError(
                "Inconsistent risk evaluation: decision == 'REJECTED' requires at "
                "least one entry in failed_rules (a rejection must always name a "
                "reason, for auditability)."
            )
        if self.decision == "APPROVED" and len(self.failed_rules) != 0:
            raise ValueError(
                "Inconsistent risk evaluation: decision == 'APPROVED' requires "
                f"failed_rules == [] (got {self.failed_rules!r})."
            )
        return self
