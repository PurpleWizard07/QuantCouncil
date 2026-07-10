"""SQLAlchemy 2.0 typed models for the QuantCouncil foundation schema.

Exactly ten tables: assets, ohlcv_daily, strategy_definitions, backtest_runs,
risk_evaluations, agent_decisions, paper_portfolios, paper_orders,
paper_positions, trade_journal.

Design decisions (per project contract, documented as assumptions):
- Status/enum-ish columns are plain String columns constrained by the Python
  StrEnum classes below (no native DB enums) to keep future Alembic
  migrations simple.
- The portable ``sqlalchemy.JSON`` type is used (not the postgres-only JSONB)
  so the models also work against SQLite in tests.
- Prices use Numeric(14, 4); capital/cash/NAV/PnL use Numeric(14, 2); volume
  uses BigInteger.
- Timestamps are timezone-aware UTC generated python-side (default=utcnow) so
  the DDL stays portable across PostgreSQL and SQLite.
- BigInteger primary keys use a SQLite variant (plain Integer) so SQLite's
  rowid autoincrement keeps working in tests.
- Schema is managed via Base.metadata.create_all in the foundation phase;
  Alembic migrations arrive in Phase 2.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# BigInteger that degrades to plain INTEGER on SQLite so autoincrement works.
BigIntPk = BigInteger().with_variant(Integer, "sqlite")


def utcnow() -> dt.datetime:
    """Timezone-aware UTC timestamp (python-side default for portability)."""
    return dt.datetime.now(dt.timezone.utc)


def default_portfolio_settings() -> dict[str, Any]:
    """Paper portfolio risk settings mandated by the project contract."""
    return {
        "max_allocation_per_stock": 0.10,
        "max_risk_per_trade": 0.01,
        "max_open_positions": 10,
        "risk_off_drawdown": 0.08,
        "require_stop_loss": True,
    }


# ---------------------------------------------------------------------------
# StrEnum constants (values stored in plain String columns)
# ---------------------------------------------------------------------------


class StrategyStatus(enum.StrEnum):
    """Strategy lifecycle states (exact strings per contract)."""

    DRAFT = "DRAFT"
    BACKTESTED = "BACKTESTED"
    RISK_EVALUATED = "RISK_EVALUATED"
    RISK_APPROVED = "RISK_APPROVED"
    PAPER_TRADING = "PAPER_TRADING"
    WATCHLIST = "WATCHLIST"
    RETIRED = "RETIRED"


class RiskDecision(enum.StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class CIODecision(enum.StrEnum):
    PAPER_TRADE = "PAPER_TRADE"
    NO_TRADE = "NO_TRADE"
    WATCHLIST = "WATCHLIST"


class OrderSide(enum.StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(enum.StrEnum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class PositionStatus(enum.StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class BacktestStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentRole(enum.StrEnum):
    TECHNICAL_ANALYST = "technical_analyst"
    QUANT_RESEARCHER = "quant_researcher"
    BULL = "bull"
    BEAR = "bear"
    RISK_NARRATOR = "risk_narrator"
    CIO = "cio"


class JournalEntryType(enum.StrEnum):
    """Trade journal entry kinds (convenience constants for entry_type)."""

    DECISION = "DECISION"
    FILL = "FILL"
    NOTE = "NOTE"
    RISK_EVENT = "RISK_EVENT"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class Asset(Base):
    """NIFTY 50 universe instruments (NSE symbols without the .NS suffix)."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    exchange: Mapped[str] = mapped_column(String(16), default="NSE")
    sector: Mapped[Optional[str]] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class OhlcvDaily(Base):
    """Daily OHLCV bars; one row per asset per trading day."""

    __tablename__ = "ohlcv_daily"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_ohlcv_daily_asset_date"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    high: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    low: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    close: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    volume: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(32), default="yfinance")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class StrategyDefinition(Base):
    """Machine-readable strategy definition and lifecycle status."""

    __tablename__ = "strategy_definitions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), default=StrategyStatus.DRAFT.value, index=True
    )
    # Machine-readable rules (entry/exit conditions, indicator params).
    rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # List of universe symbols this strategy trades.
    universe: Mapped[list[str]] = mapped_column(JSON, default=list)
    timeframe: Mapped[str] = mapped_column(String(8), default="1d")
    direction: Mapped[str] = mapped_column(String(16), default="long_only")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class BacktestRun(Base):
    """A deterministic backtest execution; metrics are the source of truth."""

    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategy_definitions.id"), index=True
    )
    start_date: Mapped[dt.date] = mapped_column(Date)
    end_date: Mapped[dt.date] = mapped_column(Date)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Populated on completion: total_return, cagr, max_drawdown, win_rate,
    # avg_win, avg_loss, profit_factor, num_trades, exposure_time, sharpe,
    # best_trade, worst_trade.
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    equity_curve_path: Mapped[Optional[str]] = mapped_column(String(512))
    trades_path: Mapped[Optional[str]] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(
        String(16), default=BacktestStatus.PENDING.value, index=True
    )
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    completed_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True)
    )


