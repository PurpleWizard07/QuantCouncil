# 05 — Technical Analysis

> ⬅ Back to [README](../README.md) · Prev: [04 Fundamental Analysis](../04-fundamental-analysis/README.md) · Next: [06 Trading Styles](../06-trading-styles/README.md)

> 💡 **Key takeaway:** Technical analysis (TA) is the study of **price and volume behavior**. Used
> honestly, indicators are *compressed summaries of past price* that encode a **hypothesis** about
> what tends to happen next. Used dishonestly (the way most social media presents them), they're sold
> as magic predictors. This section teaches TA as a set of **testable bets**, each with a mechanism, a
> failure mode, and a way to check it.

> ⚔️ **Where TA stands, epistemically:** That markets *trend* and *mean-revert* in some regimes is
> supported by evidence (momentum and reversal are documented — see [Quant](../14-quantitative-trading/README.md)).
> That *specific chart patterns reliably predict specific moves* is far weaker and often fails
> out-of-sample. Treat the **broad ideas** as 🧭 useful models and the **precise pattern claims** as
> 🔬 testable-and-usually-disappointing.

**Contents**
1. [The honest framing: indicators as hypotheses](#1-the-honest-framing-indicators-as-hypotheses)
2. [Price representation: OHLC, candlesticks, timeframes, gaps](#2-price-representation-ohlc-candlesticks-timeframes-gaps)
3. [Market structure](#3-market-structure)
4. [Support and resistance](#4-support-and-resistance)
5. [Volume](#5-volume)
6. [Indicators — mechanics *and* limitations](#6-indicators--mechanics-and-limitations)
   - [SMA/EMA](#smaema--trend-and-smoothing) · [VWAP](#vwap) · [RSI](#rsi) · [MACD](#macd) · [Bollinger Bands](#bollinger-bands) · [ATR](#atr-average-true-range) · [Stochastic](#stochastic) · [ADX](#adx)
7. [Chart patterns](#7-chart-patterns)
8. [Advanced: multi-timeframe, volume profile, order flow](#8-advanced-multi-timeframe-volume-profile-order-flow)
9. [How to test any TA idea](#9-how-to-test-any-ta-idea)
10. [Checklist & common mistakes](#10-checklist--common-mistakes)

---

## 1. The honest framing: indicators as hypotheses

Every indicator is a **function of past price/volume**. It cannot contain information that isn't
already in the price. So the right question is never "does this indicator predict the future?" but:

> For **every** indicator, ask the four questions:
> 1. **What hypothesis does it represent?** (What belief about market behavior is it a bet on?)
> 2. **Why might it work?** (What real mechanism — behavioral, structural — could make that true?)
> 3. **When does it fail?** (What regime breaks the hypothesis?)
> 4. **How could we test it?** (What out-of-sample, cost-adjusted evidence would confirm/refute it?)

If you can't answer these, you're not doing analysis — you're doing astrology with candlesticks.

> ⚠️ **Common mistake:** Stacking ten indicators and waiting for them to "align." Since most are
> different transformations of the *same* price series, they're highly correlated — ten of them is not
> ten independent votes, it's one signal wearing ten costumes. More indicators ≠ more information.

---

## 2. Price representation: OHLC, candlesticks, timeframes, gaps

- **OHLC:** each time period is summarised by four numbers — **O**pen, **H**igh, **L**ow, **C**lose.
- **Candlestick:** a visual OHLC. The **body** spans open→close (filled/red if down, hollow/green if
  up); the **wicks/shadows** reach to the high and low. Candles show, at a glance, where price *went*
  vs where it *settled* — a long upper wick means buyers pushed up but sellers rejected the highs.
- **Timeframe:** the period per candle (1-min, 5-min, daily, weekly). The *same* price looks trending
  on one timeframe and choppy on another. Your timeframe should match your [trading style](../06-trading-styles/README.md).
- **Gaps:** when a period *opens* far from the previous *close* (no trading in between) — common
  overnight after news/results/[budget](../17-indian-markets/README.md). Gaps are why
  [stops can slip](../07-risk-management/README.md#3-stop-losses-done-properly) and why holding through
  events is risky.

> 🚩 **Myth:** Individual candlestick patterns (doji, hammer, engulfing) are reliable predictors. In
> isolation and out-of-sample, most single-candle signals have weak, inconsistent edges. They are, at
> best, *context* (a long rejection wick at a key level is more meaningful than one in the middle of
> nowhere), not standalone signals. 🔬 Easy to test; usually underwhelms.

---

## 3. Market structure

"Market structure" is simply describing price as a sequence of swings:

- **Uptrend:** successive **higher highs (HH)** and **higher lows (HL)**.
- **Downtrend:** successive **lower highs (LH)** and **lower lows (LL)**.
- **Range/consolidation:** highs and lows oscillate within a band — no net direction.
- **Breakout:** price exits a range/level with force. **Pullback:** a temporary counter-move within a
  trend (a chance to enter "with the trend" at a better price).

**Hypothesis:** trends *persist* (today's direction predicts tomorrow's) more often than chance — i.e.
returns have some **positive autocorrelation** in trending regimes. **Why it might work:** slow
diffusion of information, herding, and institutional accumulation take time. **When it fails:** in
choppy/mean-reverting regimes, "breakouts" are false and trend-followers get whipsawed. This is the
core bet of [trend following](../06-trading-styles/README.md) and momentum ([Quant](../14-quantitative-trading/README.md)).

> 💡 **Key takeaway:** Structure (HH/HL vs LH/LL) is the most *robust* piece of TA because it's a
> direct description of behavior, not a derived oscillator. But even "the trend" is a bet on
> autocorrelation that fails in ranges — which is why you pair it with [risk management](../07-risk-management/README.md).

---

## 4. Support and resistance

**Support** = a price zone where buying has previously been strong enough to halt declines.
**Resistance** = a zone where selling has halted advances.

- **Hypothesis:** prices "remember" levels — round numbers, prior highs/lows, and heavily-traded
  prices act as barriers where orders cluster. **Why it might work:** (a) *memory/anchoring* — traders
  place orders at salient prices ([Psychology](../11-trading-psychology/README.md)); (b) *structural* —
  real resting limit orders and [option strikes](../10-options/README.md#6-reading-an-option-chain-nifty-example)
  sit at these levels, so they genuinely absorb flow. **When it fails:** on strong trends/news, levels
  break cleanly; and "obvious" levels get front-run or become self-defeating once everyone watches them.

> ⚠️ **Common mistake:** Drawing a level *after the fact* through the exact tops/bottoms and marvelling
> at how well it "worked." Levels are **zones**, not lines, and hindsight makes any line look
> predictive. The test is whether a level defined *in advance* has edge — often modest at best.

---

## 5. Volume

**Volume** = quantity traded in a period. It's the closest TA gets to a *second* data dimension beyond
price.

- **Hypothesis:** moves *on high volume* are more "conviction-backed" and durable than moves on thin
  volume; volume *confirms* breakouts. **Why it might work:** large participation reflects real
  institutional flow rather than a few trades drifting a thin book. **When it fails:** volume can be
  driven by index rebalancing, expiry, or algos with no directional meaning; and in an era of
  fragmented liquidity, "volume" is noisier than the folklore assumes.
- **Note the subtlety from [Price behavior](../03-price-and-market-behavior/README.md#2-why-buyers-vs-sellers-is-a-bad-explanation):**
  volume alone doesn't tell direction — every unit traded had a buyer *and* a seller. "Buying volume"
  vs "selling volume" requires inferring *aggressor* side (who crossed the spread), which basic charts
  don't show — that's [order flow](#8-advanced-multi-timeframe-volume-profile-order-flow).

---

## 6. Indicators — mechanics *and* limitations

For each: the formula/idea, the **hypothesis**, why it might work, when it fails.

### SMA/EMA — trend and smoothing
- **Mechanics:** **Simple Moving Average** = mean of the last *n* closes. **Exponential Moving
  Average** weights recent prices more (reacts faster). Formula (SMA): $\text{SMA}_n = \frac{1}{n}\sum_{i=0}^{n-1} P_{t-i}$.
- **Hypothesis:** smoothing filters noise to reveal the trend; a **crossover** (price/short-MA above
  long-MA) signals a trend has begun. This is a bet on **autocorrelation / momentum**.
- **Why it might work:** trends persist for the reasons in [§3](#3-market-structure).
- **When it fails:** MAs **lag** by construction (they average the *past*), so they enter late and exit
  late; in ranges they generate constant whipsaw — buy high, sell low, repeat. 🔬 A moving-average
  crossover is one of the *most-tested* systems ever; results are regime-dependent and heavily eroded
  by costs.

### VWAP
- **Mechanics:** **Volume-Weighted Average Price** = the average price over the day *weighted by
  volume*: $\text{VWAP} = \frac{\sum (P_i \times V_i)}{\sum V_i}$. Resets each session.
- **Hypothesis / use:** VWAP marks the "fair" average traded price of the day; institutions benchmark
  executions against it, so it can act as an intraday magnet/reference. Price above VWAP = intraday
  buyers in control; below = sellers.
- **Why it might work:** it's a *real* institutional benchmark (algos literally target it), giving it
  structural relevance rather than being an arbitrary curve.
- **When it fails:** it's an *average of the past intraday* — no predictive magic; trending days barely
  touch it, and it's meaningless across multiple days.

### RSI
- **Mechanics:** **Relative Strength Index** (0–100) compares average recent gains to average recent
  losses over *n* periods (usually 14). $\text{RSI} = 100 - \frac{100}{1 + RS}$, where
  $RS = \frac{\text{avg gain}}{\text{avg loss}}$. Convention: >70 "overbought," <30 "oversold."
- **Hypothesis:** after an extreme run, price tends to **revert** — a bet on **mean reversion** /
  negative short-term autocorrelation. **Why it might work:** short-term overreactions get corrected;
  liquidity providers fade extremes.
- **When it fails (crucially):** in a **strong trend**, RSI can stay "overbought" for a *long* time
  while price keeps rising — "overbought" is not "about to fall." Mechanically selling every RSI>70 in
  an uptrend is a classic way to lose. RSI is a mean-reversion tool used wrongly in trending regimes.

> ⚠️ **Common mistake:** Treating "overbought/oversold" as "sell/buy now." They mean "stretched," and
> stretched things can stretch further. RSI's edge (if any) is *conditional on a ranging regime.*

### MACD
- **Mechanics:** **Moving Average Convergence Divergence** = (fast EMA − slow EMA), plotted with a
  **signal line** (EMA of the MACD) and a **histogram** (MACD − signal). Common: 12/26/9.
- **Hypothesis:** momentum shifts show up as the fast EMA pulling away from/toward the slow EMA; signal
  crossovers flag momentum turns. A **momentum/trend** bet.
- **Why it might work:** same trend-persistence logic as MAs, with a momentum overlay.
- **When it fails:** it's **two lagging averages of a lagging average** — even later than a plain MA
  crossover; whipsaws in ranges; "divergences" (price makes a new high, MACD doesn't) are seductive but
  🔬 unreliable as standalone signals.

### Bollinger Bands
- **Mechanics:** a middle **SMA** with an upper/lower band at ±*k* **standard deviations** (usually
  20-period, k=2). Bands **widen** with volatility and **contract** when calm ("squeeze").
- **Hypothesis (two competing uses!):** (a) *mean reversion* — price tends to return toward the middle
  band; (b) *breakout* — a "squeeze" precedes a big directional move. These are **opposite** bets, which
  is a warning sign about interpretive flexibility.
- **Why it might work:** volatility clusters (calm follows calm, storms follow storms — see
  [ATR](#atr-average-true-range)), so squeezes/expansions carry *some* information about volatility (not
  direction).
- **When it fails:** in a trend, price "rides the band" without reverting; treating band touches as
  reversal signals in a trend loses. The bands measure *volatility*, not *direction* — don't confuse
  the two.

### ATR (Average True Range)
- **Mechanics:** **ATR** = average of the **True Range** over *n* periods, where True Range = the
  greatest of (high−low), |high−prev close|, |low−prev close| (it accounts for gaps). It's a pure
  **volatility** measure in *price units* (e.g. "₹25 average daily range").
- **Hypothesis / use:** volatility is **persistent and clusters**, so recent ATR estimates near-term
  range. This is one of TA's most *defensible* ideas (volatility clustering is well-documented).
- **Why it matters for you:** ATR is the backbone of **[volatility-adjusted position sizing and
  stops](../07-risk-management/README.md#8-volatility-adjusted-sizing)** — set stops a multiple of ATR
  away so risk is normalized across instruments. This is arguably the *most useful* single indicator in
  TA precisely because it feeds risk management rather than trying to predict direction.
- **When it's misused:** ATR says nothing about *direction* — it's a magnitude, not a signal.

### Stochastic
- **Mechanics:** the **Stochastic oscillator** (%K, %D) places the current close within the recent
  high–low range (0–100). Near 100 = closing near the top of the range; near 0 = near the bottom.
- **Hypothesis:** like RSI, a **mean-reversion** bet on overbought/oversold extremes.
- **When it fails:** identical caveat to RSI — stays pinned at extremes during trends. It's another
  ranging-regime tool.

### ADX
- **Mechanics:** **Average Directional Index** (0–100) measures **trend *strength*** (not direction).
  High ADX (>25) = strong trend (up or down); low ADX (<20) = weak/ranging.
- **Hypothesis / use:** a **regime filter** — *when* to trust trend tools vs mean-reversion tools. Use
  MAs/MACD when ADX is high; use RSI/Stochastic when ADX is low.
- **Why it's valuable:** it directly addresses the biggest TA failure mode — **using the wrong tool for
  the regime.** Most indicator losses come from applying a trend tool in a range or a reversion tool in
  a trend; ADX tries to tell them apart.
- **When it fails:** it also lags, and transitions between regimes are exactly when it's least reliable.

> 💡 **Key takeaway:** Indicators cluster into two camps — **trend/momentum** (MA, MACD, ADX-high) and
> **mean-reversion** (RSI, Stochastic, Bollinger-as-reversion). They give *opposite* signals, and each
> only "works" in its matching regime. The hard part isn't the indicator; it's knowing which regime
> you're in — and that's genuinely difficult ([regime detection](../16-advanced-topics/README.md)).

---

## 7. Chart patterns

Classic patterns and the (skeptical) reality:

| Pattern | Folklore | Honest view |
|---|---|---|
| **Double top/bottom** | Reversal after two failed highs/lows | Sometimes; often noise. Test in advance, not hindsight |
| **Head & shoulders** | Major reversal | The most famous pattern; 🔬 evidence for reliable, tradeable edge is weak and inconsistent |
| **Triangles** (asc/desc/sym) | Continuation/breakout | Describe consolidation; breakout *direction* is closer to a coin flip than folklore admits |
| **Flags / pennants** | Brief pause then continuation | Reasonable *description* of a pullback in a trend; edge modest |
| **Wedges** | Reversal/continuation | Highly interpretive |
| **Channels** | Trend within parallel lines | A structure description; useful for framing, not prophecy |

**The core problem with patterns:** they are **defined loosely and identified in hindsight**, which
makes them look far more predictive than a *pre-committed, mechanical* definition tested out-of-sample
ever delivers. This is textbook [data snooping / overfitting](../12-backtesting-and-statistics/README.md#backtesting-pitfalls).

> ⚠️ **Common mistake:** "This is a perfect head-and-shoulders!" — said while the right shoulder is
> still forming, i.e. before you know if it completes. Survivorship (you remember the ones that
> "worked") + hindsight make patterns feel reliable. Demand a *mechanical* definition and a *forward*
> test before trusting one.

> 🧭 **Where patterns *are* useful:** as a shared *language* for describing price and for framing
> risk/entries ("if it breaks *this* level, thesis is wrong → stop *here*"). That framing value is real
> even if the predictive value is oversold.

---

## 8. Advanced: multi-timeframe, volume profile, order flow

- **Multi-timeframe analysis:** align a higher timeframe (trend/context) with a lower one (entry
  timing) — e.g. trade *with* the daily trend using 15-min entries. **Hypothesis:** the dominant trend
  is set on the higher timeframe; lower timeframes offer better entries in its direction. Guards against
  fighting the bigger flow — but adds interpretive degrees of freedom (more ways to fool yourself).
- **Volume profile:** shows volume traded *at each price* (rather than over time), revealing
  **high-volume nodes** (prices where lots of business happened → potential support/resistance) and
  **low-volume gaps** (prices that tend to be traversed quickly). More structurally grounded than most
  oscillators because it maps *where real trading occurred*.
- **VWAP** (revisited): institutional benchmark and intraday reference ([above](#vwap)).
- **Order-flow concepts:** reading the *aggressor* side — who is crossing the spread — via the tape,
  footprint charts, or [order-book imbalance](../15-market-microstructure/README.md). This is the
  closest TA gets to *cause* rather than *effect*, but it's data-intensive, fast, and dominated by
  professionals/HFT ([microstructure](../15-market-microstructure/README.md)).

> 💡 **Key takeaway:** The more *structural* the tool (real volume-at-price, real order flow), the more
> defensible; the more it's a *derived oscillator of past price*, the more it's just repackaging
> information already in the chart. Prefer tools tied to *where real orders are*.

---

## 9. How to test any TA idea

This is the payoff of the whole skeptical framing. Before trusting *any* indicator, pattern, or setup:

1. **State the hypothesis precisely** (e.g. "buying RSI<30 on NIFTY stocks in a *ranging* regime yields
   positive 5-day returns net of costs").
2. **Define it mechanically** — no discretion, no hindsight. A rule a computer could execute.
3. **Backtest with realistic costs and slippage** ([Indian cost stack](../17-indian-markets/README.md#the-cost-stack)) —
   TA signals trade often, so costs matter enormously.
4. **Split data:** in-sample to design, **out-of-sample** to validate; ideally
   [walk-forward](../12-backtesting-and-statistics/README.md). If it only works in-sample, it's overfit.
5. **Check [expectancy](../07-risk-management/README.md#5-expectancy--the-master-formula), not win
   rate**, and the **drawdown** you'd have suffered.
6. **Ask "why would this edge exist and persist?"** If you can't name a mechanism, be extra suspicious —
   and expect it to decay as others find it.

> 🔬 If you do this honestly, you'll discover most indicator "signals" have little to no edge after
> costs — and the few that survive are usually simple, regime-aware, and modest. That discovery *is*
> the education. See [Backtesting & Statistics](../12-backtesting-and-statistics/README.md).

---

## 10. Checklist & common mistakes

### ✅ Using TA responsibly
- [ ] For each tool, I can state its **hypothesis, mechanism, failure mode, and test**.
- [ ] I know whether I'm in a **trending or ranging** regime and use the matching tool ([ADX](#adx)).
- [ ] I'm not stacking correlated indicators and calling it "confirmation."
- [ ] My levels/patterns were defined **in advance**, not drawn in hindsight.
- [ ] Any setup I trade has been **tested out-of-sample with costs**, judged on expectancy.
- [ ] TA feeds my **risk management** (ATR stops/sizing), not just entries.

### ⚠️ Classic TA mistakes
| Mistake | Reality |
|---|---|
| Treating indicators as predictors | They're transformations of *past* price; no hidden info |
| Selling every "overbought" RSI | In trends, overbought stays overbought |
| Ten indicators = ten confirmations | They're correlated; often one signal in ten costumes |
| Drawing levels/patterns in hindsight | Looks predictive; isn't, until forward-tested |
| Using a trend tool in a range (or vice versa) | The #1 source of indicator losses — wrong regime |
| Ignoring costs on frequent signals | TA trades a lot; costs can erase the entire edge |

---

### Related sections
- [03 Price & Market Behavior](../03-price-and-market-behavior/README.md) — what price and volume actually mean.
- [07 Risk Management → ATR sizing](../07-risk-management/README.md#8-volatility-adjusted-sizing) — TA's most useful application.
- [12 Backtesting & Statistics](../12-backtesting-and-statistics/README.md) — how to test a TA idea without fooling yourself.
- [14 Quantitative Trading](../14-quantitative-trading/README.md) — momentum/reversion as documented factors.
- [16 Advanced Topics → regime detection](../16-advanced-topics/README.md) — the hard problem of knowing the regime.
- [Glossary](../glossary/README.md) — SMA, EMA, RSI, MACD, ATR, VWAP, ADX, support/resistance.

> Next: [06 — Trading Styles](../06-trading-styles/README.md) →
