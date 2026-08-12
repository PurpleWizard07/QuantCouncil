# 14 — Quantitative Trading

> ⬅ Back to [README](../README.md) · Prev: [13 Algorithmic Trading](../13-algorithmic-trading/README.md) · Next: [15 Market Microstructure](../15-market-microstructure/README.md)

> 💡 **Key takeaway:** Quant trading systematizes an *edge* — a repeatable statistical relationship —
> into rules that don't depend on a human's gut feel. It borrows the rigor of
> [12 Backtesting & Statistics](../12-backtesting-and-statistics/README.md) and the machinery of
> [13 Algorithmic Trading](../13-algorithmic-trading/README.md), but its core question is different:
> **"what is the mechanism that makes this pattern persist, and why hasn't it been arbitraged away?"**

**Learning objectives:** understand factor investing, pairs trading/cointegration, why most "AI trading"
claims deserve skepticism, and why edges decay.

*This section is a substantive outline. It can be expanded to flagship depth — full factor-construction
code, a worked cointegration test — on request.*

---

## 1. What makes something a "quant" strategy

Not "uses math" (all trading uses math) — it's: **systematic** (rules, not judgment-per-trade),
**testable** (falsifiable on historical data, see [12](../12-backtesting-and-statistics/README.md#10-statistical-significance-and-overfitting)),
and ideally has a **stated economic mechanism**, not just a pattern that happened to work in a backtest.

> 🔬 **Testable claim vs. curve-fit:** "Momentum works because winners attract slow-moving capital
> inflows and losers face forced selling" is a mechanism. "This worked because I found parameters that
> fit 5 years of data" is not — see [overfitting](../12-backtesting-and-statistics/README.md#10-statistical-significance-and-overfitting).

---

## 2. Factor investing

| Factor | Idea | Proposed mechanism | Status |
|---|---|---|---|
| **Value** | Cheap (low P/E, P/B) stocks outperform | Compensation for risk / behavioral mispricing of unglamorous stocks | ✅ Long-documented, 🧭 decayed & crowded in recent decades |
| **Momentum** | Recent winners keep winning (3–12mo) | Slow information diffusion, herding, disposition effect (see [11](../11-trading-psychology/README.md)) | ✅ One of the most replicated anomalies, ⚔️ crash risk in reversals |
| **Size** | Small-caps outperform large-caps | Illiquidity premium, less analyst coverage | 🧭 Weaker/inconsistent post-2000s |
| **Low volatility** | Lower-vol stocks have better risk-adjusted (sometimes absolute) returns | Leverage-constrained investors bid up high-beta names | 🧭 Contested, mechanism debated |
| **Quality** | Profitable, low-debt, stable-earnings companies outperform | Market underprices durability of quality | 🧭 Reasonably robust but factor definitions vary |

> ⚠️ **Common mistake:** Treating a factor as a guarantee rather than a *tilt with a risk premium*.
> Value can underperform for over a decade (it did, globally, through much of the 2010s) before
> "working" again — see [Drawdowns](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin).

---

## 3. Pairs trading & cointegration

**Idea:** find two instruments whose prices move together long-run (e.g., two similar banks, or a
stock vs. its sector ETF). When the spread between them diverges abnormally, bet on convergence.

- **Correlation is not enough** — two series can be correlated but drift apart permanently.
  **Cointegration** is the stronger property: a *linear combination* of the two series is mean-reverting,
  even if each series individually is not.
- **Basic test flow:** (1) check both series are non-stationary individually (e.g., Augmented
  Dickey-Fuller test), (2) regress one on the other, (3) test the *residual* for stationarity
  (Engle-Granger) — if stationary, the pair is cointegrated.
- **Z-score entry:** standardize the spread; enter when it's, say, 2 standard deviations from its mean;
  exit at 0 (or use a stop if it keeps diverging — see [Stop losses](../07-risk-management/README.md#3-stop-losses-done-properly)).

> 🚩 **Red flag:** Cointegration relationships can break permanently (a merger, a regulatory change, a
> business-model divergence). "Mean reversion" is a statistical description of the past, not a law of
> physics — always risk-manage the trade as if the relationship could fail.

---

## 4. Machine learning in trading — a skeptical take

| Claim | Reality check |
|---|---|
| "Feed price data into a neural net and it finds patterns humans can't" | Financial time series are extremely low signal-to-noise; models overfit noise easily — see [Overfitting](../12-backtesting-and-statistics/README.md#10-statistical-significance-and-overfitting) |
| "More data = better model" | More *irrelevant* data often just gives the model more noise to memorize |
| "Backtested Sharpe of 3+ from an ML model" | Extremely rare to survive live trading — check for look-ahead bias, survivorship bias, and unrealistic execution assumptions first |
| "ML finds nonlinear relationships humans can't see" | True in principle, but the *feature engineering* (what you feed the model) still requires domain understanding — a model isn't a substitute for a mechanism |

> 🧭 **Useful model, not gospel:** ML can be legitimately useful for well-defined sub-problems (e.g.,
> execution-cost prediction, classifying regime, filtering false signals) — it's weakest when marketed
> as an end-to-end "black box that predicts price."

---

## 5. Why edges decay

- **Crowding:** once a pattern is known and traded by enough capital, the very act of exploiting it
  (buying the "cheap," selling the "expensive") pushes prices toward removing the mispricing.
- **Regime change:** the market structure that created the edge (e.g., specific liquidity rules,
  investor composition) changes — see [16 Advanced Topics → regime detection](../16-advanced-topics/README.md).
- **Publication effect:** documented academic anomalies often show weaker returns *after* publication —
  a well-studied empirical pattern in factor research.

> 💡 **Key takeaway:** A quant "edge" is a temporarily-underexploited pattern with a plausible economic
> reason. Expect decay. Continuous research, not "set and forget," is the job.

---

✅ **Ready to move on when:** you can define cointegration vs. correlation, name at least three
documented factors and their proposed mechanisms, and explain two concrete reasons a backtested ML
strategy might fail to work live.

**Related sections:** [12 Backtesting](../12-backtesting-and-statistics/README.md) ·
[13 Algorithmic Trading](../13-algorithmic-trading/README.md) ·
[16 Advanced Topics](../16-advanced-topics/README.md) ·
[05 Technical Analysis](../05-technical-analysis/README.md)

**Next →** [15 Market Microstructure](../15-market-microstructure/README.md)
