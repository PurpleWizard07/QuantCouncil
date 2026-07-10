"""Ingest daily OHLCV bars into the ohlcv_daily table.

Fetches bars through the SAME Phase 2 pipeline the API uses --
``CachedConnector(get_connector("yfinance"), OHLCVCache(), refresh=...)`` --
so every fetch goes through contract validation and the local Parquet cache
(never bypassed), then idempotently upserts the rows into ``ohlcv_daily``
(re-runs skip bars already present).

Usage (from the repo root, venv active, database migrated and seeded):

    # One or more symbols
    python apps/api/scripts/ingest_ohlcv.py --symbol RELIANCE --symbol TCS --start 2024-01-01

    # The full NIFTY 50 universe (continues past per-symbol failures)
    python apps/api/scripts/ingest_ohlcv.py --all --start 2024-01-01

    # Force a connector re-fetch (bypass the Parquet cache read, refresh it)
    python apps/api/scripts/ingest_ohlcv.py --symbol INFY --start 2024-01-01 --refresh

Prerequisites: schema migrated (``alembic -c infra/alembic.ini upgrade
head``) and assets seeded (``python apps/api/scripts/seed_assets.py``).
"""

import argparse
import sys
from datetime import date
from pathlib import Path

# Path bootstrap so "import app" works when this file is run directly.
API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy.exc import OperationalError  # noqa: E402

from data_connectors import (  # noqa: E402
    CachedConnector,
    OHLCVCache,
    get_connector,
    get_universe,
)

from app.db.repositories import get_asset_by_symbol, upsert_ohlcv_bars  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

DB_UNREACHABLE_HINT = (
    "ERROR: could not connect to the database.\n"
    "Is Postgres running? Start it with:  docker compose -f "
    "infra/docker-compose.yml up -d\n"
    "Also check DATABASE_URL in your repo-root .env (see .env.example)."
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest daily OHLCV bars into ohlcv_daily (idempotent)."
    )
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument(
        "--symbol",
        action="append",
        default=None,
        metavar="SYMBOL",
        help="NSE symbol to ingest (repeatable, case-insensitive).",
    )
    which.add_argument(
        "--all",
        action="store_true",
        help="Ingest the full NIFTY 50 universe.",
    )
    parser.add_argument(
        "--start",
        required=True,
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Range start (inclusive).",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="Range end (inclusive); defaults to today.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force a connector re-fetch (refresh the Parquet cache).",
    )
    args = parser.parse_args(argv)
    if args.end is None:
        args.end = date.today()
    if args.start > args.end:
        parser.error(f"--start ({args.start}) must be on or before --end ({args.end})")
    return args


def _resolve_symbols(args: argparse.Namespace) -> list[str]:
    """Canonicalize requested symbols against the universe (or take --all)."""
    universe = {record["symbol"].upper(): record["symbol"] for record in get_universe()}
    if args.all:
        return list(universe.values())
    resolved: list[str] = []
    for raw in args.symbol:
        canonical = universe.get(raw.upper())
        if canonical is None:
            raise SystemExit(
                f"ERROR: unknown symbol {raw!r}: not in the NIFTY 50 universe "
                "(see data/nifty50_symbols.json)."
            )
        resolved.append(canonical)
    return resolved


def _ingest_symbol(db, service, symbol: str, start: date, end: date) -> str:
    """Ingest one symbol; returns the per-symbol summary line.

    Raises on failure (missing asset row, fetch/validation error) -- the
    caller decides whether to abort or continue.
    """
    asset = get_asset_by_symbol(db, symbol)
    if asset is None:
        raise LookupError(
            f"no assets row for {symbol!r} -- run "
            "'python apps/api/scripts/seed_assets.py' first"
        )
    df = service.get_ohlcv(symbol, start, end, timeframe="1d")
    counts = upsert_ohlcv_bars(db, asset.id, df, source="yfinance")
    return (
        f"{symbol}: fetched {len(df)} bars, inserted {counts['inserted']}, "
        f"skipped {counts['skipped']} (already present)"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    symbols = _resolve_symbols(args)

    service = CachedConnector(
        get_connector("yfinance"), OHLCVCache(), refresh=args.refresh
    )

    failures: list[tuple[str, str]] = []
    db = SessionLocal()
    try:
        for symbol in symbols:
            try:
                print(_ingest_symbol(db, service, symbol, args.start, args.end))
            except OperationalError as exc:
                # DB down: pointless to continue for any remaining symbol.
                print(DB_UNREACHABLE_HINT, file=sys.stderr)
                print(f"(driver error: {exc.orig})", file=sys.stderr)
                return 1
            except Exception as exc:  # noqa: BLE001 -- per-symbol isolation
                db.rollback()
                if not args.all:
                    print(f"ERROR: {symbol}: {exc}", file=sys.stderr)
                    return 1
                failures.append((symbol, str(exc)))
                print(f"{symbol}: FAILED ({exc})", file=sys.stderr)
    finally:
        db.close()

    if failures:
        print(
            f"\n{len(failures)}/{len(symbols)} symbols failed:", file=sys.stderr
        )
        width = max(len(symbol) for symbol, _ in failures)
        for symbol, message in failures:
            print(f"  {symbol:<{width}}  {message}", file=sys.stderr)
        return 1

    print(f"\nDone: {len(symbols)} symbol(s) ingested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
