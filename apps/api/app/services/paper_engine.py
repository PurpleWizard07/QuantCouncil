"""The paper portfolio engine (Phase 5): deterministic, local, paper-only.

Implements the allowed execution actions from
``docs/paper-trading-design.md`` -- ``create_paper_order``,
``simulate_order_fill``, ``mark_to_market``, ``update_paper_positions``,
``calculate_paper_nav``, ``write_trade_journal_entry`` -- as one cohesive
pipeline per order rather than six separate public entry points, because a
paper order in this engine is validated, (maybe) rejected, filled, and
journaled inside a single request/response cycle. No code path here ever
places, modifies, or cancels a REAL order, connects to a broker, or touches
real money -- see the "No Real Orders -- Ever" section of the design doc.

DELIBERATE PHASE 5 DEVIATION FROM THE DESIGN DOC (explicit project-owner
instruction): the design doc's v1 fill model is "next trading day's open,
PENDING until then." Phase 5 fills are IMMEDIATE instead -- a BUY or SELL
that clears validation is filled synchronously, in the same call, at a
*reference price* (either the caller-supplied ``price_reference`` or the
latest available close fetched through the injected ``latest_close_fn``).
Orders therefore only ever reach terminal states here: FILLED or REJECTED
(never PENDING). This keeps the engine simple and fully deterministic for
local, offline testing; the design doc is updated separately to describe
this as the Phase 5 fill model. CANCELLED is unused in Phase 5 (nothing is
ever left PENDING to cancel).

Money handling convention (applied consistently everywhere below):
    - All arithmetic is done in python ``float``.
    - Values written to Numeric(14, 2) columns (cash, nav, peak_nav, pnl,
      costs, proceeds) are rounded to 2 decimals with ``_round2`` before
      the write.
    - Values written to Numeric(14, 4) columns (prices: fill_price,
      limit_price, stop_loss, avg_entry_price, last_price) are rounded to 4
      decimals with ``_round4`` before the write.
    - Values read back off the ORM (which hands back ``decimal.Decimal`` for
      Numeric columns) are converted with ``float(...)`` before any
      arithmetic -- Decimal/float mixing is never allowed.

Slippage/transaction-cost constants: ``SLIPPAGE_PCT`` and
``TRANSACTION_COST_PCT`` below are defined as their own module constants
(0.0005 == 0.05% each), matching ``quant_engine.backtest.BacktestConfig``'s
defaults so paper-trading fills stay comparable to backtest fills. This
module deliberately does NOT import ``quant_engine`` for this -- the paper
engine has to run with zero optional dependencies on the backtester, so the
two values are documented as "kept in sync by convention", not shared code.

NAV convention: NAV = cash + sum over OPEN positions of
(quantity * mark), where "mark" is ``last_price`` if a mark-to-market has
run for that position, else ``avg_entry_price`` for a position that has
never been marked (so a just-filled BUY immediately contributes its own
cost basis to NAV, before any mark-to-market call). This matches the design
doc's NAV definition (quantity * last close) with a documented bootstrap
rule for the pre-first-mark case.

Risk-off convention: risk-off is a one-way latch set by ``mark_to_market``
when drawdown >= ``settings["risk_off_drawdown"]``. It NEVER auto-clears
(there is no reset endpoint in Phase 5 -- a human reviews the journal and
would clear it via a direct DB update or a later-phase endpoint). Risk-off
blocks new BUY entries only; SELL orders (risk-reducing) are always allowed,
including while risk-off is active.

PHASE 9 ADDITION -- the Daily Ops Loop: ``run_daily_cycle`` closes the paper-
fund loop that Phase 5 left open (stops were stored but never triggered, NAV
history was never recorded, and risk-off could never be reset). It composes
three existing/new pieces in a fixed order per call -- a stop-loss sweep (see
``run_daily_cycle``'s own docstring for the exact v1 fill semantics), the
existing ``mark_to_market``, and a NAV snapshot upsert -- and ``reset_risk_off``
finally gives risk-off the human-in-the-loop reset the Phase 5 docstring
above says does not yet exist.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.db import repositories
from app.db.models import (
    Asset,
    BacktestRun,
    JournalEntryType,
    NavSnapshot,
    OrderSide,
    OrderStatus,
    PaperOrder,
    PaperPortfolio,
    PaperPosition,
    PositionStatus,
    RiskEvaluation,
    TradeJournalEntry,
    default_portfolio_settings,
    utcnow,
)

# Matches quant_engine.backtest.BacktestConfig's defaults (see module
# docstring) -- NOT imported from there, kept decoupled on purpose.
SLIPPAGE_PCT = 0.0005
TRANSACTION_COST_PCT = 0.0005

DEFAULT_PORTFOLIO_NAME = "Default Paper Fund"
DEFAULT_STARTING_CAPITAL = 1_000_000.0


# ---------------------------------------------------------------------------
# Exceptions -- the router maps each of these to an HTTP status code.
# ---------------------------------------------------------------------------


class PaperEngineError(Exception):
    """Base class for every typed error this module raises.

    ``order_id`` is populated when a REJECTED ``PaperOrder`` row (plus its
    RISK_EVENT journal entry) was persisted BEFORE this exception was
    raised (the veto, the portfolio-limit gates, insufficient cash, and
    insufficient position all persist an audit trail first) so the router
    can surface "which order got rejected" in the HTTP error detail. Pure
    input errors (bad quantity, missing thesis, unknown ids, ...) never set
    it -- no row exists to reference.
    """

    def __init__(self, message: str, *, order_id: Optional[uuid.UUID] = None) -> None:
        super().__init__(message)
        self.order_id = order_id


class NotFoundError(PaperEngineError):
    """A referenced entity (portfolio, asset, backtest, risk evaluation) is missing."""


class ValidationFailure(PaperEngineError):
    """A pure input error: malformed/missing fields, no row is ever created."""


class RiskVetoError(PaperEngineError):
    """The persisted risk evaluation is not APPROVED; the BUY is vetoed."""


class LimitRejection(PaperEngineError):
    """A portfolio rule (risk-off, open-position count, allocation, per-trade risk) failed."""


class InsufficientCash(PaperEngineError):
    """The order's total debit exceeds available cash."""


