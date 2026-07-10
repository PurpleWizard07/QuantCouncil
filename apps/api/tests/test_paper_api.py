"""Phase 5 paper trading API tests -- in-memory SQLite, no network, no Postgres.

Mirrors ``test_risk_api.py``'s fixture style: a per-test in-memory SQLite
engine installed as the ``get_db`` dependency, a deterministic fake OHLCV
connector, and a tmp_path override for ``get_backtests_dir``. A persisted
backtest run always underlies a BUY order (the backtest-prerequisite rule),
but its symbol never has to match the traded symbol -- only the persisted
``risk_evaluations`` row (linked to that backtest) is checked. To keep risk
verdicts deterministic (the real risk engine's decision on arbitrary sine
data is not guaranteed either way), tests insert ``RiskEvaluation`` rows
directly via the ``db`` session fixture rather than trusting
``POST /risk/evaluate``'s live verdict -- exactly the shortcut the Phase 5
brief calls out as acceptable.

Covers:
    - Portfolio creation (defaults and custom values).
    - BUY: APPROVED-eval success (exact fill/cost/NAV arithmetic, journal
      refs), REJECTED/NEEDS_REVIEW veto (403 + persisted REJECTED order +
      RISK_EVENT journal), eval/backtest mismatch (400), missing
      thesis/backtest_id/risk_evaluation_id/stop_loss_price, insufficient
      cash, add-on weighted-average entry, portfolio limit gates
      (allocation/per-trade-risk/max-open-positions/risk-off).
    - SELL: success (realized P&L, partial vs full close), insufficient
      position, risk-off still allows exits.
    - mark_to_market: exact unrealized P&L/NAV, drawdown->risk-off latch,
      risk-off staying True after a price recovery.
    - Endpoint smokes: list/get for portfolios/orders/positions/journal,
      404s, malformed-UUID 400s.
"""

from __future__ import annotations

import uuid

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


# --- fixtures (mirrors test_risk_api.py) --------------------------------------


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
    """A direct session for inserting Asset/RiskEvaluation rows in tests."""
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
    """Fake connector: sine-trend frame; last close overridable for latest-
    close-fn resolution (paper orders / mark-to-market) independent of the
    backtest-fetch path."""

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


# --- helpers -------------------------------------------------------------------

_NAME_COUNTER = {"n": 0}


