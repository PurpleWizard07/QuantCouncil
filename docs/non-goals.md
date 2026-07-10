# QuantCouncil Non-Goals

This document enumerates everything QuantCouncil deliberately does **not** do. These exclusions
are part of the project constitution: no phase of the
[development roadmap](development-roadmap.md) may introduce them, and no feature request may
override them without rewriting this constitution first.

## Enumerated Non-Goals

| # | Non-goal | Rationale |
|---|---|---|
| 1 | **Not a real-money trading system** | QuantCouncil is a learning and simulation lab; putting real capital at risk contradicts its entire purpose. |
| 2 | **No broker execution or broker integration** | No broker API is ever connected, eliminating any code path by which a simulated decision could become a real order. |
| 3 | **Not stock tips or financial advice** | All outputs are simulated research artifacts for personal learning; nothing produced by the system is a recommendation to anyone. |
| 4 | **No guaranteed-profit claims** | Backtests are historical simulations with survivorship and overfitting risks; no code, doc, or UI text may promise or imply future returns. |
| 5 | **No options / F&O** | Non-linear payoffs and margin mechanics are out of scope; v1 is long-only cash equities. |
| 6 | **No futures** | Leverage and margin modeling are out of scope for a daily-timeframe paper lab. |
| 7 | **No crypto** | The universe is NSE-listed NIFTY 50 equities only; different market structure, out of scope. |
| 8 | **No intraday scalping** | The system operates on the daily timeframe only; intraday data, latency, and microstructure modeling are out of scope. |
| 9 | **No reinforcement learning in v1** | Strategies are explicit, auditable rule trees (see [strategy-format.md](strategy-format.md)); RL policies are opaque and defeat the audit-first design. |
| 10 | **No short selling in v1** | Long-only keeps position accounting, risk sizing, and the fill model simple and verifiable. |
| 11 | **No premium or paid data in v1** | Local-first principle: free yfinance data only; no data subscriptions. |
| 12 | **No hosted deployment requirement in v1** | Everything runs on the local machine via Docker Compose and local dev servers; no cloud infrastructure is required. |

## Disallowed Execution Actions (Verbatim)

The following actions are disallowed in every component, every agent tool definition, every MCP
tool surface, and every phase:

- `place_real_order`
- `modify_real_order`
- `cancel_real_order`
- `connect_broker_account`
- `fetch_real_broker_holdings`
- `execute_live_strategy`
- `auto_trade_real_money`

These actions are **permanently out of scope regardless of phase**. They must never appear as
implemented functions, stubs, feature flags, configuration options, or agent-callable tools. The
only execution actions the system may ever expose are the allowed paper-trading actions listed
verbatim in [paper-trading-design.md](paper-trading-design.md).

## Relationship to the Hard Rules

The non-goals above complement the runtime hard rules described in
[architecture.md](architecture.md): LLM agents never invent numbers, deterministic Python is the
source of truth, and the risk engine's veto binds the CIO agent
(see [risk-policy.md](risk-policy.md)).
