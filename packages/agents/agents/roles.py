"""Agent roles in the QuantCouncil AI committee."""

from __future__ import annotations

from enum import StrEnum


class AgentRole(StrEnum):
    """The six committee roles.

    TECHNICAL_ANALYST: Reads indicator/signal context and describes setups.
    QUANT_RESEARCHER: Interprets backtest metrics (never recomputes them).
    BULL: Argues the strongest good-faith case for the trade.
    BEAR: Argues the strongest good-faith case against the trade.
    RISK_NARRATOR: Explains the deterministic risk engine's verdict in plain
        language (narration only; the verdict itself is not an LLM output).
    CIO: Makes the final call -- PAPER_TRADE, NO_TRADE, or WATCHLIST --
        strictly bounded by the risk engine's veto.
    """

    # Values are the persisted strings in agent_decisions.agent_role and must
    # stay in sync with apps/api/app/db/models.py::AgentRole.
    TECHNICAL_ANALYST = "technical_analyst"
    QUANT_RESEARCHER = "quant_researcher"
    BULL = "bull"
    BEAR = "bear"
    RISK_NARRATOR = "risk_narrator"
    CIO = "cio"
