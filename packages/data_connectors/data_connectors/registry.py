"""Connector factory: look up an ``OHLCVConnector`` by name.

Downstream code should depend on :func:`get_connector` (or on the
``OHLCVConnector`` / ``get_ohlcv`` interface generally) rather than
importing a specific connector class directly, so the active data source
can be swapped -- or wrapped in a cache -- without touching call sites.
"""

from __future__ import annotations

from data_connectors.base import OHLCVConnector
from data_connectors.openbb_connector import OpenBBConnector
from data_connectors.yfinance_connector import YFinanceConnector

_CONNECTORS: dict[str, type[OHLCVConnector]] = {
    "yfinance": YFinanceConnector,
    # Registered for interface completeness; inactive in v1 -- see
    # openbb_connector.py. Calling get_ohlcv()/fetch_daily() on it raises
    # NotImplementedError.
    "openbb": OpenBBConnector,
}


def get_connector(name: str = "yfinance") -> OHLCVConnector:
    """Instantiate a registered ``OHLCVConnector`` by name.

    Args:
        name: Registry key, case-insensitive. One of ``"yfinance"``
            (active) or ``"openbb"`` (placeholder -- instantiates fine, but
            raises ``NotImplementedError`` on use).

    Returns:
        A new connector instance.

    Raises:
        ValueError: If ``name`` is not a registered connector.
    """
    key = name.lower()
    try:
        connector_cls = _CONNECTORS[key]
    except KeyError as exc:
        available = ", ".join(sorted(_CONNECTORS))
        raise ValueError(
            f"Unknown connector {name!r}. Available connectors: {available}."
        ) from exc
    return connector_cls()
