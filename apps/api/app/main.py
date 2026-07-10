"""QuantCouncil API entrypoint.

Run locally from apps/api:  uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import assets, backtests, committee, health, paper, risk, strategies

settings = get_settings()

app = FastAPI(
    title="QuantCouncil API",
    version="0.1.0",
    description=(
        "Personal AI quant research and PAPER-TRADING-ONLY lab: learning, "
        "simulation, backtesting, and AI-agent experimentation on the NIFTY 50 "
        "universe (daily timeframe, long-only). No real-money trading, no "
        "broker connectivity, no financial advice. AI can propose. Math can "
        "approve. Risk can veto."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(assets.router)
app.include_router(strategies.router)
app.include_router(backtests.router)
app.include_router(risk.router)
app.include_router(paper.router)
app.include_router(committee.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "quantcouncil-api", "version": "0.1.0", "docs": "/docs"}
