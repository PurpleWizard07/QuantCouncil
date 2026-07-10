"""Risk policy: the configurable, versioned rulebook the risk engine evaluates against.

Phase 4 redesign. The provisional fraction-based policy from the foundation
phase (``max_drawdown_limit=0.20`` etc., see the old
``docs/risk-policy.md``) is superseded by a YAML-backed policy where every
``_pct`` field is a PERCENT NUMBER, not a fraction -- ``max_allowed_drawdown_pct:
15`` means 15%, not 0.15. This is a deliberate convention change: it matches
how a human reads and edits the policy file, at the cost of engine.py having
to convert quant_engine's fraction-based metrics (e.g. ``max_drawdown=0.15``
for a 15% drawdown) to percent before comparing. See ``risk_engine.engine``
for the conversion (metric fraction * 100, compared against the ``_pct``
threshold -- consistently in that one direction, documented there).

The policy is loaded from ``packages/risk_engine/risk_policy.yaml`` by
default (one directory above this module -- see ``_default_policy_path``).
Loading is a plain function, not cached: tests load different policy files
in the same process, so ``functools.lru_cache`` would be actively wrong here.
Loading the same file twice must still produce equal-by-value, independent
``RiskPolicy`` instances (pydantic models compare by value, and each call
parses the YAML fresh, so this holds for free).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

_POLICY_FILENAME = "risk_policy.yaml"
_MAX_WALK_UP = 8
"""Generous upper bound on parent directories to check when resolving the
default policy path, mirroring the walk-up-from-file-location pattern used by
``data_connectors.universe._find_data_file``."""


class RiskPolicyError(ValueError):
    """Raised when a risk policy file cannot be loaded or fails validation.

    Wraps YAML syntax errors, missing files, and pydantic schema violations
    (missing key, wrong type, unknown extra key) behind one clear message --
    callers never see a raw ``yaml.YAMLError`` or ``pydantic.ValidationError``
    traceback.
    """


class RiskPolicy(BaseModel):
    """Thresholds and limits applied by the deterministic risk engine.

    Every field name and default matches ``risk_policy.yaml`` exactly (see
    ``load_policy``). Fields ending in ``_pct`` are PERCENT numbers (``15``
    means 15%, not the fraction ``0.15``) -- the Phase 4 convention. Metrics
    coming out of quant_engine (e.g. ``BacktestResult.max_drawdown``) are
    fractions; ``risk_engine.engine`` multiplies them by 100 before comparing
    against these thresholds.
    """

    model_config = ConfigDict(extra="forbid")

    policy_version: str = Field(
        description="Version tag stored with every risk evaluation for auditability."
    )
    minimum_backtest_trades: int = Field(
        description=(
            "Minimum number of closed backtest trades required before the "
            "statistics are considered meaningful (hard gate: bt_min_trades)."
        )
    )
    max_allowed_drawdown_pct: float = Field(
        description=(
            "Maximum acceptable backtest max drawdown, as a PERCENT number "
            "(15 == 15%). Hard gate: bt_max_drawdown. Compared against "
            "metrics['max_drawdown'] * 100."
        )
    )
    minimum_profit_factor: float = Field(
        description=(
            "Minimum acceptable backtest profit factor (gross profit / gross "
            "loss). Hard gate: bt_min_profit_factor. A None profit_factor "
            "(no losing trades) skips this gate -- see engine.py."
        )
    )
    minimum_total_return_pct: float = Field(
        description=(
            "Minimum acceptable total return, as a PERCENT number (0 means "
            "the backtest must not lose money). Hard gate: bt_min_total_return. "
            "Compared against metrics['total_return'] * 100."
        )
    )
    minimum_sharpe_like: float = Field(
        description=(
            "Minimum acceptable Sharpe-like ratio from the backtest (not a "
            "percent; sharpe is already a unitless ratio). Hard gate: "
            "bt_min_sharpe."
        )
    )
    max_position_size_pct: float = Field(
        description=(
            "Maximum allowed single-position allocation, as a PERCENT number "
            "(10 == 10% of capital). Hard gate: bt_max_position_size. Compared "
            "against strategy_config['max_allocation_pct'] * 100 when provided."
        )
    )
    max_risk_per_trade_pct: float = Field(
        description=(
            "Maximum allowed risk-percent position sizing, as a PERCENT "
            "number (1 == 1% of capital at risk per trade). Hard gate: "
            "bt_max_risk_per_trade. Compared against "
            "strategy['position_sizing']['value'] * 100."
        )
    )
    max_open_positions: int = Field(
        description=(
            "Maximum number of simultaneously open paper positions. Only "
            "evaluated when a live portfolio_context is supplied (Phase 4 has "
            "no live paper portfolio yet, so this gate is currently dormant)."
        )
    )
    max_portfolio_drawdown_pct: float = Field(
        description=(
            "Portfolio drawdown, as a PERCENT number, that triggers risk-off. "
            "Only evaluated when a live portfolio_context is supplied (dormant "
            "in Phase 4; see max_open_positions)."
        )
    )
    stop_loss_required: bool = Field(
        description=(
            "Every strategy must define a stop_loss before entry. Hard gate: "
            "bt_stop_loss_required. Already schema-mandatory in "
            "quant_engine.strategy.validate_strategy; checked here too for "
            "defense-in-depth."
        )
    )
    reject_if_data_quality_bad: bool = Field(
        description=(
            "If true, a caller-flagged data_quality_bad=True hard-rejects the "
            "evaluation. Hard gate: bt_data_quality."
        )
    )
    warn_if_exposure_time_pct_above: float = Field(
        description=(
            "Warn when exposure_time, as a PERCENT number, exceeds this "
            "threshold (warn_high_exposure). Compared against "
            "metrics['exposure_time'] * 100."
        )
    )
    warn_if_trade_count_below: int = Field(
        description=(
            "Warn when num_trades is below this count (warn_low_trade_count), "
            "and also used to decide whether an infinite profit_factor is "
            "still statistically thin (warn_profit_factor_infinite_small_sample)."
        )
    )
    warn_if_profit_factor_below: float = Field(
        description="Warn when profit_factor is below this value (warn_low_profit_factor)."
    )
    warn_if_drawdown_pct_above: float = Field(
        description=(
            "Warn when max_drawdown, as a PERCENT number, exceeds this "
            "threshold (warn_high_drawdown). Compared against "
            "metrics['max_drawdown'] * 100."
        )
    )


def _default_policy_path() -> Path:
    """Walk up from this module's directory to find ``risk_policy.yaml``.

    Robust regardless of the caller's working directory (mirrors
    ``data_connectors.universe._find_data_file``): the packaged policy file
    lives one directory above the ``risk_engine`` package
    (``packages/risk_engine/risk_policy.yaml``), but we walk up rather than
    hardcoding a fixed number of ``..`` segments so this keeps working if the
    package moves within the repo.

    Raises:
        RiskPolicyError: If no ``risk_policy.yaml`` is found within
            ``_MAX_WALK_UP`` parent directories.
    """
    here = Path(__file__).resolve()
    candidates = [here.parent, *here.parents][: _MAX_WALK_UP + 1]
    for parent in candidates:
        candidate = parent / _POLICY_FILENAME
        if candidate.is_file():
            return candidate
    raise RiskPolicyError(
        f"Could not locate '{_POLICY_FILENAME}' by walking up from {here}. "
        "Expected it at <repo_root>/packages/risk_engine/risk_policy.yaml -- "
        "this module requires running from within the QuantCouncil monorepo "
        "checkout, or pass an explicit path to load_policy()."
    )


def load_policy(path: Path | str | None = None) -> RiskPolicy:
    """Load and validate a risk policy YAML file into a ``RiskPolicy``.

    Deterministic: the same file always loads to an equal-by-value
    ``RiskPolicy`` (a fresh, independent instance each call -- no caching, by
    design, since tests need to load different policy files within the same
    process).

    Args:
        path: Path to a policy YAML file. ``None`` (the default) resolves to
            the packaged ``risk_policy.yaml`` via ``_default_policy_path``.

    Returns:
        A validated ``RiskPolicy``.

    Raises:
        RiskPolicyError: If the file is missing, is not valid YAML, does not
            parse to a mapping, is missing a required key, has a key of the
            wrong type, or has an unknown extra key. Never leaks a raw
            ``yaml.YAMLError`` or ``pydantic.ValidationError`` traceback.
    """
    resolved = _default_policy_path() if path is None else Path(path)

    if not resolved.is_file():
        raise RiskPolicyError(f"Risk policy file not found: {resolved}")

    try:
        raw_text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise RiskPolicyError(f"Could not read risk policy file {resolved}: {exc}") from exc

    try:
        payload: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise RiskPolicyError(f"Malformed YAML in risk policy file {resolved}: {exc}") from exc

    if not isinstance(payload, dict):
        raise RiskPolicyError(
            f"Risk policy file {resolved} must contain a YAML mapping at the "
            f"top level, got {type(payload).__name__}."
        )

    try:
        return RiskPolicy(**payload)
    except ValidationError as exc:
        raise RiskPolicyError(
            f"Risk policy file {resolved} failed schema validation: {exc}"
        ) from exc


def default_policy() -> RiskPolicy:
    """Convenience wrapper: ``load_policy(None)`` -- the packaged default policy."""
    return load_policy(None)
