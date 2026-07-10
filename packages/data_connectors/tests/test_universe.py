"""Foundation tests for the NIFTY 50 universe constants.

Also covers Phase 2's JSON-backed refactor: ``data/nifty50_symbols.json`` is
now the source of truth, and these tests confirm the JSON and the derived
``NIFTY50``/``get_universe()`` stay consistent.
"""

import json
import re
from pathlib import Path

from data_connectors.universe import (
    NIFTY50,
    YFINANCE_SUFFIX,
    get_universe,
    to_yfinance_symbol,
)

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&-]+$")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_JSON_PATH = _REPO_ROOT / "data" / "nifty50_symbols.json"


def test_nifty50_has_exactly_50_symbols() -> None:
    assert len(NIFTY50) == 50


def test_nifty50_symbols_are_unique() -> None:
    assert len(set(NIFTY50)) == len(NIFTY50)


def test_nifty50_symbol_format() -> None:
    for symbol in NIFTY50:
        assert SYMBOL_PATTERN.fullmatch(symbol), f"Bad symbol format: {symbol!r}"


def test_yfinance_suffix() -> None:
    assert YFINANCE_SUFFIX == ".NS"


def test_to_yfinance_symbol() -> None:
    assert to_yfinance_symbol("RELIANCE") == "RELIANCE.NS"
    assert to_yfinance_symbol("M&M") == "M&M.NS"


def _load_json_symbols() -> list[dict]:
    with _JSON_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)["symbols"]


def test_json_file_exists_at_expected_repo_root_path() -> None:
    assert _JSON_PATH.is_file(), f"Expected {_JSON_PATH} to exist"


def test_json_has_exactly_50_symbols_matching_nifty50_order() -> None:
    records = _load_json_symbols()
    assert [r["symbol"] for r in records] == NIFTY50


def test_json_records_have_required_metadata_keys() -> None:
    required_keys = {"symbol", "name", "exchange", "sector", "yfinance_symbol"}
    for record in _load_json_symbols():
        assert required_keys <= record.keys(), record


def test_json_yfinance_symbol_matches_to_yfinance_symbol() -> None:
    for record in _load_json_symbols():
        assert record["yfinance_symbol"] == to_yfinance_symbol(record["symbol"])


def test_json_exchange_is_nse() -> None:
    for record in _load_json_symbols():
        assert record["exchange"] == "NSE"


def test_json_name_and_sector_are_non_empty() -> None:
    for record in _load_json_symbols():
        assert record["name"].strip()
        assert record["sector"].strip()


def test_get_universe_returns_50_records_matching_nifty50() -> None:
    universe = get_universe()
    assert len(universe) == 50
    assert [r["symbol"] for r in universe] == NIFTY50


def test_get_universe_returns_defensive_copies() -> None:
    universe = get_universe()
    universe[0]["symbol"] = "MUTATED"
    universe.pop()
    # A fresh call must be unaffected by mutating a previously returned list.
    fresh = get_universe()
    assert len(fresh) == 50
    assert fresh[0]["symbol"] != "MUTATED"


def test_get_universe_records_are_dicts_with_string_values() -> None:
    for record in get_universe():
        for key in ("symbol", "name", "exchange", "sector", "yfinance_symbol"):
            assert isinstance(record[key], str)
