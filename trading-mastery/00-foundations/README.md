# 00 — Foundations

> ⬅ Back to [README](../README.md) · Next: [01 How Markets Work](../01-how-markets-work/README.md)

> 💡 **Key takeaway:** Before you can trade anything, you need a clear mental model of what money,
> assets, risk, and return *are*. Most trading mistakes trace back to fuzzy foundations — people
> chase "returns" without understanding risk, or confuse a lucky outcome with a good decision.

**Contents**
1. [What is money?](#1-what-is-money)
2. [What is an asset?](#2-what-is-an-asset)
3. [What is a financial market, and why do they exist?](#3-what-is-a-financial-market-and-why-do-they-exist)
4. [Investing vs trading vs speculation](#4-investing-vs-trading-vs-speculation)
5. [Risk vs uncertainty](#5-risk-vs-uncertainty)
6. [Return](#6-return)
7. [Compounding](#7-compounding)
8. [Inflation; nominal vs real returns](#8-inflation-nominal-vs-real-returns)
9. [Liquidity](#9-liquidity)
10. [Volatility](#10-volatility)
11. [Correlation](#correlation)
12. [Diversification](#diversification)
13. [Risk-adjusted returns](#13-risk-adjusted-returns)

---

## 1. What is money?

Money is a **social technology** that solves the problems of barter. It performs three jobs:

| Function | What it means | Failure example |
|---|---|---|
| **Medium of exchange** | Everyone accepts it, so you don't need a "double coincidence of wants" | Barter: a farmer with rice must find a tailor who wants rice |
| **Unit of account** | A common yardstick to price everything | Without it, you'd memorise rice↔cloth↔shoes↔… ratios |
| **Store of value** | Holds purchasing power across time | High inflation erodes this (see [§8](#8-inflation-nominal-vs-real-returns)) |

Modern money (the ₹ in your bank account) is **fiat** — it has value because a government decrees it
legal tender and, crucially, because *everyone else accepts it*. It is mostly digital ledger entries,
not physical notes. This matters for trading because **prices are quoted in money**, and money itself
is not a fixed ruler — it shrinks over time via inflation.

> 💡 **Key takeaway:** Money is a claim on real goods and services, not wealth itself. Holding cash is
> a *position* — a bet that its purchasing power holds up. See [nominal vs real](#8-inflation-nominal-vs-real-returns).

---

## 2. What is an asset?

An **asset** is anything expected to produce **future economic benefit** — cash flows, or the ability
to sell it later for money. Assets fall into rough families by *where their value comes from*:

| Asset family | Value comes from… | Indian example |
|---|---|---|
| **Productive / cash-flowing** | Future cash it generates | A share of INFY (dividends + earnings growth); a bond's coupons; a rented flat |
| **Store-of-value / non-cash-flowing** | What others will pay later | Gold, most commodities, currencies |
| **Derivative** | The price of *another* asset | NIFTY futures, options ([09](../09-futures/README.md)/[10](../10-options/README.md)) |

The deepest divide is between assets that **produce something** (a business earns profits; a bond pays
interest) and assets that merely **sit there** (gold produces no cash; its price is purely what the
next person will pay). Both can be traded, but they must be *valued* differently — a business by its
cash flows ([Fundamental Analysis](../04-fundamental-analysis/README.md)), gold only by supply/demand
and sentiment.

> 🤔 **Think about this:** Is a lottery ticket an asset? (It has an expected value, but it's a
> negative-expectancy bet, not a productive asset. The distinction between "has some payoff" and "is
> worth owning" recurs throughout trading — see [expectancy](../07-risk-management/README.md#5-expectancy--the-master-formula).)

---

## 3. What is a financial market, and why do they exist?

A **financial market** is any venue where people trade financial assets. Markets exist because they
solve real problems:

1. **Capital formation.** A company that needs ₹500 crore to build a factory can raise it from many
   investors at once (via shares or bonds) instead of one lender. Society channels savings to
   productive use.
2. **Liquidity.** You can sell your share of a company *without* the company having to buy back its
   factory. A market lets ownership change hands cheaply and quickly.
3. **Price discovery.** The constant tug-of-war of buyers and sellers produces a *price* — a
   compressed summary of everything the crowd currently believes about an asset's value
   ([Price behavior](../03-price-and-market-behavior/README.md)).
4. **Risk transfer.** Someone who wants to *shed* risk (a farmer hedging crop prices, an airline
   hedging fuel) can transfer it to someone willing to *bear* it (a speculator). Derivatives markets
   exist largely for this ([Futures](../09-futures/README.md)).

> 💡 **Key takeaway:** Markets are not casinos bolted onto the economy — they perform genuine
> economic functions. *Speculation* (below) is part of the machinery that provides liquidity and
> price discovery, not a moral failing — though it can certainly be done recklessly.

---

## 4. Investing vs trading vs speculation

These three words are used loosely, but the distinctions are real and shape everything about how you
should behave.

| | **Investing** | **Trading** | **Speculation** |
|---|---|---|---|
| Source of return | The asset's underlying cash flows / growth | Short-term price changes | A specific bet on a price move or event |
| Typical horizon | Years to decades | Minutes to months | Any (often event-driven) |
| Primary question | "Is this a good business at a fair price?" | "Will price move in my favour soon?" | "Is this specific bet mispriced?" |
| Example | Buying an index fund for retirement | Swing-trading a breakout in TATAMOTORS | Buying weekly OTM options before results |
| Main risk | Business/valuation risk over time | Being wrong repeatedly; costs | Total loss on the specific bet |

**The honest framing:** these lie on a *spectrum*, not in tidy boxes. Buying a stock you'll hold a
week because you like the chart is trading. Buying it because you'll hold it 20 years for its earnings
is investing. Buying a lottery-like option is speculation. Many people **speculate while telling
themselves they're investing** — that self-deception is where a lot of money dies.

> ⚠️ **Common mistake:** Calling a losing trade a "long-term investment" *after* it drops. Changing
> your thesis to justify not taking a loss is the [disposition effect](../11-trading-psychology/README.md)
> in disguise. Decide *before* you enter which game you're playing.

---

## 5. Risk vs uncertainty

A distinction from economist Frank Knight that is central to trading:

- **Risk** = outcomes are unknown but the **probabilities are (roughly) knowable**. A fair die: you
  don't know the next roll, but you know each face is 1/6. You can price it.
- **Uncertainty** = you **don't even know the probabilities** (or the full set of outcomes). What will
  Indian equity markets do over the next decade given unknown policy, technology, and geopolitics? No
  reliable probability distribution exists.

Markets contain **both**. Options pricing pretends volatility is a knowable "risk" (a number you can
plug into a model) — but true regime shifts, crashes, and black-swan events are **uncertainty** that
no model fully captures. This is why:

> 💡 **Key takeaway:** Treat your probability estimates as *estimates*, not facts, and always keep
> capital back for the outcomes you didn't imagine. Models convert uncertainty into risk *on paper*;
> reality does not always cooperate. This is the philosophical root of
> [risk of ruin](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin) and
> [why fat tails matter in options](../10-options/README.md#why-selling-options-is-not-free-money).

---

## 6. Return

A **return** is the gain or loss on an investment as a fraction of what you put in.

$$R = \frac{P_{end} - P_{start} + \text{Income}}{P_{start}}$$

- **What it calculates:** total percentage gain, including price change *and* income (dividends/coupons).
- **Why it matters:** it lets you compare investments of different sizes on one scale.
- **Variables:** `P_start`/`P_end` = start/end price; Income = dividends or coupons received.
- **Example (Indian):** Buy 100 shares of a stock at ₹200 (₹20,000). A year later price is ₹230 and it
  paid ₹4/share dividend. Return = `(23,000 − 20,000 + 400) / 20,000 = 3,400/20,000 =` **17%.**
- **Limitations:** a single-period return ignores *when* cash flowed and *how much risk* you took. A
  17% return with wild swings is not the same as a steady 17% (see [risk-adjusted returns](#13-risk-adjusted-returns)).

**Arithmetic vs geometric (CAGR).** Averaging returns naively overstates growth. If you make +50% then
−50%, the *arithmetic* average is 0%, but you actually have `1.5 × 0.5 = 0.75` → you **lost 25%.**
The **CAGR** (compound annual growth rate) captures what you actually earned:

$$\text{CAGR} = \left(\frac{P_{end}}{P_{start}}\right)^{1/n} - 1$$

where `n` = number of years. This asymmetry (gains and losses don't cancel) is the same math as
[drawdown recovery](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin).

---

## 7. Compounding

**Compounding** = earning returns on your past returns. It is the most important — and most
*underestimated* — force in finance because it grows **exponentially**, and human intuition is linear.

$$FV = PV \times (1 + r)^n$$

- **What it calculates:** future value of an amount growing at rate `r` for `n` periods.
- **Variables:** `PV` = present value, `r` = periodic return, `n` = number of periods.
- **Example:** ₹1,00,000 at **12%/year** for **30 years** = `1,00,000 × 1.12^30 ≈` **₹29,96,000** —
  nearly **30×**, from a rate that sounds modest. At 15% it's ~₹66 lakh; at 8% it's ~₹10 lakh. Small
  differences in rate → huge differences over decades.
- **The Rule of 72 (handy heuristic):** years to double ≈ `72 ÷ (rate %)`. At 12%, money doubles in
  ~6 years; at 8%, ~9 years. 🧭 A useful *approximation*, not exact.
- **Limitations:** compounding cuts *both ways* — costs, taxes, and losses compound against you too. A
  1.5% annual fee over 30 years can quietly eat a *third or more* of your final wealth. And a big
  drawdown resets the compounding base, which is why avoiding ruin matters so much.

> 💡 **Key takeaway:** Time in the market and *avoiding large losses* usually beat clever timing,
> because compounding rewards uninterrupted growth. A trader's real enemy is not "missing gains" — it
> is the deep drawdown that breaks the compounding chain.

🤔 **Think about this:** Would you rather have ₹10 lakh today, or ₹1 that doubles every day for 30
days? (₹1 doubling for 30 days ≈ ₹53 crore. Exponential growth crushes linear intuition — this is why
people mis-judge both compounding *and* how fast a leveraged loss can spiral.)

---

## 8. Inflation; nominal vs real returns

**Inflation** is the general rise in prices over time — equivalently, the fall in money's purchasing
power. If inflation is 6%, something that costs ₹100 today costs ₹106 next year; your ₹100 note buys
*less*.

- **Nominal return** = the raw percentage your money grew (the number on your statement).
- **Real return** = nominal return *adjusted for inflation* — what your wealth grew in terms of actual
  purchasing power.

$$\text{Real} \approx \text{Nominal} - \text{Inflation}$$ (a good approximation; exact form is
`(1+nom)/(1+inf) − 1`).

- **Example:** A fixed deposit pays **7%** while inflation runs **6%**. Nominal return = 7%, **real
  return ≈ 1%.** You feel richer (more rupees) but are barely gaining purchasing power. If inflation
  were 8%, your "safe" 7% FD is a **−1% real** loss — you're getting poorer safely.

> ⚠️ **Common mistake:** Judging investments by nominal returns and calling cash/FDs "risk-free."
> They carry **inflation risk** — a near-guaranteed slow erosion of purchasing power. "Safe" and "no
> loss" are not the same thing. This is *why* people take on market risk at all: to try to beat
> inflation over the long run.

---

## 9. Liquidity

**Liquidity** = how easily you can convert an asset to cash **near its fair price, quickly, without
moving the price against you.**

| High liquidity | Low liquidity |
|---|---|
| RELIANCE, HDFCBANK, NIFTY futures | An illiquid smallcap, real estate, unlisted shares |
| Tight [bid-ask spread](../01-how-markets-work/README.md#bid-ask-and-the-spread) | Wide spread; few buyers/sellers |
| You can exit large size fast | Selling in size *crashes* the price |

Liquidity is a *hidden risk*. A position can look great on paper but be a trap if you can't exit
without a huge haircut. In a panic, liquidity **evaporates precisely when you need it** — spreads
blow out, and "market orders" fill at terrible prices ([slippage](../01-how-markets-work/README.md#slippage)).

> 💡 **Key takeaway:** Always ask "how will I get *out*?" before you get in. Illiquidity is fine for a
> patient long-term holder and lethal for a trader who might need to exit fast. It also directly
> raises your trading costs (see [microstructure](../15-market-microstructure/README.md)).

---

## 10. Volatility

**Volatility** = how much a price *swings around*, usually measured as the **standard deviation** of
returns ([stats](../12-backtesting-and-statistics/README.md)). High volatility = big, frequent moves;
low volatility = calm.

- **It is not the same as risk, but it's related.** Volatility measures *variability*; risk is the
  chance of a *bad outcome*. A wildly volatile asset that always ends higher isn't "risky" in the
  ruin sense — but volatility raises the odds of hitting a stop, forces smaller position sizes
  ([vol-adjusted sizing](../07-risk-management/README.md#8-volatility-adjusted-sizing)), and creates
  drawdowns that break compounding and nerve.
- **Example:** Two stocks both return 12%/year on average. Stock A ranges ±10% around it; Stock B
  ranges ±40%. Same average, very different *experience* and very different odds of being shaken out
  at the worst time.
- India's **India VIX** measures expected NIFTY volatility from option prices — a market-implied "fear
  gauge" ([Options → IV](../10-options/README.md#5-volatility-implied-vs-historical-smile-skew)).

> 💡 **Key takeaway:** Volatility is the *raw material* of trading (no movement, no opportunity) and
> simultaneously the thing that must be *managed*. More volatility means you must trade *smaller*, not
> bigger, to keep rupee risk constant.

---

## Correlation

**Correlation** measures how two assets' returns move *together*, on a scale from −1 to +1:

| Correlation | Meaning | Example |
|---|---|---|
| **+1** | Move perfectly together | Two large private banks in the same selloff |
| **0** | No linear relationship | Gold and a random midcap (often loosely related) |
| **−1** | Move perfectly opposite | A stock and a well-designed hedge against it |

Correlation is the hinge of [diversification](#diversification) and portfolio risk. Combining assets
that *don't* move together smooths your equity curve; combining assets that *do* just concentrates one
bet ([Risk Management → correlation](../07-risk-management/README.md#10-portfolio-level-risk-correlation-exposure-leverage)).

> ⚠️ **Common mistake:** Assuming correlations are stable. In a crisis, *everything* tends to fall
> together — correlations "go to 1" exactly when you were counting on diversification to protect you.
> Historical correlation is a 🧭 useful model, not a guarantee.

---

## Diversification

**Diversification** = spreading capital across assets whose risks are *not the same*, so that no single
bad event sinks you. It is often called "the only free lunch in finance" because, done right, it
reduces risk **without** proportionally reducing expected return.

- **Why it works:** if you hold many *uncorrelated* positions, their random ups and downs partly
  cancel, so the *portfolio* is steadier than any single holding. The average return is preserved; the
  *variability* shrinks.
- **Example:** Ten uncorrelated bets each with the same edge produce a far smoother equity curve than
  putting everything on one — the same total return with smaller drawdowns.
- **The catch (and it's a big one):** diversification only works to the extent holdings are genuinely
  **uncorrelated** ([correlation](#correlation)). Ten Indian bank stocks are *not* diversified — they
  are one leveraged bet on banking. True diversification spans sectors, asset classes, and strategies.

> 💡 **Key takeaway:** Don't count *positions*; count *bets*. Five correlated trades are one bet plus
> five brokerages. Diversify across things that fail for *different reasons.*

---

## 13. Risk-adjusted returns

The final, unifying idea of this section: **returns must always be judged relative to the risk taken
to earn them.** A 30% return by betting the account on one option is *not* better than a 15% return
earned steadily — the first was a coin flip that happened to land well.

The standard tool is the **Sharpe ratio** (full treatment in
[Backtesting & Statistics](../12-backtesting-and-statistics/README.md#the-sharpe-ratio)):

$$\text{Sharpe} = \frac{R_p - R_f}{\sigma_p}$$

- **What it calculates:** excess return (above the risk-free rate) *per unit of volatility.*
- **Variables:** `R_p` = portfolio return, `R_f` = risk-free rate (e.g. Indian T-bill/G-Sec yield),
  `σ_p` = volatility of the portfolio's returns.
- **Example:** Strategy A returns 20% with 25% volatility; Strategy B returns 14% with 8% volatility;
  `R_f = 6%`. Sharpe(A) = `(20−6)/25 = 0.56`; Sharpe(B) = `(14−6)/8 = 1.0`. **B is the better
  strategy** on a risk-adjusted basis, despite the lower headline return — you could even *leverage* B
  to match A's return at lower risk.
- **Limitations:** Sharpe penalizes upside and downside volatility equally (the [Sortino ratio](../12-backtesting-and-statistics/README.md)
  fixes this), assumes returns are well-behaved (they have [fat tails](#5-risk-vs-uncertainty)), and
  can be gamed by strategies that hide risk in rare tail losses (like [naked option selling](../10-options/README.md#why-selling-options-is-not-free-money)).

> 💡 **Key takeaway:** "How much did you make?" is the wrong first question. "How much did you make
> *per unit of risk*, and could you survive the bad path?" is the right one. This mindset — return
> *relative to risk* — is the thread connecting every later section.

---

### Related sections
- [01 How Markets Work](../01-how-markets-work/README.md) — the mechanics that turn these concepts into trades.
- [07 Risk Management](../07-risk-management/README.md) — where return, volatility, and compounding become survival math.
- [12 Backtesting & Statistics](../12-backtesting-and-statistics/README.md) — measuring returns and risk rigorously.
- [Glossary](../glossary/README.md) — money, liquidity, volatility, correlation, CAGR, Sharpe.
- [20 Exercises → Beginner](../20-exercises/README.md#beginner) — compute returns, real returns, and compounding.

> Next: [01 — How Markets Work](../01-how-markets-work/README.md) →
