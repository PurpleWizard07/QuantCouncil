"""Backtest endpoints: run a strategy backtest and optionally persist it.

POST /backtests/run -- validate a strategy definition (inline or a persisted
``strategy_id``), fetch daily bars for one symbol through the shared cached
OHLCV connector, run the deterministic ``quant_engine`` backtester, and
return the full metrics set plus the equity curve and trade list. With
``persist=true`` the run is also written to the ``backtest_runs`` table and
its equity-curve/trades artifacts to ``<backtests_dir>/<run_id>/``.

GET /backtests/{backtest_id} -- load a persisted run: DB row (metrics,
params, dates, status) plus both artifact files read back from disk.

Persistence semantics (Phase 3.5, v1 simplifications documented):
    - ``persist=false`` (default) + inline ``strategy``: EXACTLY the Phase 3
      behavior -- nothing is written; the response carries
      ``persisted: false`` and ``backtest_id: null``.
    - ``persist=true``: the strategy row is resolved first --
      ``strategy_id`` if given; otherwise the inline definition is matched
      by name against persisted rows (identical normalized rules -> reuse;
      different rules -> 409; absent -> created as DRAFT after a successful
      run). Only SUCCESSFUL runs are persisted: engine errors return the
      same error responses as ever and write no FAILED rows and no strategy
      rows (failure paths are side-effect-free).
    - After a persisted run, the strategy is promoted DRAFT -> BACKTESTED
      (never demoted from a later lifecycle state).
    - Artifact paths are stored relative to the repo root with forward
      slashes (portable); a configured ``BACKTESTS_DIR`` outside the repo
      falls back to an absolute POSIX-style path.

This router shares the assets router's plumbing (the dependency-injected
``get_ohlcv_service`` connector, date-range parsing, symbol canonicalization,
and upstream-error mapping) by importing it from ``app.routers.assets`` --
one source of truth, and FastAPI dependency overrides installed against
``assets.get_ohlcv_service`` apply here too. The artifact root comes from the
``get_backtests_dir`` dependency (default: settings ``BACKTESTS_DIR`` or
``<repo_root>/data/backtests``), overridable in tests.

Error mapping (mirrors assets.py, plus persistence):
    400 -- invalid strategy definition, both/neither of strategy and
           strategy_id given, malformed UUIDs, symbol not in the strategy's
           universe, bad date strings, start_date > end_date, or
           insufficient data for the backtester.
    404 -- symbol not in the NIFTY 50 universe; unknown strategy_id or
           backtest_id.
    409 -- inline persist where the name exists with different rules.
    500 -- persisted run's artifact file missing on disk (GET).
    502 -- upstream data source failed or returned invalid data.
    503 -- database unreachable while a DB operation was required.

JSON safety: metric values that are NaN or infinite (e.g. ``profit_factor``
when there are no losing trades) are serialized as ``null``; trade and
equity-curve dates are ISO ``YYYY-MM-DD`` strings; datetimes are ISO strings;
UUIDs are strings.
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from quant_engine.backtest import BacktestConfig, Backtester, BacktestResult
from quant_engine.strategy import StrategyValidationError, validate_strategy

from app.core.config import find_repo_root, get_settings
from app.db import repositories
from app.db.models import BacktestStatus, StrategyDefinition, utcnow
from app.db.session import get_db
from app.routers.assets import (
    DAILY_TIMEFRAME,
    OHLCVService,
    _fetch_ohlcv,
    _parse_range,
    _resolve_symbol,
    get_ohlcv_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtests", tags=["backtests"])

PERSISTENCE_NOTE = (
    "results not persisted; set persist=true to save this run "
    "(persistence added in Phase 3.5)"
)

DB_UNAVAILABLE_DETAIL = (
    "Database unavailable. Is Postgres running? Start it with "
    "'docker compose -f infra/docker-compose.yml up -d' and check "
    "DATABASE_URL in the repo-root .env."
)

METRIC_FIELDS = (
    "total_return",
    "cagr",
    "max_drawdown",
    "win_rate",
    "avg_win",
    "avg_loss",
    "profit_factor",
    "num_trades",
    "exposure_time",
    "sharpe",
    "best_trade",
    "worst_trade",
    "starting_capital",
    "final_equity",
)


def get_backtests_dir() -> Path:
    """FastAPI dependency: root directory for persisted run artifacts.

    Resolved from settings (``BACKTESTS_DIR`` env var, default
    ``<repo_root>/data/backtests``). A dependency rather than a direct
    settings read so tests can override it with a tmp_path without fighting
    the ``lru_cache`` on ``get_settings``.
    """
    return get_settings().backtests_dir_path


class BacktestRunRequest(BaseModel):
    """Request body for POST /backtests/run.

    Attributes:
        strategy: Full inline strategy definition JSON per
            docs/strategy-format.md. Mutually exclusive with ``strategy_id``
            (exactly one must be provided).
        strategy_id: UUID of a persisted strategy whose stored rules are used
            as the definition. Mutually exclusive with ``strategy``.
        symbol: NIFTY 50 symbol to backtest (case-insensitive); must also be
            present in the strategy's ``universe``.
        start_date: ISO date (YYYY-MM-DD); defaults to end_date minus 365
            days (same defaults as the assets endpoints).
        end_date: ISO date (YYYY-MM-DD); defaults to today.
        persist: When true, persist the run (DB row + artifacts on disk) and
            return its ``backtest_id``. Default false (compute-only).
    """

    strategy: dict | None = None
    strategy_id: str | None = None
    symbol: str
    start_date: str | None = None
    end_date: str | None = None
    persist: bool = False


# --- serialization helpers ---------------------------------------------------


def _json_scalar(value: Any) -> Any:
    """JSON-safe scalar: NaN/NaT and infinities become None."""
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if pd.isna(value):
        return None
    return value


def _iso_date(value: Any) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _serialize_equity_curve(equity_curve: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {"date": _iso_date(row["date"]), "equity": _json_scalar(float(row["equity"]))}
        for row in equity_curve.to_dict(orient="records")
    ]


def _serialize_trades(trades: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for trade in trades:
        record = {key: _json_scalar(value) for key, value in trade.items()}
        record["entry_date"] = _iso_date(trade["entry_date"])
        record["exit_date"] = _iso_date(trade["exit_date"])
        out.append(record)
    return out


def _iso_datetime(value: Any) -> str | None:
    """Datetime -> ISO string (None passes through)."""
    return None if value is None else value.isoformat()


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    """Parse a path/body UUID string, mapping failure to 400."""
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"{field}={value!r} is not a valid UUID.",
        ) from None


# --- persistence helpers ------------------------------------------------------


def _repo_relative(path: Path) -> str:
    """Path stored in the DB: repo-root-relative, forward slashes.

    Falls back to an absolute POSIX-style path when the artifact directory
    lives outside the repo (e.g. a custom BACKTESTS_DIR or a test tmp dir).
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(find_repo_root()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _artifact_abspath(stored: str) -> Path:
    """Inverse of ``_repo_relative``: resolve a stored path for reading."""
    path = Path(stored)
    if not path.is_absolute():
        path = find_repo_root() / path
    return path


def _write_artifacts(
    backtests_dir: Path,
    run_id: uuid.UUID,
    equity_curve: list[dict[str, Any]],
    trades: list[dict[str, Any]],
) -> tuple[str, str]:
    """Write both artifact files; returns (equity_curve_path, trades_path).

    Paths are returned in stored form (repo-relative, forward slashes).
    """
    run_dir = backtests_dir / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    equity_path = run_dir / "equity_curve.json"
    trades_path = run_dir / "trades.json"
    equity_path.write_text(json.dumps(equity_curve), encoding="utf-8")
    trades_path.write_text(json.dumps(trades), encoding="utf-8")
    return _repo_relative(equity_path), _repo_relative(trades_path)


def _read_artifact(stored: str | None, label: str) -> Any:
    """Read a persisted artifact JSON file, mapping absence to 500."""
    path = _artifact_abspath(stored) if stored else None
    if path is None or not path.is_file():
        logger.error("Backtest artifact missing on disk: %s (%s)", label, stored)
        raise HTTPException(
            status_code=500,
            detail=(
                f"Backtest artifact missing on disk: {label}. The run's "
                "database row exists but its artifact file was not found; "
                "see server logs for the stored path."
            ),
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_strategy_row(
    db: Session, request: BacktestRunRequest
) -> tuple[StrategyDefinition | None, dict]:
    """Resolve (strategy_row_or_None, raw_definition) from the request.

    ``strategy_id`` path: load the row (400 malformed UUID, 404 unknown) and
    use its stored rules. Inline + persist path: match by name -- identical
    normalized rules reuse the row; different rules 409; no match returns
    ``(None, inline_definition)`` and the caller creates the row after a
    successful run. Inline without persist never touches the database.
    """
    if request.strategy_id is not None:
        strategy_uuid = _parse_uuid(request.strategy_id, "strategy_id")
        row = repositories.get_strategy(db, strategy_uuid)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No persisted strategy with id {request.strategy_id!r}. "
                    "List persisted strategies via GET /strategies."
                ),
            )
        return row, row.rules
    return None, request.strategy