class RiskEvaluation(Base):
    """Deterministic risk engine verdict; holds veto power over the CIO."""

    __tablename__ = "risk_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategy_definitions.id"), index=True
    )
    # RiskDecision value: APPROVED | REJECTED | NEEDS_REVIEW.
    decision: Mapped[str] = mapped_column(String(16))
    approved: Mapped[bool] = mapped_column(Boolean)
    risk_score: Mapped[int] = mapped_column(Integer)
    reasons: Mapped[list[Any]] = mapped_column(JSON, default=list)
    failed_rules: Mapped[list[Any]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[Any]] = mapped_column(JSON, default=list)
    policy_version: Mapped[str] = mapped_column(String(16), default="v1")
    # Phase 4: verbatim audit copies of the inputs the evaluation was run
    # against -- the exact metrics dict evaluated, and policy.model_dump()
    # at evaluation time. Nullable: rows written before this column existed
    # (none in practice pre-Phase 4) would have neither.
    metrics_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    policy_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class AgentDecision(Base):
    """Audit log of every LLM agent input/output (agents never calculate)."""

    __tablename__ = "agent_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("strategy_definitions.id"), index=True
    )
    backtest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    # AgentRole value: technical_analyst | quant_researcher | bull | bear |
    # risk_narrator | cio.
    agent_role: Mapped[str] = mapped_column(String(32), index=True)
    model: Mapped[Optional[str]] = mapped_column(String(128))
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class PaperPortfolio(Base):
    """Paper (simulated) portfolio. Starting capital 1,000,000 INR."""

    __tablename__ = "paper_portfolios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    starting_capital: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("1000000")
    )
    cash: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    nav: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    peak_nav: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    # Set when portfolio drawdown breaches risk_off_drawdown (8%).
    risk_off: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=default_portfolio_settings
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class PaperOrder(Base):
    """Simulated order. Fills are simulated at the NEXT day's open price with
    zero slippage in v1 (documented assumption). No real broker connectivity
    exists anywhere in this system."""

    __tablename__ = "paper_orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("paper_portfolios.id"), index=True
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("strategy_definitions.id"), index=True
    )
    backtest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("backtest_runs.id")
    )
    risk_evaluation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("risk_evaluations.id")
    )
    # OrderSide value: BUY | SELL.
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[int] = mapped_column(Integer)
    order_type: Mapped[str] = mapped_column(String(16), default="MARKET")
    status: Mapped[str] = mapped_column(
        String(16), default=OrderStatus.PENDING.value, index=True
    )
    limit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    fill_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    # Stop-loss is REQUIRED by business logic for entry (BUY) orders; the
    # requirement is enforced in the paper-trading engine, not in DDL, so the
    # column stays nullable (exit orders do not carry one).
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    filled_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))


class PaperPosition(Base):
    """Open or closed simulated position in a paper portfolio."""

    __tablename__ = "paper_positions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("paper_portfolios.id"), index=True
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("strategy_definitions.id"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    avg_entry_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    # Every paper position must carry a stop-loss (contract rule).
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    status: Mapped[str] = mapped_column(
        String(16), default=PositionStatus.OPEN.value, index=True
    )
    last_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    unrealized_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    realized_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    opened_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    closed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))


class TradeJournalEntry(Base):
    """Append-only audit journal: decisions, fills, notes, risk events."""

    __tablename__ = "trade_journal"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("paper_portfolios.id"), index=True
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("paper_orders.id")
    )
    position_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("paper_positions.id")
    )
    strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("strategy_definitions.id")
    )
    # JournalEntryType value: DECISION | FILL | NOTE | RISK_EVENT.
    entry_type: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    # Audit refs: backtest_id, risk_evaluation_id, agent_decision_ids.
    refs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