class InsufficientPosition(PaperEngineError):
    """A SELL requests more quantity than the position currently holds."""


LatestCloseFn = Callable[[str], float]


# ---------------------------------------------------------------------------
# Money-handling helpers (see module docstring for the convention).
# ---------------------------------------------------------------------------


def _round2(value: float) -> float:
    return round(float(value), 2)


def _round4(value: float) -> float:
    return round(float(value), 4)


# ---------------------------------------------------------------------------
# JSON-safe serializers -- shared by the service's own return values and by
# the router's list/get endpoints (Decimals -> float, UUIDs -> str,
# datetimes -> ISO strings).
# ---------------------------------------------------------------------------


def portfolio_dict(portfolio: PaperPortfolio) -> dict[str, Any]:
    """A paper portfolio as a JSON-safe API record.

    ``risk_mode`` is derived from ``risk_off`` (never stored directly):
    "RISK_OFF" when true, "NORMAL" otherwise. ``current_cash``/``current_nav``
    are the API's names for the ``cash``/``nav`` columns.
    """
    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "starting_capital": float(portfolio.starting_capital),
        "current_cash": float(portfolio.cash),
        "current_nav": float(portfolio.nav),
        "peak_nav": float(portfolio.peak_nav) if portfolio.peak_nav is not None else None,
        "risk_mode": "RISK_OFF" if portfolio.risk_off else "NORMAL",
        "settings": portfolio.settings,
        "created_at": portfolio.created_at.isoformat() if portfolio.created_at else None,
        "updated_at": portfolio.updated_at.isoformat() if portfolio.updated_at else None,
    }


def order_dict(order: PaperOrder) -> dict[str, Any]:
    """A paper order as a JSON-safe API record."""
    return {
        "id": str(order.id),
        "portfolio_id": str(order.portfolio_id),
        "asset_id": order.asset_id,
        "strategy_id": str(order.strategy_id) if order.strategy_id else None,
        "backtest_run_id": str(order.backtest_run_id) if order.backtest_run_id else None,
        "risk_evaluation_id": (
            str(order.risk_evaluation_id) if order.risk_evaluation_id else None
        ),
        "side": order.side,
        "quantity": order.quantity,
        "order_type": order.order_type,
        "status": order.status,
        "limit_price": float(order.limit_price) if order.limit_price is not None else None,
        "fill_price": float(order.fill_price) if order.fill_price is not None else None,
        "stop_loss": float(order.stop_loss) if order.stop_loss is not None else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "filled_at": order.filled_at.isoformat() if order.filled_at else None,
    }


def position_dict(position: PaperPosition) -> dict[str, Any]:
    """A paper position as a JSON-safe API record."""
    return {
        "id": str(position.id),
        "portfolio_id": str(position.portfolio_id),
        "asset_id": position.asset_id,
        "strategy_id": str(position.strategy_id) if position.strategy_id else None,
        "quantity": position.quantity,
        "avg_entry_price": float(position.avg_entry_price),
        "stop_loss": float(position.stop_loss),
        "status": position.status,
        "last_price": float(position.last_price) if position.last_price is not None else None,
        "unrealized_pnl": (
            float(position.unrealized_pnl) if position.unrealized_pnl is not None else None
        ),
        "realized_pnl": (
            float(position.realized_pnl) if position.realized_pnl is not None else None
        ),
        "opened_at": position.opened_at.isoformat() if position.opened_at else None,
        "closed_at": position.closed_at.isoformat() if position.closed_at else None,
    }


def nav_snapshot_dict(snapshot: NavSnapshot) -> dict[str, Any]:
    """A NAV snapshot as a JSON-safe API record (date -> ISO string)."""
    return {
        "date": snapshot.date.isoformat(),
        "nav": float(snapshot.nav),
        "cash": float(snapshot.cash),
        "drawdown": float(snapshot.drawdown) if snapshot.drawdown is not None else None,
        "risk_off": snapshot.risk_off,
    }


