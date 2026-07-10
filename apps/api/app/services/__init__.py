"""Business-logic services layer (Phase 5: the paper portfolio engine).

Routers stay thin (HTTP parsing, dependency injection, error-code mapping);
the actual paper-trading rules -- validation order, the risk-evaluation
veto, portfolio limit gates, fill simulation, NAV/drawdown math -- live here
so they can be unit-tested directly against a ``Session`` without spinning up
a FastAPI ``TestClient``.
"""