@router.post("/run")
def run_backtest(
    request: BacktestRunRequest,
    service: OHLCVService = Depends(get_ohlcv_service),
    db: Session = Depends(get_db),
    backtests_dir: Path = Depends(get_backtests_dir),
) -> dict[str, Any]:
    """Run a single-symbol backtest, optionally persisting the result.

    The strategy is validated against the strict v1 schema, bars are fetched
    through the shared Parquet-cached connector, and the deterministic
    backtester produces all numbers (endpoints never hand-roll calculations).
    See the module docstring for persistence semantics.
    """
    canonical = _resolve_symbol(request.symbol)

    if (request.strategy is None) == (request.strategy_id is None):
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide exactly one of 'strategy' (inline definition) or "
                "'strategy_id' (persisted strategy UUID)."
            ),
        )

    try:
        strategy_row, definition = _resolve_strategy_row(db, request)
    except OperationalError:
        logger.exception("POST /backtests/run: database unavailable (strategy_id)")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    try:
        validated = validate_strategy(definition)
    except StrategyValidationError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid strategy definition: {exc}"
        ) from None

    universe_upper = {entry.upper() for entry in validated["universe"]}
    if canonical.upper() not in universe_upper:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Symbol {canonical!r} is not in strategy "
                f"{validated['name']!r}'s universe {validated['universe']}. "
                "Add it to the strategy's universe to backtest it."
            ),
        )

    start, end = _parse_range(request.start_date, request.end_date, DAILY_TIMEFRAME)

    # Inline + persist: fail fast on a name conflict BEFORE the (expensive)
    # run; identical rules reuse the existing row.
    if request.persist and strategy_row is None:
        try:
            existing = repositories.find_strategy_by_name(db, validated["name"])
        except OperationalError:
            logger.exception("POST /backtests/run: database unavailable (name check)")
            raise HTTPException(
                status_code=503, detail=DB_UNAVAILABLE_DETAIL
            ) from None
        if existing is not None:
            if existing.rules != validated:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"A persisted strategy named {validated['name']!r} "
                        "already exists with different rules; rename the "
                        "strategy or pass its strategy_id."
                    ),
                )
            strategy_row = existing

    df = _fetch_ohlcv(service, canonical, start, end)

    config = BacktestConfig()
    try:
        result: BacktestResult = Backtester(config).run(df, validated, symbol=canonical)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    metrics = {name: _json_scalar(getattr(result, name)) for name in METRIC_FIELDS}
    equity_curve = _serialize_equity_curve(result.equity_curve)
    trades = _serialize_trades(result.trades)

    response: dict[str, Any] = {
        "strategy_name": validated["name"],
        "symbol": canonical,
        "timeframe": DAILY_TIMEFRAME,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "config": {
            "initial_capital": config.initial_capital,
            "slippage_pct": config.slippage_pct,
            "transaction_cost_pct": config.transaction_cost_pct,
            "max_allocation_pct": config.max_allocation_pct,
        },
        "metrics": metrics,
        "equity_curve": equity_curve,
        "trades": trades,
        "persisted": False,
        "backtest_id": None,
    }

    if not request.persist:
        response["note"] = PERSISTENCE_NOTE
        return response

    run_id = uuid.uuid4()
    try:
        if strategy_row is None:
            strategy_row = repositories.create_strategy(db, validated)
        equity_path, trades_path = _write_artifacts(
            backtests_dir, run_id, equity_curve, trades
        )
        row = repositories.create_backtest_run(
            db,
            run_id=run_id,
            strategy_id=strategy_row.id,
            start_date=start,
            end_date=end,
            initial_capital=config.initial_capital,
            params={
                "symbol": canonical,
                "timeframe": DAILY_TIMEFRAME,
                "config": {
                    "slippage_pct": config.slippage_pct,
                    "transaction_cost_pct": config.transaction_cost_pct,
                    "max_allocation_pct": config.max_allocation_pct,
                },
            },
            metrics=metrics,
            equity_curve_path=equity_path,
            trades_path=trades_path,
            status=BacktestStatus.COMPLETED.value,
            completed_at=utcnow(),
        )
        repositories.mark_strategy_backtested(db, strategy_row)
    except OperationalError:
        logger.exception("POST /backtests/run: database unavailable (persist)")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    response["persisted"] = True
    response["backtest_id"] = str(row.id)
    return response


