"""Strategy definition schema validation.

Validates strategy definitions against the strict-JSON contract documented in
docs/strategy-format.md (Phase 3). ``validate_strategy`` is the single entry
point: it accepts a plain ``dict``, raises :class:`StrategyValidationError`
with a message naming the offending key/value on any schema violation, and
otherwise returns a normalized deep copy that downstream code
(``quant_engine.signals``, the backtester, the API layer) can trust without
re-validating.

This module intentionally does NOT check that ``universe`` symbols are a
subset of the NIFTY 50 constituent list -- that lookup depends on data the
API layer owns, not this package.
"""

from __future__ import annotations

from typing import Any

_TIMEFRAME = "1d"
_DIRECTION = "long_only"

_TOP_LEVEL_REQUIRED = {
    "name",
    "universe",
    "timeframe",
    "direction",
    "entry",
    "exit",
    "stop_loss",
    "position_sizing",
}
_TOP_LEVEL_OPTIONAL = {"description", "max_holding_days", "costs"}
_TOP_LEVEL_FIELDS = _TOP_LEVEL_REQUIRED | _TOP_LEVEL_OPTIONAL

_COMBINATORS = {"all", "any"}

_OPERATORS = {"crosses_above", "crosses_below", "greater_than", "less_than"}

# Indicator name -> set of required params keys. Indicators not listed here
# take no params at all (close, volume).
_WINDOW_INDICATORS = {"sma", "ema", "rsi", "volume_sma", "highest_close"}
_PARAMLESS_INDICATORS = {"close", "volume"}
_INDICATORS = _WINDOW_INDICATORS | _PARAMLESS_INDICATORS

_CONDITION_KEYS = {"indicator", "params", "op", "value", "target"}
_CONDITION_REQUIRED_KEYS = {"indicator", "params", "op"}
_TARGET_KEYS = {"indicator", "params", "multiplier"}
_TARGET_REQUIRED_KEYS = {"indicator", "params"}

_STOP_LOSS_KEYS = {"type", "value"}
_POSITION_SIZING_KEYS = {"type", "value"}
_COST_KEYS = {"transaction_cost_pct", "slippage_pct"}


class StrategyValidationError(ValueError):
    """Raised when a strategy definition dict violates the v1 schema."""


def validate_strategy(definition: dict) -> dict:
    """Validate a strategy definition dict against the v1 schema.

    Strict: unknown top-level keys, unknown condition/target keys, unknown
    operators, unknown indicators, and unknown combinator keys are all
    rejected with a message naming the offending key or value plus the
    allowed options. See docs/strategy-format.md for the full contract.

    Args:
        definition: The strategy definition, e.g. loaded from JSON.

    Returns:
        A normalized deep copy of ``definition``. Normalization fills in
        defaults omitted by the caller (currently: ``target.multiplier``
        defaults to ``1.0``) and coerces numeric fields to ``float``/``int``
        as appropriate. The returned dict never aliases ``definition`` --
        mutating it has no effect on the input.

    Raises:
        StrategyValidationError: If ``definition`` violates the schema.
    """
    if not isinstance(definition, dict):
        raise StrategyValidationError(
            f"strategy definition must be an object, got {type(definition).__name__}"
        )

    extra = set(definition.keys()) - _TOP_LEVEL_FIELDS
    if extra:
        raise StrategyValidationError(
            f"unknown top-level key(s) {sorted(extra)}; allowed keys are {sorted(_TOP_LEVEL_FIELDS)}"
        )
    missing = _TOP_LEVEL_REQUIRED - set(definition.keys())
    if missing:
        raise StrategyValidationError(f"missing required top-level key(s) {sorted(missing)}")

    normalized: dict[str, Any] = {}

    name = definition["name"]
    if not isinstance(name, str) or not name.strip():
        raise StrategyValidationError(f"name: must be a non-empty string, got {name!r}")
    normalized["name"] = name

    if "description" in definition:
        description = definition["description"]
        if not isinstance(description, str):
            raise StrategyValidationError(
                f"description: must be a string, got {type(description).__name__}"
            )
        normalized["description"] = description

    normalized["universe"] = _validate_universe(definition["universe"])

    timeframe = definition["timeframe"]
    if timeframe != _TIMEFRAME:
        raise StrategyValidationError(
            f"timeframe: only {_TIMEFRAME!r} is supported (daily only in v1), got {timeframe!r}"
        )
    normalized["timeframe"] = timeframe

    direction = definition["direction"]
    if direction != _DIRECTION:
        raise StrategyValidationError(
            f"direction: only {_DIRECTION!r} is supported in v1, got {direction!r}"
        )
    normalized["direction"] = direction

    normalized["entry"] = _validate_condition_tree(definition["entry"], "entry")
    normalized["exit"] = _validate_condition_tree(definition["exit"], "exit")

    normalized["stop_loss"] = _validate_stop_loss(definition["stop_loss"])
    normalized["position_sizing"] = _validate_position_sizing(definition["position_sizing"])

    if "max_holding_days" in definition:
        normalized["max_holding_days"] = _validate_max_holding_days(
            definition["max_holding_days"]
        )

    if "costs" in definition:
        normalized["costs"] = _validate_costs(definition["costs"])

    return normalized


