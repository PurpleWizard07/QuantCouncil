"""Paper portfolio endpoints (Phase 5): the paper-trading engine's HTTP surface.

PAPER-TRADING ONLY. No endpoint in this router places, modifies, or cancels
a real order, connects to a broker, or touches real money -- see
docs/paper-trading-design.md's "No Real Orders -- Ever" section. All of the
actual business logic (validation order, the risk-evaluation veto,
portfolio-limit gates, fill simulation, NAV/drawdown math, journaling) lives
in ``app.services.paper_engine``; this router only does HTTP-shaped work:
dependency injection, UUID/query parsing, and mapping the engine's typed
exceptions to status codes.

Endpoints:
    POST   /paper/portfolios                        -- create a portfolio.
    GET    /paper/portfolios                         -- list portfolios.
    GET    /paper/portfolios/{id}                    -- load one portfolio.
    POST   /paper/orders                              -- BUY or SELL (fills
        immediately; see the Phase 5 deviation note in paper_engine.py).
    GET    /paper/orders (?portfolio_id=)             -- list orders.
    GET    /paper/orders/{id}                         -- load one order.
    GET    /paper/positions (?portfolio_id=&status=)  -- list positions.
    GET    /paper/portfolios/{id}/positions (?status=)-- one portfolio's positions.
    POST   /paper/portfolios/{id}/mark-to-market      -- revalue open positions.
    GET    /paper/journal (?portfolio_id=)            -- list journal entries.
    GET    /paper/portfolios/{id}/journal             -- one portfolio's journal.
    POST   /paper/portfolios/{id}/daily-cycle         -- Phase 9: stop-loss
        sweep + mark-to-market + NAV snapshot, in that order (see
        ``paper_engine.run_daily_cycle``).
    GET    /paper/portfolios/{id}/nav-history (?limit=)-- Phase 9: a
        portfolio's NAV/cash/drawdown/risk-off history, oldest -> newest.
    POST   /paper/portfolios/{id}/risk-off/reset      -- Phase 9: manually
        clear the risk-off latch (see ``paper_engine.reset_risk_off``).

Error mapping:
    400 -- malformed UUID; ValidationFailure (bad input); LimitRejection /
           InsufficientCash / InsufficientPosition (business rejections;
           detail names the persisted REJECTED order id where one exists);
           risk-off reset requested with an empty note or while not in
           risk-off mode.
    403 -- RiskVetoError (the persisted risk evaluation is not APPROVED;
           detail names the decision, risk_score, and rejected order id).
    404 -- NotFoundError (unknown portfolio/asset/backtest/risk_evaluation,
           or a BUY missing a required backtest_id/risk_evaluation_id).
    502 -- the injected latest-close price fetch failed or returned no data.
    503 -- database unreachable (reuses backtests.py's DB_UNAVAILABLE_DETAIL).

Price resolution when ``price_reference`` is omitted: this router builds a
``latest_close_fn`` closure around the shared, dependency-injected
``get_ohlcv_service`` (the same connector ``assets.py``/``backtests.py``
use, so tests can fake it via ``app.dependency_overrides``) -- it fetches a
~10 calendar day window ending today and takes the last close. An empty
result or an upstream fetch/validation failure both map to 502.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from data_connectors import DataFetchError, DataValidationError

from app.db import repositories
from app.db.session import get_db
from app.routers.assets import DAILY_TIMEFRAME, OHLCVService, get_ohlcv_service
from app.routers.backtests import DB_UNAVAILABLE_DETAIL, _parse_uuid
from app.services import paper_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/paper", tags=["paper"])

LATEST_CLOSE_LOOKBACK_DAYS = 10


class LatestCloseUnavailable(Exception):
    """Raised by the router's ``latest_close_fn`` when no close is available.

    Kept router-local (not in ``paper_engine``) because it is purely a
    price-lookup plumbing error, not a paper-trading business rule -- the
    engine only knows it received an exception from ``latest_close_fn`` and
    lets it propagate; this router is what turns it into a 502.
    """


def _make_latest_close_fn(service: OHLCVService):
    """Build a ``latest_close_fn`` closure around the injected OHLCV service."""

    def _latest_close(symbol: str) -> float:
        end = date.today()
        start = end - timedelta(days=LATEST_CLOSE_LOOKBACK_DAYS)
        try:
            df = service.get_ohlcv(symbol, start, end, timeframe=DAILY_TIMEFRAME)
        except DataFetchError:
            logger.exception("latest-close fetch failed for %s", symbol)
            raise LatestCloseUnavailable(
                f"Could not fetch a latest close price for {symbol!r}: "
                "upstream data source error."
            ) from None
        except DataValidationError:
            logger.exception("latest-close data failed validation for %s", symbol)
            raise LatestCloseUnavailable(
                f"Could not fetch a latest close price for {symbol!r}: "
                "upstream data failed validation."
            ) from None
        if df is None or len(df) == 0:
            raise LatestCloseUnavailable(
                f"No OHLCV data available for {symbol!r} in the last "
                f"{LATEST_CLOSE_LOOKBACK_DAYS} days; cannot resolve a "
                "latest close price. Pass 'price_reference' explicitly to "
                "bypass this lookup."
            )
        return float(df.iloc[-1]["close"])

    return _latest_close


def _detail_with_order_id(exc: paper_engine.PaperEngineError) -> str:
    """Error detail text, appending the persisted REJECTED order id if any."""
    detail = str(exc)
    order_id = getattr(exc, "order_id", None)
    if order_id is not None:
        detail = f"{detail} (rejected paper_order_id={order_id})"
    return detail


# --- request bodies -----------------------------------------------------------


class PortfolioCreateRequest(BaseModel):
    """Request body for POST /paper/portfolios (entirely optional)."""

    name: str | None = None
    starting_capital: float | None = None


class OrderCreateRequest(BaseModel):
    """Request body for POST /paper/orders.

    Attributes:
        portfolio_id: UUID of a persisted paper portfolio.
        symbol: NIFTY 50 symbol (case-insensitive); must resolve to a
            persisted Asset row.
        side: "BUY" or "SELL".
        quantity: Whole shares, >= 1.
        thesis: Human-readable rationale. Required for BUY; for SELL, either
            ``thesis`` or ``exit_reason`` (or both) must be non-empty.
        backtest_id: Required for BUY (persisted backtest prerequisite);
            optional for SELL (see paper_engine._execute_sell).
        risk_evaluation_id: Required for BUY (persisted risk-evaluation
            prerequisite, and THE VETO); optional for SELL.
        price_reference: Optional explicit reference price; when omitted the
            router resolves the latest close through the OHLCV service.
        stop_loss_price: Required for BUY (mandatory stop-loss); unused for SELL.
        exit_reason: SELL-only rationale (see ``thesis``).
    """

    portfolio_id: str
    symbol: str
    side: str
    quantity: int
    thesis: str | None = None
    backtest_id: str | None = None
    risk_evaluation_id: str | None = None
    price_reference: float | None = None
    stop_loss_price: float | None = None
    exit_reason: str | None = None


class RiskOffResetRequest(BaseModel):
    """Request body for POST /paper/portfolios/{id}/risk-off/reset.

    Attributes:
        note: Required, non-empty rationale for the manual reset -- stored
            verbatim on the resulting RISK_EVENT journal entry.
    """

    note: str


# --- portfolios ----------------------------------------------------------------


@router.post("/portfolios", status_code=201)
def create_portfolio(
    request: PortfolioCreateRequest = PortfolioCreateRequest(),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create a new paper portfolio (defaults: "Default Paper Fund", Rs 10,00,000)."""
    kwargs: dict[str, Any] = {}
    if request.name is not None:
        kwargs["name"] = request.name
    if request.starting_capital is not None:
        kwargs["starting_capital"] = request.starting_capital

    try:
        portfolio = paper_engine.create_portfolio(db, **kwargs)
    except OperationalError:
        logger.exception("POST /paper/portfolios: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    return paper_engine.portfolio_dict(portfolio)


@router.get("/portfolios")
def list_portfolios(db: Session = Depends(get_db)) -> dict[str, Any]:
    """List all persisted paper portfolios."""
    try:
        rows = repositories.list_paper_portfolios(db)
    except OperationalError:
        logger.exception("GET /paper/portfolios: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    portfolios = [paper_engine.portfolio_dict(row) for row in rows]
    return {"count": len(portfolios), "portfolios": portfolios}


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Load a single paper portfolio by id."""
    pid = _parse_uuid(portfolio_id, "portfolio_id")

    try:
        row = repositories.get_paper_portfolio(db, pid)
    except OperationalError:
        logger.exception("GET /paper/portfolios/%s: database unavailable", portfolio_id)
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if row is None:
        raise HTTPException(
            status_code=404, detail=f"No paper portfolio with id {portfolio_id!r}."
        )
    return paper_engine.portfolio_dict(row)


# --- orders ----------------------------------------------------------------------


@router.post("/orders", status_code=201)
def create_order(
    request: OrderCreateRequest,
    service: OHLCVService = Depends(get_ohlcv_service),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Place a paper BUY or SELL order (fills immediately; see module docstring)."""
    portfolio_id = _parse_uuid(request.portfolio_id, "portfolio_id")
    backtest_id = (
        _parse_uuid(request.backtest_id, "backtest_id")
        if request.backtest_id is not None
        else None
    )
    risk_evaluation_id = (
        _parse_uuid(request.risk_evaluation_id, "risk_evaluation_id")
        if request.risk_evaluation_id is not None
        else None
    )

    latest_close_fn = _make_latest_close_fn(service)

    try:
        result = paper_engine.create_paper_order(
            db,
            portfolio_id=portfolio_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            thesis=request.thesis,
            backtest_id=backtest_id,
            risk_evaluation_id=risk_evaluation_id,
            price_reference=request.price_reference,
            stop_loss_price=request.stop_loss_price,
            exit_reason=request.exit_reason,
            latest_close_fn=latest_close_fn,
        )
    except paper_engine.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except paper_engine.RiskVetoError as exc:
        raise HTTPException(status_code=403, detail=_detail_with_order_id(exc)) from None
    except (
        paper_engine.LimitRejection,
        paper_engine.InsufficientCash,
        paper_engine.InsufficientPosition,
    ) as exc:
        raise HTTPException(status_code=400, detail=_detail_with_order_id(exc)) from None
    except paper_engine.ValidationFailure as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except LatestCloseUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except OperationalError:
        logger.exception("POST /paper/orders: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    return result


@router.get("/orders")
def list_orders(
    portfolio_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List paper orders, optionally filtered by portfolio_id, newest first."""
    pid = _parse_uuid(portfolio_id, "portfolio_id") if portfolio_id is not None else None

    try:
        rows = repositories.list_paper_orders(db, portfolio_id=pid)
    except OperationalError:
        logger.exception("GET /paper/orders: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    orders = [paper_engine.order_dict(row) for row in rows]
    return {"count": len(orders), "orders": orders}


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Load a single paper order by id."""
    oid = _parse_uuid(order_id, "order_id")

    try:
        row = repositories.get_paper_order(db, oid)
    except OperationalError:
        logger.exception("GET /paper/orders/%s: database unavailable", order_id)
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if row is None:
        raise HTTPException(status_code=404, detail=f"No paper order with id {order_id!r}.")
    return paper_engine.order_dict(row)


# --- positions ---------------------------------------------------------------------


@router.get("/positions")
def list_positions(
    portfolio_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List paper positions, optionally filtered by portfolio_id and/or status."""
    pid = _parse_uuid(portfolio_id, "portfolio_id") if portfolio_id is not None else None

    try:
        rows = repositories.list_positions(db, portfolio_id=pid, status=status)
    except OperationalError:
        logger.exception("GET /paper/positions: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    positions = [paper_engine.position_dict(row) for row in rows]
    return {"count": len(positions), "positions": positions}


@router.get("/portfolios/{portfolio_id}/positions")
def list_portfolio_positions(
    portfolio_id: str,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List one portfolio's positions, optionally filtered by status."""
    pid = _parse_uuid(portfolio_id, "portfolio_id")

    try:
        portfolio = repositories.get_paper_portfolio(db, pid)
        rows = (
            repositories.list_positions(db, portfolio_id=pid, status=status)
            if portfolio is not None
            else None
        )
    except OperationalError:
        logger.exception(
            "GET /paper/portfolios/%s/positions: database unavailable", portfolio_id
        )
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if portfolio is None:
        raise HTTPException(
            status_code=404, detail=f"No paper portfolio with id {portfolio_id!r}."
        )
    positions = [paper_engine.position_dict(row) for row in rows]
    return {"count": len(positions), "positions": positions}


# --- mark-to-market ------------------------------------------------------------------


@router.post("/portfolios/{portfolio_id}/mark-to-market")
def mark_to_market(
    portfolio_id: str,
    service: OHLCVService = Depends(get_ohlcv_service),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Revalue every OPEN position at its latest close; update NAV/drawdown/risk-off."""
    pid = _parse_uuid(portfolio_id, "portfolio_id")
    latest_close_fn = _make_latest_close_fn(service)

    try:
        result = paper_engine.mark_to_market(db, pid, latest_close_fn)
    except paper_engine.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except LatestCloseUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except OperationalError:
        logger.exception(
            "POST /paper/portfolios/%s/mark-to-market: database unavailable",
            portfolio_id,
        )
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    return result


# --- journal -----------------------------------------------------------------------


@router.get("/journal")
def list_journal(
    portfolio_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List trade journal entries, optionally filtered by portfolio_id, newest first."""
    pid = _parse_uuid(portfolio_id, "portfolio_id") if portfolio_id is not None else None

    try:
        rows = repositories.list_journal_entries(db, portfolio_id=pid)
    except OperationalError:
        logger.exception("GET /paper/journal: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    entries = [paper_engine.journal_dict(row) for row in rows]
    return {"count": len(entries), "journal": entries}


@router.get("/portfolios/{portfolio_id}/journal")
def list_portfolio_journal(portfolio_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """List one portfolio's trade journal entries, newest first."""
    pid = _parse_uuid(portfolio_id, "portfolio_id")

    try:
        portfolio = repositories.get_paper_portfolio(db, pid)
        rows = (
            repositories.list_journal_entries(db, portfolio_id=pid)
            if portfolio is not None
            else None
        )
    except OperationalError:
        logger.exception(
            "GET /paper/portfolios/%s/journal: database unavailable", portfolio_id
        )
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if portfolio is None:
        raise HTTPException(
            status_code=404, detail=f"No paper portfolio with id {portfolio_id!r}."
        )
    entries = [paper_engine.journal_dict(row) for row in rows]
    return {"count": len(entries), "journal": entries}


# --- daily ops loop (Phase 9) --------------------------------------------------------


@router.post("/portfolios/{portfolio_id}/daily-cycle")
def run_daily_cycle(
    portfolio_id: str,
    service: OHLCVService = Depends(get_ohlcv_service),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run one daily cycle: stop-loss sweep, then mark-to-market, then a NAV snapshot.

    See ``paper_engine.run_daily_cycle`` for the exact order of operations and
    v1 fill semantics. Any exit triggered by the stop-loss sweep is placed
    through the same order pipeline as ``POST /paper/orders`` (a SELL of the
    position's full remaining quantity, filled immediately at the breaching
    close) -- risk-off never blocks it (exits are always allowed).
    """
    pid = _parse_uuid(portfolio_id, "portfolio_id")
    latest_close_fn = _make_latest_close_fn(service)

    try:
        result = paper_engine.run_daily_cycle(db, pid, latest_close_fn)
    except paper_engine.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except paper_engine.PaperEngineError as exc:
        raise HTTPException(status_code=400, detail=_detail_with_order_id(exc)) from None
    except LatestCloseUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except OperationalError:
        logger.exception(
            "POST /paper/portfolios/%s/daily-cycle: database unavailable",
            portfolio_id,
        )
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    return result


@router.get("/portfolios/{portfolio_id}/nav-history")
def get_nav_history(
    portfolio_id: str,
    limit: int = Query(default=365),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """A portfolio's NAV/cash/drawdown/risk-off history, oldest -> newest."""
    pid = _parse_uuid(portfolio_id, "portfolio_id")

    try:
        portfolio = repositories.get_paper_portfolio(db, pid)
        rows = (
            repositories.list_nav_snapshots(db, pid, limit=limit)
            if portfolio is not None
            else None
        )
    except OperationalError:
        logger.exception(
            "GET /paper/portfolios/%s/nav-history: database unavailable", portfolio_id
        )
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if portfolio is None:
        raise HTTPException(
            status_code=404, detail=f"No paper portfolio with id {portfolio_id!r}."
        )
    snapshots = [paper_engine.nav_snapshot_dict(row) for row in rows]
    return {"portfolio_id": portfolio_id, "count": len(snapshots), "snapshots": snapshots}


@router.post("/portfolios/{portfolio_id}/risk-off/reset")
def reset_risk_off(
    portfolio_id: str,
    request: RiskOffResetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Manually clear a portfolio's risk-off latch (see ``paper_engine.reset_risk_off``).

    Response is the portfolio's summary dict (same shape as every other
    portfolio endpoint) plus ``{"journaled": true}`` confirming the RISK_EVENT
    journal entry was written.
    """
    pid = _parse_uuid(portfolio_id, "portfolio_id")

    try:
        result = paper_engine.reset_risk_off(db, pid, request.note)
    except paper_engine.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except paper_engine.ValidationFailure as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except OperationalError:
        logger.exception(
            "POST /paper/portfolios/%s/risk-off/reset: database unavailable",
            portfolio_id,
        )
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    return {**result, "journaled": True}
