"""Asset endpoints: the NIFTY 50 universe, OHLCV bars, indicators, and fundamentals.

GET /assets                       -- the NIFTY 50 universe with metadata.
GET /assets/{symbol}/ohlcv        -- daily OHLCV bars over a date range.
GET /assets/{symbol}/indicators   -- a fixed default indicator set over a range.
GET /assets/{symbol}/fundamentals -- valuation, profitability, financial health,
                                      and a 5-year statement history.

The universe is served straight from ``data_connectors.get_universe()`` (the
``data/nifty50_symbols.json`` snapshot) with NO database dependency: seeding
assets into Postgres is deferred to Phase 3, and until then this router is
intentionally stateless apart from the on-disk Parquet OHLCV cache.

Data flow: OHLCV comes through ``CachedConnector(get_connector("yfinance"),
OHLCVCache())``, so repeated requests for a covered date range are served from
the local Parquet cache without hitting Yahoo Finance. The connector is
constructed inside the ``get_ohlcv_service`` FastAPI dependency so tests can
substitute a deterministic fake via ``app.dependency_overrides``.

Indicators are computed exclusively by ``quant_engine.indicators``
(deterministic pandas code -- the project's source-of-truth rule: endpoints
never hand-roll calculations). Leading ``null`` values in the indicator
response are the indicator warm-up window over the requested range: v1 does
not pre-fetch extra lookback history before ``start_date``, so e.g. ``sma_50``
is null for the first 49 rows of whatever range was requested.

Fundamentals are fetched fresh from yfinance on every request (not yet
cached -- see ``data_connectors.fundamentals`` module docstring) and shaped
into a stable response by ``quant_engine.fundamentals`` (ratio computation
and unit conventions documented there); missing individual fields (not every
company reports every line item) are ``null``, not an error.

Error mapping:
    400 -- bad date strings, start_date > end_date, or timeframe != "1d".
    404 -- symbol not in the NIFTY 50 universe.
    502 -- the upstream data source failed (fetch error) or returned data
           that failed contract validation. Details are logged server-side
           and never leaked to the client.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Protocol

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from data_connectors import (
    CachedConnector,
    DataFetchError,
    DataValidationError,
    OHLCVCache,
    RawFundamentals,
    YFinanceFundamentalsConnector,
    get_connector,
    get_universe,
)
from quant_engine import fundamentals as fundamentals_engine
from quant_engine import indicators

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])

DAILY_TIMEFRAME = "1d"
DEFAULT_LOOKBACK_DAYS = 365


class OHLCVService(Protocol):
    """The slice of the connector interface this router depends on."""

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date | str,
        end_date: date | str,
        timeframe: str = "1d",
    ) -> pd.DataFrame: ...


def get_ohlcv_service() -> OHLCVService:
    """FastAPI dependency providing the cached OHLCV connector.

    Constructed per-request (both objects are cheap; the heavy state is the
    on-disk Parquet cache, which is shared). Tests override this dependency
    with a fake returning a deterministic DataFrame, so no endpoint test ever
    touches the network or the real cache directory.
    """
    return CachedConnector(get_connector("yfinance"), OHLCVCache())


class FundamentalsService(Protocol):
    """The slice of the fundamentals connector interface this router depends on."""

    def fetch_fundamentals(self, symbol: str) -> RawFundamentals: ...


def get_fundamentals_service() -> FundamentalsService:
    """FastAPI dependency providing the fundamentals connector.

    Not cached (see ``data_connectors.fundamentals`` module docstring):
    every request re-fetches from yfinance. Tests override this dependency
    with a fake returning deterministic data, so no endpoint test ever
    touches the network.
    """
    return YFinanceFundamentalsConnector()


def _universe_by_upper_symbol() -> dict[str, dict[str, Any]]:
    """Map upper-cased symbol -> universe metadata record."""
    return {record["symbol"].upper(): record for record in get_universe()}


def _resolve_symbol(symbol: str) -> str:
    """Resolve a path-parameter symbol to its canonical universe casing.

    Raises:
        HTTPException: 404 if the symbol is not in the NIFTY 50 universe.
    """
    record = _universe_by_upper_symbol().get(symbol.upper())
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown symbol {symbol!r}: not in the NIFTY 50 universe. "
                "List valid symbols via GET /assets."
            ),
        )
    return record["symbol"]


def _parse_range(
    start_date: str | None, end_date: str | None, timeframe: str
) -> tuple[date, date]:
    """Validate and default the shared date-range/timeframe query params.

    Defaults: ``end_date`` = today, ``start_date`` = ``end_date`` minus 365
    days.

    Raises:
        HTTPException: 400 on a non-"1d" timeframe, an unparseable date, or
            ``start_date`` after ``end_date``.
    """
    if timeframe != DAILY_TIMEFRAME:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported timeframe {timeframe!r}: daily timeframe only "
                "in v1 (use '1d')."
            ),
        )

    def _parse(value: str, field: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{field}={value!r} is not a valid ISO date "
                    "(expected 'YYYY-MM-DD')."
                ),
            ) from None

    end = _parse(end_date, "end_date") if end_date is not None else date.today()
    start = (
        _parse(start_date, "start_date")
        if start_date is not None
        else end - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    )
    if start > end:
        raise HTTPException(
            status_code=400,
            detail=(
                f"start_date ({start.isoformat()}) must be on or before "
                f"end_date ({end.isoformat()})."
            ),
        )
    return start, end


def _fetch_ohlcv(
    service: OHLCVService, symbol: str, start: date, end: date
) -> pd.DataFrame:
    """Fetch bars through the service, mapping errors to HTTP responses.

    Raises:
        HTTPException: 400 for input ValueErrors, 502 for upstream fetch or
            validation failures (details logged server-side, not leaked).
    """
    try:
        return service.get_ohlcv(symbol, start, end, timeframe=DAILY_TIMEFRAME)
    except DataFetchError:
        logger.exception("Upstream fetch failed for %s [%s, %s]", symbol, start, end)
        raise HTTPException(
            status_code=502,
            detail=(
                f"Upstream data source error while fetching OHLCV for "
                f"{symbol!r}. The symbol may have no data in the requested "
                "range, or the data source may be unavailable; see server "
                "logs for details."
            ),
        ) from None
    except DataValidationError:
        logger.exception(
            "Upstream data failed validation for %s [%s, %s]", symbol, start, end
        )
        raise HTTPException(
            status_code=502,
            detail=(
                f"Upstream data source returned data for {symbol!r} that "
                "failed contract validation; see server logs for details."
            ),
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


def _fetch_fundamentals(service: FundamentalsService, symbol: str) -> RawFundamentals:
    """Fetch fundamentals through the service, mapping errors to HTTP responses.

    Raises:
        HTTPException: 502 if the upstream data source fails (invalid/
            delisted symbol, or a Yahoo Finance outage).
    """
    try:
        return service.fetch_fundamentals(symbol)
    except DataFetchError:
        logger.exception("Upstream fundamentals fetch failed for %s", symbol)
        raise HTTPException(
            status_code=502,
            detail=(
                f"Upstream data source error while fetching fundamentals for "
                f"{symbol!r}. The symbol may have been delisted or renamed "
                "since the last universe refresh, or the data source may be "
                "unavailable; see server logs for details."
            ),
        ) from None


def _nan_to_none(value: Any) -> Any:
    """JSON-safe scalar: NaN/NaT become None (JSON cannot represent NaN)."""
    if value is None or pd.isna(value):
        return None
    return value


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialize a frame to JSON-safe records: ISO dates, NaN -> null."""
    out: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        record = {key: _nan_to_none(value) for key, value in row.items()}
        record["date"] = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
        out.append(record)
    return out


