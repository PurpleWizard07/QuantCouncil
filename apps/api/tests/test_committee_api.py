"""Phase 6 AI committee API tests -- in-memory SQLite, no network, no Postgres.

Mirrors ``test_risk_api.py`` / ``test_paper_api.py``'s fixture style: a
per-test in-memory SQLite engine installed as the ``get_db`` dependency, a
deterministic fake OHLCV connector, and a tmp_path override for
``get_backtests_dir``. A real backtest is persisted through
``POST /backtests/run`` (so it carries a real ``trades.json`` artifact and
real metrics); its ``metrics.total_return`` is then overwritten directly via
the ``db`` session (the natural SMA-crossover result on the shared sine-trend
fixture frame is slightly negative, and several tests need a specific sign
deterministically) -- exactly the kind of direct-row-mutation shortcut
``test_paper_api.py`` already uses for portfolio settings. A ``RiskEvaluation``
row is inserted directly (never computed live), matching
``test_paper_api.py``'s documented shortcut.

An autouse fixture monkeypatches ``httpx.get``/``httpx.post`` to raise if
called at all, proving no test in this module ever reaches the network: the
mock provider path never imports a cloud SDK, and the no-key manual-provider
path fails inside ``agents.providers.registry.get_provider`` (a plain
``is_configured()`` env-var check) before any client or request is built.

Covers:
    - POST /committee/evaluate happy path (mock, provider omitted): full
      six-section response shape, cio.approved_by_risk, 7
      agent_decision_ids, 7 persisted rows.
    - The deterministic risk veto end to end: REJECTED + positive return
      overrides a raw PAPER_TRADE to NO_TRADE with the exact override
      string; APPROVED + positive return allows PAPER_TRADE through.
    - provider="auto" with every cloud key absent and Ollama unreachable
      resolves to mock.
    - provider="anthropic" with no key -> 503 naming ANTHROPIC_API_KEY, and
      crucially zero agent_decisions rows created (no silent mock fallback).
    - provider="bogus" -> 400 listing allowed provider names.
    - 404 unknown backtest_id; 400 risk evaluation belonging to a different
      backtest; 400 malformed UUIDs.
    - GET /committee/backtests/{id}: newest-first listing, count, 404 for an
      unknown backtest.
"""

from __future__ import annotations

import uuid

import httpx
import numpy as np
import pandas as pd
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import agents.providers.ollama_provider as ollama_provider

from app.db import models, repositories
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routers import assets, backtests
from quant_engine.strategies import get_builtin_strategies

client = TestClient(app)

ALLOWED_PROVIDER_NAMES = ("mock", "anthropic", "gemini", "openrouter", "ollama", "auto")


# --- fixtures (mirrors test_risk_api.py / test_paper_api.py) -----------------


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
    """A direct session for inserting RiskEvaluation rows / mutating metrics."""
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