def journal_dict(entry: TradeJournalEntry) -> dict[str, Any]:
    """A trade journal entry as a JSON-safe API record."""
    return {
        "id": str(entry.id),
        "portfolio_id": str(entry.portfolio_id),
        "order_id": str(entry.order_id) if entry.order_id else None,
        "position_id": str(entry.position_id) if entry.position_id else None,
        "strategy_id": str(entry.strategy_id) if entry.strategy_id else None,
        "entry_type": entry.entry_type,
        "title": entry.title,
        "body": entry.body,
        "refs": entry.refs,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


# ---------------------------------------------------------------------------
# Portfolio creation
# ---------------------------------------------------------------------------


def create_portfolio(
    db: Session,
    name: str = DEFAULT_PORTFOLIO_NAME,
    starting_capital: float = DEFAULT_STARTING_CAPITAL,
) -> PaperPortfolio:
    """Create a new paper portfolio: cash = nav = peak_nav = starting_capital."""
    return repositories.create_paper_portfolio(
        db, name=name, starting_capital=starting_capital
    )


# ---------------------------------------------------------------------------
# NAV
# ---------------------------------------------------------------------------


def _calculate_paper_nav(db: Session, portfolio: PaperPortfolio) -> float:
    """NAV = cash + sum over OPEN positions of (qty * mark).

    "mark" is ``last_price`` if the position has been marked at least once,
    else ``avg_entry_price`` (see module docstring's NAV convention). Reads
    ``portfolio.cash`` off the in-memory object, so callers must set the new
    cash value BEFORE calling this (fills always update cash first).
    """
    total = float(portfolio.cash)
    positions = repositories.list_positions(
        db, portfolio_id=portfolio.id, status=PositionStatus.OPEN.value
    )
    for position in positions:
        mark = (
            float(position.last_price)
            if position.last_price is not None
            else float(position.avg_entry_price)
        )
        total += position.quantity * mark
    return total


def _apply_nav_update(db: Session, portfolio: PaperPortfolio, *, commit: bool = True) -> None:
    """Recompute NAV from the portfolio's current (already-updated) cash and
    update ``peak_nav`` (running max). Does not touch risk_off (only
    ``mark_to_market`` decides risk-off transitions).

    ``commit`` defaults to True (commit and refresh immediately). A fill
    pipeline that needs this update to land atomically with sibling writes
    (order/position/journal) passes ``commit=False``: this only
    ``flush()``-es (so the new NAV is visible to any later query in the same
    transaction) and the caller commits once, later, for the whole batch.
    """
    nav = _calculate_paper_nav(db, portfolio)
    portfolio.nav = _round2(nav)
    peak = float(portfolio.peak_nav) if portfolio.peak_nav is not None else portfolio.nav
    portfolio.peak_nav = _round2(max(peak, portfolio.nav))
    if commit:
        db.commit()
        db.refresh(portfolio)
    else:
        db.flush()


# ---------------------------------------------------------------------------
# create_paper_order -- the full BUY/SELL pipeline
# ---------------------------------------------------------------------------


def create_paper_order(
    db: Session,
    *,
    portfolio_id: uuid.UUID,
    symbol: str,
    side: str,
    quantity: int,
    thesis: Optional[str],
    backtest_id: Optional[uuid.UUID] = None,
    risk_evaluation_id: Optional[uuid.UUID] = None,
    price_reference: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    exit_reason: Optional[str] = None,
    latest_close_fn: LatestCloseFn,
) -> dict[str, Any]:
    """Validate, (maybe) reject, fill, and journal one paper order.

    ``portfolio_id`` / ``backtest_id`` / ``risk_evaluation_id`` are already-
    parsed UUIDs (or None) -- malformed-UUID-string handling is the router's
    job (400, same pattern as every other router), so this function never
    sees a raw string for an id field. ``latest_close_fn`` is only called
    when ``price_reference`` is omitted; it is injected so this module never
    imports the OHLCV connector (see the router for the real wiring).

    Raises:
        NotFoundError: unknown portfolio/asset/backtest/risk_evaluation, or
            a BUY missing its required backtest_id/risk_evaluation_id.
        ValidationFailure: bad quantity/price/thesis/stop_loss, or a risk
            evaluation that does not belong to the given backtest.
        RiskVetoError: the persisted risk evaluation is not APPROVED (BUY).
        LimitRejection: risk-off / max-open-positions / allocation / per-
            trade-risk breach (BUY).
        InsufficientCash: total debit exceeds available cash (BUY).
        InsufficientPosition: SELL quantity exceeds the held quantity.
    """
    side_upper = (side or "").strip().upper()
    if side_upper not in (OrderSide.BUY.value, OrderSide.SELL.value):
        raise ValidationFailure(f"side must be 'BUY' or 'SELL' (got {side!r}).")

    portfolio = repositories.get_paper_portfolio(db, portfolio_id)
    if portfolio is None:
        raise NotFoundError(f"No paper portfolio with id {portfolio_id!s}.")

    asset = repositories.get_asset_by_symbol(db, symbol)
    if asset is None:
        raise NotFoundError(
            f"No asset with symbol {symbol!r}. Seed the NIFTY 50 universe "
            "(run scripts/seed_assets.py) or insert an Asset row before "
            "placing paper orders against it."
        )

    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        raise ValidationFailure(
            "quantity must be a whole number >= 1 (whole shares only; no "
            "fractional shares, no shorting)."
        )
    if price_reference is not None and price_reference <= 0:
        raise ValidationFailure("price_reference must be > 0 when supplied.")

    if side_upper == OrderSide.BUY.value:
        return _execute_buy(
            db,
            portfolio=portfolio,
            asset=asset,
            quantity=quantity,
            thesis=thesis,
            backtest_id=backtest_id,
            risk_evaluation_id=risk_evaluation_id,
            price_reference=price_reference,
            stop_loss_price=stop_loss_price,
            latest_close_fn=latest_close_fn,
        )

    return _execute_sell(
        db,
        portfolio=portfolio,
        asset=asset,
        quantity=quantity,
        thesis=thesis,
        exit_reason=exit_reason,
        backtest_id=backtest_id,
        risk_evaluation_id=risk_evaluation_id,
        price_reference=price_reference,
        latest_close_fn=latest_close_fn,
    )


def _persist_buy_rejection(
    db: Session,
    *,
    portfolio: PaperPortfolio,
    asset: Asset,
    quantity: int,
    stop_loss_price: Optional[float],
    price_reference: Optional[float],
    backtest: Optional[BacktestRun],
    risk_eval: Optional[RiskEvaluation],
    thesis: Optional[str],
    reason: str,
    exception_cls: type[PaperEngineError],
) -> None:
    """Persist a REJECTED PaperOrder + RISK_EVENT journal entry, then raise.

    Shared by every BUY business-rejection point (the veto and every
    portfolio-limit / cash gate) so the audit trail is written identically
    everywhere -- steps 8/10/11 of the design's validation order, per the
    module docstring's "order_id" contract. Pure input errors (steps 1-7)
    never call this.

    The REJECTED order and its RISK_EVENT journal entry are flushed (not
    committed) individually and then committed together in one
    ``db.commit()`` -- so a mid-write crash or DB error can never leave a
    REJECTED order persisted with no journal entry documenting why.
    """
    order = repositories.create_paper_order(
        db,
        portfolio_id=portfolio.id,
        asset_id=asset.id,
        strategy_id=backtest.strategy_id if backtest is not None else None,
        backtest_run_id=backtest.id if backtest is not None else None,
        risk_evaluation_id=risk_eval.id if risk_eval is not None else None,
        side=OrderSide.BUY.value,
        quantity=quantity,
        status=OrderStatus.REJECTED.value,
        limit_price=price_reference,
        stop_loss=stop_loss_price,
        commit=False,
    )
    repositories.create_journal_entry(
        db,
        portfolio_id=portfolio.id,
        order_id=order.id,
        strategy_id=order.strategy_id,
        entry_type=JournalEntryType.RISK_EVENT.value,
        title=f"BUY rejected: {quantity} {asset.symbol}",
        body=reason,
        refs={
            "paper_order_id": str(order.id),
            "backtest_id": str(backtest.id) if backtest is not None else None,
            "risk_evaluation_id": str(risk_eval.id) if risk_eval is not None else None,
            "symbol": asset.symbol,
            "thesis": thesis,
            "rejection_reason": reason,
        },
        commit=False,
    )
    db.commit()
    db.refresh(order)
    raise exception_cls(reason, order_id=order.id)


def _execute_buy(
    db: Session,
    *,
    portfolio: PaperPortfolio,
    asset: Asset,
    quantity: int,
    thesis: Optional[str],
    backtest_id: Optional[uuid.UUID],
    risk_evaluation_id: Optional[uuid.UUID],
    price_reference: Optional[float],
    stop_loss_price: Optional[float],
    latest_close_fn: LatestCloseFn,
) -> dict[str, Any]:
    """BUY validation order per docs/paper-trading-design.md + the brief:

    1-2. portfolio/asset already resolved by the caller.
    3.   quantity/price_reference already validated by the caller.
    4.   thesis non-empty; stop_loss_price required, > 0, and (when
         price_reference is known already) < price_reference.
    5.   backtest_id required; must load a persisted BacktestRun.
    6.   risk_evaluation_id required; must load a persisted RiskEvaluation.
    7.   the evaluation must belong to the backtest.
    8.   THE VETO: approved is not True -> reject (reads ONLY the persisted
         row -- nothing in the request can override it).
    9.   resolve the fill price (and, if price_reference was omitted, only
         now do we know "the reference price" to validate stop_loss against).
    10.  portfolio-limit gates: risk-off, max open positions, allocation,
         per-trade risk.
    11.  insufficient cash.
    12.  fill: order FILLED, position created/added-to, cash/NAV updated,
         FILL journal entry written.
    """
    if not thesis or not str(thesis).strip():
        raise ValidationFailure("thesis is required for a BUY order.")
    if stop_loss_price is None:
        raise ValidationFailure(
            "stop_loss_price is required for a BUY order (every paper "
            "position must carry a stop-loss)."
        )
    if stop_loss_price <= 0:
        raise ValidationFailure("stop_loss_price must be > 0.")
    if price_reference is not None and stop_loss_price >= price_reference:
        raise ValidationFailure(
            f"stop_loss_price ({stop_loss_price}) must be below the "
            f"reference price ({price_reference})."
        )

    if backtest_id is None:
        raise NotFoundError(
            "backtest_id is required for a BUY order (no paper trade "
            "without a persisted backtest run)."
        )
    backtest = repositories.get_backtest_run(db, backtest_id)
    if backtest is None:
        raise NotFoundError(f"No persisted backtest run with id {backtest_id!s}.")

    if risk_evaluation_id is None:
        raise NotFoundError(
            "risk_evaluation_id is required for a BUY order (no paper "
            "trade without a persisted risk evaluation)."
        )
    risk_eval = repositories.get_risk_evaluation(db, risk_evaluation_id)
    if risk_eval is None:
        raise NotFoundError(
            f"No persisted risk evaluation with id {risk_evaluation_id!s}."
        )

    if risk_eval.backtest_run_id != backtest.id:
        raise ValidationFailure(
            f"Risk evaluation {risk_evaluation_id!s} was evaluated against "
            f"backtest {risk_eval.backtest_run_id!s}, not the supplied "
            f"backtest_id {backtest_id!s}; a risk evaluation may only "
            "approve paper trades for its own backtest."
        )

    # -- 8. THE VETO -- reads ONLY the persisted evaluation row. Nothing in
    # the request body can override a REJECTED/NEEDS_REVIEW decision.
    if risk_eval.approved is not True:
        reason = (
            f"risk evaluation {risk_eval.id!s} decision={risk_eval.decision} "
            f"(risk_score={risk_eval.risk_score}) is not APPROVED; both "
            "REJECTED and NEEDS_REVIEW decisions block paper BUY orders. "
            "The persisted evaluation is the sole source of truth and "
            "cannot be overridden by this request."
        )
        _persist_buy_rejection(
            db,
            portfolio=portfolio,
            asset=asset,
            quantity=quantity,
            stop_loss_price=stop_loss_price,
            price_reference=price_reference,
            backtest=backtest,
            risk_eval=risk_eval,
            thesis=thesis,
            reason=reason,
            exception_cls=RiskVetoError,
        )

    # -- 9. resolve the fill price --
    ref = price_reference if price_reference is not None else latest_close_fn(asset.symbol)
    if ref is None or ref <= 0:
        raise ValidationFailure("resolved reference price must be > 0.")
    if stop_loss_price >= ref:
        # Only reachable when price_reference was omitted (the
        # price_reference-known case was already checked above).
        raise ValidationFailure(
            f"stop_loss_price ({stop_loss_price}) must be below the "
            f"resolved reference price ({ref})."
        )
    fill = ref * (1 + SLIPPAGE_PCT)
    cost = quantity * fill * TRANSACTION_COST_PCT
    total_debit = quantity * fill + cost

    settings = portfolio.settings or default_portfolio_settings()
    nav = float(portfolio.nav)
    existing_position = repositories.get_open_position(db, portfolio.id, asset.id)

    # -- 10. portfolio-limit gates --
    if portfolio.risk_off:
        _persist_buy_rejection(
            db,
            portfolio=portfolio,
            asset=asset,
            quantity=quantity,
            stop_loss_price=stop_loss_price,
            price_reference=price_reference,
            backtest=backtest,
            risk_eval=risk_eval,
            thesis=thesis,
            reason=(
                "risk-off mode is active on this portfolio; new entries "
                "are blocked (exits remain allowed)."
            ),
            exception_cls=LimitRejection,
        )

    if existing_position is None:
        open_count = len(
            repositories.list_positions(
                db, portfolio_id=portfolio.id, status=PositionStatus.OPEN.value
            )
        )
        max_open = settings["max_open_positions"]
        if open_count >= max_open:
            _persist_buy_rejection(
                db,
                portfolio=portfolio,
                asset=asset,
                quantity=quantity,
                stop_loss_price=stop_loss_price,
                price_reference=price_reference,
                backtest=backtest,
                risk_eval=risk_eval,
                thesis=thesis,
                reason=(
                    f"max open positions ({max_open}) reached; cannot open "
                    f"a new position in {asset.symbol} (add-ons to an "
                    "existing open position are still allowed)."
                ),
                exception_cls=LimitRejection,
            )

    existing_cost_basis = (
        existing_position.quantity * float(existing_position.avg_entry_price)
        if existing_position is not None
        else 0.0
    )
    allocation = existing_cost_basis + quantity * fill
    max_allocation = settings["max_allocation_per_stock"] * nav
    if allocation > max_allocation:
        _persist_buy_rejection(
            db,
            portfolio=portfolio,
            asset=asset,
            quantity=quantity,
            stop_loss_price=stop_loss_price,
            price_reference=price_reference,
            backtest=backtest,
            risk_eval=risk_eval,
            thesis=thesis,
            reason=(
                f"allocation breach: {asset.symbol} cost basis would be "
                f"{allocation:.2f}, exceeding "
                f"{settings['max_allocation_per_stock'] * 100:.0f}% of NAV "
                f"({max_allocation:.2f})."
            ),
            exception_cls=LimitRejection,
        )

    trade_risk = (fill - stop_loss_price) * quantity
    max_risk = settings["max_risk_per_trade"] * nav
    if trade_risk > max_risk:
        _persist_buy_rejection(
            db,
            portfolio=portfolio,
            asset=asset,
            quantity=quantity,
            stop_loss_price=stop_loss_price,
            price_reference=price_reference,
            backtest=backtest,
            risk_eval=risk_eval,
            thesis=thesis,
            reason=(
                f"per-trade risk breach: (fill {fill:.4f} - stop "
                f"{stop_loss_price:.4f}) * {quantity} = {trade_risk:.2f}, "
                f"exceeding {settings['max_risk_per_trade'] * 100:.0f}% of "
                f"NAV ({max_risk:.2f})."
            ),
            exception_cls=LimitRejection,
        )

    # -- 11. insufficient cash --
    cash = float(portfolio.cash)
    if total_debit > cash:
        _persist_buy_rejection(
            db,
            portfolio=portfolio,
            asset=asset,
            quantity=quantity,
            stop_loss_price=stop_loss_price,
            price_reference=price_reference,
            backtest=backtest,
            risk_eval=risk_eval,
            thesis=thesis,
            reason=(
                f"insufficient cash: total debit {total_debit:.2f} exceeds "
                f"available cash {cash:.2f}."
            ),
            exception_cls=InsufficientCash,
        )

    # -- 12. fill -- everything below is ONE atomic transaction: the order,
    # the position (new or add-on), the cash/NAV update, and the FILL
    # journal entry are each flushed (not committed) individually and then
    # committed together in a single db.commit() at the end (mirrors
    # mark_to_market's atomic commit-once pattern). A crash or DB error
    # partway through this block therefore can never leave a FILLED order
    # persisted without its matching position/cash update/journal entry --
    # either the whole fill lands, or none of it does.
    order = repositories.create_paper_order(
        db,
        portfolio_id=portfolio.id,
        asset_id=asset.id,
        strategy_id=backtest.strategy_id,
        backtest_run_id=backtest.id,
        risk_evaluation_id=risk_eval.id,
        side=OrderSide.BUY.value,
        quantity=quantity,
        status=OrderStatus.FILLED.value,
        limit_price=price_reference,
        fill_price=_round4(fill),
        stop_loss=_round4(stop_loss_price),
        filled_at=utcnow(),
        commit=False,
    )

    if existing_position is not None:
        old_qty = existing_position.quantity
        old_avg = float(existing_position.avg_entry_price)
        new_qty = old_qty + quantity
        new_avg = (old_qty * old_avg + quantity * fill) / new_qty
        existing_position.quantity = new_qty
        existing_position.avg_entry_price = _round4(new_avg)
        # Documented design decision: an add-on's stop-loss REPLACES the
        # position's stop (the newest order's risk plan governs the whole
        # position going forward) rather than being averaged or ignored.
        existing_position.stop_loss = _round4(stop_loss_price)
        if existing_position.strategy_id is None:
            existing_position.strategy_id = backtest.strategy_id
        # Flush (not commit) so the updated quantity/avg_entry_price is
        # visible to _apply_nav_update's own query below, without ending
        # this transaction early.
        db.flush()
        position = existing_position
    else:
        position = repositories.create_paper_position(
            db,
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            strategy_id=backtest.strategy_id,
            quantity=quantity,
            avg_entry_price=_round4(fill),
            stop_loss=_round4(stop_loss_price),
            commit=False,
        )

    portfolio.cash = _round2(cash - total_debit)
    _apply_nav_update(db, portfolio, commit=False)

    journal = repositories.create_journal_entry(
        db,
        portfolio_id=portfolio.id,
        order_id=order.id,
        position_id=position.id,
        strategy_id=backtest.strategy_id,
        entry_type=JournalEntryType.FILL.value,
        title=f"BUY FILLED: {quantity} {asset.symbol} @ {fill:.4f}",
        body=(
            f"Filled BUY of {quantity} {asset.symbol} @ {fill:.4f} "
            f"(reference {ref:.4f}, slippage {SLIPPAGE_PCT * 100:.2f}%); "
            f"cost {cost:.2f}; thesis: {thesis}"
        ),
        refs={
            "paper_order_id": str(order.id),
            "position_id": str(position.id),
            "backtest_id": str(backtest.id),
            "risk_evaluation_id": str(risk_eval.id),
            "symbol": asset.symbol,
            "thesis": thesis,
            "risk_summary": f"{risk_eval.decision} (score {risk_eval.risk_score})",
            "side": "BUY",
            "quantity": quantity,
            "fill_price": _round4(fill),
            "cost": _round2(cost),
        },
        commit=False,
    )

    db.commit()
    db.refresh(order)
    db.refresh(position)
    db.refresh(portfolio)
    db.refresh(journal)

    return {
        "order": order_dict(order),
        "position": position_dict(position),
        "portfolio": portfolio_dict(portfolio),
        "journal_entry_id": str(journal.id),
        "fill": {
            "reference_price": _round4(ref),
            "fill_price": _round4(fill),
            "slippage_pct": SLIPPAGE_PCT,
            "transaction_cost_pct": TRANSACTION_COST_PCT,
            "cost": _round2(cost),
            "total_debit": _round2(total_debit),
        },
    }


def _execute_sell(
    db: Session,
    *,
    portfolio: PaperPortfolio,
    asset: Asset,
    quantity: int,
    thesis: Optional[str],
    exit_reason: Optional[str],
    backtest_id: Optional[uuid.UUID],
    risk_evaluation_id: Optional[uuid.UUID],
    price_reference: Optional[float],
    latest_close_fn: LatestCloseFn,
) -> dict[str, Any]:
    """SELL: risk-reducing, so NO risk-evaluation approval check and NO
    risk-off block -- exits are ALWAYS allowed, including while risk-off is
    active (the design doc's risk-off semantics: it must never trap the
    portfolio in a losing position).

    ``backtest_id``/``risk_evaluation_id`` are optional here and are NOT
    validated against persisted rows (documented design decision: a SELL is
    closing out a decision that was already audited at BUY time; the
    ``position_id`` on the FILL journal entry is the audit linkage back to
    that BUY, not a fresh backtest/risk check). Whatever the caller supplies
    is simply stored on the order row as-is.
    """
    reason_text = exit_reason if exit_reason and str(exit_reason).strip() else thesis
    if not reason_text or not str(reason_text).strip():
        raise ValidationFailure(
            "thesis or exit_reason is required for a SELL order (at least one)."
        )

    position = repositories.get_open_position(db, portfolio.id, asset.id)
    held = position.quantity if position is not None else 0
    if position is None or held < quantity:
        reason = f"cannot sell {quantity}; holding {held}."
        # Flushed (not committed) individually, then committed together --
        # same atomic-audit-trail reasoning as _persist_buy_rejection.
        order = repositories.create_paper_order(
            db,
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            strategy_id=position.strategy_id if position is not None else None,
            backtest_run_id=backtest_id,
            risk_evaluation_id=risk_evaluation_id,
            side=OrderSide.SELL.value,
            quantity=quantity,
            status=OrderStatus.REJECTED.value,
            limit_price=price_reference,
            commit=False,
        )
        repositories.create_journal_entry(
            db,
            portfolio_id=portfolio.id,
            order_id=order.id,
            position_id=position.id if position is not None else None,
            strategy_id=order.strategy_id,
            entry_type=JournalEntryType.RISK_EVENT.value,
            title=f"SELL rejected: {quantity} {asset.symbol}",
            body=reason,
            refs={
                "paper_order_id": str(order.id),
                "position_id": str(position.id) if position is not None else None,
                "symbol": asset.symbol,
                "thesis": thesis,
                "exit_reason": exit_reason,
                "rejection_reason": reason,
            },
            commit=False,
        )
        db.commit()
        db.refresh(order)
        raise InsufficientPosition(reason, order_id=order.id)

    ref = price_reference if price_reference is not None else latest_close_fn(asset.symbol)
    if ref is None or ref <= 0:
        raise ValidationFailure("resolved reference price must be > 0.")
    fill = ref * (1 - SLIPPAGE_PCT)
    proceeds = quantity * fill
    cost = proceeds * TRANSACTION_COST_PCT

    # Everything below is ONE atomic transaction -- same reasoning as
    # _execute_buy's step 12: each write is flushed (not committed)
    # individually and all of them are committed together in a single
    # db.commit() at the end, so a mid-fill crash or DB error can never
    # leave a FILLED SELL order persisted without its matching
    # position/cash update/journal entry.
    order = repositories.create_paper_order(
        db,
        portfolio_id=portfolio.id,
        asset_id=asset.id,
        strategy_id=position.strategy_id,
        backtest_run_id=backtest_id,
        risk_evaluation_id=risk_evaluation_id,
        side=OrderSide.SELL.value,
        quantity=quantity,
        status=OrderStatus.FILLED.value,
        limit_price=price_reference,
        fill_price=_round4(fill),
        filled_at=utcnow(),
        commit=False,
    )

    avg_entry = float(position.avg_entry_price)
    # Sell-side cost only: entry-side transaction cost was already deducted
    # from cash at BUY time (see _execute_buy's total_debit), so charging it
    # again here would double-count it in realized P&L.
    realized_this_sale = (fill - avg_entry) * quantity - cost
    position.realized_pnl = _round2(float(position.realized_pnl or 0.0) + realized_this_sale)
    position.quantity = held - quantity
    position_closed = position.quantity == 0
    if position_closed:
        position.status = PositionStatus.CLOSED.value
        position.closed_at = utcnow()
        position.unrealized_pnl = None
    # Flush (not commit) so the updated quantity/status is visible to
    # _apply_nav_update's own query below (a CLOSED position must drop out
    # of the OPEN-positions NAV sum), without ending this transaction early.
    db.flush()

    portfolio.cash = _round2(float(portfolio.cash) + proceeds - cost)
    _apply_nav_update(db, portfolio, commit=False)

    journal = repositories.create_journal_entry(
        db,
        portfolio_id=portfolio.id,
        order_id=order.id,
        position_id=position.id,
        strategy_id=position.strategy_id,
        entry_type=JournalEntryType.FILL.value,
        title=f"SELL FILLED: {quantity} {asset.symbol} @ {fill:.4f}",
        body=(
            f"Filled SELL of {quantity} {asset.symbol} @ {fill:.4f} "
            f"(reference {ref:.4f}, slippage {SLIPPAGE_PCT * 100:.2f}%); "
            f"exit_reason: {reason_text}; realized P&L this sale: "
            f"{realized_this_sale:.2f}"
            + ("; position closed" if position_closed else "; position remains open")
        ),
        refs={
            "paper_order_id": str(order.id),
            "position_id": str(position.id),
            "backtest_id": str(backtest_id) if backtest_id is not None else None,
            "risk_evaluation_id": (
                str(risk_evaluation_id) if risk_evaluation_id is not None else None
            ),
            "symbol": asset.symbol,
            "thesis": thesis,
            "exit_reason": reason_text,
            "side": "SELL",
            "quantity": quantity,
            "fill_price": _round4(fill),
            "cost": _round2(cost),
            "realized_pnl": _round2(realized_this_sale),
            "position_closed": position_closed,
        },
        commit=False,
    )

    db.commit()
    db.refresh(order)
    db.refresh(position)
    db.refresh(portfolio)
    db.refresh(journal)

    return {
        "order": order_dict(order),
        "position": position_dict(position),
        "portfolio": portfolio_dict(portfolio),
        "journal_entry_id": str(journal.id),
        "fill": {
            "reference_price": _round4(ref),
            "fill_price": _round4(fill),
            "slippage_pct": SLIPPAGE_PCT,
            "transaction_cost_pct": TRANSACTION_COST_PCT,
            "proceeds": _round2(proceeds),
            "cost": _round2(cost),
            "realized_pnl_this_sale": _round2(realized_this_sale),
            "position_closed": position_closed,
        },
    }


# ---------------------------------------------------------------------------
# mark_to_market
# ---------------------------------------------------------------------------


def mark_to_market(
    db: Session, portfolio_id: uuid.UUID, latest_close_fn: LatestCloseFn
) -> dict[str, Any]:
    """Revalue every OPEN position at its latest close; update NAV/drawdown.

    Fetches every symbol's latest close FIRST, before mutating any state --
    if ``latest_close_fn`` raises for any symbol (e.g. the router's 502 for
    an unavailable price), no partial update has been applied and the
    portfolio/positions are left exactly as they were.

    Drawdown = (peak_nav - nav) / peak_nav. If drawdown crosses
    ``settings["risk_off_drawdown"]`` (8% by default) and risk-off is not
    already active, this call flips it on and journals a RISK_EVENT.
    Risk-off is a ONE-WAY LATCH here: it is never cleared by a later
    recovery (see module docstring) -- there is no reset endpoint in
    Phase 5.
    """
    portfolio = repositories.get_paper_portfolio(db, portfolio_id)
    if portfolio is None:
        raise NotFoundError(f"No paper portfolio with id {portfolio_id!s}.")

    positions = repositories.list_positions(
        db, portfolio_id=portfolio.id, status=PositionStatus.OPEN.value
    )

    # Fetch every mark BEFORE mutating anything (see docstring).
    marks: dict[uuid.UUID, float] = {}
    for position in positions:
        asset = db.get(Asset, position.asset_id)
        symbol = asset.symbol if asset is not None else str(position.asset_id)
        marks[position.id] = latest_close_fn(symbol)

    total = float(portfolio.cash)
    for position in positions:
        last = float(marks[position.id])
        position.last_price = _round4(last)
        position.unrealized_pnl = _round2((last - float(position.avg_entry_price)) * position.quantity)
        total += position.quantity * last

    portfolio.nav = _round2(total)
    peak = float(portfolio.peak_nav) if portfolio.peak_nav is not None else portfolio.nav
    peak = max(peak, portfolio.nav)
    portfolio.peak_nav = _round2(peak)
    drawdown = (peak - portfolio.nav) / peak if peak > 0 else 0.0

    settings = portfolio.settings or default_portfolio_settings()
    newly_risk_off = False
    if drawdown >= settings["risk_off_drawdown"] and not portfolio.risk_off:
        portfolio.risk_off = True
        newly_risk_off = True

    db.commit()
    db.refresh(portfolio)
    for position in positions:
        db.refresh(position)

    if newly_risk_off:
        repositories.create_journal_entry(
            db,
            portfolio_id=portfolio.id,
            entry_type=JournalEntryType.RISK_EVENT.value,
            title="Risk-off activated",
            body=(
                f"Drawdown {drawdown * 100:.2f}% breached the "
                f"{settings['risk_off_drawdown'] * 100:.0f}% threshold "
                f"(peak NAV {peak:.2f}, current NAV {portfolio.nav}); "
                "risk-off activated. New BUY entries are now blocked; "
                "SELL exits remain allowed. This does NOT auto-clear on "
                "recovery -- a human must review and reset it explicitly."
            ),
            refs={
                "paper_portfolio_id": str(portfolio.id),
                "drawdown": _round4(drawdown),
                "nav": float(portfolio.nav),
                "peak_nav": float(portfolio.peak_nav),
            },
        )

    return {
        "portfolio_id": str(portfolio.id),
        "nav": float(portfolio.nav),
        "cash": float(portfolio.cash),
        "peak_nav": float(portfolio.peak_nav),
        "drawdown": _round4(drawdown),
        "risk_off": portfolio.risk_off,
        "positions": [position_dict(position) for position in positions],
    }


# ---------------------------------------------------------------------------
# run_daily_cycle (Phase 9: Daily Ops Loop)
# ---------------------------------------------------------------------------


def run_daily_cycle(
    db: Session, portfolio_id: uuid.UUID, latest_close_fn: LatestCloseFn
) -> dict[str, Any]:
    """Run one portfolio's full daily cycle: stop-loss sweep, then MTM, then a NAV snapshot.

    Fixed order of operations (each step commits before the next begins):

    (a) STOP-LOSS SWEEP -- for every OPEN position, resolve its symbol (via
        the position's ``asset_id``) and fetch its latest close through
        ``latest_close_fn``. ALL closes are fetched first, before any exit is
        executed, so that one symbol's price being unavailable raises
        immediately (propagated to the router as a 502) with NO order
        created and NO snapshot written -- the cycle either fully runs or
        leaves the portfolio exactly as it was. For every position whose
        close is <= its stored ``stop_loss``, this reuses the existing
        ``create_paper_order`` pipeline to place a SELL of the position's
        FULL remaining quantity at ``price_reference=close`` -- so the fill,
        cash flow, realized P&L, and FILL journal entry are computed by the
        exact same code path as a manually-placed exit order (no duplicate
        fill logic). Because the sweep always exits the full quantity, a
        triggered position always ends up CLOSED. SELLs are risk-reducing,
        so risk-off never blocks a stop-loss exit (see the module
        docstring's risk-off convention).

        v1 fill semantics (deliberate, matching the module docstring's Phase
        5 deviation): a stop-loss "triggers" and fills IMMEDIATELY at the
        breaching close, in the same daily-cycle call -- not at the next
        trading day's open. The design doc's next-open fill model remains
        future work; this keeps the daily cycle synchronous and fully
        deterministic for local/offline testing, exactly like every other
        fill in this module.

    (b) MARK TO MARKET -- calls the existing ``mark_to_market`` on the
        POST-EXIT position set (whatever the sweep left OPEN), which updates
        last_price/unrealized_pnl/nav/peak_nav/risk_off exactly as it always
        has.

    (c) NAV SNAPSHOT -- upserts today's (``dt.date.today()``) NAV snapshot
        row (nav/cash/drawdown/risk_off) from the mark-to-market result, via
        ``repositories.upsert_nav_snapshot`` (idempotent: re-running the
        cycle again today updates the same row rather than duplicating it).

    Raises:
        NotFoundError: unknown portfolio_id, or an OPEN position's
            ``asset_id`` no longer resolves to a persisted ``Asset`` row.
        Any exception ``latest_close_fn`` raises (e.g. the router's
            ``LatestCloseUnavailable``) propagates unchanged -- it is raised
            during step (a)'s fetch-everything-first pass, before any state
            is mutated.

    Returns:
        ``{"portfolio_id", "date", "stops_triggered": [...], "mark_to_market":
        <mark_to_market's own return dict>, "snapshot": {"date", "nav",
        "cash", "drawdown", "risk_off"}}``. Each ``stops_triggered`` entry is
        ``{"position_id", "symbol", "quantity", "stop_loss", "close",
        "order_id"}`` (the quantity/stop_loss/close that triggered the exit,
        and the resulting FILLED SELL order's id).
    """
    portfolio = repositories.get_paper_portfolio(db, portfolio_id)
    if portfolio is None:
        raise NotFoundError(f"No paper portfolio with id {portfolio_id!s}.")

    open_positions = repositories.list_positions(
        db, portfolio_id=portfolio.id, status=PositionStatus.OPEN.value
    )

    # -- (a) STOP-LOSS SWEEP -- fetch every close BEFORE executing any exit.
    symbols: dict[uuid.UUID, str] = {}
    closes: dict[uuid.UUID, float] = {}
    for position in open_positions:
        asset = db.get(Asset, position.asset_id)
        if asset is None:
            raise NotFoundError(
                f"No asset with id {position.asset_id!s} referenced by "
                f"position {position.id!s}."
            )
        symbols[position.id] = asset.symbol
        closes[position.id] = float(latest_close_fn(asset.symbol))

    stops_triggered: list[dict[str, Any]] = []
    for position in open_positions:
        close = closes[position.id]
        stop = float(position.stop_loss)
        if close > stop:
            continue

        symbol = symbols[position.id]
        quantity = position.quantity
        result = create_paper_order(
            db,
            portfolio_id=portfolio.id,
            symbol=symbol,
            side=OrderSide.SELL.value,
            quantity=quantity,
            thesis=None,
            price_reference=close,
            exit_reason=f"Stop-loss triggered: close {close} <= stop {stop}",
            latest_close_fn=latest_close_fn,
        )
        stops_triggered.append(
            {
                "position_id": str(position.id),
                "symbol": symbol,
                "quantity": quantity,
                "stop_loss": stop,
                "close": close,
                "order_id": result["order"]["id"],
            }
        )

    # -- (b) MARK TO MARKET -- on the post-exit OPEN position set.
    mtm = mark_to_market(db, portfolio.id, latest_close_fn)

    # -- (c) NAV SNAPSHOT --
    today = dt.date.today()
    snapshot = repositories.upsert_nav_snapshot(
        db,
        portfolio_id=portfolio.id,
        date=today,
        nav=mtm["nav"],
        cash=mtm["cash"],
        drawdown=mtm["drawdown"],
        risk_off=mtm["risk_off"],
    )

    return {
        "portfolio_id": str(portfolio.id),
        "date": today.isoformat(),
        "stops_triggered": stops_triggered,
        "mark_to_market": mtm,
        "snapshot": nav_snapshot_dict(snapshot),
    }


# ---------------------------------------------------------------------------
# reset_risk_off (Phase 9: Daily Ops Loop)
# ---------------------------------------------------------------------------


def reset_risk_off(db: Session, portfolio_id: uuid.UUID, note: str) -> dict[str, Any]:
    """Manually clear a portfolio's risk-off latch (the reset Phase 5 lacked).

    ``mark_to_market`` only ever turns risk-off ON (a one-way latch, see the
    module docstring); this is the human-in-the-loop counterpart that turns
    it back off after a reviewer has looked at the journal and decided the
    portfolio may resume new entries.

    Args:
        portfolio_id: Must resolve to a persisted portfolio.
        note: Required, non-empty rationale for the reset; stored verbatim
            on the journal entry (both in ``body`` and in ``refs["note"]``).

    Raises:
        NotFoundError: unknown portfolio_id.
        ValidationFailure: the portfolio is not currently in risk-off mode,
            or ``note`` is missing/blank.

    Returns:
        The portfolio's summary dict (``portfolio_dict`` -- same shape as
        every other portfolio endpoint), with ``risk_mode`` now "NORMAL".
    """
    portfolio = repositories.get_paper_portfolio(db, portfolio_id)
    if portfolio is None:
        raise NotFoundError(f"No paper portfolio with id {portfolio_id!s}.")

    if not portfolio.risk_off:
        raise ValidationFailure("portfolio is not in risk-off mode.")

    if not note or not str(note).strip():
        raise ValidationFailure("note is required to reset risk-off.")

    portfolio.risk_off = False
    db.commit()
    db.refresh(portfolio)

    repositories.create_journal_entry(
        db,
        portfolio_id=portfolio.id,
        entry_type=JournalEntryType.RISK_EVENT.value,
        title="Risk-off manually reset",
        body=note,
        refs={"portfolio_id": str(portfolio.id), "note": note},
    )

    return portfolio_dict(portfolio)