_LIST_METRIC_FIELDS = ("total_return", "max_drawdown", "sharpe", "num_trades")


def _list_metrics_subset(metrics: dict[str, Any] | None) -> dict[str, Any]:
    """Null-safe subset of a run's metrics for the list response."""
    metrics = metrics or {}
    return {field: metrics.get(field) for field in _LIST_METRIC_FIELDS}


@router.get("")
def list_backtests(
    limit: int = 20, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """List persisted backtest runs, newest first.

    Declared before ``GET /{backtest_id}`` on this router; FastAPI matches
    routes in declaration order and a literal path (``""`` -> ``/backtests``)
    never collides with the dynamic ``/{backtest_id}`` segment, but the
    ordering is kept defensive/readable regardless.
    """
    try:
        rows = repositories.list_backtest_runs(db, limit=limit)
        strategies = {
            row.strategy_id: repositories.get_strategy(db, row.strategy_id)
            for row in rows
        }
    except OperationalError:
        logger.exception("GET /backtests: database unavailable")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    items = []
    for row in rows:
        strategy = strategies.get(row.strategy_id)
        params = row.params or {}
        items.append(
            {
                "backtest_id": str(row.id),
                "strategy_id": str(row.strategy_id),
                "strategy_name": strategy.name if strategy is not None else None,
                "symbol": params.get("symbol"),
                "timeframe": params.get("timeframe"),
                "start_date": row.start_date.isoformat(),
                "end_date": row.end_date.isoformat(),
                "status": row.status,
                "created_at": _iso_datetime(row.created_at),
                "metrics": _list_metrics_subset(row.metrics),
            }
        )
    return {"count": len(items), "backtests": items}


@router.get("/{backtest_id}")
def get_backtest(backtest_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Load a persisted backtest run: DB row plus both on-disk artifacts."""
    run_uuid = _parse_uuid(backtest_id, "backtest_id")

    try:
        row = repositories.get_backtest_run(db, run_uuid)
        strategy = (
            repositories.get_strategy(db, row.strategy_id) if row is not None else None
        )
    except OperationalError:
        logger.exception("GET /backtests/%s: database unavailable", backtest_id)
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No persisted backtest run with id {backtest_id!r}.",
        )

    equity_curve = _read_artifact(row.equity_curve_path, "equity_curve.json")
    trades = _read_artifact(row.trades_path, "trades.json")

    params = row.params or {}
    config = {
        "initial_capital": float(row.initial_capital),
        **params.get("config", {}),
    }

    return {
        "backtest_id": str(row.id),
        "strategy_id": str(row.strategy_id),
        "strategy_name": strategy.name if strategy is not None else None,
        "symbol": params.get("symbol"),
        "timeframe": params.get("timeframe"),
        "config": config,
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat(),
        "status": row.status,
        "created_at": _iso_datetime(row.created_at),
        "completed_at": _iso_datetime(row.completed_at),
        "metrics": row.metrics,
        "equity_curve": equity_curve,
        "trades": trades,
        "persisted": True,
    }


@router.get("/{backtest_id}/risk")
def get_backtest_risk(backtest_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Load the latest persisted risk evaluation for a backtest run.

    Nested under ``/backtests`` (rather than living on the ``risk`` router)
    since it is a convenience view of "this backtest's risk verdict", not a
    general risk-evaluation lookup (see ``GET /risk/evaluations/{id}`` for
    that). No risk evaluation is ever computed here -- call
    ``POST /risk/evaluate`` to produce one; this endpoint only reads back the
    most recent persisted row, if any.

    404 distinguishes an unknown backtest from a known backtest that has not
    yet been risk-evaluated.
    """
    run_uuid = _parse_uuid(backtest_id, "backtest_id")

    try:
        row = repositories.get_backtest_run(db, run_uuid)
        evaluation = (
            repositories.get_latest_risk_evaluation_for_backtest(db, run_uuid)
            if row is not None
            else None
        )
    except OperationalError:
        logger.exception("GET /backtests/%s/risk: database unavailable", backtest_id)
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from None

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No persisted backtest run with id {backtest_id!r}.",
        )
    if evaluation is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Backtest run {backtest_id!r} has no persisted risk evaluation "
                "yet. Call POST /risk/evaluate with this backtest_id to produce one."
            ),
        )

    return {
        "risk_evaluation_id": str(evaluation.id),
        "backtest_id": str(evaluation.backtest_run_id),
        "strategy_id": str(evaluation.strategy_id),
        "decision": evaluation.decision,
        "approved": evaluation.approved,
        "risk_score": evaluation.risk_score,
        "policy_version": evaluation.policy_version,
        "reasons": evaluation.reasons,
        "failed_rules": evaluation.failed_rules,
        "warnings": evaluation.warnings,
        "metrics_snapshot": evaluation.metrics_snapshot,
        "policy_snapshot": evaluation.policy_snapshot,
        "created_at": _iso_datetime(evaluation.created_at),
        "persisted": True,
    }