def _unique_strategy_name() -> str:
    _NAME_COUNTER["n"] += 1
    return f"paper_engine_strategy_{_NAME_COUNTER['n']}"


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
    failed_rules: list | None = None,
) -> models.RiskEvaluation:
    row = models.RiskEvaluation(
        backtest_run_id=uuid.UUID(backtest_id),
        strategy_id=uuid.UUID(strategy_id),
        decision=decision,
        approved=approved,
        risk_score=risk_score,
        reasons=["test-inserted evaluation"],
        failed_rules=failed_rules if failed_rules is not None else ([] if approved else ["test_rule"]),
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


def _approved_context(db, symbol: str, risk_score: int = 95) -> dict:
    """Insert an Asset + persisted backtest + APPROVED risk evaluation."""
    _insert_asset(db, symbol)
    posted = _persist_backtest()
    fetched = client.get(f"/backtests/{posted['backtest_id']}").json()
    risk_eval = _insert_risk_evaluation(
        db,
        backtest_id=posted["backtest_id"],
        strategy_id=fetched["strategy_id"],
        decision="APPROVED",
        approved=True,
        risk_score=risk_score,
    )
    return {
        "symbol": symbol,
        "backtest_id": posted["backtest_id"],
        "strategy_id": fetched["strategy_id"],
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


# --- portfolio creation ----------------------------------------------------------


def test_create_portfolio_defaults(api_db):
    body = _create_portfolio()
    assert body["name"] == "Default Paper Fund"
    assert body["starting_capital"] == 1_000_000.0
    assert body["current_cash"] == 1_000_000.0
    assert body["current_nav"] == 1_000_000.0
    assert body["peak_nav"] == 1_000_000.0
    assert body["risk_mode"] == "NORMAL"
    assert body["settings"]["max_allocation_per_stock"] == 0.10
    assert body["settings"]["max_risk_per_trade"] == 0.01
    assert body["settings"]["max_open_positions"] == 10
    assert body["settings"]["risk_off_drawdown"] == 0.08
    assert body["settings"]["require_stop_loss"] is True
    uuid.UUID(body["id"])
    assert body["created_at"]


def test_create_portfolio_custom_values(api_db):
    body = _create_portfolio(name="My Fund", starting_capital=250000.0)
    assert body["name"] == "My Fund"
    assert body["starting_capital"] == 250000.0
    assert body["current_cash"] == 250000.0
    assert body["current_nav"] == 250000.0


def test_create_portfolio_no_body(api_db):
    resp = client.post("/paper/portfolios")
    assert resp.status_code == 201
    assert resp.json()["name"] == "Default Paper Fund"


def test_list_and_get_portfolio(api_db):
    created = _create_portfolio()
    listed = client.get("/paper/portfolios").json()
    assert listed["count"] >= 1
    assert any(p["id"] == created["id"] for p in listed["portfolios"])

    fetched = client.get(f"/paper/portfolios/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]

    assert client.get("/paper/portfolios/not-a-uuid").status_code == 400
    assert client.get(f"/paper/portfolios/{uuid.uuid4()}").status_code == 404


# --- BUY: success + exact arithmetic ----------------------------------------------


def test_buy_approved_fills_with_exact_arithmetic(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "BUYOK1")
    portfolio = _create_portfolio()

    resp = client.post("/paper/orders", json=_buy_body(ctx, portfolio["id"], quantity=10, price_reference=1000.0, stop_loss_price=900.0))
    assert resp.status_code == 201, resp.text
    body = resp.json()

    ref = 1000.0
    fill = round(ref * (1 + SLIP), 4)
    cost = round(10 * fill * COST_PCT, 2)
    total_debit = round(10 * fill + cost, 2)

    assert body["order"]["status"] == "FILLED"
    assert body["order"]["side"] == "BUY"
    assert body["order"]["fill_price"] == fill
    assert body["fill"]["fill_price"] == fill
    assert body["fill"]["cost"] == cost
    assert body["fill"]["total_debit"] == total_debit

    assert body["position"]["avg_entry_price"] == fill
    assert body["position"]["quantity"] == 10
    assert body["position"]["status"] == "OPEN"
    assert body["position"]["stop_loss"] == 900.0

    expected_cash = round(1_000_000.0 - total_debit, 2)
    assert body["portfolio"]["current_cash"] == expected_cash
    expected_nav = round(expected_cash + 10 * fill, 2)
    assert body["portfolio"]["current_nav"] == expected_nav

    # Journal entry persisted with full audit refs.
    journal = client.get(f"/paper/journal?portfolio_id={portfolio['id']}").json()
    assert journal["count"] == 1
    entry = journal["journal"][0]
    assert entry["entry_type"] == "FILL"
    assert entry["refs"]["backtest_id"] == ctx["backtest_id"]
    assert entry["refs"]["risk_evaluation_id"] == ctx["risk_evaluation_id"]
    assert entry["refs"]["thesis"] == "unit test thesis"
    assert "risk_summary" in entry["refs"] and "APPROVED" in entry["refs"]["risk_summary"]
    assert entry["id"] == body["journal_entry_id"]


def test_buy_without_price_reference_uses_latest_close(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "BUYOK2")
    portfolio = _create_portfolio()
    fake_service.latest_close = 250.0

    body = _buy_body(ctx, portfolio["id"], quantity=5)
    del body["price_reference"]
    body["stop_loss_price"] = 200.0

    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 201, resp.text
    result = resp.json()
    fill = round(250.0 * (1 + SLIP), 4)
    assert result["order"]["fill_price"] == fill


# --- BUY: veto ---------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["REJECTED", "NEEDS_REVIEW"])
def test_buy_vetoed_by_non_approved_eval_returns_403(api_db, fake_service, artifacts_dir, db, decision):
    _insert_asset(db, f"VETO_{decision}")
    posted = _persist_backtest()
    fetched = client.get(f"/backtests/{posted['backtest_id']}").json()
    risk_eval = _insert_risk_evaluation(
        db,
        backtest_id=posted["backtest_id"],
        strategy_id=fetched["strategy_id"],
        decision=decision,
        approved=False,
        risk_score=10,
    )
    ctx = {
        "symbol": f"VETO_{decision}",
        "backtest_id": posted["backtest_id"],
        "risk_evaluation_id": str(risk_eval.id),
    }
    portfolio = _create_portfolio()

    resp = client.post("/paper/orders", json=_buy_body(ctx, portfolio["id"]))
    assert resp.status_code == 403, resp.text
    detail = resp.json()["detail"]
    assert decision in detail
    assert "risk_score=10" in detail
    assert "rejected paper_order_id=" in detail

    orders = client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()
    assert orders["count"] == 1
    assert orders["orders"][0]["status"] == "REJECTED"

    journal = client.get(f"/paper/journal?portfolio_id={portfolio['id']}").json()
    assert journal["count"] == 1
    assert journal["journal"][0]["entry_type"] == "RISK_EVENT"
    assert journal["journal"][0]["refs"]["rejection_reason"] == detail.split(" (rejected")[0]


def test_buy_eval_belongs_to_different_backtest_returns_400(api_db, fake_service, artifacts_dir, db):
    _insert_asset(db, "MISMATCH")
    posted_a = _persist_backtest()
    posted_b = _persist_backtest()
    fetched_b = client.get(f"/backtests/{posted_b['backtest_id']}").json()
    risk_eval_b = _insert_risk_evaluation(
        db, backtest_id=posted_b["backtest_id"], strategy_id=fetched_b["strategy_id"]
    )
    ctx = {
        "symbol": "MISMATCH",
        "backtest_id": posted_a["backtest_id"],
        "risk_evaluation_id": str(risk_eval_b.id),
    }
    portfolio = _create_portfolio()

    resp = client.post("/paper/orders", json=_buy_body(ctx, portfolio["id"]))
    assert resp.status_code == 400, resp.text
    assert posted_a["backtest_id"] in resp.json()["detail"]
    assert str(risk_eval_b.backtest_run_id) in resp.json()["detail"]

    # No rows created for this pure-input error.
    assert client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()["count"] == 0


# --- BUY: pure-input validation (no rows created) ---------------------------------


def test_buy_missing_thesis_returns_400_no_rows(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "NOTHESIS")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"])
    del body["thesis"]
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 400
    assert client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()["count"] == 0


def test_buy_missing_backtest_id_returns_404(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "NOBT")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"])
    del body["backtest_id"]
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 404


def test_buy_missing_risk_evaluation_id_returns_404(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "NORISK")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"])
    del body["risk_evaluation_id"]
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 404


def test_buy_missing_stop_loss_price_returns_400(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "NOSTOP")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"])
    del body["stop_loss_price"]
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 400


def test_buy_unknown_backtest_id_returns_404(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "UNKBT")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"], backtest_id=str(uuid.uuid4()))
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 404


def test_buy_unknown_risk_evaluation_id_returns_404(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "UNKRISK")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"], risk_evaluation_id=str(uuid.uuid4()))
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 404


def test_buy_unknown_portfolio_returns_404(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "UNKPF")
    body = _buy_body(ctx, str(uuid.uuid4()))
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 404


def test_buy_unknown_symbol_returns_404(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "REALSYM")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"], symbol="NOPE_NOT_AN_ASSET")
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 404


def test_buy_stop_loss_above_reference_returns_400(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "BADSTOP")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"], price_reference=100.0, stop_loss_price=150.0)
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 400


def test_buy_bad_quantity_returns_400(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "BADQTY")
    portfolio = _create_portfolio()
    body = _buy_body(ctx, portfolio["id"], quantity=0)
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 400


def test_order_and_portfolio_bad_uuid_returns_400(api_db):
    assert client.get("/paper/orders/not-a-uuid").status_code == 400
    assert client.get(f"/paper/orders/{uuid.uuid4()}").status_code == 404


# --- BUY: insufficient cash --------------------------------------------------------


def test_buy_insufficient_cash_returns_400_with_rejected_order(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "POORFUND", risk_score=95)
    portfolio = _create_portfolio(starting_capital=1000.0)
    # Relax the allocation/risk caps so only the cash gate can trigger --
    # otherwise a 100x-of-NAV order trips the allocation gate first.
    row = db.get(models.PaperPortfolio, uuid.UUID(portfolio["id"]))
    row.settings = {**row.settings, "max_allocation_per_stock": 1000.0, "max_risk_per_trade": 1000.0}
    db.commit()

    body = _buy_body(ctx, portfolio["id"], quantity=100, price_reference=1000.0, stop_loss_price=1.0)

    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 400, resp.text
    assert "insufficient cash" in resp.json()["detail"]
    assert "rejected paper_order_id=" in resp.json()["detail"]

    orders = client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()
    assert orders["count"] == 1
    assert orders["orders"][0]["status"] == "REJECTED"
    journal = client.get(f"/paper/journal?portfolio_id={portfolio['id']}").json()
    assert journal["count"] == 1


# --- BUY: add-on weighted average entry --------------------------------------------


def test_buy_addon_computes_weighted_average_entry(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "ADDON")
    portfolio = _create_portfolio()

    first = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=10, price_reference=100.0, stop_loss_price=90.0),
    ).json()
    fill1 = first["fill"]["fill_price"]
    assert first["position"]["quantity"] == 10

    second_resp = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=10, price_reference=200.0, stop_loss_price=150.0),
    )
    assert second_resp.status_code == 201, second_resp.text
    second = second_resp.json()
    fill2 = second["fill"]["fill_price"]

    expected_avg = round((10 * fill1 + 10 * fill2) / 20, 4)
    assert second["position"]["quantity"] == 20
    assert second["position"]["avg_entry_price"] == expected_avg
    # Documented decision: add-on stop-loss replaces the position's stop.
    assert second["position"]["stop_loss"] == 150.0

    # Only one position row exists for this (portfolio, asset).
    positions = client.get(f"/paper/portfolios/{portfolio['id']}/positions").json()
    assert positions["count"] == 1


