"""QuantCouncil data connectors.

Free market data only (yfinance active in Phase 2; OpenBB registered as an
inactive placeholder). Daily OHLCV bars for the NIFTY 50 universe. Every
connector implements the ``OHLCVConnector`` contract in ``data_connectors.base``
so that downstream code (quant_engine, the API) can rely on a single
validated DataFrame shape by calling ``get_ohlcv(...)`` -- never a specific
connector's ``fetch_daily`` directly.

Typical usage::

    from data_connectors import get_connector, OHLCVCache, CachedConnector

    connector = CachedConnector(get_connector("yfinance"), OHLCVCache())
    df = connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-12-31")

Phase 2: the abstract contract, the NIFTY 50 universe (backed by
``data/nifty50_symbols.json``), the yfinance connector, shared OHLCV
validation, and the local DuckDB/Parquet cache are all implemented. OpenBB
integration remains a registered but inactive placeholder.
"""

from __future__ import annotations

from data_connectors.base import OHLCVConnector
from data_connectors.cache import CachedConnector, OHLCVCache
from data_connectors.exceptions import CacheError, DataFetchError
from data_connectors.fundamentals import RawFundamentals, YFinanceFundamentalsConnector
from data_connectors.openbb_connector import OpenBBConnector
from data_connectors.registry import get_connector
from data_connectors.universe import (
    NIFTY50,
    YFINANCE_SUFFIX,
    get_universe,
    to_yfinance_symbol,
)
from data_connectors.validation import (
    DataValidationError,
    validate_ohlcv,
    validate_ohlcv_report,
)
from data_connectors.yfinance_connector import YFinanceConnector

__all__ = [
    "OHLCVConnector",
    "YFinanceConnector",
    "OpenBBConnector",
    "CachedConnector",
    "OHLCVCache",
    "get_connector",
    "NIFTY50",
    "YFINANCE_SUFFIX",
    "to_yfinance_symbol",
    "get_universe",
    "DataFetchError",
    "CacheError",
    "DataValidationError",
    "validate_ohlcv",
    "validate_ohlcv_report",
    "RawFundamentals",
    "YFinanceFundamentalsConnector",
]

__version__ = "0.1.0"
