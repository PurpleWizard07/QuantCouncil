"""The trading universe: NIFTY 50 constituents (NSE symbols).

NOTE: Index constituents change over time (NSE reviews the index
semi-annually, and symbols occasionally change on corporate actions or
renames). The metadata backing this module is a point-in-time snapshot taken
from publicly available NSE index data around the March 2025 index review,
and it is refreshed MANUALLY -- there is no automatic reconstitution.
Backtests over long histories therefore carry survivorship bias; this is an
accepted limitation of the v1 learning lab and is documented in the project
docs.

Source of truth: ``<repo_root>/data/nifty50_symbols.json``. This module
loads that JSON at import time and derives the module-level ``NIFTY50``
constant from it, so there is exactly one place (the JSON file) to update
when the index is reconstituted or a symbol is renamed. ``get_universe()``
exposes the full metadata records (name, exchange, sector, yfinance symbol)
for callers that need more than the bare symbol list.

Symbols are plain NSE tickers (no exchange suffix). Use
``to_yfinance_symbol`` to convert to Yahoo Finance format (".NS" suffix).

Path resolution: this package is developed and run as an editable install
from within the QuantCouncil monorepo (see ``pyproject.toml`` and the root
``requirements-dev.txt``), so the JSON file stays reachable relative to this
source file for the lifetime of the checkout. We locate it by walking up
from this module's directory looking for ``data/nifty50_symbols.json``
rather than hardcoding a fixed number of ``..`` segments, so the lookup
keeps working even if this package moves within the repo. This module is
not designed to work if the package is installed standalone (e.g. from a
built wheel) outside the monorepo, since the data file would not be bundled
-- that is an accepted v1 simplification for a personal, local-first project.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

YFINANCE_SUFFIX: str = ".NS"
"""Yahoo Finance suffix for NSE-listed symbols."""

_DATA_FILENAME = "nifty50_symbols.json"
_MAX_WALK_UP = 8
"""Generous upper bound on how many parent directories to check; the repo
root is only a few levels above this file, but walking further is cheap and
keeps this robust to the package being moved within the repo."""


class UniverseDataError(RuntimeError):
    """Raised when the NIFTY 50 metadata JSON cannot be located or parsed."""


def _find_data_file() -> Path:
    """Walk up from this module's directory to find ``data/<filename>``.

    Returns:
        Path to ``<repo_root>/data/nifty50_symbols.json``.

    Raises:
        UniverseDataError: If no ``data/nifty50_symbols.json`` is found
            within ``_MAX_WALK_UP`` parent directories.
    """
    here = Path(__file__).resolve()
    candidates = [here.parent, *here.parents][: _MAX_WALK_UP + 1]
    for parent in candidates:
        candidate = parent / "data" / _DATA_FILENAME
        if candidate.is_file():
            return candidate
    raise UniverseDataError(
        f"Could not locate 'data/{_DATA_FILENAME}' by walking up from {here}. "
        "Expected it at <repo_root>/data/nifty50_symbols.json -- this module "
        "requires running from within the QuantCouncil monorepo checkout."
    )


def _load_universe() -> list[dict[str, Any]]:
    """Load and lightly validate the NIFTY 50 metadata records from JSON."""
    path = _find_data_file()
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    try:
        records = payload["symbols"]
    except (TypeError, KeyError) as exc:
        raise UniverseDataError(
            f"{path} does not have the expected top-level 'symbols' array."
        ) from exc
    required_keys = {"symbol", "name", "exchange", "sector", "yfinance_symbol"}
    for record in records:
        missing = required_keys - record.keys()
        if missing:
            raise UniverseDataError(
                f"{path}: record {record!r} is missing key(s) {sorted(missing)}."
            )
    return records


_UNIVERSE: list[dict[str, Any]] = _load_universe()

NIFTY50: list[str] = [record["symbol"] for record in _UNIVERSE]
"""The 50 NIFTY 50 constituents as plain NSE symbols (manual snapshot),
derived from ``data/nifty50_symbols.json``."""


def get_universe() -> list[dict[str, Any]]:
    """Return the full NIFTY 50 metadata records.

    Each record has keys: ``symbol``, ``name``, ``exchange``, ``sector``,
    ``yfinance_symbol``. A defensive copy is returned so callers mutating
    the result cannot corrupt the module-level cache.

    Returns:
        List of 50 metadata dicts, in the same order as ``NIFTY50``.
    """
    return [dict(record) for record in _UNIVERSE]


def to_yfinance_symbol(symbol: str) -> str:
    """Convert a plain NSE symbol to its Yahoo Finance ticker.

    Example:
        >>> to_yfinance_symbol("RELIANCE")
        'RELIANCE.NS'
    """
    return f"{symbol}{YFINANCE_SUFFIX}"