# --- BUY: portfolio limit gates -----------------------------------------------------


def test_buy_allocation_breach_returns_400(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "ALLOC")
    portfolio = _create_portfolio(starting_capital=100000.0)
    # 10% of NAV = 10,000; 200 * ~100.05 ~= 20,010 > 10,000.
    body = _buy_body(ctx, portfolio["id"], quantity=200, price_reference=100.0, stop_loss_price=50.0)
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 400, resp.text
    assert "allocation breach" in resp.json()["detail"]


def test_buy_per_trade_risk_breach_returns_400(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "RISKBREACH")
    portfolio = _create_portfolio(starting_capital=1000000.0)
    # 1% of NAV = 10,000. (fill - stop) * qty must stay <= 10,000.
    # fill ~= 100.05; stop = 50 -> risk per share ~50.05; qty=10 -> ~500.5 (ok)
    # Use a wide stop instead to breach: stop=1 -> risk/share ~99 * qty 200 ~= 19,800 > 10,000.
    body = _buy_body(ctx, portfolio["id"], quantity=200, price_reference=100.0, stop_loss_price=1.0)
    resp = client.post("/paper/orders", json=body)
    assert resp.status_code == 400, resp.text
    assert "per-trade risk breach" in resp.json()["detail"]


def test_buy_max_open_positions_breach_returns_400(api_db, fake_service, artifacts_dir, db):
    portfolio = _create_portfolio(starting_capital=10_000_000.0)
    contexts = []
    for i in range(10):
        symbol = f"MAXPOS{i}"
        ctx = _approved_context(db, symbol)
        contexts.append(ctx)
        resp = client.post(
            "/paper/orders",
            json=_buy_body(ctx, portfolio["id"], quantity=1, price_reference=10.0, stop_loss_price=5.0),
        )
        assert resp.status_code == 201, resp.text

    positions = client.get(f"/paper/portfolios/{portfolio['id']}/positions").json()
    assert positions["count"] == 10

    # 11th distinct asset -> rejected (max open positions reached).
    eleventh_ctx = _approved_context(db, "MAXPOS_11TH")
    resp = client.post(
        "/paper/orders",
        json=_buy_body(eleventh_ctx, portfolio["id"], quantity=1, price_reference=10.0, stop_loss_price=5.0),
    )
    assert resp.status_code == 400, resp.text
    assert "max open positions" in resp.json()["detail"]

    # An add-on to an already-open position is still allowed.
    addon_resp = client.post(
        "/paper/orders",
        json=_buy_body(contexts[0], portfolio["id"], quantity=1, price_reference=10.0, stop_loss_price=5.0),
    )
    assert addon_resp.status_code == 201, addon_resp.text


