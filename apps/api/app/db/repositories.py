"""Repository layer: plain persistence functions over a SQLAlchemy Session.

Thin, deliberately boring data access for Phase 3.5. Every function takes an
explicit ``Session`` and performs persistence only -- no business logic
beyond what is required to keep writes idempotent and lifecycle transitions
legal. Callers own the transaction: every function COMMITS its own work (the
functions here are the transaction boundary for the CLIs and routers that
use them).

Portability note: everything here must work identically on PostgreSQL and
SQLite (the test vehicle), so no dialect-specific constructs (e.g. postgres
``ON CONFLICT``) are used -- idempotency is implemented as query-then-insert.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Optional

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentDecision,
    Asset,
    BacktestRun,
    NavSnapshot,
    OhlcvDaily,
    PaperOrder,
    PaperPortfolio,
    PaperPosition,
    PositionStatus,
    RiskEvaluation,
    StrategyDefinition,
    StrategyStatus,
    TradeJournalEntry,
    utcnow,
)

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


def upsert_assets(db: Session, records: list[dict]) -> dict[str, int]:
    """Idempotently upsert asset metadata records.

    Each record must carry ``symbol``, ``name``, ``exchange``, ``sector``
    (the shape returned by ``data_connectors.get_universe()``). Symbols are
    stored in canonical upper case. For each record: insert if the symbol is
    absent; update ``name`` / ``exchange`` / ``sector`` if any changed;
    otherwise leave the row untouched.

    NOTE: ``yfinance_symbol`` is intentionally NOT a column on ``assets`` --
    it is derived on demand via ``data_connectors.to_yfinance_symbol`` so the
    Yahoo suffix rule lives in exactly one place. Records carrying that key
    are accepted; the key is simply ignored here.

    Returns:
        Counts dict: ``{"created": int, "updated": int, "unchanged": int}``.
    """
    created = updated = unchanged = 0
    for record in records:
        symbol = record["symbol"].upper()
        asset = get_asset_by_symbol(db, symbol)
        if asset is None:
            db.add(
                Asset(
                    symbol=symbol,
                    name=record["name"],
                    exchange=record["exchange"],
                    sector=record.get("sector"),
                )
            )
            created += 1
            continue
        changed = False
        for field in ("name", "exchange", "sector"):
            new_value = record.get(field)
            if getattr(asset, field) != new_value:
                setattr(asset, field, new_value)
                changed = True
        if changed:
            updated += 1
        else:
            unchanged += 1
    db.commit()
    return {"created": created, "updated": updated, "unchanged": unchanged}


def get_asset_by_symbol(db: Session, symbol: str) -> Optional[Asset]:
    """Look up an asset by symbol, case-insensitively.

    Symbols are stored canonical-upper by ``upsert_assets``; lookup uppercases
    the input and also matches case-insensitively for robustness against rows
    seeded by other means.
    """
    wanted = symbol.upper()
    return db.execute(
        select(Asset).where(func.upper(Asset.symbol) == wanted)
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# OHLCV bars
# ---------------------------------------------------------------------------


def upsert_ohlcv_bars(
    db: Session, asset_id: int, df: pd.DataFrame, source: str = "yfinance"
) -> dict[str, int]:
    """Idempotently insert daily bars for one asset from a connector frame.

    Portable insert-if-missing: existing dates for ``asset_id`` within the
    frame's date range are queried first and only missing rows are inserted,
    so re-running an ingest never duplicates bars and never relies on
    ``IntegrityError`` for control flow (the ``uq_ohlcv_daily_asset_date``
    constraint remains a safety net, not a mechanism).

    Args:
        db: Session.
        asset_id: FK into ``assets``.
        df: OHLCV frame satisfying the data-connector contract (columns
            ``[date, open, high, low, close, volume]``). Floats go straight
            into the ``Numeric`` columns (the dialect coerces).
        source: Stored in ``ohlcv_daily.source``.

    Returns:
        Counts dict: ``{"inserted": int, "skipped": int}``.
    """
    if len(df) == 0:
        return {"inserted": 0, "skipped": 0}

    dates = pd.to_datetime(df["date"]).dt.date
    lo, hi = dates.min(), dates.max()

    existing = set(
        db.execute(
            select(OhlcvDaily.date).where(
                OhlcvDaily.asset_id == asset_id,
                OhlcvDaily.date >= lo,
                OhlcvDaily.date <= hi,
            )
        ).scalars()
    )

    inserted = skipped = 0
    for row, bar_date in zip(df.itertuples(index=False), dates):
        if bar_date in existing:
            skipped += 1
            continue
        db.add(
            OhlcvDaily(
                asset_id=asset_id,
                date=bar_date,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=int(row.volume),
                source=source,
            )
        )
        inserted += 1
    db.commit()
    return {"inserted": inserted, "skipped": skipped}


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


def create_strategy(db: Session, validated: dict) -> StrategyDefinition:
    """Persist a validated strategy definition as a DRAFT row.

    Args:
        db: Session.
        validated: The OUTPUT of ``quant_engine.strategy.validate_strategy``
            (normalized deep copy). The FULL validated JSON is stored in
            ``rules``; ``name`` / ``description`` / ``universe`` /
            ``timeframe`` / ``direction`` are denormalized into their own
            columns for querying.

    Returns:
        The persisted (committed, refreshed) row.
    """
    row = StrategyDefinition(
        name=validated["name"],
        description=validated.get("description"),
        rules=validated,
        universe=validated["universe"],
        timeframe=validated["timeframe"],
        direction=validated["direction"],
        status=StrategyStatus.DRAFT.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_strategy(db: Session, strategy_id: uuid.UUID) -> Optional[StrategyDefinition]:
    """Load a strategy row by primary key, or None."""
    return db.get(StrategyDefinition, strategy_id)


def list_strategies(db: Session) -> list[StrategyDefinition]:
    """All persisted strategies, oldest first (stable listing order)."""
    return list(
        db.execute(
            select(StrategyDefinition).order_by(StrategyDefinition.created_at)
        ).scalars()
    )


def find_strategy_by_name(db: Session, name: str) -> Optional[StrategyDefinition]:
    """Find a persisted strategy by exact name, or None."""
    return db.execute(
        select(StrategyDefinition).where(StrategyDefinition.name == name)
    ).scalar_one_or_none()


def mark_strategy_backtested(db: Session, strategy: StrategyDefinition) -> None:
    """Advance a strategy DRAFT -> BACKTESTED (never demote later states).

    Lifecycle rule: only a DRAFT strategy is promoted; a strategy already at
    BACKTESTED or any later state (RISK_EVALUATED, RISK_APPROVED, ...) is
    left untouched -- re-running a backtest must never move a strategy
    backwards through its lifecycle. (Editing a strategy resets it to DRAFT;
    that path arrives with strategy editing in a later phase.)
    """
    if strategy.status == StrategyStatus.DRAFT.value:
        strategy.status = StrategyStatus.BACKTESTED.value
        db.commit()


# ---------------------------------------------------------------------------
# Backtest runs
# ---------------------------------------------------------------------------


def create_backtest_run(
    db: Session,
    *,
    strategy_id: uuid.UUID,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    params: dict[str, Any],
    metrics: dict[str, Any],
    equity_curve_path: str,
    trades_path: str,
    status: str,
    completed_at: Optional[dt.datetime] = None,
    run_id: Optional[uuid.UUID] = None,
) -> BacktestRun:
    """Persist a backtest run row (v1: only successful, COMPLETED runs).

    Args:
        run_id: Optional pre-generated UUID -- the API generates it first so
            the artifact directory can be named after the row's id before the
            row exists. Defaults to a fresh UUID.
        completed_at: Defaults to now (UTC) -- pass explicitly if the caller
            recorded completion earlier.

    Returns:
        The persisted (committed, refreshed) row.
    """
    row = BacktestRun(
        id=run_id if run_id is not None else uuid.uuid4(),
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        params=params,
        metrics=metrics,
        equity_curve_path=equity_curve_path,
        trades_path=trades_path,
        status=status,
        completed_at=completed_at if completed_at is not None else utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_backtest_run(db: Session, run_id: uuid.UUID) -> Optional[BacktestRun]:
    """Load a backtest run by primary key, or None."""
    return db.get(BacktestRun, run_id)


def list_backtest_runs(db: Session, limit: int = 20) -> list[BacktestRun]:
    """Persisted backtest runs, newest first, capped at ``limit`` rows."""
    return list(
        db.execute(
            select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit)
        ).scalars()
    )


# ---------------------------------------------------------------------------
# Risk evaluations
# ---------------------------------------------------------------------------


def create_risk_evaluation(
    db: Session,
    *,
    backtest_run_id: uuid.UUID,
    strategy_id: uuid.UUID,
    decision: str,
    approved: bool,
    risk_score: int,
    policy_version: str,
    reasons: list[Any],
    failed_rules: list[Any],
    warnings: list[Any],
    metrics_snapshot: Optional[dict[str, Any]],
    policy_snapshot: Optional[dict[str, Any]],
) -> RiskEvaluation:
    """Persist a risk evaluation row.

    Args:
        backtest_run_id: FK into ``backtest_runs`` -- NOT NULL, so callers
            without a persisted backtest run must not call this function
            (the inline-payload risk evaluation path in the API stays
            unpersisted for exactly this reason).
        strategy_id: FK into ``strategy_definitions``.
        decision, approved, risk_score, policy_version, reasons,
            failed_rules, warnings, metrics_snapshot, policy_snapshot:
            the full ``RiskEvaluationResult`` contract fields.

    Returns:
        The persisted (committed, refreshed) row.
    """
    row = RiskEvaluation(
        backtest_run_id=backtest_run_id,
        strategy_id=strategy_id,
        decision=decision,
        approved=approved,
        risk_score=risk_score,
        policy_version=policy_version,
        reasons=reasons,
        failed_rules=failed_rules,
        warnings=warnings,
        metrics_snapshot=metrics_snapshot,
        policy_snapshot=policy_snapshot,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_risk_evaluation(db: Session, id: uuid.UUID) -> Optional[RiskEvaluation]:
    """Load a risk evaluation by primary key, or None."""
    return db.get(RiskEvaluation, id)


def list_risk_evaluations(db: Session, limit: int = 20) -> list[RiskEvaluation]:
    """Persisted risk evaluations, newest first, capped at ``limit`` rows."""
    return list(
        db.execute(
            select(RiskEvaluation)
            .order_by(RiskEvaluation.created_at.desc())
            .limit(limit)
        ).scalars()
    )


def get_latest_risk_evaluation_for_backtest(
    db: Session, backtest_run_id: uuid.UUID
) -> Optional[RiskEvaluation]:
    """Most recent risk evaluation for a backtest run, or None.

    "Most recent" is ``created_at`` descending -- re-evaluating a backtest
    (e.g. under a newer policy version) writes a new row rather than
    mutating history, so this is the read side of that append-only pattern.
    """
    return db.execute(
        select(RiskEvaluation)
        .where(RiskEvaluation.backtest_run_id == backtest_run_id)
        .order_by(RiskEvaluation.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Agent decisions (Phase 6: AI committee)
# ---------------------------------------------------------------------------


def create_agent_decision(
    db: Session,
    *,
    agent_role: str,
    model: Optional[str],
    input: dict[str, Any],
    output: dict[str, Any],
    backtest_run_id: Optional[uuid.UUID] = None,
    strategy_id: Optional[uuid.UUID] = None,
) -> AgentDecision:
    """Persist one committee agent decision row (audit log; never mutated).

    Args:
        agent_role: An ``agents.AgentRole`` value (technical_analyst |
            quant_researcher | bull | bear | risk_narrator | cio).
        model: Free-form provider/model identifier (e.g. "mock",
            "anthropic:final"). Nullable to match the column.
        input: JSON-safe payload the agent actually received.
        output: JSON-safe validated output (or the final decision dump, for
            the authoritative seventh "cio" row -- see
            ``app.services.committee_service``).
        backtest_run_id: FK into ``backtest_runs``, nullable.
        strategy_id: FK into ``strategy_definitions``, nullable.

    Returns:
        The persisted (committed, refreshed) row.
    """
    row = AgentDecision(
        strategy_id=strategy_id,
        backtest_run_id=backtest_run_id,
        agent_role=agent_role,
        model=model,
        input=input,
        output=output,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_decisions_for_backtest(
    db: Session, backtest_run_id: uuid.UUID
) -> list[AgentDecision]:
    """Persisted committee agent decisions for a backtest run, newest first."""
    return list(
        db.execute(
            select(AgentDecision)
            .where(AgentDecision.backtest_run_id == backtest_run_id)
            .order_by(AgentDecision.created_at.desc())
        ).scalars()
    )


# ---------------------------------------------------------------------------
# Paper portfolios (Phase 5)
# ---------------------------------------------------------------------------


def create_paper_portfolio(
    db: Session, *, name: str, starting_capital: float
) -> PaperPortfolio:
    """Persist a new paper portfolio: cash = nav = peak_nav = starting_capital.

    ``settings`` and ``risk_off`` are left to the model's column defaults
    (``default_portfolio_settings()`` / ``False``) so this function stays a
    thin insert, matching the rest of this module's style.
    """
    capital = round(float(starting_capital), 2)
    row = PaperPortfolio(
        name=name,
        starting_capital=capital,
        cash=capital,
        nav=capital,
        peak_nav=capital,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_paper_portfolio(db: Session, portfolio_id: uuid.UUID) -> Optional[PaperPortfolio]:
    """Load a paper portfolio by primary key, or None."""
    return db.get(PaperPortfolio, portfolio_id)


def list_paper_portfolios(db: Session) -> list[PaperPortfolio]:
    """All persisted paper portfolios, oldest first (stable listing order)."""
    return list(
        db.execute(
            select(PaperPortfolio).order_by(PaperPortfolio.created_at)
        ).scalars()
    )


# ---------------------------------------------------------------------------
# Paper positions
# ---------------------------------------------------------------------------


def get_open_position(
    db: Session, portfolio_id: uuid.UUID, asset_id: int
) -> Optional[PaperPosition]:
    """The single OPEN position for (portfolio, asset), or None.

    At most one OPEN position per (portfolio, asset) pair is a paper-engine
    invariant (add-ons update the existing row rather than creating a
    second); this lookup assumes that invariant holds.
    """
    return db.execute(
        select(PaperPosition).where(
            PaperPosition.portfolio_id == portfolio_id,
            PaperPosition.asset_id == asset_id,
            PaperPosition.status == PositionStatus.OPEN.value,
        )
    ).scalar_one_or_none()


def get_paper_position(db: Session, position_id: uuid.UUID) -> Optional[PaperPosition]:
    """Load a paper position by primary key, or None."""
    return db.get(PaperPosition, position_id)


def list_positions(
    db: Session,
    portfolio_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
) -> list[PaperPosition]:
    """Positions, optionally filtered by portfolio and/or status.

    Ordered oldest-opened first (stable listing order); callers wanting
    newest-first (e.g. a UI feed) sort client-side.
    """
    stmt = select(PaperPosition)
    if portfolio_id is not None:
        stmt = stmt.where(PaperPosition.portfolio_id == portfolio_id)
    if status is not None:
        stmt = stmt.where(PaperPosition.status == status)
    stmt = stmt.order_by(PaperPosition.opened_at)
    return list(db.execute(stmt).scalars())


def create_paper_position(
    db: Session,
    *,
    portfolio_id: uuid.UUID,
    asset_id: int,
    quantity: int,
    avg_entry_price: float,
    stop_loss: float,
    strategy_id: Optional[uuid.UUID] = None,
) -> PaperPosition:
    """Persist a new OPEN position (a fresh entry, not an add-on)."""
    row = PaperPosition(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        strategy_id=strategy_id,
        quantity=quantity,
        avg_entry_price=avg_entry_price,
        stop_loss=stop_loss,
        status=PositionStatus.OPEN.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Paper orders
# ---------------------------------------------------------------------------


def create_paper_order(
    db: Session,
    *,
    portfolio_id: uuid.UUID,
    asset_id: int,
    side: str,
    quantity: int,
    status: str,
    order_type: str = "MARKET",
    limit_price: Optional[float] = None,
    fill_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    strategy_id: Optional[uuid.UUID] = None,
    backtest_run_id: Optional[uuid.UUID] = None,
    risk_evaluation_id: Optional[uuid.UUID] = None,
    filled_at: Optional[dt.datetime] = None,
) -> PaperOrder:
    """Persist a paper order row (any terminal ``status``: FILLED/REJECTED).

    Low-level: callers (the paper engine) decide the status and every field;
    this function performs persistence only, matching the rest of this
    module's split between "decide" (service) and "persist" (repository).
    """
    row = PaperOrder(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        strategy_id=strategy_id,
        backtest_run_id=backtest_run_id,
        risk_evaluation_id=risk_evaluation_id,
        side=side,
        quantity=quantity,
        order_type=order_type,
        status=status,
        limit_price=limit_price,
        fill_price=fill_price,
        stop_loss=stop_loss,
        filled_at=filled_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_paper_order(db: Session, order_id: uuid.UUID) -> Optional[PaperOrder]:
    """Load a paper order by primary key, or None."""
    return db.get(PaperOrder, order_id)


def list_paper_orders(
    db: Session, portfolio_id: Optional[uuid.UUID] = None
) -> list[PaperOrder]:
    """Paper orders, optionally filtered by portfolio, newest first."""
    stmt = select(PaperOrder)
    if portfolio_id is not None:
        stmt = stmt.where(PaperOrder.portfolio_id == portfolio_id)
    stmt = stmt.order_by(PaperOrder.created_at.desc())
    return list(db.execute(stmt).scalars())


# ---------------------------------------------------------------------------
# Trade journal
# ---------------------------------------------------------------------------


def create_journal_entry(
    db: Session,
    *,
    portfolio_id: uuid.UUID,
    entry_type: str,
    title: str,
    body: str,
    order_id: Optional[uuid.UUID] = None,
    position_id: Optional[uuid.UUID] = None,
    strategy_id: Optional[uuid.UUID] = None,
    refs: Optional[dict[str, Any]] = None,
) -> TradeJournalEntry:
    """Append a trade journal entry (the journal is append-only; no updates)."""
    row = TradeJournalEntry(
        portfolio_id=portfolio_id,
        order_id=order_id,
        position_id=position_id,
        strategy_id=strategy_id,
        entry_type=entry_type,
        title=title,
        body=body,
        refs=refs if refs is not None else {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_journal_entry(
    db: Session, entry_id: uuid.UUID
) -> Optional[TradeJournalEntry]:
    """Load a trade journal entry by primary key, or None."""
    return db.get(TradeJournalEntry, entry_id)


def list_journal_entries(
    db: Session, portfolio_id: Optional[uuid.UUID] = None
) -> list[TradeJournalEntry]:
    """Journal entries, optionally filtered by portfolio, newest first."""
    stmt = select(TradeJournalEntry)
    if portfolio_id is not None:
        stmt = stmt.where(TradeJournalEntry.portfolio_id == portfolio_id)
    stmt = stmt.order_by(TradeJournalEntry.created_at.desc())
    return list(db.execute(stmt).scalars())


# ---------------------------------------------------------------------------
# NAV snapshots (Phase 9: Daily Ops Loop)
# ---------------------------------------------------------------------------


def upsert_nav_snapshot(
    db: Session,
    *,
    portfolio_id: uuid.UUID,
    date: dt.date,
    nav: float,
    cash: float,
    drawdown: Optional[float],
    risk_off: bool,
) -> NavSnapshot:
    """Insert or update the ``(portfolio_id, date)`` NAV snapshot row.

    Portable query-then-insert/update (no dialect-specific upsert, matching
    this module's convention -- see the module docstring): a second call for
    the same portfolio/date (e.g. running the daily cycle twice in one day)
    updates the existing row's nav/cash/drawdown/risk_off in place rather
    than creating a duplicate (``uq_nav_snapshots_portfolio_date`` is the
    safety net, not the mechanism).
    """
    existing = db.execute(
        select(NavSnapshot).where(
            NavSnapshot.portfolio_id == portfolio_id, NavSnapshot.date == date
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.nav = nav
        existing.cash = cash
        existing.drawdown = drawdown
        existing.risk_off = risk_off
        db.commit()
        db.refresh(existing)
        return existing

    row = NavSnapshot(
        portfolio_id=portfolio_id,
        date=date,
        nav=nav,
        cash=cash,
        drawdown=drawdown,
        risk_off=risk_off,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_nav_snapshots(
    db: Session, portfolio_id: uuid.UUID, limit: int = 365
) -> list[NavSnapshot]:
    """A portfolio's NAV history, oldest -> newest, capped at ``limit`` rows.

    Chart-friendly ordering: takes the newest ``limit`` rows (so a capped
    query still returns the *most recent* history, not the oldest) and then
    sorts that page ascending by date for direct use as a chart's x-axis.
    """
    newest_first = list(
        db.execute(
            select(NavSnapshot)
            .where(NavSnapshot.portfolio_id == portfolio_id)
            .order_by(NavSnapshot.date.desc())
            .limit(limit)
        ).scalars()
    )
    return list(reversed(newest_first))
