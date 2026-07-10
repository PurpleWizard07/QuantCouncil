"""The QuantCouncil AI committee: pure orchestration over an injected provider.

All agent outputs are strict JSON validated by the Pydantic models in
``agents.schemas`` (and stored as agent_decisions rows by the API layer). The
CIO veto is enforced by the ``CIODecision`` model validator, NOT by prompt
text -- an LLM response that tries to paper-trade against a risk rejection
fails validation and never reaches execution. This module adds a SECOND,
independent enforcement of the same rule: the raw CIO output is deliberately
never trusted with ``approved_by_risk``, and deterministic code here computes
the final decision and overrides a vetoed PAPER_TRADE before the (still
validator-guarded) ``CIODecision`` is ever constructed.

Agents receive deterministic context (indicator values, backtest metrics,
risk evaluation results) and produce reasoning, narratives, and proposals.
They never compute numbers themselves -- every metric an agent cites must
come verbatim from the provided input.

This module has no database and no HTTP client of its own: it is pure
orchestration over whatever ``AgentProvider`` the caller injects (see
``agents.providers``). The API layer is responsible for resolving a provider,
supplying context, and persisting the result.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from agents.providers.base import AgentProvider
from agents.roles import AgentRole
from agents.schemas import (
    AuditRefs,
    BearCaseOutput,
    BullCaseOutput,
    CIODecision,
    CIORawOutput,
    QuantResearcherOutput,
    RiskNarratorOutput,
    ROLE_OUTPUT_SCHEMAS,
    TechnicalAnalystOutput,
)

ROLE_ORDER: tuple[AgentRole, ...] = (
    AgentRole.TECHNICAL_ANALYST,
    AgentRole.QUANT_RESEARCHER,
    AgentRole.BULL,
    AgentRole.BEAR,
    AgentRole.RISK_NARRATOR,
    AgentRole.CIO,
)
"""The fixed order the six committee roles run in. Later roles see earlier
roles' summaries (see ``build_agent_payload``); this order is also the order
results are reported in on ``CommitteeResult``."""

_PROMPT_PREAMBLE = (
    "You are the {role} on QuantCouncil's AI committee for a "
    "PAPER-TRADING-ONLY research lab. Never invent numbers: every metric you "
    "cite must come verbatim from the provided input. Respond ONLY with JSON "
    "matching the required schema."
)

SYSTEM_PROMPTS: dict[AgentRole, str] = {
    AgentRole.TECHNICAL_ANALYST: (
        _PROMPT_PREAMBLE.format(role="Technical Analyst")
        + " Describe the technical setup implied by the indicator/signal "
        "context and backtest metrics you are given. Do not recommend a "
        "position size or a final trading decision -- that belongs to the "
        "CIO. Focus on what the price/indicator evidence shows."
    ),
    AgentRole.QUANT_RESEARCHER: (
        _PROMPT_PREAMBLE.format(role="Quant Researcher")
        + " Interpret the backtest metrics you are given -- you must NEVER "
        "recompute or restate a metric with a different value than the one "
        "provided. Judge whether the strategy's historical evidence is "
        "statistically meaningful (sample size, consistency) and explain "
        "what the numbers do and do not support."
    ),
    AgentRole.BULL: (
        _PROMPT_PREAMBLE.format(role="Bull")
        + " Argue the strongest good-faith case FOR taking this paper trade, "
        "using only the evidence provided (metrics, prior committee "
        "summaries). Do not dismiss real weaknesses; make the best honest "
        "case, not a dishonest one."
    ),
    AgentRole.BEAR: (
        _PROMPT_PREAMBLE.format(role="Bear")
        + " Argue the strongest good-faith case AGAINST taking this paper "
        "trade, using only the evidence provided (metrics, prior committee "
        "summaries). Do not dismiss real strengths; make the best honest "
        "case, not a dishonest one."
    ),
    AgentRole.RISK_NARRATOR: (
        _PROMPT_PREAMBLE.format(role="Risk Narrator")
        + " Explain the deterministic risk engine's verdict (decision, "
        "failed rules, warnings) in plain English for a human reader. You "
        "narrate the verdict; you never alter it, soften it, or second-guess "
        "it -- the risk_evaluation you are given is final."
    ),
    AgentRole.CIO: (
        _PROMPT_PREAMBLE.format(role="Chief Investment Officer (CIO)")
        + " Make the final committee call: PAPER_TRADE, NO_TRADE, or "
        "WATCHLIST. You know the risk engine's verdict binds you -- if the "
        "risk evaluation was not approved, a PAPER_TRADE recommendation from "
        "you will be structurally overridden to NO_TRADE regardless of what "
        "you say, so do not fight the risk verdict; instead explain your "
        "view and, if you disagree, use conditions_to_reconsider."
    ),
}
"""One system prompt per committee role. Every prompt states the shared
ground rules (paper-trading-only, never invent numbers, JSON-only) plus
role-specific guidance."""

_PAYLOAD_CONTEXT_KEYS: tuple[str, ...] = (
    "strategy",
    "metrics",
    "risk_evaluation",
    "trades_summary",
    "symbol",
    "dates",
)


def _summary_of(role: AgentRole, output: BaseModel) -> str:
    """Extract the one-line takeaway a later agent should see for ``role``.

    Every schema has a ``summary`` field except the risk narrator, whose
    plain-English verdict plays the same role.
    """
    if role == AgentRole.RISK_NARRATOR:
        assert isinstance(output, RiskNarratorOutput)
        return output.plain_english_verdict
    return getattr(output, "summary")


def build_agent_payload(
    role: AgentRole,
    context: dict,
    prior_outputs: dict[AgentRole, BaseModel] | None = None,
) -> dict:
    """Build the JSON-safe payload a provider receives for ``role``.

    Args:
        role: The committee role about to run.
        context: Plain dict with keys ``strategy`` (name + rules summary),
            ``metrics`` (the backtest scalar metrics), ``risk_evaluation``
            (decision/approved/risk_score/failed_rules/warnings/
            policy_version), ``trades_summary`` (count + a few sample
            trades), ``symbol``, and ``dates``. Extra keys (e.g.
            ``backtest_id``, ``risk_evaluation_id``) are ignored here -- they
            are used only for audit refs in ``run_committee``.
        prior_outputs: Validated outputs from roles that already ran this
            committee, in run order. ``None`` or empty for the first role.

    Returns:
        A JSON-safe dict: the relevant context fields, plus
        ``committee_so_far`` (each prior role's summary / plain-English
        verdict) once at least one prior role has run.
    """
    payload: dict = {key: context.get(key) for key in _PAYLOAD_CONTEXT_KEYS}
    if prior_outputs:
        payload["committee_so_far"] = {
            prior_role.value: _summary_of(prior_role, output)
            for prior_role, output in prior_outputs.items()
        }
    return payload


@dataclass
class CommitteeResult:
    """The full output of one committee run.

    Attributes:
        technical_analyst: Validated ``TechnicalAnalystOutput``.
        quant_researcher: Validated ``QuantResearcherOutput``.
        bull: Validated ``BullCaseOutput``.
        bear: Validated ``BearCaseOutput``.
        risk_narrator: Validated ``RiskNarratorOutput``.
        cio_raw: Validated ``CIORawOutput`` -- the CIO's untrusted raw call,
            BEFORE the deterministic veto step (never exposed without going
            through it).
        final_decision: The veto-checked ``CIODecision`` actually usable
            downstream. Structurally cannot be PAPER_TRADE when
            ``approved_by_risk`` is False.
        override_warning: ``None`` if the CIO's raw decision was used as-is;
            otherwise the exact string explaining that the raw PAPER_TRADE
            was overridden because risk rejected the backtest.
        provider_name: ``provider.name`` of whatever ``AgentProvider`` ran
            this committee (e.g. "mock", "anthropic").
    """

    technical_analyst: TechnicalAnalystOutput
    quant_researcher: QuantResearcherOutput
    bull: BullCaseOutput
    bear: BearCaseOutput
    risk_narrator: RiskNarratorOutput
    cio_raw: CIORawOutput
    final_decision: CIODecision
    override_warning: str | None
    provider_name: str

    def ordered_outputs(self) -> list[tuple[AgentRole, BaseModel]]:
        """Return the six raw agent outputs as ``(role, output)`` pairs, in
        the fixed committee run order (``ROLE_ORDER``)."""
        by_role: dict[AgentRole, BaseModel] = {
            AgentRole.TECHNICAL_ANALYST: self.technical_analyst,
            AgentRole.QUANT_RESEARCHER: self.quant_researcher,
            AgentRole.BULL: self.bull,
            AgentRole.BEAR: self.bear,
            AgentRole.RISK_NARRATOR: self.risk_narrator,
            AgentRole.CIO: self.cio_raw,
        }
        return [(role, by_role[role]) for role in ROLE_ORDER]


OVERRIDE_WARNING = (
    "CIO raw PAPER_TRADE overridden because risk engine rejected the backtest."
)
"""Exact text of ``CommitteeResult.override_warning`` when the deterministic
veto step overrides the CIO's raw decision."""