def test_buy_risk_off_blocks_entries_but_sell_still_allowed(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "RISKOFF1")
    portfolio = _create_portfolio(starting_capital=100000.0)

    # quantity=95 @ ref100 sits just under the 10% allocation cap (~9,505 of
    # a 10,000 cap); stop=95 keeps per-trade risk (~480) well under the 1%
    # cap (~1,000) -- both portfolio-limit gates pass, so this position
    # actually opens (unlike a naive quantity that would silently breach a
    # gate and leave no position to mark down).
    buy_resp = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=95, price_reference=100.0, stop_loss_price=95.0),
    )
    assert buy_resp.status_code == 201, buy_resp.text

    # Force risk-off via a severe price drop + mark-to-market: wiping out
    # nearly all of a ~9.5%-of-NAV position is well over the 8% threshold.
    fake_service.latest_close = 1.0
    mtm = client.post(f"/paper/portfolios/{portfolio['id']}/mark-to-market")
    assert mtm.status_code == 200, mtm.text
    assert mtm.json()["drawdown"] >= 0.08
    assert mtm.json()["risk_off"] is True

    # New entry into a DIFFERENT asset is blocked.
    other_ctx = _approved_context(db, "RISKOFF2")
    blocked = client.post(
        "/paper/orders",
        json=_buy_body(other_ctx, portfolio["id"], quantity=1, price_reference=10.0, stop_loss_price=5.0),
    )
    assert blocked.status_code == 400, blocked.text
    assert "risk-off" in blocked.json()["detail"]

    # SELL (exit) of the existing position is still allowed.
    sell_body = {
        "portfolio_id": portfolio["id"],
        "symbol": ctx["symbol"],
        "side": "SELL",
        "quantity": 5,
        "exit_reason": "reducing risk under risk-off",
        "price_reference": 1.0,
    }
    sell_resp = client.post("/paper/orders", json=sell_body)
    assert sell_resp.status_code == 201, sell_resp.text


