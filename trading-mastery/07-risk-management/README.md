# 07 — Risk Management

> ⬅ Back to [README](../README.md) · Prev: [06 Trading Styles](../06-trading-styles/README.md) · Next: [08 Strategy Development](../08-strategy-development/README.md)

> 💡 **Key takeaway (read this even if you read nothing else):** Trading is not a game of being
> right. It is a game of **staying solvent while a positive edge plays out over many trades.** You
> can be right often and still go broke; you can be wrong often and still get rich. This section
> shows you the arithmetic of why.

**Contents**
1. [Why risk management comes first](#1-why-risk-management-comes-first)
2. [Risk per trade & position sizing](#2-risk-per-trade--position-sizing)
3. [Stop losses done properly](#3-stop-losses-done-properly)
4. [Risk/reward and the R multiple](#4-riskreward-and-the-r-multiple)
5. [Expectancy — the master formula](#5-expectancy--the-master-formula)
6. [Why a 40% win rate can win and a 70% win rate can lose](#6-why-a-40-win-rate-can-win-and-a-70-win-rate-can-lose)
7. [Drawdown, losing streaks, and risk of ruin](#7-drawdown-losing-streaks-and-risk-of-ruin)
8. [Volatility-adjusted sizing](#8-volatility-adjusted-sizing)
9. [The Kelly criterion (and why to use a fraction of it)](#9-the-kelly-criterion-and-why-to-use-a-fraction-of-it)
10. [Portfolio-level risk: correlation, exposure, leverage](#10-portfolio-level-risk-correlation-exposure-leverage)
11. [Checklist & common mistakes](#11-checklist--common-mistakes)

---

## 1. Why risk management comes first

Consider two facts that sound contradictory but are both true:

- A strategy with a **genuine positive edge** can still wipe you out if you size positions too big,
  because bad luck clusters.
- A strategy with **no edge at all** can look brilliant for months, then give it all back.

The job of risk management is to keep you in the game long enough for a real edge (if you have one)
to express itself, and to lose *slowly and survivably* if you don't. Everything else — entries,
indicators, patterns — is secondary. This is not a motivational slogan; the rest of the section is
the math that makes it literally true.

> ⚠️ **Common mistake:** Beginners obsess over *entries* ("what's the best indicator to buy?") and
> ignore *sizing* and *exits*, which dominate long-run results. Two traders with the **same entries**
> but different position sizing can have opposite outcomes.

---

## 2. Risk per trade & position sizing

The single most important habit: **decide how much money you are willing to lose on a trade
*before* you enter, and size the position so that hitting your stop loses exactly that amount.**

### The core position-sizing formula

$$\text{Quantity} = \frac{\text{Account} \times \text{Risk per trade (\%)}}{\text{Entry price} - \text{Stop price}}$$

- **What it calculates:** how many shares/contracts to buy so that a stop-out costs a fixed
  fraction of your account.
- **Why it matters:** it decouples *how much you risk* from *the price of the stock*. A ₹3,000 stock
  and a ₹30 stock can carry the *same* rupee risk.
- **Variables:**
  - *Account* — your total trading capital (₹).
  - *Risk per trade* — the fraction you'll lose if stopped (commonly **0.5%–2%**; see below).
  - *Entry − Stop* — the per-share loss if the stop triggers (the "risk per share").
- **Numerical example (Indian):**
  - Account = **₹5,00,000**. Risk per trade = **1%** → you will risk **₹5,000**.
  - You buy RELIANCE at **₹1,400** with a stop at **₹1,370** → risk per share = **₹30**.
  - Quantity = ₹5,000 ÷ ₹30 = **166 shares** (round down to be safe).
  - Position value = 166 × ₹1,400 = **₹2,32,400** — notice this is ~46% of your account, yet you
    only risk 1% of it, because the stop is close.
- **Limitations:** Stops are not guaranteed fills — **gaps and slippage** can make the realized loss
  larger than planned (see [§3](#3-stop-losses-done-properly)). The formula also ignores costs; in
  India, STT/brokerage/GST/stamp duty widen your true breakeven (see
  [Indian Markets → cost stack](../17-indian-markets/README.md#the-cost-stack)).

### How much should "risk per trade" be?

| Risk/trade | Trades to a 20% drawdown (roughly, if you lose every one) | Character |
|---|---|---|
| 0.25% | ~90 | Very conservative; slow but hard to blow up. |
| 0.5%  | ~45 | Conservative. A common professional choice. |
| 1%    | ~22 | Standard "aggressive but sane" retail level. |
| 2%    | ~11 | Aggressive; a 10-loss streak already hurts a lot. |
| 5%+   | ~4  | 🚩 Reckless. A normal losing streak can end you. |

> 💡 **Key takeaway:** Small, *consistent* risk per trade is what lets you survive the losing
> streaks that **every** strategy produces. The goal of sizing is not to maximize this trade's
> profit — it is to guarantee you are still here for trade #500.

---

## 3. Stop losses done properly

A **stop loss** is a pre-committed exit that caps a trade's loss. It exists because humans are
terrible at cutting losers in the moment (see [Psychology → disposition effect](../11-trading-psychology/README.md)).

### Placement: structure, not round numbers

Place stops where your **thesis is proven wrong**, not at an arbitrary "I can only lose ₹X" level.
If you're long on a breakout above resistance, the trade is wrong if price falls back *below* the
breakout level — so the stop belongs just under it. Then use [§2](#2-risk-per-trade--position-sizing)
to size *around* that stop, not the other way round.

### Stops are promises the market can break

| Order used as stop | What it guarantees | What it does **not** guarantee |
|---|---|---|
| **Stop-market** | You *will* exit (it becomes a market order when triggered) | The *price* — in a gap you can fill far worse |
| **Stop-limit** | The *price* (won't fill worse than your limit) | The *fill* — in a fast move it may not execute at all, leaving you in the trade |

> ⚠️ **Common mistake:** Assuming a ₹30 stop caps your loss at ₹30/share. On an overnight gap, an
> earnings shock, or a lower-circuit move, you can lose far more. This is called **gap/slippage
> risk** and is the main reason to keep per-trade risk small and to be cautious holding through
> known events (results, budgets, RBI policy). See
> [Price behavior → gaps](../03-price-and-market-behavior/README.md).

🤔 **Think about this:** If stops can slip, why use them at all? (Because a *distribution of losses
that is usually capped and occasionally larger* is vastly better than *no cap at all* — you survive
the ordinary and only rarely suffer the extreme.)

---

## 4. Risk/reward and the R multiple

Define **1R = the amount you risk on a trade** (from entry to stop). Then measure every outcome in R.

- Risk ₹5,000, make ₹10,000 → **+2R**. Risk ₹5,000, lose ₹5,000 → **−1R**. Stopped at half → −0.5R.

Thinking in **R** frees you from rupee amounts and lets you compare trades of different sizes on one
scale. Your entire track record becomes a list like `+2R, −1R, −1R, +3R, −1R, +1R…`, which is
exactly what expectancy ([§5](#5-expectancy--the-master-formula)) needs.

> 💡 **Key takeaway:** The two levers of profitability are **how often you win (win rate)** and **how
> big wins are versus losses (reward:risk)**. Neither alone tells you if a strategy makes money —
> only their *combination* does.

---

## 5. Expectancy — the master formula

**Expectancy** is the average profit (or loss) per trade, in rupees or in R. It is the number that
actually decides whether a strategy makes money.

$$E = (W \times A_w) - (L \times A_l)$$

- **What it calculates:** expected P&L per trade.
- **Why it matters:** if `E > 0` and you take enough trades at sane size, you make money; if `E < 0`,
  no entry technique or "discipline" can save you — you are feeding a negative-sum machine.
- **Variables:**
  - `W` = win rate (probability of a win), `L = 1 − W` = loss rate.
  - `A_w` = average win size (in ₹ or R). `A_l` = average loss size (positive number).
- **Numerical example:** Win rate 45%, average win ₹8,000, average loss ₹4,000.
  - `E = (0.45 × 8,000) − (0.55 × 4,000) = 3,600 − 2,200 =` **₹1,400 per trade**.
  - Over 200 trades that's ~₹2,80,000 *before costs* — but see the cost caveat below.
- **Limitations:**
  - **Costs are not optional.** Subtract *average cost per round-trip trade* from `E`. In Indian
    intraday/F&O, costs per trade can easily be ₹100–₹500+; a strategy with `E = +₹150` gross can be
    *negative* net. Always compute **net expectancy.**
  - Expectancy assumes your historical `W`, `A_w`, `A_l` are stable and representative. They drift.
  - A positive expectancy says nothing about *path* — you still need [§7](#7-drawdown-losing-streaks-and-risk-of-ruin).

### Expectancy in R (cleaner)

$$E_R = W \times R_{win} - L \times 1$$ where `R_win` = average win in R (since a full loss = 1R).

Example: Win rate 40%, average winner = **2.5R**. `E_R = 0.40 × 2.5 − 0.60 × 1 = 1.0 − 0.6 =` **+0.4R
per trade.** You net 0.4R on average every time you press the button. *That* is an edge.

---

## 6. Why a 40% win rate can win and a 70% win rate can lose

This is the heart of the section. **Win rate alone is meaningless.** What matters is
`win rate × reward:risk`.

### Case A — the 40% winner that makes money (trend-following flavour)

- Win rate **40%**, average win **+3R**, average loss **−1R** (you cut losers fast, let winners run).
- `E_R = 0.40 × 3 − 0.60 × 1 = 1.2 − 0.6 =` **+0.6R per trade.**
- Over 100 trades at ₹5,000 risk (1R): `100 × 0.6R × ₹5,000 =` **₹3,00,000** expected profit
  (before costs). You **lose more often than you win** and get richer, because the wins are big.

### Case B — the 70% winner that loses money (naive option-selling / "picking pennies" flavour)

- Win rate **70%**, average win **+0.5R**, average loss **−2R** (small frequent gains, occasional
  large losses — the classic "selling options / martingale" payoff shape).
- `E_R = 0.70 × 0.5 − 0.30 × 2 = 0.35 − 0.60 =` **−0.25R per trade.**
- Over 100 trades at ₹5,000 risk: `100 × (−0.25R) × ₹5,000 =` **−₹1,25,000** expected loss.
  You **win 7 out of 10 trades** and go broke, because the 3 losses each erase four wins.

### Side-by-side

| | Case A (trend) | Case B (penny-picking) |
|---|---|---|
| Win rate | 40% ✅ *feels bad* | 70% ✅ *feels great* |
| Avg win | +3R | +0.5R |
| Avg loss | −1R | −2R |
| **Expectancy** | **+0.6R** ✅ | **−0.25R** 🚩 |
| Emotional experience | Frequent small losses, rare big wins — *hard to hold* | Frequent small wins, rare big losses — *seductive, then ruinous* |

> 💡 **Key takeaway:** The market pays you for **expectancy**, not for being right. High-win-rate
> strategies are psychologically pleasant and can be *fine* — **but only if the rare losses stay
> small relative to the frequent wins.** The danger is a payoff shape where you "win small, win
> small, win small… lose huge." That shape shows up again in
> [Options → why selling isn't free money](../10-options/README.md#why-selling-options-is-not-free-money).

🤔 **Think about this:** Someone shows you a screenshot: "92% win rate!" What are the *first two
numbers* you must ask for before being impressed? (Average win size and average loss size — i.e. the
payoff of the 8%.)

🔬 **Testable claim:** "This strategy is profitable." The evidence that matters is a large,
out-of-sample sample of trades whose **net** expectancy (after realistic Indian costs and slippage)
is reliably positive — not a high win rate on a cherry-picked in-sample window. See
[Backtesting](../12-backtesting-and-statistics/README.md).

---

## 7. Drawdown, losing streaks, and risk of ruin

### Losing streaks are normal — and longer than your intuition

Even a good 50%-win strategy will, over a few hundred trades, hand you streaks of 6–8 losses in a
row *by pure chance*. The probability of a streak of length `k` shows up surprisingly often over
many trades.

- Probability of `k` losses in a row (independent trades) = `L^k`.
- With `L = 0.5`: seven losses in a row = `0.5^7 ≈ 0.8%` on any given start — but across **hundreds**
  of trades, encountering *some* such streak becomes almost certain.

If you risk **2%** per trade and hit an 8-loss streak, you're down ~15% and rattled. If you risk
**10%** per trade, the same ordinary streak leaves you down ~57% — and needing a **+133%** gain just
to recover. This asymmetry is the killer:

### The recovery math (why drawdowns are asymmetric)

$$\text{Gain needed to recover} = \frac{1}{1 - d} - 1$$

- **What it calculates:** the return required to climb back from a drawdown of fraction `d`.
- **Why it matters:** losses and gains are *not* symmetric — a −50% needs +100%, not +50%.
- **Example table:**

| Drawdown `d` | Gain to recover |
|---|---|
| −10% | +11.1% |
| −20% | +25% |
| −33% | +50% |
| −50% | **+100%** |
| −75% | **+300%** |
| −90% | **+900%** |

> ⚠️ **Common mistake:** "I'm down 50%, I just need 50% to get back." No — you need **100%**. Deep
> drawdowns are mathematically brutal, which is *why* small per-trade risk is non-negotiable.

### Maximum drawdown, defined

**Maximum drawdown (MDD)** = the largest peak-to-trough fall in your equity curve over a period. It
is the single most honest measure of "how bad did it feel / how close to quitting or ruin did I get."
Two strategies with identical returns but different MDD are *not* equally good — the lower-MDD one is
superior on a risk-adjusted basis (see [Sharpe/Calmar](../12-backtesting-and-statistics/README.md)).

### Risk of ruin (intuition + a usable bound)

**Risk of ruin (RoR)** = the probability that a losing streak takes your account below a threshold
you can't come back from (either literal zero, or the point where you stop trading). Three levers
control it:

1. **Edge** (expectancy) — more edge → lower RoR.
2. **Risk per trade** — smaller size → dramatically lower RoR.
3. **Bankroll relative to bet size** — more "bullets" → lower RoR.

A simplified model (equal-sized bets, win prob `p`, lose prob `q = 1−p`, risking a fixed fraction):
for a **negative-edge** game, ruin is essentially certain given enough trades — *time is the
gambler's enemy.* For a **positive-edge** game, RoR falls roughly geometrically as you cut bet size.
The practical lesson doesn't need the full formula:

> 💡 **Key takeaway:** With a real edge, **halving your risk per trade cuts your risk of ruin far
> more than proportionally.** With no edge, no bet size saves you — only *not playing* does. This is
> why the [Kelly criterion](#9-the-kelly-criterion-and-why-to-use-a-fraction-of-it) below never tells
> a negative-edge bettor to bet anything.

---

## 8. Volatility-adjusted sizing

A fixed ₹ stop makes no sense across instruments with wildly different volatility: ₹30 is a tight
stop on RELIANCE but an absurdly loose one on a ₹40 penny stock. **Volatility-adjusted sizing** sets
your stop distance from the instrument's own movement, usually via **ATR** (Average True Range — see
[Technical Analysis → ATR](../05-technical-analysis/README.md#atr-average-true-range)).

### ATR-based sizing

1. Choose risk per trade (e.g. ₹5,000).
2. Choose stop distance as a multiple of ATR (e.g. 2 × ATR). If daily ATR = ₹25, stop distance = ₹50.
3. Quantity = ₹5,000 ÷ ₹50 = **100 shares.**

Now a calm stock (small ATR) gets a *bigger* position and a wild stock gets a *smaller* one, so each
trade risks the same rupees **and** roughly the same "amount of normal wiggle." This is how you make
positions comparable across a portfolio.

> 💡 **Key takeaway:** Normalize by volatility so that "1 unit of risk" means the same thing whether
> you're trading a sleepy PSU or a volatile smallcap. Fixed share counts are how portfolios end up
> accidentally dominated by their most volatile name.

---

## 9. The Kelly criterion (and why to use a fraction of it)

The **Kelly criterion** answers: "Given my edge, what bet fraction maximizes long-run *growth rate*
of capital?" Bet more and you grow faster — until volatility drag and ruin risk overwhelm you; bet
less and you leave growth on the table. Kelly is the theoretical sweet spot for growth.

### For a simple win/lose bet

$$f^* = \frac{bp - q}{b}$$

- **What it calculates:** the fraction of capital to risk to maximize long-term geometric growth.
- **Variables:** `p` = win prob, `q = 1 − p`, `b` = reward-to-risk (win size ÷ loss size).
- **Example:** `p = 0.55`, `q = 0.45`, `b = 1` (win = risk). `f* = (1×0.55 − 0.45)/1 =` **0.10 → risk
  10% per trade** for maximum growth.
- **Crucial property:** if edge is zero or negative (`bp ≤ q`), Kelly returns `f* ≤ 0` → **bet
  nothing.** Kelly literally forbids betting a negative-edge game. 🚩

### Why almost nobody bets full Kelly

- Full Kelly is a **wild ride**: it routinely produces 50%+ drawdowns even when "correct."
- Your inputs (`p`, `b`) are **estimates**; overestimating edge makes full Kelly *over*bet, which is
  far more dangerous than underbetting. Growth is roughly flat near the Kelly peak but risk rises
  steeply past it — so erring high is punished asymmetrically.
- **Standard practice: fractional Kelly** — bet ¼ to ½ of `f*`. Half-Kelly captures ~75% of the
  growth with far less than half the drawdown. This is why the sane retail numbers in
  [§2](#2-risk-per-trade--position-sizing) (0.5%–2%) exist: they are *fractional-Kelly-sized* for
  realistic, uncertain edges.

> ⚠️ **Common mistake:** Plugging optimistic, overfit backtest numbers into Kelly and betting the
> result. Since your edge estimate is almost always too high, this over-bets — the very thing Kelly's
> own math punishes hardest.

🤔 **Think about this:** Two traders have the same true edge. One bets full Kelly, one bets
half-Kelly. Over 20 years, why might the half-Kelly trader end up *wealthier and definitely
saner*? (Lower drawdowns mean less chance of a forced stop, less emotional error, and less volatility
drag on compounding.)

---

## 10. Portfolio-level risk: correlation, exposure, leverage

Sizing each trade correctly is not enough — **your positions interact.**

- **Correlation.** Five "different" long trades in banking (HDFCBANK, ICICIBANK, AXISBANK,
  KOTAKBANK, SBIN) are essentially **one big bet on banks**. In a sector selloff they all hit stops
  together, so your "1% per trade × 5 = 5% at risk" is really ~5% on a *single* correlated event.
  See [Foundations → correlation](../00-foundations/README.md#correlation) and
  [Foundations → diversification](../00-foundations/README.md#diversification).
- **Total exposure & heat.** Track the sum of *open risk* ("portfolio heat"). A common cap: total
  simultaneous risk ≤ **6%** of the account. When many correlated positions are open, treat their
  combined risk as larger than the naive sum.
- **Leverage & margin.** Leverage multiplies **both** returns and losses and introduces **margin
  calls** — forced liquidation at the worst possible moment. In Indian F&O, leverage is inherent and
  SEBI has *raised* the capital required per lot precisely because retail traders were over-levered
  (see [Indian Markets → F&O framework](../17-indian-markets/README.md#the-sebi-fo-overhaul-2024-2026)).
  Leverage does not create edge; it only scales what you already have — including a *negative* edge.

> 💡 **Key takeaway:** Diversification only helps when positions are genuinely **uncorrelated**. Ten
> correlated bets are one bet with extra brokerage. Always ask: *if I'm wrong, how many of these lose
> at once?*

---

## 11. Checklist & common mistakes

### ✅ Pre-trade risk checklist

- [ ] I know my **stop level** (where the thesis is wrong) *before* entering.
- [ ] I sized the position from **risk per trade** ([§2](#2-risk-per-trade--position-sizing)), not gut feel.
- [ ] Risk per trade ≤ my chosen cap (e.g. 1%).
- [ ] My **net** expectancy (after Indian costs) is positive, or this is a tested edge.
- [ ] Total **portfolio heat** (all open risk, correlations included) is within my cap.
- [ ] I've considered **gap/event risk** (results, budget, RBI) for anything held overnight.
- [ ] The position size is **fractional-Kelly** sane, not full-Kelly greedy.

### ⚠️ The classic ways people blow up

| Mistake | Why it kills you | Fix |
|---|---|---|
| No stop / "mental stop" ignored in the moment | One trade becomes 20 trades' worth of loss | Pre-committed hard stop, sized small |
| Sizing by "shares I can afford" | Risk varies randomly with stock price | Size by risk/trade formula |
| Averaging down a loser | Adds risk exactly when thesis is failing | Add only to *winners*, per plan |
| Risking 5–10% per trade | Normal streaks → catastrophic drawdown | 0.5–2% per trade |
| Ignoring correlation | "Diversified" book is one bet | Cap sector/factor exposure |
| Betting full Kelly on overfit stats | Over-bets a mis-estimated edge | Half-Kelly or less |
| Forgetting costs | Positive gross edge, negative net | Always compute net expectancy |

---

### Related sections
- [12 Backtesting & Statistics](../12-backtesting-and-statistics/README.md) — measuring expectancy, Sharpe, and drawdown honestly.
- [10 Options → why selling isn't free money](../10-options/README.md#why-selling-options-is-not-free-money) — the "win small, lose huge" payoff in the wild.
- [11 Trading Psychology](../11-trading-psychology/README.md) — why we break our own risk rules.
- [19 Case Studies](../19-case-studies/README.md) — a bad risk decision and a famous blow-up, dissected.
- [Glossary](../glossary/README.md) — expectancy, drawdown, Kelly, risk of ruin, R multiple.

> Next: [08 — Strategy Development](../08-strategy-development/README.md) →