def run_committee(provider: AgentProvider, context: dict) -> CommitteeResult:
    """Run the six committee roles in order, then apply the deterministic veto.

    Args:
        provider: Any ``AgentProvider`` (mock or real). Injected, never
            constructed here -- this function has no opinion on provider
            selection.
        context: Plain dict; see ``build_agent_payload`` for the fields used
            to build each role's payload, plus ``backtest_id`` and
            ``risk_evaluation_id`` (used only for ``AuditRefs``) and
            ``risk_evaluation["approved"]`` (used only for the veto step,
            read verbatim -- never from any agent output).

    Returns:
        A ``CommitteeResult`` with every role's validated output, the raw CIO
        call, the final veto-checked ``CIODecision``, and an override warning
        if the veto fired.

    THE DETERMINISTIC VETO STEP happens entirely in this function, in plain
    code, after every agent has already run:

        approved_by_risk = bool(context["risk_evaluation"]["approved"])
        if not approved_by_risk and cio_raw.decision == "PAPER_TRADE":
            final = "NO_TRADE"  # override; risk engine has veto power

    The resulting ``CIODecision`` is then built with the deterministic
    ``approved_by_risk`` flag, and its own model validator enforces the same
    invariant a second, independent time.
    """
    prior_outputs: dict[AgentRole, BaseModel] = {}
    for role in ROLE_ORDER:
        schema = ROLE_OUTPUT_SCHEMAS[role]
        payload = build_agent_payload(role, context, prior_outputs)
        output = provider.generate(role, SYSTEM_PROMPTS[role], payload, schema)
        prior_outputs[role] = output

    cio_raw = prior_outputs[AgentRole.CIO]
    assert isinstance(cio_raw, CIORawOutput)

    approved_by_risk = bool(context["risk_evaluation"]["approved"])
    final = cio_raw.decision
    override_warning: str | None = None
    if not approved_by_risk and cio_raw.decision == "PAPER_TRADE":
        final = "NO_TRADE"
        override_warning = OVERRIDE_WARNING

    final_decision = CIODecision(
        decision=final,
        approved_by_risk=approved_by_risk,
        summary=cio_raw.summary,
        reason=cio_raw.reason,
        conditions_to_reconsider=cio_raw.conditions_to_reconsider,
        audit_refs=AuditRefs(
            backtest_id=context["backtest_id"],
            risk_evaluation_id=context["risk_evaluation_id"],
            agent_decision_ids=[],
        ),
    )

    return CommitteeResult(
        technical_analyst=prior_outputs[AgentRole.TECHNICAL_ANALYST],
        quant_researcher=prior_outputs[AgentRole.QUANT_RESEARCHER],
        bull=prior_outputs[AgentRole.BULL],
        bear=prior_outputs[AgentRole.BEAR],
        risk_narrator=prior_outputs[AgentRole.RISK_NARRATOR],
        cio_raw=cio_raw,
        final_decision=final_decision,
        override_warning=override_warning,
        provider_name=provider.name,
    )
