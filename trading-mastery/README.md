# Trading Mastery — A First-Principles Knowledge Base

> A serious, skeptical, textbook-grade reference that takes you from *"what is money?"* to
> discretionary, quantitative, and algorithmic trading — with concrete Indian-market examples
> (NSE/BSE, NIFTY/SENSEX, INR) and risk management treated as a first-class citizen.

---

## ⚠️ Read this first

This is an **educational reference**, not investment advice, not a signal service, and not a
promise that you will make money. Most people who actively trade **lose money** after costs —
this is not cynicism, it is the documented base rate (see
[Indian Markets → The retail F&O reality](17-indian-markets/README.md#the-retail-fo-reality)).
The purpose of this knowledge base is to help you understand markets deeply enough to make your
own informed decisions and to *survive long enough to possibly get good*.

Three commitments run through every page:

1. **First principles.** No term is assumed. If you see jargon, it is defined here or in the
   [Glossary](glossary/README.md).
2. **Why, not just what.** Every important concept comes with the underlying mechanism.
3. **Skepticism.** Claims are tagged so you always know what kind of thing you are reading:

| Tag | Meaning |
|---|---|
| ✅ **Established** | Well-supported by theory and evidence; safe to build on. |
| 🧭 **Useful model** | A simplification that is often helpful but has known failure modes. |
| ⚔️ **Contested** | Reasonable experts disagree; treat with care. |
| 🚩 **Myth / dubious** | Commonly repeated, poorly supported, or statistically shaky. |
| 🔬 **Testable claim** | An empirical assertion; the text says what evidence would confirm or refute it. |

---

## How to use this knowledge base

- Start at this README and follow the **10-level path** below. Each level lists prerequisites,
  learning objectives, exercises, and an explicit *"you are ready to move on when…"* checklist.
- Every section is a folder with a `README.md`. Internal links let you navigate naturally.
- When you hit an unfamiliar word, check the [Glossary](glossary/README.md).
- Do the [Exercises](20-exercises/README.md). Reading about trading and trading are as different
  as reading about swimming and swimming.
- For anything about **fees, taxes, settlement, or regulation**, treat the numbers here as a
  *snapshot* and verify against current official sources — these change with every Union Budget
  and SEBI circular. Date-sensitive facts are flagged 🗓️.

---

## The map — all sections

| # | Section | What it answers |
|---|---|---|
| 00 | [Foundations](00-foundations/README.md) | What money, assets, risk, return, and compounding actually are. |
| 01 | [How Markets Work](01-how-markets-work/README.md) | The plumbing: exchanges, brokers, order books, and *what happens after you press BUY*. |
| 02 | [Assets & Instruments](02-assets-and-instruments/README.md) | Equities, ETFs, bonds, commodities, FX, funds, REITs/InvITs, derivatives. |
| 03 | [Price & Market Behavior](03-price-and-market-behavior/README.md) | *Why* prices move — and why "buyers vs sellers" is a bad explanation. |
| 04 | [Fundamental Analysis](04-fundamental-analysis/README.md) | Financial statements, ratios, moats, valuation, DCF. |
| 05 | [Technical Analysis](05-technical-analysis/README.md) | Charts and indicators — as *hypotheses to be tested*, not magic. |
| 06 | [Trading Styles](06-trading-styles/README.md) | Investing → scalping, and the trade-offs of each. |
| 07 | [Risk Management](07-risk-management/README.md) | Position sizing, expectancy, drawdown, Kelly, risk of ruin. **The most important section.** |
| 08 | [Strategy Development](08-strategy-development/README.md) | Turning "this looks good" into a precisely defined system. |
| 09 | [Futures](09-futures/README.md) | Contracts, basis, margin, mark-to-market, contango/backwardation. |
| 10 | [Options](10-options/README.md) | Greeks, IV, strategies, payoffs, and *why selling options isn't free money*. |
| 11 | [Trading Psychology](11-trading-psychology/README.md) | Why understanding probability doesn't stop you behaving irrationally. |
| 12 | [Backtesting & Statistics](12-backtesting-and-statistics/README.md) | Returns, Sharpe, overfitting, walk-forward — the bridge to quant. |
| 13 | [Algorithmic Trading](13-algorithmic-trading/README.md) | Data → signal → risk → execution → broker, in code. |
| 14 | [Quantitative Trading](14-quantitative-trading/README.md) | Factors, pairs, cointegration, and honest skepticism about ML. |
| 15 | [Market Microstructure](15-market-microstructure/README.md) | The order book up close: matching, adverse selection, HFT. |
| 16 | [Advanced Topics](16-advanced-topics/README.md) | Regimes, risk parity, vol trading, market-neutral strategies. |
| 17 | [Indian Markets](17-indian-markets/README.md) | SEBI, NSE/BSE, demat, settlement, the full cost stack, taxation. 🗓️ |
| 18 | [Practical Trading](18-practical-trading/README.md) | Accounts, order entry, journaling, scaling capital — with templates. |
| 19 | [Case Studies](19-case-studies/README.md) | Ten worked stories: setup → thesis → risk → outcome → lesson. |
| 20 | [Exercises](20-exercises/README.md) | Progressive problems with solutions. |
| — | [Glossary](glossary/README.md) | Every term: simple def → technical def → example → related. |
| — | [Resources](resources/README.md) | Books, papers, official docs, data sources, libraries — no gurus. |

---

## The 10-level learning path

```text
LEVEL 1 — Market Literacy
      ↓
LEVEL 2 — Analysis
      ↓
LEVEL 3 — Risk Management
      ↓
LEVEL 4 — Strategy
      ↓
LEVEL 5 — Derivatives
      ↓
LEVEL 6 — Statistics & Backtesting
      ↓
LEVEL 7 — Algorithmic Trading
      ↓
LEVEL 8 — Quantitative Trading
      ↓
LEVEL 9 — Market Microstructure
      ↓
LEVEL 10 — Advanced Research
```

> **Golden rule of sequencing:** Do **not** skip Level 3. More traders are destroyed by weak risk
> management than by weak analysis. A brilliant entry with reckless sizing is a slot machine.

---

### 🟢 LEVEL 1 — Market Literacy

- **Prerequisites:** None. Bring curiosity and basic arithmetic.
- **Sections:** [00 Foundations](00-foundations/README.md), [01 How Markets Work](01-how-markets-work/README.md), [02 Assets & Instruments](02-assets-and-instruments/README.md), [03 Price & Market Behavior](03-price-and-market-behavior/README.md)
- **Learning objectives:**
  - Explain the difference between investing, trading, and speculation.
  - Trace an order from your screen to the exchange matching engine and back.
  - Read a bid/ask spread and market depth ladder.
  - Explain *why* the next trade in a ₹500 stock might print at ₹501.
- **Exercises:** [Beginner set](20-exercises/README.md#beginner) — returns, P&L, spread, and reading an order book.
- **✅ Ready to move on when you can:** describe, without notes, what a clearing corporation does,
  why a limit order can go unfilled, and why "there's a buyer for every seller" does *not* explain
  price moves.

---

### 🟢 LEVEL 2 — Analysis

- **Prerequisites:** Level 1.
- **Sections:** [04 Fundamental Analysis](04-fundamental-analysis/README.md), [05 Technical Analysis](05-technical-analysis/README.md), [06 Trading Styles](06-trading-styles/README.md)
- **Learning objectives:**
  - Read an income statement, balance sheet, and cash-flow statement.
  - Compute and interpret P/E, ROCE, EV/EBITDA — *and* say when each misleads.
  - State the *hypothesis* behind an indicator (e.g. RSI) and how you would test it.
  - Match a trading style to a realistic amount of capital, time, and skill.
- **Exercises:** [Intermediate set](20-exercises/README.md#intermediate) — analyze a stock, build a thesis.
- **✅ Ready to move on when you can:** value a simple business two different ways and explain why a
  moving-average crossover is a *bet on autocorrelation of returns*, not a crystal ball.

---

### 🟢 LEVEL 3 — Risk Management  ⭐

- **Prerequisites:** Level 1 (Level 2 helps but isn't required — risk is that fundamental).
- **Sections:** [07 Risk Management](07-risk-management/README.md)
- **Learning objectives:**
  - Size a position from a fixed *risk-per-trade*, not a fixed number of shares.
  - Compute **expectancy** and explain why a 40% win-rate system can print money while a 70%
    win-rate system bleeds out.
  - Estimate **risk of ruin** and explain why full **Kelly** is usually too aggressive.
- **Exercises:** [Intermediate set](20-exercises/README.md#intermediate) — expectancy and sizing.
- **✅ Ready to move on when you can:** take any strategy's win rate, average win, and average loss
  and immediately say whether it is worth trading — and at what size you would survive a bad streak.

---

### 🟢 LEVEL 4 — Strategy

- **Prerequisites:** Levels 1–3.
- **Sections:** [08 Strategy Development](08-strategy-development/README.md)
- **Learning objectives:**
  - Convert a vague setup into an unambiguous rule set (entry, exit, stop, size, filter, regime).
  - Write a one-page trading plan and keep a structured journal.
- **Exercises:** [Advanced set](20-exercises/README.md#advanced) — design a complete strategy on paper.
- **✅ Ready to move on when:** a stranger could execute your strategy from your written rules and
  get materially the same trades you would.

---

### 🟡 LEVEL 5 — Derivatives

- **Prerequisites:** Levels 1–4. Do **not** trade derivatives without Level 3.
- **Sections:** [09 Futures](09-futures/README.md), [10 Options](10-options/README.md)
- **Learning objectives:**
  - Explain leverage, margin, and mark-to-market with an INR example.
  - Read an option chain; compute intrinsic and time value; reason with the Greeks.
  - Draw the payoff of a spread and explain why selling options is *not* free money.
- **Exercises:** [Intermediate](20-exercises/README.md#intermediate) & [Advanced](20-exercises/README.md#advanced) — option chain analysis and a realistic options trade.
- **✅ Ready to move on when you can:** explain, to a skeptical friend, exactly how a short-straddle
  seller can win 80% of the time and still go broke.

---

### 🟡 LEVEL 6 — Statistics & Backtesting

- **Prerequisites:** Levels 1–5. Comfort with basic Python helps.
- **Sections:** [12 Backtesting & Statistics](12-backtesting-and-statistics/README.md)
- **Learning objectives:**
  - Compute mean, variance, Sharpe, Sortino, max drawdown, Calmar from a return series.
  - Identify look-ahead bias, survivorship bias, and overfitting in a backtest.
  - Run a train/test split, a walk-forward test, and a Monte Carlo on trade order.
- **Exercises:** [Advanced set](20-exercises/README.md#advanced) — backtest and validate a strategy.
- **✅ Ready to move on when you can:** look at an impressive equity curve and list five ways it
  might be a lie.

---

### 🔴 LEVEL 7 — Algorithmic Trading

- **Prerequisites:** Levels 1–6.
- **Sections:** [13 Algorithmic Trading](13-algorithmic-trading/README.md)
- **Learning objectives:**
  - Understand the standard architecture: data → signal → risk → sizing → execution → broker.
  - Paper-trade a simple systematic strategy end-to-end before risking capital.
- **✅ Ready to move on when you can:** draw the full system diagram and say where each failure mode
  (bad data, stale signal, fat-finger order, broker outage) is handled.

---

### 🔴 LEVEL 8 — Quantitative Trading

- **Prerequisites:** Levels 1–7.
- **Sections:** [14 Quantitative Trading](14-quantitative-trading/README.md)
- **Learning objectives:**
  - Explain the classic factors (value, momentum, quality, low-vol) and what could erode them.
  - Understand pairs trading and cointegration; run a regression sensibly.
  - Explain *why most ML trading projects are overfit backtests in disguise.*
- **✅ Ready to move on when you can:** critique a "neural network predicts NIFTY" claim on
  statistical grounds in under a minute.

---

### 🔴 LEVEL 9 — Market Microstructure

- **Prerequisites:** Levels 1–8.
- **Sections:** [15 Market Microstructure](15-market-microstructure/README.md)
- **Learning objectives:**
  - Explain price-time priority, adverse selection, and order-flow imbalance.
  - Describe how institutional and HFT trading differs from retail.
- **✅ Ready to move on when you can:** explain why your market order's *effective* price differs
  from the last-traded price, in book terms.

---

### 🔴 LEVEL 10 — Advanced Research

- **Prerequisites:** Levels 1–9.
- **Sections:** [16 Advanced Topics](16-advanced-topics/README.md), plus the papers in [Resources](resources/README.md).
- **Learning objectives:** regime detection, portfolio construction, risk parity, volatility
  trading, market-neutral design — and the humility to know when an edge has decayed.
- **✅ You are never "done".** Markets adapt; edges erode. Level 10 is a posture, not a destination.

---

## Formatting conventions used throughout

- **Formulas** always come with: what it calculates → why it matters → each variable → a numerical
  example → limitations.
- **Confusable concepts** are compared in a table with a "common mistake" column.
- Boxes you will see repeatedly:
  - > 💡 **Key takeaway** — the one thing to remember.
  - > ⚠️ **Common mistake** — how people get hurt.
  - > 🤔 **Think about this** — a question to test understanding.

---

## A note on sources

Where current facts matter (Indian fees, taxes, settlement, regulation), this base prefers
**official exchange/regulator documentation, academic papers, established textbooks, and reputable
institutions** over social media, YouTube, or "trading gurus." See [Resources](resources/README.md).
Date-sensitive Indian data in [Section 17](17-indian-markets/README.md) was checked against current
sources at the time of writing and is flagged 🗓️ — always re-verify before it affects money.

---

*Begin at [00 — Foundations](00-foundations/README.md). Take your time. The market will still be
there tomorrow.*
