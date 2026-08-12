# 12 — Backtesting and Statistics

> ⬅ Back to [README](../README.md) · Prev: [11 Trading Psychology](../11-trading-psychology/README.md) · Next: [13 Algorithmic Trading](../13-algorithmic-trading/README.md)

> 💡 **Key takeaway:** A backtest is not evidence that a strategy works — it is evidence that a
> strategy *would have* worked *on that specific past data, as you measured it.* The gap between those
> two statements is where fortunes are lost. This section gives you the statistics to measure honestly
> and the checklist of ways backtests lie.

**Contents**
1. [Data: OHLCV and its hazards](#1-data-ohlcv-and-its-hazards)
2. [Returns and log returns](#2-returns-and-log-returns)
3. [The core statistics](#3-the-core-statistics)
4. [Distributions and fat tails](#4-distributions-and-fat-tails)
5. [Performance metrics: Sharpe, Sortino, drawdown, Calmar](#the-sharpe-ratio)
6. [Backtesting: the basic loop](#6-backtesting-the-basic-loop)
7. [Backtesting pitfalls (the important part)](#backtesting-pitfalls)
8. [Validation: train/test, walk-forward, out-of-sample](#8-validation-traintest-walk-forward-out-of-sample)
9. [Monte Carlo and the bootstrap](#9-monte-carlo-and-the-bootstrap)
10. [Statistical significance and overfitting](#10-statistical-significance-and-overfitting)
11. [Checklist & common mistakes](#11-checklist--common-mistakes)

---

## 1. Data: OHLCV and its hazards

Market data usually arrives as **OHLCV** per period: **O**pen, **H**igh, **L**ow, **C**lose, **V**olume
(see [charts](../05-technical-analysis/README.md#2-price-representation-ohlc-candlesticks-timeframes-gaps)).
Before any statistic, the data must be *clean and honest*:

- **Adjusted vs unadjusted prices:** raw prices jump on splits/bonuses/dividends. For return studies
  you need **adjusted** series (corporate actions handled) — or your backtest will "see" a −50% crash
  that was really a 2:1 split. See [corporate actions](#backtesting-pitfalls).
- **Survivorship:** a dataset of "currently listed" stocks silently **excludes the losers that got
  delisted/bankrupt** — inflating every historical result. See [pitfalls](#backtesting-pitfalls).
- **Timestamps and alignment:** know exactly when each bar "closes" and when you could *actually* have
  acted; sloppy alignment causes [look-ahead bias](#backtesting-pitfalls).

> 💡 **Key takeaway:** Garbage in, gospel out — the danger is that *clean-looking* but subtly-biased
> data produces *beautiful, believable, wrong* results. Data quality is not a preliminary; it is half
> the battle.

---

## 2. Returns and log returns

- **Simple (arithmetic) return:** $R_t = \frac{P_t - P_{t-1}}{P_{t-1}}$. Intuitive; what you actually
  earn in a period.
- **Log return:** $r_t = \ln\!\left(\frac{P_t}{P_{t-1}}\right)$. Preferred for analysis because:
  - **Additive over time:** log returns *sum* across periods (simple returns *compound*, i.e. multiply)
    — so a month's log return is just the sum of daily log returns. Much easier math.
  - **Symmetric-ish** and better-behaved statistically.
- **Relationship:** for small moves, $r_t \approx R_t$; they diverge for large moves.

**Example:** ₹100 → ₹110. Simple = `10/100 = 10%`. Log = `ln(1.10) ≈ 9.53%`. Then ₹110 → ₹100: simple
= `−9.09%`, log = `ln(100/110) ≈ −9.53%`. Note the log returns are equal-and-opposite (+9.53 / −9.53)
and sum to 0 — matching the reality that you're back to ₹100. Simple returns (+10 / −9.09) don't sum
to zero, which is exactly the [asymmetry](../00-foundations/README.md#6-return) that trips people up.

> ⚠️ **Common mistake:** Averaging *simple* returns and treating the mean as your growth rate. Use
> **log returns** for time-aggregation, or compute the **[CAGR/geometric mean](../00-foundations/README.md#6-return)** —
> the arithmetic mean of simple returns *overstates* compounded growth.

---

## 3. The core statistics

From a series of returns you compute:

| Statistic | Formula (conceptual) | What it tells you |
|---|---|---|
| **Mean** ($\mu$) | average return | central tendency / typical period |
| **Variance** ($\sigma^2$) | average squared deviation from the mean | spread of outcomes |
| **Std deviation** ($\sigma$) = **volatility** | $\sqrt{\text{variance}}$ | typical size of swings, in return units |
| **Annualized volatility** | $\sigma_{daily} \times \sqrt{252}$ | volatility scaled to a year (≈252 trading days) |
| **Expected value** | $\sum (\text{outcome} \times \text{probability})$ | probability-weighted average outcome |

- **Why $\sqrt{252}$?** Under the (idealized) assumption of independent daily returns, variance scales
  *linearly* with time, so *volatility* scales with the **square root** of time. A daily vol of 1% →
  annual vol ≈ `1% × √252 ≈ 15.9%`. 🧭 A useful model; real returns aren't perfectly independent.
- **Expected value / expectancy** is the bridge to [Risk Management](../07-risk-management/README.md#5-expectancy--the-master-formula):
  a strategy's per-trade expectancy is just the expected value of its trade-return distribution.

```python
import numpy as np

prices = np.array([100, 102, 101, 104, 103, 107, 110.0])
simple_ret = prices[1:] / prices[:-1] - 1
log_ret    = np.log(prices[1:] / prices[:-1])

mu_daily    = log_ret.mean()
sigma_daily = log_ret.std(ddof=1)          # sample std
ann_return  = mu_daily * 252               # log returns annualize by summing
ann_vol     = sigma_daily * np.sqrt(252)

print(f"daily mean log-ret: {mu_daily:.4%}")
print(f"annualized vol:     {ann_vol:.2%}")
```

---

## 4. Distributions and fat tails

A **distribution** describes how likely each outcome is. Finance loves the **normal (Gaussian)**
distribution because it's mathematically convenient — but real market returns are **not normal**:

- **Fat tails (leptokurtosis):** extreme moves (crashes, gap-ups) happen **far more often** than a
  normal distribution predicts. A "6-sigma" event should be almost impossible under normality, yet
  markets deliver them every few years.
- **Volatility clustering:** big moves follow big moves; calm follows calm (the basis of
  [ATR](../05-technical-analysis/README.md#atr-average-true-range) and vol models in [Advanced](../16-advanced-topics/README.md)).
- **Skew:** equity returns are often negatively skewed — crashes are sharper than melt-ups.

> ⚠️ **Common mistake:** Using models (Sharpe, VaR, option pricing) that *assume* normality and being
> blindsided by the tail. This is the statistical root of [why selling options can ruin you](../10-options/README.md#why-selling-options-is-not-free-money)
> and why [risk of ruin](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin) is
> larger than "normal" math suggests. **Respect the tails.**

---

## The Sharpe ratio
*(and Sortino, drawdown, Calmar — the performance metrics)*

Raw return is meaningless without risk ([Foundations → risk-adjusted](../00-foundations/README.md#13-risk-adjusted-returns)).
The standard metrics:

### Sharpe ratio — return per unit of volatility
$$\text{Sharpe} = \frac{R_p - R_f}{\sigma_p}$$
- **Calculates:** excess return (over risk-free `R_f`, e.g. an Indian T-bill/G-Sec yield) per unit of
  total volatility `σ_p`, usually annualized.
- **Example:** 18% return, 12% vol, 6% risk-free → `(18−6)/12 = 1.0`. Rough rule of thumb: <1 modest,
  1–2 good, >2 excellent, >3 be suspicious (often overfit or hidden tail risk).
- **Limitations:** penalizes upside and downside volatility *equally*; assumes returns are
  well-behaved (they [aren't](#4-distributions-and-fat-tails)); easy to **game** by strategies that
  look smooth but hide rare catastrophic losses (naked option selling can post a lovely Sharpe — until
  it doesn't).

### Sortino ratio — return per unit of *downside* volatility
$$\text{Sortino} = \frac{R_p - R_f}{\sigma_{downside}}$$
Same idea, but only counts **downside** deviation — because you don't mind upside volatility. Better
than Sharpe for asymmetric strategies, but still tail-blind.

### Maximum drawdown (MDD)
The largest **peak-to-trough** equity decline over the period — the most *visceral* risk measure ("how
bad did it get / how close to quitting or ruin"). Recall the brutal [recovery math](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin):
−50% needs +100% to recover.

### Calmar ratio — return per unit of drawdown
$$\text{Calmar} = \frac{\text{Annualized return}}{|\text{Max drawdown}|}$$
Rewards strategies that earn without deep drawdowns. A strategy returning 20%/yr with a −40% MDD
(Calmar 0.5) is arguably *worse* than one returning 12% with a −10% MDD (Calmar 1.2).

```python
def max_drawdown(equity):
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return dd.min()          # most negative value

def sharpe(returns, rf_daily=0.0, periods=252):
    excess = returns - rf_daily
    return np.sqrt(periods) * excess.mean() / returns.std(ddof=1)
```

> 💡 **Key takeaway:** Never quote a return without a **risk-adjusted** companion (Sharpe/Sortino) *and*
> a **drawdown**. A high return with a huge drawdown and fat tails is a landmine, not an achievement.

---

## 6. Backtesting: the basic loop

A **backtest** simulates a strategy on historical data to estimate how it *would have* performed. The
skeleton:

1. **Data** → clean, adjusted OHLCV.
2. **Signal** → rules that decide long/short/flat each bar (from [TA](../05-technical-analysis/README.md),
   [fundamentals](../04-fundamental-analysis/README.md), or a [quant factor](../14-quantitative-trading/README.md)).
3. **Position sizing** → convert signals to quantities ([risk-based sizing](../07-risk-management/README.md#2-risk-per-trade--position-sizing)).
4. **Execution model** → *when* and at *what price* you'd fill (with costs & slippage!).
5. **Accounting** → track P&L, equity curve, trades.
6. **Metrics** → returns, Sharpe, drawdown, [expectancy](../07-risk-management/README.md#5-expectancy--the-master-formula).

```python
# Toy backtest: 20/50 SMA crossover on a daily close series (illustrative, NOT trade-ready)
import pandas as pd

df = pd.DataFrame({"close": prices})               # use a real, adjusted series in practice
df["fast"] = df["close"].rolling(20).mean()
df["slow"] = df["close"].rolling(50).mean()

# signal decided on bar t, ACTED ON bar t+1's open -> shift(1) prevents look-ahead
df["signal"] = (df["fast"] > df["slow"]).astype(int)
df["position"] = df["signal"].shift(1).fillna(0)

df["mkt_ret"] = df["close"].pct_change()
COST = 0.0005                                       # per-trade cost estimate (tune to Indian reality)
df["trade"] = df["position"].diff().abs().fillna(0)
df["strat_ret"] = df["position"] * df["mkt_ret"] - df["trade"] * COST

equity = (1 + df["strat_ret"].fillna(0)).cumprod()
```

> ⚠️ Note the **`.shift(1)`** — it forces the strategy to *decide* on bar `t` but *act* on `t+1`,
> because in reality you cannot trade on a close you haven't seen yet. Omitting this is the single most
> common backtesting bug ([look-ahead](#backtesting-pitfalls)).

---

## Backtesting pitfalls
*(This is the most important section — read it twice.)*

Almost every impressive backtest that fails live was killed by one of these:

| Pitfall | What it is | Why it inflates results | Guard |
|---|---|---|---|
| **Look-ahead bias** | Using data you couldn't have had at decision time | You "trade" on tomorrow's close today | `shift()`; strict as-of timestamps |
| **Survivorship bias** | Testing only stocks that *survived* | Excludes the bankruptcies/delistings | Point-in-time universe incl. dead names |
| **Data snooping / p-hacking** | Trying thousands of variants and keeping the best | Best-of-N *will* look great by luck | Out-of-sample; limit trials; adjust for multiplicity |
| **Overfitting** | Model fits noise, not signal | Too many parameters memorize the past | Fewer params; walk-forward; simplicity |
| **Ignoring costs/slippage** | Frictionless fills at printed prices | Frequent strategies feed on nonexistent edge | Model [Indian cost stack](../17-indian-markets/README.md#the-cost-stack) + slippage |
| **Ignoring liquidity/impact** | Assuming unlimited size at last price | Your size would've moved the market | Cap size vs volume; model impact |
| **Corporate-action errors** | Unadjusted splits/dividends | Phantom crashes/spikes | Use adjusted data |
| **Regime dependence** | Works only in the tested regime | One bull market ≠ an edge | Test across bull/bear/range, multiple periods |
| **Selection of period** | Cherry-picking start/end dates | Flatters the curve | Report full history; multiple windows |

### The two you must burn into memory

- **Overfitting** is fitting your model to the *noise* in past data. With enough parameters you can
  fit *anything* historically and predict *nothing* forward. The more knobs you turn and variants you
  try, the more you're just memorizing history. **Simplicity and out-of-sample testing are the
  antidotes.**
- **Data snooping** is the meta-version: if you (or the internet) test 1,000 strategies, ~50 will look
  "significant" at p<0.05 *by pure chance*. The winner of a big search is probably a lucky fluke, not
  an edge. This is why "I found a pattern that backtests great" is weak evidence.

> ⚠️ **Common mistake:** Iterating: tweak rule → backtest → tweak → backtest, on the *same* data, until
> the curve is gorgeous. You have now **fit the noise** and learned nothing about the future. The
> beautiful curve is a *portrait of the past's randomness.*

🤔 **Think about this:** You test 500 indicator combos and the best has a Sharpe of 2.5 in-sample.
Before getting excited, what's the *expected* best-of-500 result even if **none** has real edge? (High,
purely by luck. That's why the *out-of-sample* result — on data you never touched while searching — is
the only one that counts.)

---

## 8. Validation: train/test, walk-forward, out-of-sample

- **Train/test split:** design/optimize on an **in-sample** slice; evaluate *once* on a held-out
  **out-of-sample** slice you never peeked at. If it collapses out-of-sample, it was overfit.
- **Out-of-sample (OOS):** the sacred principle — **never let evaluation data influence design.** Peek
  once and it's contaminated.
- **Walk-forward analysis:** the gold standard for time series. Roll a window forward: optimize on
  months 1–12, test on month 13; slide to 2–13, test on 14; and so on. This mimics *actually
  re-fitting a live system over time* and produces a *stitched* out-of-sample curve — a far more honest
  estimate than a single split.

```text
Walk-forward:
[--- train 1 ---][test1]
      [--- train 2 ---][test2]
            [--- train 3 ---][test3]  ...
Concatenate test1+test2+test3+... = out-of-sample performance
```

> 💡 **Key takeaway:** In-sample results are a *hypothesis*; out-of-sample (ideally walk-forward)
> results are the closest you get to *evidence*. If a strategy only shines in-sample, it is overfit —
> full stop.

---

## 9. Monte Carlo and the bootstrap

Even a valid backtest shows just **one** historical path. You care about the *distribution* of paths
you might face:

- **Monte Carlo on trade order:** shuffle the sequence of your trade results many times to see the
  range of equity curves and **drawdowns** you *could* have experienced. Your actual max drawdown might
  have been −18%, but the simulation may show −35% was well within the realm of luck — informing your
  [position sizing](../07-risk-management/README.md#2-risk-per-trade--position-sizing) and nerve.
- **Bootstrap:** resample returns *with replacement* to build confidence intervals around metrics
  (Sharpe, CAGR) — quantifying how *uncertain* your estimates are given a finite sample.

```python
# Monte Carlo: distribution of max drawdown by reshuffling trade returns
trade_returns = df["strat_ret"].dropna().values
rng = np.random.default_rng(42)
dds = []
for _ in range(5000):
    shuffled = rng.permutation(trade_returns)
    eq = np.cumprod(1 + shuffled)
    dds.append(max_drawdown(eq))
print(f"median MDD: {np.median(dds):.1%}, 5th percentile MDD: {np.percentile(dds,5):.1%}")
```

> 💡 **Key takeaway:** Your realized history is one sample from a distribution. Monte Carlo/bootstrap
> reveal the **worse paths luck could have dealt you** — size for *those*, not for the comfortable path
> you happened to get.

---

## 10. Statistical significance and overfitting

- A result is **statistically significant** if it's unlikely under the "no edge" null hypothesis. But
  significance is **not** the same as *real, tradeable, persistent* edge — especially after
  [data snooping](#backtesting-pitfalls) and costs.
- **Sample size matters enormously.** A strategy with 30 trades tells you almost nothing; you need
  *hundreds* of independent trades before expectancy estimates stabilize. Beware "great" results built
  on a handful of trades (or a handful of *huge* winners doing all the work).
- **Multiplicity:** if you test many things, adjust your bar for significance (the more you look, the
  more flukes you find). The honest defenses are **fewer trials, more out-of-sample data, simpler
  models, and a plausible economic mechanism.**

> 🔬 **The mindset:** treat every backtest as **guilty until proven innocent.** Ask: enough trades? out
> of sample? costs modeled? robust across regimes/periods? is there a *reason* the edge exists and
> would persist? If any answer is shaky, don't bet real money — this is the discipline that separates
> [quant trading](../14-quantitative-trading/README.md) from curve-fitting.

---

## 11. Checklist & common mistakes

### ✅ Before trusting any backtest
- [ ] Data is **adjusted** for corporate actions and **free of survivorship** bias.
- [ ] No **look-ahead** (decisions use only past-available data; `shift`/as-of timestamps).
- [ ] **Costs and slippage** modeled to Indian reality; liquidity/size caps applied.
- [ ] Evaluated **out-of-sample** (ideally walk-forward), not just in-sample.
- [ ] Judged on **expectancy, Sharpe/Sortino, and drawdown** — not headline return or win rate.
- [ ] **Enough trades** (hundreds) and not driven by a few outliers.
- [ ] **Monte Carlo/bootstrap** run to see the range of possible drawdowns.
- [ ] I can name a **mechanism** for why the edge exists and might persist.

### ⚠️ The classic statistical sins
| Sin | Consequence |
|---|---|
| Optimizing and evaluating on the same data | Overfit; beautiful past, useless future |
| Ignoring costs/slippage | Phantom edge that evaporates live |
| Survivorship in the dataset | Systematically inflated results |
| Judging by win rate or headline return | Misses expectancy and tail/drawdown risk |
| Tiny sample / outlier-driven | Illusory significance |
| Assuming normality | Blindsided by fat tails |

---

### Related sections
- [07 Risk Management](../07-risk-management/README.md) — expectancy, drawdown, and sizing that these stats feed.
- [05 Technical Analysis → how to test a TA idea](../05-technical-analysis/README.md#9-how-to-test-any-ta-idea) — applying this rigor to indicators.
- [13 Algorithmic Trading](../13-algorithmic-trading/README.md) — turning a validated strategy into a running system.
- [14 Quantitative Trading](../14-quantitative-trading/README.md) — factors, and honest skepticism about ML.
- [19 Case Studies → an overfit backtest](../19-case-studies/README.md) — a worked cautionary tale.
- [Glossary](../glossary/README.md) — Sharpe, Sortino, drawdown, overfitting, walk-forward, Monte Carlo.

> Next: [13 — Algorithmic Trading](../13-algorithmic-trading/README.md) →
