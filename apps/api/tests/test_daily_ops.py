"""Phase 9 Daily Ops Loop API tests -- in-memory SQLite, no network, no Postgres.

Mirrors ``test_paper_api.py``'s fixture style (itself mirroring
``test_risk_api.py``): a per-test in-memory SQLite engine installed as the
``get_db`` dependency, a deterministic fake OHLCV connector, and a tmp_path
override for ``get_backtests_dir``.

Covers the three new endpoints:
    POST /paper/portfolios/{id}/daily-cycle
    GET  /paper/portfolios/{id}/nav-history
    POST /paper/portfolios/{id}/risk-off/reset

and the two new service functions behind them (``paper_engine.run_daily_cycle``,
``paper_engine.reset_risk_off``):
    - no positions -> snapshot only, no stops.
    - stop not breached -> position stays OPEN.
    - stop breached -> full-quantity SELL through the existing order pipeline
      (exact fill/cost/realized-pnl math), position CLOSED, FILL journal
      entry, correct ``stops_triggered`` payload.
    - multiple positions, one breached one not.
    - snapshot upsert (same day, twice, one row) and nav-history ordering
      (oldest -> newest) + limit.
    - risk-off latch during the daily cycle, and the manual reset endpoint
      (missing note, not-in-risk-off, and the valid path).
    - price-unavailable fetch-first behavior: 502, no partial exits, no
      snapshot written.
    - malformed UUID / unknown portfolio smokes across all three endpoints.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routers import assets, backtests
from app.services import paper_engine
from quant_engine.strategies import get_builtin_strategies

client = TestClient(app)

SLIP = paper_engine.SLIPPAGE_PCT
COST_PCT = paper_engine.TRANSACTION_COST_PCT


# --- fixtures (mirrors test_paper_api.py) ---------------------------------------


@pytest.fixture
def engine():
    eng = sa.create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    """A direct session for inserting Asset/RiskEvaluation/NavSnapshot rows."""
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def api_db(session_factory):
    """Install the in-memory database as the app's get_db dependency."""

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def _sine_trend_frame(n: int = 200) -> pd.DataFrame:
    """Deterministic frame with SMA(20)/SMA(50) crossovers (sine + drift)."""
    i = np.arange(n)
    closes = 100.0 + 10.0 * np.sin(2.0 * np.pi * i / 80.0) + 0.02 * i
    opens = np.concatenate([[closes[0]], closes[:-1]])
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": opens,
            "high": np.maximum(opens, closes) + 0.25,
            "low": np.minimum(opens, closes) - 0.25,
            "close": closes,
            "volume": np.full(n, 1_000.0),
        }
    )


class _FakeOHLCVService:
    """Fake connector: sine-trend frame; last close overridable (applies
    uniformly to every symbol not in ``raise_for``) for latest-close-fn
    resolution independent of the backtest-fetch path."""

    def __init__(self) -> None:
        self.latest_close: float | None = None
        self.raise_for: set[str] = set()

    def get_ohlcv(self, symbol, start_date, end_date, timeframe="1d"):
        if symbol.upper() in self.raise_for:
            from data_connectors import DataFetchError

            raise DataFetchError(f"no data for {symbol}")
        frame = _sine_trend_frame().copy()
        if self.latest_close is not None:
            frame.loc[frame.index[-1], "close"] = self.latest_close
        return frame