# --- SELL --------------------------------------------------------------------------


def test_sell_more_than_held_returns_400_with_rejected_order(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "SELLOVER")
    portfolio = _create_portfolio()
    client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=5, price_reference=100.0, stop_loss_price=50.0),
    )
    resp = client.post(
        "/paper/orders",
        json={
            "portfolio_id": portfolio["id"],
            "symbol": ctx["symbol"],
            "side": "SELL",
            "quantity": 10,
            "exit_reason": "test overselling",
            "price_reference": 100.0,
        },
    )
    assert resp.status_code == 400, resp.text
    assert "holding 5" in resp.json()["detail"]

    orders = client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()
    rejected = [o for o in orders["orders"] if o["side"] == "SELL" and o["status"] == "REJECTED"]
    assert len(rejected) == 1


def test_sell_with_no_position_returns_400(api_db, fake_service, artifacts_dir, db):
    _insert_asset(db, "NOPOS")
    portfolio = _create_portfolio()
    resp = client.post(
        "/paper/orders",
        json={
            "portfolio_id": portfolio["id"],
            "symbol": "NOPOS",
            "side": "SELL",
            "quantity": 1,
            "exit_reason": "no position",
            "price_reference": 10.0,
        },
    )
    assert resp.status_code == 400


def test_sell_missing_thesis_and_exit_reason_returns_400(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "SELLNOREASON")
    portfolio = _create_portfolio()
    client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=5, price_reference=100.0, stop_loss_price=50.0),
    )
    resp = client.post(
        "/paper/orders",
        json={
            "portfolio_id": portfolio["id"],
            "symbol": ctx["symbol"],
            "side": "SELL",
            "quantity": 1,
            "price_reference": 100.0,
        },
    )
    assert resp.status_code == 400


