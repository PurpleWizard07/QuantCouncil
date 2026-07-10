# QuantCouncil MCP Server (Phase 8, optional)

An optional Model Context Protocol (MCP) server exposing QuantCouncil's
paper-trading and research capabilities as tools. **This server is out of
scope until Phase 8** -- this package is a documented placeholder so the tool
surface is agreed on before any code exists.

Philosophy: "AI can propose. Math can approve. Risk can veto." The MCP server
changes nothing about that pipeline; it only exposes the same deterministic,
paper-only actions the rest of the system uses.

## Planned tool surface (allowed execution actions)

Exactly these six actions, and no others:

1. `create_paper_order`
2. `simulate_order_fill`
3. `mark_to_market`
4. `update_paper_positions`
5. `calculate_paper_nav`
6. `write_trade_journal_entry`

All tools operate exclusively on the paper portfolio (starting capital
1,000,000 INR) and are subject to the same guards as the API: no paper trade
without a backtest, no paper trade without a risk evaluation, no paper trade
if the risk engine rejects.

## Disallowed actions (will never be implemented)

The following actions are permanently out of scope for this server and for
QuantCouncil as a whole. They will never be implemented, in any phase:

1. `place_real_order`
2. `modify_real_order`
3. `cancel_real_order`
4. `connect_broker_account`
5. `fetch_real_broker_holdings`
6. `execute_live_strategy`
7. `auto_trade_real_money`

QuantCouncil is a learning and simulation lab. There is no real-money
trading, no broker connectivity, and no live execution anywhere in the
project, and this MCP server is no exception.

## Status

- Foundation phase: placeholder only (`__init__.py` docstring + this README).
- Phase 8: implement the six allowed tools over the existing API/services.