@pytest.fixture
def fake_service():
    fake = _FakeOHLCVService()
    app.dependency_overrides[assets.get_ohlcv_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(assets.get_ohlcv_service, None)


@pytest.fixture
def artifacts_dir(tmp_path):
    app.dependency_overrides[backtests.get_backtests_dir] = lambda: tmp_path
    yield tmp_path
    app.dependency_overrides.pop(backtests.get_backtests_dir, None)


# --- helpers (mirrors test_paper_api.py) ----------------------------------------

_NAME_COUNTER = {"n": 0}


def _unique_strategy_name() -> str:
    _NAME_COUNTER["n"] += 1
    return f"daily_ops_strategy_{_NAME_COUNTER['n']}"


def _strategy(name: str) -> dict:
    for strategy in get_builtin_strategies():
        if strategy["name"] == "sma_crossover_20_50":
            strategy = dict(strategy)
            strategy["name"] = name
            return strategy
    raise AssertionError("sma_crossover_20_50 builtin missing")


def _persist_backtest() -> dict:
    """POST /backtests/run persist=true against the shared fake service."""
    run = client.post(
        "/backtests/run",
        json={
            "symbol": "RELIANCE",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "strategy": _strategy(_unique_strategy_name()),
            "persist": True,
        },
    )
    assert run.status_code == 200, run.text
    return run.json()


def _insert_risk_evaluation(
    db,
    *,
    backtest_id: str,
    strategy_id: str,
    decision: str = "APPROVED",
    approved: bool = True,
    risk_score: int = 95,
) -> models.RiskEvaluation:
    row = models.RiskEvaluation(
        backtest_run_id=uuid.UUID(backtest_id),
        strategy_id=uuid.UUID(strategy_id),
        decision=decision,
        approved=approved,
        risk_score=risk_score,
        reasons=["test-inserted evaluation"],
        failed_rules=[] if approved else ["test_rule"],
        warnings=[],
        policy_version="v1-test",
        metrics_snapshot={},
        policy_snapshot={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _insert_asset(db, symbol: str, name: str | None = None, exchange: str = "NSE") -> models.Asset:
    asset = models.Asset(symbol=symbol, name=name or f"{symbol} Test Co", exchange=exchange)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _approved_context(db, symbol: str) -> dict:
    """Insert an Asset + persisted backtest + APPROVED risk evaluation."""
    _insert_asset(db, symbol)
    posted = _persist_backtest()
    fetched = client.get(f"/backtests/{posted['backtest_id']}").json()
    risk_eval = _insert_risk_evaluation(
        db,
        backtest_id=posted["backtest_id"],
        strategy_id=fetched["strategy_id"],
    )
    return {
        "symbol": symbol,
        "backtest_id": posted["backtest_id"],
        "risk_evaluation_id": str(risk_eval.id),
    }


def _create_portfolio(**overrides) -> dict:
    resp = client.post("/paper/portfolios", json=overrides or {})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _buy_body(ctx: dict, portfolio_id: str, **overrides) -> dict:
    body = {
        "portfolio_id": portfolio_id,
        "symbol": ctx["symbol"],
        "side": "BUY",
        "quantity": 10,
        "thesis": "unit test thesis",
        "backtest_id": ctx["backtest_id"],
        "risk_evaluation_id": ctx["risk_evaluation_id"],
        "price_reference": 1000.0,
        "stop_loss_price": 900.0,
    }
    body.update(overrides)
    return body


def _daily_cycle(portfolio_id: str):
    return client.post(f"/paper/portfolios/{portfolio_id}/daily-cycle")


def _nav_history(portfolio_id: str, limit: int | None = None):
    url = f"/paper/portfolios/{portfolio_id}/nav-history"
    if limit is not None:
        url += f"?limit={limit}"
    return client.get(url)


def _reset_risk_off(portfolio_id: str, note: str):
    return client.post(f"/paper/portfolios/{portfolio_id}/risk-off/reset", json={"note": note})


# --- daily cycle: no positions ---------------------------------------------------


def test_daily_cycle_no_positions_writes_snapshot_with_current_nav(api_db, fake_service):
    portfolio = _create_portfolio()

    resp = _daily_cycle(portfolio["id"])
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["portfolio_id"] == portfolio["id"]
    assert body["stops_triggered"] == []
    assert body["mark_to_market"]["positions"] == []
    assert body["snapshot"]["nav"] == portfolio["current_nav"]
    assert body["snapshot"]["cash"] == portfolio["current_cash"]
    assert body["snapshot"]["risk_off"] is False
    assert body["snapshot"]["drawdown"] == 0.0
    assert body["snapshot"]["date"] == date.today().isoformat()

    hist = _nav_history(portfolio["id"]).json()
    assert hist["count"] == 1
    assert hist["snapshots"][0]["nav"] == portfolio["current_nav"]
    assert hist["snapshots"][0]["date"] == date.today().isoformat()


# --- daily cycle: stop-loss sweep ------------------------------------------------


def test_daily_cycle_stop_not_breached_position_stays_open(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "DAILYNOBREACH")
    portfolio = _create_portfolio()
    client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=10, price_reference=100.0, stop_loss_price=50.0),
    )

    fake_service.latest_close = 80.0  # 80 > 50 -> no breach

    resp = _daily_cycle(portfolio["id"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stops_triggered"] == []

    positions = client.get(f"/paper/portfolios/{portfolio['id']}/positions").json()
    assert positions["count"] == 1
    assert positions["positions"][0]["status"] == "OPEN"
    assert positions["positions"][0]["last_price"] == 80.0


def test_daily_cycle_stop_breached_triggers_full_exit_with_exact_math(
    api_db, fake_service, artifacts_dir, db
):
    ctx = _approved_context(db, "DAILYBREACH")
    portfolio = _create_portfolio()
    buy = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=10, price_reference=100.0, stop_loss_price=90.0),
    ).json()
    avg_entry = buy["position"]["avg_entry_price"]
    orders_before = client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()["count"]

    fake_service.latest_close = 80.0  # 80 <= 90 -> breach

    resp = _daily_cycle(portfolio["id"])
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert len(body["stops_triggered"]) == 1
    trig = body["stops_triggered"][0]
    assert trig["symbol"] == ctx["symbol"]
    assert trig["quantity"] == 10
    assert trig["stop_loss"] == 90.0
    assert trig["close"] == 80.0
    order_id = trig["order_id"]

    order = client.get(f"/paper/orders/{order_id}").json()
    assert order["status"] == "FILLED"
    assert order["side"] == "SELL"
    fill = round(80.0 * (1 - SLIP), 4)
    assert order["fill_price"] == fill

    orders_after = client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()["count"]
    assert orders_after == orders_before + 1

    positions = client.get(f"/paper/portfolios/{portfolio['id']}/positions").json()
    assert positions["count"] == 1
    pos = positions["positions"][0]
    assert pos["status"] == "CLOSED"
    assert pos["quantity"] == 0
    assert pos["closed_at"] is not None

    proceeds = round(10 * fill, 2)
    cost = round(proceeds * COST_PCT, 2)
    realized = round((fill - avg_entry) * 10 - cost, 2)
    assert pos["realized_pnl"] == realized

    journal = client.get(f"/paper/portfolios/{portfolio['id']}/journal").json()
    sell_fills = [
        e for e in journal["journal"] if e["entry_type"] == "FILL" and e["refs"].get("side") == "SELL"
    ]
    assert len(sell_fills) == 1
    assert "Stop-loss triggered" in sell_fills[0]["refs"]["exit_reason"]
    assert sell_fills[0]["refs"]["realized_pnl"] == realized
    assert sell_fills[0]["refs"]["position_closed"] is True

    # Position is closed, so mark-to-market has nothing left to mark.
    assert body["mark_to_market"]["positions"] == []
    assert body["snapshot"]["nav"] == body["mark_to_market"]["nav"]
    assert body["snapshot"]["cash"] == body["mark_to_market"]["cash"]


def test_daily_cycle_multiple_positions_one_breached_one_not(api_db, fake_service, artifacts_dir, db):
    ctx_a = _approved_context(db, "DAILYMULTIA")
    ctx_b = _approved_context(db, "DAILYMULTIB")
    portfolio = _create_portfolio()
    client.post(
        "/paper/orders",
        json=_buy_body(ctx_a, portfolio["id"], quantity=10, price_reference=100.0, stop_loss_price=95.0),
    )
    client.post(
        "/paper/orders",
        json=_buy_body(ctx_b, portfolio["id"], quantity=10, price_reference=100.0, stop_loss_price=50.0),
    )

    fake_service.latest_close = 80.0  # breaches A's stop (95) but not B's (50)

    resp = _daily_cycle(portfolio["id"])
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert len(body["stops_triggered"]) == 1
    assert body["stops_triggered"][0]["symbol"] == ctx_a["symbol"]

    positions = client.get(f"/paper/portfolios/{portfolio['id']}/positions").json()
    open_positions = [p for p in positions["positions"] if p["status"] == "OPEN"]
    closed_positions = [p for p in positions["positions"] if p["status"] == "CLOSED"]
    assert len(open_positions) == 1
    assert len(closed_positions) == 1
    assert open_positions[0]["last_price"] == 80.0


# --- daily cycle: NAV snapshot upsert + nav-history ------------------------------


def test_daily_cycle_snapshot_upsert_same_day_and_nav_history_ordering(
    api_db, fake_service, artifacts_dir, db
):
    portfolio = _create_portfolio()
    portfolio_uuid = uuid.UUID(portfolio["id"])
    today = date.today()

    # Seed five days of prior history directly (oldest -> newest: -5..-1).
    for offset in range(5, 0, -1):
        row = models.NavSnapshot(
            portfolio_id=portfolio_uuid,
            date=today - timedelta(days=offset),
            nav=1_000_000 + offset,
            cash=1_000_000 + offset,
            drawdown=0.0,
            risk_off=False,
        )
        db.add(row)
    db.commit()

    ctx = _approved_context(db, "DAILYSNAP")
    client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=10, price_reference=100.0, stop_loss_price=10.0),
    )

    fake_service.latest_close = 110.0
    resp1 = _daily_cycle(portfolio["id"])
    assert resp1.status_code == 200, resp1.text
    nav1 = resp1.json()["snapshot"]["nav"]

    fake_service.latest_close = 130.0
    resp2 = _daily_cycle(portfolio["id"])
    assert resp2.status_code == 200, resp2.text
    nav2 = resp2.json()["snapshot"]["nav"]

    assert nav2 != nav1  # NAV actually moved between the two same-day calls

    hist_all = _nav_history(portfolio["id"]).json()
    assert hist_all["count"] == 6  # 5 seeded + 1 today (upserted, not duplicated)
    dates = [s["date"] for s in hist_all["snapshots"]]
    assert dates == sorted(dates)
    assert hist_all["snapshots"][-1]["date"] == today.isoformat()
    assert hist_all["snapshots"][-1]["nav"] == nav2  # latest upsert won

    hist_limited = _nav_history(portfolio["id"], limit=3).json()
    assert hist_limited["count"] == 3
    limited_dates = [s["date"] for s in hist_limited["snapshots"]]
    assert limited_dates == sorted(limited_dates)
    assert hist_limited["snapshots"][-1]["date"] == today.isoformat()