@router.get("")
def list_assets() -> dict[str, Any]:
    """The NIFTY 50 universe with metadata (no database; see module docstring)."""
    assets = get_universe()
    return {"count": len(assets), "assets": assets}


@router.get("/{symbol}/ohlcv")
def get_ohlcv(
    symbol: str,
    start_date: str | None = Query(
        default=None,
        description="ISO date (YYYY-MM-DD); defaults to end_date minus 365 days.",
    ),
    end_date: str | None = Query(
        default=None, description="ISO date (YYYY-MM-DD); defaults to today."
    ),
    timeframe: str = Query(default="1d", description="Only '1d' is supported in v1."),
    service: OHLCVService = Depends(get_ohlcv_service),
) -> dict[str, Any]:
    """Daily OHLCV bars for one NIFTY 50 symbol over [start_date, end_date].

    Served through the local Parquet cache: only ranges not already cached
    hit Yahoo Finance. Symbol lookup is case-insensitive; the response echoes
    the canonical universe casing.
    """
    canonical = _resolve_symbol(symbol)
    start, end = _parse_range(start_date, end_date, timeframe)
    df = _fetch_ohlcv(service, canonical, start, end)
    return {
        "symbol": canonical,
        "timeframe": DAILY_TIMEFRAME,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "rows": len(df),
        "data": _records(df),
    }