def test_sell_partial_then_full_close_with_exact_pnl(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "SELLPNL")
    portfolio = _create_portfolio()
    buy = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=10, price_reference=100.0, stop_loss_price=50.0),
    ).json()
    avg_entry = buy["position"]["avg_entry_price"]
    cash_after_buy = buy["portfolio"]["current_cash"]

    # Partial sell: 4 of 10 @ ref 120.
    partial = client.post(
        "/paper/orders",
        json={
            "portfolio_id": portfolio["id"],
            "symbol": ctx["symbol"],
            "side": "SELL",
            "quantity": 4,
            "exit_reason": "partial exit",
            "price_reference": 120.0,
        },
    )
    assert partial.status_code == 201, partial.text
    presult = partial.json()

    sell_fill = round(120.0 * (1 - SLIP), 4)
    proceeds = round(4 * sell_fill, 2)
    sell_cost = round(proceeds * COST_PCT, 2)
    realized = round((sell_fill - avg_entry) * 4 - sell_cost, 2)

    assert presult["fill"]["fill_price"] == sell_fill
    assert presult["fill"]["proceeds"] == proceeds
    assert presult["fill"]["cost"] == sell_cost
    assert presult["fill"]["realized_pnl_this_sale"] == realized
    assert presult["fill"]["position_closed"] is False
    assert presult["position"]["status"] == "OPEN"
    assert presult["position"]["quantity"] == 6
    assert presult["position"]["realized_pnl"] == realized
    expected_cash = round(cash_after_buy + proceeds - sell_cost, 2)
    assert presult["portfolio"]["current_cash"] == expected_cash

    # Full close: remaining 6 @ ref 80 (a loss this time).
    full = client.post(
        "/paper/orders",
        json={
            "portfolio_id": portfolio["id"],
            "symbol": ctx["symbol"],
            "side": "SELL",
            "quantity": 6,
            "exit_reason": "full exit",
            "price_reference": 80.0,
        },
    )
    assert full.status_code == 201, full.text
    fresult = full.json()
    assert fresult["fill"]["position_closed"] is True
    assert fresult["position"]["status"] == "CLOSED"
    assert fresult["position"]["quantity"] == 0
    assert fresult["position"]["closed_at"] is not None

    fill2 = round(80.0 * (1 - SLIP), 4)
    proceeds2 = round(6 * fill2, 2)
    cost2 = round(proceeds2 * COST_PCT, 2)
    realized2 = round((fill2 - avg_entry) * 6 - cost2, 2)
    assert fresult["fill"]["realized_pnl_this_sale"] == realized2
    total_realized = round(realized + realized2, 2)
    assert fresult["position"]["realized_pnl"] == total_realized

    journal = client.get(f"/paper/journal?portfolio_id={portfolio['id']}").json()
    fills = [e for e in journal["journal"] if e["entry_type"] == "FILL"]
    assert len(fills) == 3  # buy + 2 sells
    full_close_entry = next(e for e in fills if e["refs"].get("position_closed") is True)
    assert "position closed" in full_close_entry["body"]
    assert full_close_entry["refs"]["exit_reason"] == "full exit"


# --- mark-to-market ------------------------------------------------------------------


def test_mark_to_market_exact_pnl_and_nav(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "MTM1")
    portfolio = _create_portfolio()
    buy = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=10, price_reference=100.0, stop_loss_price=50.0),
    ).json()
    avg_entry = buy["position"]["avg_entry_price"]
    cash = buy["portfolio"]["current_cash"]

    fake_service.latest_close = 150.0
    mtm = client.post(f"/paper/portfolios/{portfolio['id']}/mark-to-market")
    assert mtm.status_code == 200, mtm.text
    result = mtm.json()

    expected_unrealized = round((150.0 - avg_entry) * 10, 2)
    position = result["positions"][0]
    assert position["last_price"] == 150.0
    assert position["unrealized_pnl"] == expected_unrealized

    expected_nav = round(cash + 10 * 150.0, 2)
    assert result["nav"] == expected_nav
    assert result["risk_off"] is False