# --- risk-off latch + manual reset -----------------------------------------------


def test_daily_cycle_risk_off_latch_and_manual_reset(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "DAILYRISKOFF")
    portfolio = _create_portfolio(starting_capital=100000.0)
    # quantity=95 @ ref100/stop95 fits both the 10% allocation cap and the 1%
    # per-trade-risk cap (same math as the Phase 5 risk-off tests).
    opened = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=95, price_reference=100.0, stop_loss_price=95.0),
    )
    assert opened.status_code == 201, opened.text

    # A severe overnight crash blows through the stop (triggering the sweep's
    # exit) AND still leaves NAV down >=8% from peak once realized -- the
    # combination is realistic (a stop-loss caps *planned* per-trade risk at
    # 1% of NAV, so an 8%+ single-day portfolio drawdown can only happen via
    # a gap well past the stop, exactly like the Phase 5 mark-to-market
    # risk-off test's price crash).
    fake_service.latest_close = 10.0
    resp = _daily_cycle(portfolio["id"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["stops_triggered"]) == 1
    assert body["mark_to_market"]["drawdown"] >= 0.08
    assert body["mark_to_market"]["risk_off"] is True
    assert body["snapshot"]["risk_off"] is True

    pf = client.get(f"/paper/portfolios/{portfolio['id']}").json()
    assert pf["risk_mode"] == "RISK_OFF"

    # Empty note -> 400 (portfolio IS in risk-off; only the note is bad).
    bad_note = _reset_risk_off(portfolio["id"], "")
    assert bad_note.status_code == 400, bad_note.text
    still = client.get(f"/paper/portfolios/{portfolio['id']}").json()
    assert still["risk_mode"] == "RISK_OFF"

    # Not currently in risk-off -> 400 (a fresh, un-latched portfolio).
    other_portfolio = _create_portfolio()
    not_risk_off = _reset_risk_off(other_portfolio["id"], "trying anyway")
    assert not_risk_off.status_code == 400, not_risk_off.text

    # Valid reset.
    good = _reset_risk_off(portfolio["id"], "reviewed and cleared")
    assert good.status_code == 200, good.text
    good_body = good.json()
    assert good_body["risk_mode"] == "NORMAL"
    assert good_body["journaled"] is True

    journal = client.get(f"/paper/portfolios/{portfolio['id']}/journal").json()
    reset_entries = [
        e
        for e in journal["journal"]
        if e["entry_type"] == "RISK_EVENT" and e["title"] == "Risk-off manually reset"
    ]
    assert len(reset_entries) == 1
    assert reset_entries[0]["body"] == "reviewed and cleared"
    assert reset_entries[0]["refs"]["note"] == "reviewed and cleared"
    assert reset_entries[0]["refs"]["portfolio_id"] == portfolio["id"]

    final = client.get(f"/paper/portfolios/{portfolio['id']}").json()
    assert final["risk_mode"] == "NORMAL"


# --- price unavailable: fetch-first, no partial state ----------------------------


def test_daily_cycle_price_unavailable_returns_502_with_no_partial_state(
    api_db, fake_service, artifacts_dir, db
):
    ctx = _approved_context(db, "DAILYBADPRICE")
    portfolio = _create_portfolio()
    client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=5, price_reference=100.0, stop_loss_price=50.0),
    )
    orders_before = client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()["count"]

    fake_service.raise_for.add(ctx["symbol"].upper())

    resp = _daily_cycle(portfolio["id"])
    assert resp.status_code == 502, resp.text

    orders_after = client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()["count"]
    assert orders_after == orders_before  # no exit order created

    hist = _nav_history(portfolio["id"]).json()
    assert hist["count"] == 0  # no snapshot written

    positions = client.get(f"/paper/portfolios/{portfolio['id']}/positions").json()
    assert positions["positions"][0]["status"] == "OPEN"  # untouched


# --- endpoint smokes: bad UUID / unknown portfolio -------------------------------


def test_daily_ops_endpoints_bad_uuid_and_unknown_portfolio(api_db, fake_service):
    assert client.post("/paper/portfolios/not-a-uuid/daily-cycle").status_code == 400
    assert _daily_cycle(str(uuid.uuid4())).status_code == 404

    assert client.get("/paper/portfolios/not-a-uuid/nav-history").status_code == 400
    assert _nav_history(str(uuid.uuid4())).status_code == 404

    assert (
        client.post("/paper/portfolios/not-a-uuid/risk-off/reset", json={"note": "x"}).status_code
        == 400
    )
    assert _reset_risk_off(str(uuid.uuid4()), "x").status_code == 404