def _validate_universe(universe: Any) -> list[str]:
    if not isinstance(universe, list) or len(universe) == 0:
        raise StrategyValidationError(f"universe: must be a non-empty list, got {universe!r}")
    normalized = []
    for i, symbol in enumerate(universe):
        if not isinstance(symbol, str) or not symbol.strip():
            raise StrategyValidationError(f"universe[{i}]: must be a non-empty string, got {symbol!r}")
        normalized.append(symbol)
    return normalized


def _is_number(value: Any) -> bool:
    """True for int/float, explicitly excluding bool (a JSON true/false)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_condition_tree(node: Any, path: str) -> dict:
    """Recursively validate a combinator or leaf condition node.

    Args:
        node: The condition tree node (a combinator dict or a condition dict).
        path: Dotted/indexed path to ``node``, used only for error messages.

    Returns:
        The normalized node.

    Raises:
        StrategyValidationError: If ``node`` violates the schema.
    """
    if not isinstance(node, dict):
        raise StrategyValidationError(
            f"{path}: condition tree node must be an object, got {type(node).__name__}"
        )

    combinator_keys = [key for key in _COMBINATORS if key in node]
    if combinator_keys:
        extra = set(node.keys()) - _COMBINATORS
        if extra:
            raise StrategyValidationError(
                f"{path}: combinator node allows only one of {sorted(_COMBINATORS)}, "
                f"found extra/unknown key(s) {sorted(extra)}"
            )
        if len(combinator_keys) != 1:
            raise StrategyValidationError(
                f"{path}: combinator node must contain exactly one of {sorted(_COMBINATORS)}, "
                f"found both {sorted(combinator_keys)}"
            )
        key = combinator_keys[0]
        children = node[key]
        if not isinstance(children, list) or len(children) == 0:
            raise StrategyValidationError(
                f"{path}.{key}: combinator list must be a non-empty list, got {children!r}"
            )
        return {
            key: [
                _validate_condition_tree(child, f"{path}.{key}[{i}]")
                for i, child in enumerate(children)
            ]
        }

    return _validate_condition(node, path)


def _validate_condition(node: dict, path: str) -> dict:
    extra = set(node.keys()) - _CONDITION_KEYS
    if extra:
        raise StrategyValidationError(
            f"{path}: unknown condition key(s) {sorted(extra)}; allowed keys are {sorted(_CONDITION_KEYS)}"
        )
    missing = _CONDITION_REQUIRED_KEYS - set(node.keys())
    if missing:
        raise StrategyValidationError(f"{path}: condition missing required key(s) {sorted(missing)}")

    indicator, params = _validate_indicator_ref(node["indicator"], node["params"], path)

    op = node["op"]
    if op not in _OPERATORS:
        raise StrategyValidationError(
            f"{path}.op: unknown operator {op!r}; allowed operators are {sorted(_OPERATORS)}"
        )

    has_value = "value" in node
    has_target = "target" in node
    if has_value and has_target:
        raise StrategyValidationError(
            f"{path}: exactly one of 'value' or 'target' is allowed, found both"
        )
    if not has_value and not has_target:
        raise StrategyValidationError(
            f"{path}: exactly one of 'value' or 'target' is required, found neither"
        )

    result: dict[str, Any] = {"indicator": indicator, "params": params, "op": op}

    if has_value:
        value = node["value"]
        if not _is_number(value):
            raise StrategyValidationError(f"{path}.value: must be numeric, got {value!r}")
        result["value"] = float(value)
    else:
        result["target"] = _validate_target(node["target"], f"{path}.target")

    return result


def _validate_target(target: Any, path: str) -> dict:
    if not isinstance(target, dict):
        raise StrategyValidationError(f"{path}: must be an object, got {type(target).__name__}")

    extra = set(target.keys()) - _TARGET_KEYS
    if extra:
        raise StrategyValidationError(
            f"{path}: unknown key(s) {sorted(extra)}; allowed keys are {sorted(_TARGET_KEYS)}"
        )
    missing = _TARGET_REQUIRED_KEYS - set(target.keys())
    if missing:
        raise StrategyValidationError(f"{path}: missing required key(s) {sorted(missing)}")

    indicator, params = _validate_indicator_ref(target["indicator"], target["params"], path)

    multiplier = target.get("multiplier", 1.0)
    if not _is_number(multiplier):
        raise StrategyValidationError(f"{path}.multiplier: must be numeric, got {multiplier!r}")
    multiplier = float(multiplier)
    if multiplier <= 0:
        raise StrategyValidationError(
            f"{path}.multiplier: must be a positive number, got {multiplier}"
        )

    return {"indicator": indicator, "params": params, "multiplier": multiplier}


def _validate_indicator_ref(indicator: Any, params: Any, path: str) -> tuple[str, dict]:
    """Validate an ``{indicator, params}`` pair (shared by conditions and targets)."""
    if indicator not in _INDICATORS:
        raise StrategyValidationError(
            f"{path}.indicator: unknown indicator {indicator!r}; allowed indicators are "
            f"{sorted(_INDICATORS)}"
        )
    if not isinstance(params, dict):
        raise StrategyValidationError(f"{path}.params: must be an object, got {type(params).__name__}")

    if indicator in _WINDOW_INDICATORS:
        expected_keys = {"window"}
    else:
        expected_keys = set()

    extra = set(params.keys()) - expected_keys
    if extra:
        raise StrategyValidationError(
            f"{path}.params: unknown param(s) {sorted(extra)} for indicator {indicator!r}; "
            f"expected {sorted(expected_keys) if expected_keys else 'no params'}"
        )
    param_missing = expected_keys - set(params.keys())
    if param_missing:
        raise StrategyValidationError(
            f"{path}.params: missing required param(s) {sorted(param_missing)} for indicator {indicator!r}"
        )

    if indicator not in _WINDOW_INDICATORS:
        return indicator, {}

    window = params["window"]
    if isinstance(window, bool) or not isinstance(window, int) or window < 1:
        raise StrategyValidationError(
            f"{path}.params.window: must be an integer >= 1 for indicator {indicator!r}, got {window!r}"
        )
    return indicator, {"window": window}


def _validate_stop_loss(stop_loss: Any) -> dict:
    if not isinstance(stop_loss, dict):
        raise StrategyValidationError(f"stop_loss: must be an object, got {type(stop_loss).__name__}")
    extra = set(stop_loss.keys()) - _STOP_LOSS_KEYS
    if extra:
        raise StrategyValidationError(
            f"stop_loss: unknown key(s) {sorted(extra)}; allowed keys are {sorted(_STOP_LOSS_KEYS)}"
        )
    missing = _STOP_LOSS_KEYS - set(stop_loss.keys())
    if missing:
        raise StrategyValidationError(f"stop_loss: missing required key(s) {sorted(missing)}")

    stop_type = stop_loss["type"]
    if stop_type == "atr":
        raise StrategyValidationError(
            "stop_loss.type: 'atr' is reserved for a later phase; only 'percent' is supported in v1"
        )
    if stop_type != "percent":
        raise StrategyValidationError(
            f"stop_loss.type: unknown type {stop_type!r}; allowed types are ['percent']"
        )

    value = stop_loss["value"]
    if not _is_number(value) or not (0 < value < 1):
        raise StrategyValidationError(f"stop_loss.value: must be a number in (0, 1), got {value!r}")

    return {"type": "percent", "value": float(value)}


def _validate_position_sizing(position_sizing: Any) -> dict:
    if not isinstance(position_sizing, dict):
        raise StrategyValidationError(
            f"position_sizing: must be an object, got {type(position_sizing).__name__}"
        )
    extra = set(position_sizing.keys()) - _POSITION_SIZING_KEYS
    if extra:
        raise StrategyValidationError(
            f"position_sizing: unknown key(s) {sorted(extra)}; allowed keys are "
            f"{sorted(_POSITION_SIZING_KEYS)}"
        )
    missing = _POSITION_SIZING_KEYS - set(position_sizing.keys())
    if missing:
        raise StrategyValidationError(f"position_sizing: missing required key(s) {sorted(missing)}")

    sizing_type = position_sizing["type"]
    if sizing_type != "risk_percent":
        raise StrategyValidationError(
            f"position_sizing.type: unknown type {sizing_type!r}; allowed types are ['risk_percent']"
        )

    value = position_sizing["value"]
    if not _is_number(value) or not (0 < value < 1):
        raise StrategyValidationError(
            f"position_sizing.value: must be a number in (0, 1), got {value!r}"
        )

    return {"type": "risk_percent", "value": float(value)}


def _validate_max_holding_days(max_holding_days: Any) -> int:
    if isinstance(max_holding_days, bool) or not isinstance(max_holding_days, int) or max_holding_days < 1:
        raise StrategyValidationError(
            f"max_holding_days: must be an integer >= 1, got {max_holding_days!r}"
        )
    return max_holding_days


def _validate_costs(costs: Any) -> dict:
    if not isinstance(costs, dict):
        raise StrategyValidationError(f"costs: must be an object, got {type(costs).__name__}")
    extra = set(costs.keys()) - _COST_KEYS
    if extra:
        raise StrategyValidationError(
            f"costs: unknown key(s) {sorted(extra)}; allowed keys are {sorted(_COST_KEYS)}"
        )

    normalized: dict[str, float] = {}
    for key in _COST_KEYS:
        if key not in costs:
            continue
        value = costs[key]
        if not _is_number(value) or not (0 <= value < 1):
            raise StrategyValidationError(f"costs.{key}: must be a number in [0, 1), got {value!r}")
        normalized[key] = float(value)
    return normalized