@router.get("/{symbol}/indicators")
def get_indicators(
    symbol: str,
    start_date: str | None = Query(
        default=None,
        description="ISO date (YYYY-MM-DD); defaults to end_date minus 365 days.",
    ),
    end_date: str | None = Query(
        default=None, description="ISO date (YYYY-MM-DD); defaults to today."
    ),
    timeframe: str = Query(default="1d", description="Only '1d' is supported in v1."),
    service: OHLCVService = Depends(get_ohlcv_service),
) -> dict[str, Any]:
    """A fixed default indicator set for one NIFTY 50 symbol over a range.

    All values are computed by ``quant_engine.indicators`` over exactly the
    requested range (no extra lookback is pre-fetched in v1), so the leading
    ``null`` values on each indicator are its warm-up window -- e.g.
    ``sma_50`` is null until 50 bars are available within the range. Request
    a wider range if warmed-up values are needed from a specific date.
    """
    canonical = _resolve_symbol(symbol)
    start, end = _parse_range(start_date, end_date, timeframe)
    df = _fetch_ohlcv(service, canonical, start, end)

    close = df["close"]
    frame = pd.DataFrame(
        {
            "date": df["date"],
            "close": close,
            "sma_20": indicators.sma(close, 20),
            "sma_50": indicators.sma(close, 50),
            "ema_20": indicators.ema(close, 20),
            "rsi_14": indicators.rsi(close, 14),
            "atr_14": indicators.atr(df["high"], df["low"], close, 14),
            "volume_sma_20": indicators.volume_sma(df["volume"], 20),
            "rolling_high_20": indicators.rolling_high(df["high"], 20),
            "rolling_low_20": indicators.rolling_low(df["low"], 20),
            "daily_returns": indicators.daily_returns(close),
            "volatility_20": indicators.volatility(close, 20, annualize=True),
        }
    )
    return {
        "symbol": canonical,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "rows": len(frame),
        "indicators": _records(frame),
    }


@router.get("/{symbol}/fundamentals")
def get_fundamentals(
    symbol: str,
    service: FundamentalsService = Depends(get_fundamentals_service),
) -> dict[str, Any]:
    """A fundamentals snapshot for one NIFTY 50 symbol: valuation,
    profitability, financial health, and a 5-year annual statement history.

    All ratios are computed by ``quant_engine.fundamentals`` (unit
    conventions and the ``.info``-vs-computed fallback rule are documented
    there). Missing fields are ``null`` -- not every company reports every
    line item (e.g. banks have no current ratio; a company with no
    inventory has quick ratio == current ratio).
    """
    canonical = _resolve_symbol(symbol)
    raw = _fetch_fundamentals(service, canonical)
    snapshot = fundamentals_engine.build_snapshot(
        raw.info, raw.income_stmt, raw.balance_sheet, raw.cashflow
    )
    return {"symbol": canonical, **snapshot}