@pytest.fixture
def fake_service():
    class FakeOHLCVService:
        def get_ohlcv(self, symbol, start_date, end_date, timeframe="1d"):
            return _sine_trend_frame().copy()

    fake = FakeOHLCVService()
    app.dependency_overrides[assets.get_ohlcv_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(assets.get_ohlcv_service, None)


@pytest.fixture
def artifacts_dir(tmp_path):
    app.dependency_overrides[backtests.get_backtests_dir] = lambda: tmp_path
    yield tmp_path
    app.dependency_overrides.pop(backtests.get_backtests_dir, None)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Fail loudly if any test in this module reaches for the network."""

    def _boom(*args, **kwargs):
        raise AssertionError("network access attempted during a no-network committee test")

    monkeypatch.setattr(httpx, "get", _boom)
    monkeypatch.setattr(httpx, "post", _boom)
    yield


# --- helpers -------------------------------------------------------------------

_NAME_COUNTER = {"n": 0}


def _unique_strategy_name() -> str:
    _NAME_COUNTER["n"] += 1
    return f"committee_api_strategy_{_NAME_COUNTER['n']}"


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


def _set_total_return(db, backtest_id: str, total_return: float) -> None:
    """Force a specific total_return sign (the natural SMA result is ~ -0.006)."""
    row = db.get(models.BacktestRun, uuid.UUID(backtest_id))
    row.metrics = {**(row.metrics or {}), "total_return": total_return}
    db.commit()


def _insert_risk_evaluation(
    db,
    *,
    backtest_id: str,
    strategy_id: str,
    decision: str,
    approved: bool,
    risk_score: int = 80,
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


def _committee_context(db, *, approved: bool, total_return: float, risk_score: int = 80) -> dict:
    """Persist a backtest (forcing total_return) + a matching risk evaluation."""
    posted = _persist_backtest()
    _set_total_return(db, posted["backtest_id"], total_return)
    fetched = client.get(f"/backtests/{posted['backtest_id']}").json()
    risk_eval = _insert_risk_evaluation(
        db,
        backtest_id=posted["backtest_id"],
        strategy_id=fetched["strategy_id"],
        decision="APPROVED" if approved else "REJECTED",
        approved=approved,
        risk_score=risk_score,
    )
    return {
        "backtest_id": posted["backtest_id"],
        "risk_evaluation_id": str(risk_eval.id),
    }


_SECTION_KEYS = {
    "technical_analyst": {"view", "confidence", "signals", "warnings", "summary"},
    "quant_researcher": {
        "strategy_quality",
        "rule_interpretation",
        "strengths",
        "weaknesses",
        "improvement_ideas",
        "summary",
    },
    "bull_case": {"case_strength", "arguments", "best_case_scenario", "summary"},
    "bear_case": {"case_strength", "risks", "failure_modes", "worst_case_scenario", "summary"},
    "risk_narrator": {
        "risk_summary",
        "failed_rules_explained",
        "warnings_explained",
        "plain_english_verdict",
    },
    "cio": {"decision", "approved_by_risk", "summary", "reason", "conditions_to_reconsider", "audit_refs"},
    "cio_raw": {"decision", "summary", "reason", "conditions_to_reconsider"},
}


# --- POST /committee/evaluate: happy path (mock, default provider) -----------


def test_evaluate_mock_happy_path_returns_full_committee_and_persists(
    api_db, fake_service, artifacts_dir, db
):
    ctx = _committee_context(db, approved=True, total_return=0.1)

    response = client.post("/committee/evaluate", json=ctx)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["requested_provider"] == "mock"
    assert body["selected_provider"] == "mock"
    assert body["backtest_id"] == ctx["backtest_id"]
    assert body["risk_evaluation_id"] == ctx["risk_evaluation_id"]

    for section, keys in _SECTION_KEYS.items():
        assert keys <= set(body[section].keys()), f"{section} missing keys"

    assert body["cio"]["approved_by_risk"] is True
    assert body["cio"]["audit_refs"]["backtest_id"] == ctx["backtest_id"]
    assert body["cio"]["audit_refs"]["risk_evaluation_id"] == ctx["risk_evaluation_id"]
    assert len(body["agent_decision_ids"]) == 7
    assert len(set(body["agent_decision_ids"])) == 7  # all distinct
    # audit_refs on the persisted CIODecision references the six raw-role
    # rows that fed it (it cannot know its own row id before being
    # persisted); the seventh id (this final row itself) is appended only to
    # the top-level agent_decision_ids list.
    assert body["cio"]["audit_refs"]["agent_decision_ids"] == body["agent_decision_ids"][:6]
    assert body["agent_decision_ids"][6] not in body["cio"]["audit_refs"]["agent_decision_ids"]

    rows = repositories.list_agent_decisions_for_backtest(db, uuid.UUID(ctx["backtest_id"]))
    assert len(rows) == 7
    roles = [row.agent_role for row in rows]
    assert roles.count("cio") == 2
    assert roles.count("technical_analyst") == 1


# --- the deterministic risk veto, end to end ----------------------------------


def test_veto_end_to_end_overrides_paper_trade_to_no_trade(api_db, fake_service, artifacts_dir, db):
    ctx = _committee_context(db, approved=False, total_return=0.15)

    response = client.post("/committee/evaluate", json=ctx)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["cio_raw"]["decision"] == "PAPER_TRADE"
    assert body["cio"]["decision"] == "NO_TRADE"
    assert body["cio"]["approved_by_risk"] is False
    assert body["override_warning"] == (
        "CIO raw PAPER_TRADE overridden because risk engine rejected the backtest."
    )


def test_approved_end_to_end_allows_paper_trade(api_db, fake_service, artifacts_dir, db):
    ctx = _committee_context(db, approved=True, total_return=0.15)

    response = client.post("/committee/evaluate", json=ctx)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["cio_raw"]["decision"] == "PAPER_TRADE"
    assert body["cio"]["decision"] == "PAPER_TRADE"
    assert body["cio"]["approved_by_risk"] is True
    assert body["override_warning"] is None


# --- provider selection --------------------------------------------------------


def test_provider_auto_with_no_keys_resolves_to_mock(
    api_db, fake_service, artifacts_dir, db, monkeypatch
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(
        ollama_provider.OllamaAgentProvider, "_probe", staticmethod(lambda base_url: False)
    )

    ctx = _committee_context(db, approved=True, total_return=0.1)
    response = client.post("/committee/evaluate", json={**ctx, "provider": "auto"})
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["requested_provider"] == "auto"
    assert body["selected_provider"] == "mock"


def test_provider_anthropic_without_key_returns_503_and_creates_no_rows(
    api_db, fake_service, artifacts_dir, db, monkeypatch
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ctx = _committee_context(db, approved=True, total_return=0.1)

    response = client.post("/committee/evaluate", json={**ctx, "provider": "anthropic"})
    assert response.status_code == 503, response.text
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]

    rows = repositories.list_agent_decisions_for_backtest(db, uuid.UUID(ctx["backtest_id"]))
    assert len(rows) == 0


def test_provider_bogus_returns_400_listing_allowed_values(api_db, fake_service, artifacts_dir, db):
    ctx = _committee_context(db, approved=True, total_return=0.1)

    response = client.post("/committee/evaluate", json={**ctx, "provider": "bogus"})
    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert "bogus" in detail
    for name in ALLOWED_PROVIDER_NAMES:
        assert name in detail


# --- error mapping: unknown / mismatched / malformed ids ----------------------


def test_unknown_backtest_id_returns_404(api_db):
    response = client.post(
        "/committee/evaluate",
        json={"backtest_id": str(uuid.uuid4()), "risk_evaluation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


def test_unknown_risk_evaluation_id_returns_404(api_db, fake_service, artifacts_dir):
    posted = _persist_backtest()
    response = client.post(
        "/committee/evaluate",
        json={"backtest_id": posted["backtest_id"], "risk_evaluation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


def test_evaluation_belongs_to_different_backtest_returns_400(api_db, fake_service, artifacts_dir, db):
    ctx_a = _committee_context(db, approved=True, total_return=0.1)
    ctx_b = _committee_context(db, approved=True, total_return=0.1)

    response = client.post(
        "/committee/evaluate",
        json={"backtest_id": ctx_a["backtest_id"], "risk_evaluation_id": ctx_b["risk_evaluation_id"]},
    )
    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert ctx_a["backtest_id"] in detail
    assert ctx_b["backtest_id"] in detail  # the backtest the evaluation actually belongs to


def test_malformed_backtest_id_returns_400(api_db):
    response = client.post(
        "/committee/evaluate",
        json={"backtest_id": "not-a-uuid", "risk_evaluation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 400


def test_malformed_risk_evaluation_id_returns_400(api_db, fake_service, artifacts_dir):
    posted = _persist_backtest()
    response = client.post(
        "/committee/evaluate",
        json={"backtest_id": posted["backtest_id"], "risk_evaluation_id": "not-a-uuid"},
    )
    assert response.status_code == 400


# --- GET /committee/backtests/{id} --------------------------------------------


def test_get_committee_evaluations_for_backtest_lists_newest_first(
    api_db, fake_service, artifacts_dir, db
):
    ctx = _committee_context(db, approved=True, total_return=0.1)
    evaluated = client.post("/committee/evaluate", json=ctx)
    assert evaluated.status_code == 200, evaluated.text

    response = client.get(f"/committee/backtests/{ctx['backtest_id']}")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["backtest_id"] == ctx["backtest_id"]
    assert body["count"] == 7
    assert len(body["decisions"]) == 7
    for entry in body["decisions"]:
        assert set(entry.keys()) == {"id", "agent_role", "model", "output", "created_at"}
        assert "input" not in entry

    roles = [entry["agent_role"] for entry in body["decisions"]]
    assert roles.count("cio") == 2

    # Newest first: the timestamps are non-decreasing walking the list back
    # to front (i.e. non-increasing front to back).
    created_at = [entry["created_at"] for entry in body["decisions"]]
    assert created_at == sorted(created_at, reverse=True)


def test_get_committee_evaluations_unknown_backtest_returns_404(api_db):
    response = client.get(f"/committee/backtests/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_committee_evaluations_malformed_uuid_returns_400(api_db):
    response = client.get("/committee/backtests/not-a-uuid")
    assert response.status_code == 400