def test_mark_to_market_drawdown_flips_risk_off_and_stays_true_after_recovery(
    api_db, fake_service, artifacts_dir, db
):
    ctx = _approved_context(db, "MTM2")
    portfolio = _create_portfolio(starting_capital=100000.0)
    # quantity=95 @ ref100/stop95 fits both the 10% allocation cap and the
    # 1% per-trade-risk cap (see the risk-off test above for the same math),
    # so the position actually opens.
    opened = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=95, price_reference=100.0, stop_loss_price=95.0),
    )
    assert opened.status_code == 201, opened.text

    # Drop the price hard enough to breach 8% drawdown from peak NAV.
    fake_service.latest_close = 10.0
    mtm1 = client.post(f"/paper/portfolios/{portfolio['id']}/mark-to-market")
    assert mtm1.status_code == 200, mtm1.text
    result1 = mtm1.json()
    assert result1["drawdown"] >= 0.08
    assert result1["risk_off"] is True

    journal = client.get(f"/paper/journal?portfolio_id={portfolio['id']}").json()
    risk_events = [e for e in journal["journal"] if e["entry_type"] == "RISK_EVENT" and "activated" in e["title"]]
    assert len(risk_events) == 1

    # Recovery: price bounces back above the original reference.
    fake_service.latest_close = 200.0
    mtm2 = client.post(f"/paper/portfolios/{portfolio['id']}/mark-to-market")
    assert mtm2.status_code == 200, mtm2.text
    result2 = mtm2.json()
    assert result2["risk_off"] is True  # one-way latch: never auto-clears

    # No duplicate risk-off activation journal entry on the second mark.
    journal2 = client.get(f"/paper/journal?portfolio_id={portfolio['id']}").json()
    risk_events2 = [e for e in journal2["journal"] if e["entry_type"] == "RISK_EVENT" and "activated" in e["title"]]
    assert len(risk_events2) == 1


def test_mark_to_market_unknown_portfolio_returns_404(api_db, fake_service):
    resp = client.post(f"/paper/portfolios/{uuid.uuid4()}/mark-to-market")
    assert resp.status_code == 404


def test_mark_to_market_price_unavailable_returns_502(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "MTMBAD")
    portfolio = _create_portfolio()
    client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=1, price_reference=100.0, stop_loss_price=50.0),
    )
    fake_service.raise_for.add(ctx["symbol"].upper())
    resp = client.post(f"/paper/portfolios/{portfolio['id']}/mark-to-market")
    assert resp.status_code == 502


# --- endpoint smokes -----------------------------------------------------------------


def test_positions_endpoints_smoke(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "SMOKEPOS")
    portfolio = _create_portfolio()
    client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=1, price_reference=100.0, stop_loss_price=50.0),
    )

    all_positions = client.get("/paper/positions").json()
    assert all_positions["count"] >= 1

    filtered = client.get(f"/paper/positions?portfolio_id={portfolio['id']}&status=OPEN").json()
    assert filtered["count"] == 1

    scoped = client.get(f"/paper/portfolios/{portfolio['id']}/positions").json()
    assert scoped["count"] == 1

    assert client.get(f"/paper/portfolios/{uuid.uuid4()}/positions").status_code == 404
    assert client.get("/paper/portfolios/not-a-uuid/positions").status_code == 400


def test_journal_endpoints_smoke(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "SMOKEJRNL")
    portfolio = _create_portfolio()
    client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=1, price_reference=100.0, stop_loss_price=50.0),
    )

    all_journal = client.get("/paper/journal").json()
    assert all_journal["count"] >= 1

    scoped = client.get(f"/paper/portfolios/{portfolio['id']}/journal").json()
    assert scoped["count"] == 1
    assert scoped["journal"][0]["entry_type"] == "FILL"

    assert client.get(f"/paper/portfolios/{uuid.uuid4()}/journal").status_code == 404
    assert client.get("/paper/portfolios/not-a-uuid/journal").status_code == 400


def test_orders_list_and_get_smoke(api_db, fake_service, artifacts_dir, db):
    ctx = _approved_context(db, "SMOKEORD")
    portfolio = _create_portfolio()
    created = client.post(
        "/paper/orders",
        json=_buy_body(ctx, portfolio["id"], quantity=1, price_reference=100.0, stop_loss_price=50.0),
    ).json()
    order_id = created["order"]["id"]

    fetched = client.get(f"/paper/orders/{order_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == order_id

    listed = client.get(f"/paper/orders?portfolio_id={portfolio['id']}").json()
    assert listed["count"] == 1
    assert listed["orders"][0]["id"] == order_id
