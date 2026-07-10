"""QuantCouncil AI committee agents.

LLM agents may reason, summarize, debate, and propose -- they must NEVER
calculate, never fake results, and never override risk. Every number an agent
cites must trace back to deterministic output from quant_engine or
risk_engine (via audit refs). The risk engine's veto is enforced structurally
by the schema validators in this package, not by prompt text.

Public API surface for callers (e.g. the API layer):
    Schemas: ``AuditRefs``, ``CIODecision`` (the veto-validated final
        decision), ``CIORawOutput`` (untrusted raw CIO call),
        ``TechnicalAnalystOutput``, ``QuantResearcherOutput``,
        ``BullCaseOutput``, ``BearCaseOutput``, ``RiskNarratorOutput``,
        ``ROLE_OUTPUT_SCHEMAS``.
    Roles: ``AgentRole``.
    Providers: ``get_provider``, ``resolve_auto``, ``PROVIDER_CLASSES``,
        ``AUTO_PRIORITY``, ``AgentProvider``, ``ProviderError``,
        ``ProviderNotConfiguredError``, ``ProviderResponseError``.
    Committee orchestration: ``run_committee``, ``build_agent_payload``,
        ``SYSTEM_PROMPTS``, ``CommitteeResult``, ``ROLE_ORDER``.

The offline ``MockAgentProvider`` is always configured, so every feature in
this package -- and every test in this repo -- works with zero LLM
credentials and zero network access.
"""

from __future__ import annotations

from agents.committee import (
    ROLE_ORDER,
    SYSTEM_PROMPTS,
    CommitteeResult,
    build_agent_payload,
    run_committee,
)
from agents.providers import (
    AUTO_PRIORITY,
    PROVIDER_CLASSES,
    AgentProvider,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
    get_provider,
    resolve_auto,
)
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

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # roles
    "AgentRole",
    # schemas
    "AuditRefs",
    "CIODecision",
    "CIORawOutput",
    "TechnicalAnalystOutput",
    "QuantResearcherOutput",
    "BullCaseOutput",
    "BearCaseOutput",
    "RiskNarratorOutput",
    "ROLE_OUTPUT_SCHEMAS",
    # providers
    "AgentProvider",
    "ProviderError",
    "ProviderNotConfiguredError",
    "ProviderResponseError",
    "get_provider",
    "resolve_auto",
    "PROVIDER_CLASSES",
    "AUTO_PRIORITY",
    # committee
    "run_committee",
    "build_agent_payload",
    "SYSTEM_PROMPTS",
    "CommitteeResult",
    "ROLE_ORDER",
]
