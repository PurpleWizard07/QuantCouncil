# 08 — Strategy Development

> ⬅ Back to [README](../README.md) · Prev: [07 Risk Management](../07-risk-management/README.md) · Next: [09 Futures](../09-futures/README.md)

> 💡 **Key takeaway:** "This setup looks good" is not a strategy. A **strategy** is a set of rules so
> precise that a stranger — or a computer — would take the *same* trades you would. Vagueness is where
> hindsight, bias, and inconsistency creep in. This section turns intuition into a system.

**Learning objectives:** specify a complete strategy (the 10 components); distinguish rules-based vs
discretionary; document a trading plan and keep a useful journal.

---

## The 10 components of a complete strategy

A strategy is under-specified until *all ten* are unambiguous:

| # | Component | The question it answers | Example (a swing momentum idea) |
|---|---|---|---|
| 1 | **Hypothesis** | *Why* should this make money? What edge/mechanism? | "Stocks breaking to 52-wk highs on volume tend to continue for weeks (momentum)." |
| 2 | **Universe & regime filter** | *What* do you trade and *when* is it valid? | Liquid NSE stocks; only when NIFTY is above its 200-DMA ([regime](../05-technical-analysis/README.md#adx)) |
| 3 | **Entry** | *Exact* trigger to get in | Close > 52-wk high AND volume > 1.5× 20-day avg |
| 4 | **Stop** | Where the thesis is *wrong* | Below the breakout level / 2×[ATR](../05-technical-analysis/README.md#atr-average-true-range) |
| 5 | **Exit (target/trail)** | How you *take profit* | Trail a 3×ATR stop; or exit on close < 20-DMA |
| 6 | **Position sizing** | *How much* | [Risk-per-trade](../07-risk-management/README.md#2-risk-per-trade--position-sizing) = 1%, sized off the stop |
| 7 | **Time horizon** | Expected holding period | Days–weeks |
| 8 | **Filters** | What to *avoid* | Skip earnings within N days ([event/gap risk](../03-price-and-market-behavior/README.md#7-forced-flows-and-positioning)) |
| 9 | **Execution** | Order types, timing, slippage plan | Limit orders near close; avoid illiquid opens |
| 10 | **Risk limits** | Portfolio-level guardrails | Max heat 6%; max 3 correlated names ([correlation](../07-risk-management/README.md#10-portfolio-level-risk-correlation-exposure-leverage)) |

> ⚠️ **Common mistake:** Specifying only entries and leaving exits/sizing "to feel." Since
> [exits and sizing dominate results](../07-risk-management/README.md#1-why-risk-management-comes-first),
> a great entry with fuzzy exits is not a strategy — it's a hope.

---

## Rules-based vs discretionary

| | **Rules-based (systematic)** | **Discretionary** |
|---|---|---|
| Decisions | Mechanical, from fixed rules | Judgment within a framework |
| Backtestable | Yes, cleanly | Hard (hindsight contaminates) |
| Failure mode | Rules stop fitting the market | Emotion/bias creep; inconsistency |
| Strength | Consistent, testable, scalable | Adapts to context a rulebook misses |

Most durable retail approaches are **rules-based or heavily rule-guided**, because rules are
[testable](../12-backtesting-and-statistics/README.md) and immune to in-the-moment
[psychology](../11-trading-psychology/README.md). Discretionary trading can work but demands elite
self-honesty and is very hard to validate.

---

## From idea → validated system (the workflow)

1. **Write the hypothesis and mechanism** (component 1). If you can't articulate *why* an edge exists,
   be suspicious.
2. **Define all 10 components mechanically.**
3. **[Backtest](../12-backtesting-and-statistics/README.md) with realistic Indian costs/slippage**;
   judge on [expectancy, Sharpe, drawdown](../12-backtesting-and-statistics/README.md#the-sharpe-ratio),
   not win rate.
4. **Validate [out-of-sample / walk-forward](../12-backtesting-and-statistics/README.md#8-validation-traintest-walk-forward-out-of-sample)**;
   run [Monte Carlo](../12-backtesting-and-statistics/README.md#9-monte-carlo-and-the-bootstrap) to see
   possible drawdowns.
5. **[Paper trade](../18-practical-trading/README.md)** to catch execution gaps the backtest missed.
6. **Go live tiny**, scale only with evidence.

---

## Trading plan & journal (templates)

### One-page trading plan
```text
STRATEGY NAME:
Hypothesis (why edge exists):
Universe & regime filter:
Entry rules:
Stop rules:
Exit/target/trail rules:
Position sizing (risk % / method):
Filters (avoid):
Execution (order types/timing):
Risk limits (max heat, correlation caps, daily loss limit):
Review cadence:
```

### Trade journal (per trade)
```text
Date | Instrument | Setup/why | Entry | Stop | Size | Risk (₹/R) |
Exit | Result (R) | Costs | Followed plan? (Y/N) | Mistake? | Screenshot | Notes
```

> 💡 **Key takeaway:** The journal's most valuable column is **"Followed plan? (Y/N)"** — separating
> *process* from *outcome*. A losing trade that followed the plan is a *good* trade; a winning trade
> that broke the plan is a *dangerous* one. Grade yourself on **process**, and the outcomes follow.

**✅ Ready to move on when:** a stranger could execute your written strategy and get materially the same
trades — and your journal lets you review *decisions*, not just P&L.

---
*Outline — ask to expand into 2–3 fully-worked example strategies (trend, mean-reversion, event) with
complete rules and a filled-in journal.*

### Related
[07 Risk Management](../07-risk-management/README.md) · [12 Backtesting](../12-backtesting-and-statistics/README.md) · [13 Algorithmic Trading](../13-algorithmic-trading/README.md) · [18 Practical Trading](../18-practical-trading/README.md) · [Glossary](../glossary/README.md)

> Next: [09 — Futures](../09-futures/README.md) →
