# 03 — Price and Market Behavior

> ⬅ Back to [README](../README.md) · Prev: [02 Assets & Instruments](../02-assets-and-instruments/README.md) · Next: [04 Fundamental Analysis](../04-fundamental-analysis/README.md)

> 💡 **Key takeaway:** A price is not a fact about an asset — it is the **most recent point of
> agreement between a buyer and a seller**, and it moves because *expectations* and *the order book*
> change, not because "there were more buyers than sellers." That last phrase is one of the most
> repeated and least accurate ideas in retail trading.

**Contents**
1. [What a price actually is](#1-what-a-price-actually-is)
2. [Why "buyers vs sellers" is a bad explanation](#2-why-buyers-vs-sellers-is-a-bad-explanation)
3. ["If a stock is ₹500, why does the next trade happen at ₹501?"](#3-if-a-stock-is-500-why-does-the-next-trade-happen-at-501)
4. [The real drivers of price](#4-the-real-drivers-of-price)
5. [Price discovery, arbitrage, and market makers](#5-price-discovery-arbitrage-and-market-makers)
6. [Information and expectations](#6-information-and-expectations)
7. [Forced flows and positioning](#7-forced-flows-and-positioning)
8. [How efficient are markets, really?](#8-how-efficient-are-markets-really)
9. [Checklist & common mistakes](#9-checklist--common-mistakes)

---

## 1. What a price actually is

The "price" of a stock you see on a screen is simply the **price of the last trade** — the last moment
a buyer and a seller agreed. It is history, not a promise. The *tradeable* prices right now are the
**bid** (best buyer) and **ask** (best seller) in the [order book](../01-how-markets-work/README.md#3-the-order-book-bid-ask-and-spread);
the "price" lives *between* them and only updates when a new trade prints.

> 💡 **Key takeaway:** There is no single "true price" sitting inside a stock. There is a *book of
> intentions* (bids and asks) and a *record of past agreements* (trades). Price is the trail those
> agreements leave behind.

---

## 2. Why "buyers vs sellers" is a bad explanation

Social media loves "price went up because there were more buyers than sellers." This is **logically
incoherent** as stated: **every trade has exactly one buyer and one seller for the same quantity.**
Shares are not created or destroyed by trading — for every share bought, a share is sold. So there can
never be "more buyers than sellers" in the count-the-people sense.

What people *mean* (and should say) is about **urgency and price, not counts**:

- Price rises when **buyers are more *aggressive*** — willing to pay *higher* prices to get filled —
  so they lift the ask and consume sell orders at rising prices.
- Price falls when **sellers are more *aggressive*** — willing to accept *lower* prices to exit — so
  they hit the bid and consume buy orders at falling prices.

It is a contest of **who is more willing to cross the spread and at what price**, not a headcount.

| Sloppy claim | Precise reality |
|---|---|
| "More buyers than sellers" | Impossible — every trade is one buyer + one seller |
| "Buying pressure pushed it up" | *Aggressive* buyers lifted the ask, consuming resting sell liquidity at higher prices |
| "Everyone's selling" | Sellers are *hitting bids*; each sale still has a buyer taking the other side |

> ⚠️ **Common mistake:** Building a mental model where "buying volume" mechanically raises price. High
> volume can occur with price flat, up, *or* down. What moves price is the **imbalance in
> aggression/urgency** relative to the liquidity resting in the book — [order-flow imbalance](../15-market-microstructure/README.md).

---

## 3. "If a stock is ₹500, why does the next trade happen at ₹501?"

This is the concrete version of the whole section. Walk through the [order book](../01-how-markets-work/README.md#3-the-order-book-bid-ask-and-spread):

```text
        BUYERS (bids)                 SELLERS (asks)
   Qty     Price                 Price     Qty
   1,200   499.90   <- best bid  500.10    400    <- best ask
     900   499.80                500.50    700
   1,500   499.60                501.00    2,000
```

Last trade was ₹500. Now suppose a piece of good news hits, or a big buyer simply *needs* shares. Here
is *mechanically* how the next print becomes ₹501:

1. An **aggressive buyer** sends a market (or aggressive limit) buy for **1,500** shares.
2. It **consumes the ask ladder**: 400 @ ₹500.10, then 700 @ ₹500.50, then 400 of the 2,000 @ **₹501.00**.
3. The **last of those fills prints at ₹501.00** — so the "price" is now ₹501. The buyer *walked the
   book* up because there wasn't enough size at ₹500 to satisfy their demand.

The price didn't rise because "more people wanted to buy." It rose because **one buyer's demand
exceeded the sell liquidity available at ₹500**, forcing fills at successively higher offers until the
order was filled. Equivalently, sellers at ₹500.10–500.50 got taken out and the *next available seller*
was at ₹501.

Two deeper reasons the ₹500 sellers weren't replaced instantly at ₹500:
- **New information** may have made resting sellers *cancel* their ₹500 offers and re-post higher (they
  now think the stock is worth more) — the ask ladder *lifts* even before big trades occur.
- **Prices move in ticks:** exchanges quote in a minimum increment (**tick size**), so ₹500 → ₹500.05
  → ₹500.10 … the "next" price is the next tick where a trade clears, not a continuous slide.

> 💡 **Key takeaway:** The next trade prints at ₹501 when **demand at ₹500 exhausts the supply at
> ₹500** (and/or sellers re-price higher on new information). Price is discovered *level by level* as
> aggressive orders consume, or fail to consume, the liquidity resting in the book.

🤔 **Think about this:** If a giant buyer wants 10 lakh shares *right now* in a stock that only shows
50,000 for sale nearby, what happens to the price — and why might a smart buyer *hide* their size or
trade slowly instead? (They'd push the price up against themselves; hence [execution algorithms](../13-algorithmic-trading/README.md)
and [microstructure](../15-market-microstructure/README.md) exist to minimise this *market impact*.)

---

## 4. The real drivers of price

Underneath the mechanics, *why* do buyers and sellers change their aggression and their resting orders?
Because their **estimate of value, or their need to transact, changed.** The main drivers:

| Driver | How it moves price |
|---|---|
| **Information / news** | New facts (earnings, orders, scandals) change perceived value → orders re-price |
| **Expectations** | Prices reflect the *future*; a "good" result that's *worse than expected* falls ([§6](#6-information-and-expectations)) |
| **Earnings & fundamentals** | Cash-flow reality over time anchors long-run value ([Fundamentals](../04-fundamental-analysis/README.md)) |
| **Interest rates** | Higher rates lower the present value of future cash flows → valuations compress ([Advanced](../16-advanced-topics/README.md)) |
| **Liquidity** | Thin books move more per order; abundant liquidity absorbs flow ([§1 of microstructure](../15-market-microstructure/README.md)) |
| **Sentiment** | Fear/greed shift how aggressively people chase or dump ([Psychology](../11-trading-psychology/README.md)) |
| **Positioning** | Who is already long/short and how leveraged → sets up forced flows ([§7](#7-forced-flows-and-positioning)) |
| **Institutional flows** | Large funds entering/exiting create sustained pressure |
| **Forced buying/selling** | Margin calls, redemptions, index rebalancing → price-insensitive orders ([§7](#7-forced-flows-and-positioning)) |
| **Arbitrage** | Keeps related prices (spot/futures, dual listings) aligned ([§5](#5-price-discovery-arbitrage-and-market-makers)) |

> 💡 **Key takeaway:** Price is the market's *running estimate of value plus the pressure of who needs
> to trade*. Long-run, fundamentals dominate; short-run, flows, liquidity, and sentiment can dominate —
> which is exactly why short-term trading is hard and [risk management](../07-risk-management/README.md) is essential.

---

## 5. Price discovery, arbitrage, and market makers

- **Price discovery** is the *process* by which all this buying and selling converges on a price that
  reflects available information. A market's core social function ([Foundations](../00-foundations/README.md#3-what-is-a-financial-market-and-why-do-they-exist)).
- **Market makers / liquidity providers** continuously post both bids and asks, earning the [spread](../01-how-markets-work/README.md#3-the-order-book-bid-ask-and-spread)
  for providing liquidity. They make trading smoother — but they *withdraw* when risk spikes, which is
  why spreads blow out in a panic. See [microstructure](../15-market-microstructure/README.md).
- **Arbitrage** is the force that keeps *related* prices consistent. If NIFTY futures drift too far
  from the NIFTY spot basket, arbitrageurs buy the cheap one and sell the dear one until the gap
  closes ([Futures → basis](../09-futures/README.md)). Arbitrage is *why* you can usually trust that a
  future, an ETF, and its underlying stay tethered.

> 🚩 **Myth:** "Markets are pushed around freely by whoever has the most money." Arbitrage and
> competition constrain how far prices can stray from fair value *for related instruments and liquid
> assets* — though thin/illiquid names are far easier to move. See [§8](#8-how-efficient-are-markets-really).

---

## 6. Information and expectations

Markets are **forward-looking**. Today's price already embeds the *consensus expectation* of the
future. This produces the single most counter-intuitive fact for beginners:

> **"Good news" can make a price *fall*, and "bad news" can make it *rise* — if the news is better or
> worse than what was already priced in.**

- **Example:** A company reports **25% profit growth** — sounds great — but analysts *expected 35%*.
  The stock *drops*, because the price had already assumed 35%; the report was a *disappointment
  relative to expectations.*
- **Example:** A struggling firm reports a loss, but a *smaller* loss than feared, plus signs of a
  turnaround → the stock *jumps*. Reality beat a very low bar.

This is why "buy the rumour, sell the news" exists: expectations build into the price *ahead* of the
event, and the event itself resolves the uncertainty — often triggering the *opposite* of the naive
reaction. It's also why an [options buyer can be directionally right and still lose](../10-options/README.md#4-the-greeks)
(the move was already priced; IV collapses after the event).

> ⚠️ **Common mistake:** Trading the *headline* instead of the *surprise*. What moves price is the
> **delta between reality and expectation**, not whether the news is "good" in absolute terms.

---

## 7. Forced flows and positioning

Some of the sharpest moves come from traders who are **not choosing** to trade — they are *forced*:

- **Margin calls / stop cascades:** leveraged longs get liquidated as price falls, and their forced
  *selling* pushes price lower, triggering *more* liquidations — a self-reinforcing cascade (and the
  mirror image in a short squeeze, where forced *buying* spikes price). See [Risk → margin](../07-risk-management/README.md#10-portfolio-level-risk-correlation-exposure-leverage).
- **Fund redemptions:** investors pull money → the fund must sell holdings regardless of value.
- **Index rebalancing:** when a stock is added to/removed from an index, index funds must buy/sell it
  *because of the rule*, not because of value — creating predictable, price-insensitive flow.

**Positioning** (who is already long/short, and how crowded/leveraged) sets up these dynamics. A
market where "everyone" is already long has few new buyers and lots of potential forced sellers — it is
*fragile to the downside* even on modest bad news.

> 💡 **Key takeaway:** Price is not always about value or fresh information — sometimes it's about
> **who is trapped**. Understanding positioning explains "unexplained" violent moves and why crowded
> trades unwind painfully.

---

## 8. How efficient are markets, really?

The **Efficient Market Hypothesis (EMH)** says prices already reflect available information, so
consistently beating the market is very hard. The honest, skeptical view:

- ✅ **Established:** Markets are *hard to beat*. Most active managers underperform simple index funds
  after fees over long horizons. Obvious, liquid mispricings are quickly arbitraged away.
- 🧭 **Useful model:** Treating liquid markets as "mostly efficient" keeps you humble and cost-aware —
  a good default that prevents a lot of overconfidence.
- ⚔️ **Contested:** Whether *some* persistent inefficiencies exist (factor premia like value/momentum,
  behavioral biases, microstructure edges) is genuinely debated — and some appear real but *decay* as
  they're discovered and crowded ([Quant](../14-quantitative-trading/README.md)).
- 🚩 **Myth (both extremes):** "Markets are perfectly efficient, edges are impossible" **and** "markets
  are totally irrational, easily beaten by chart patterns" are *both* wrong. Reality is in between and
  regime-dependent.

> 💡 **Key takeaway:** Assume markets are **efficient enough that easy money is gone**, but not so
> perfect that disciplined edges are impossible. This posture makes you skeptical of get-rich schemes
> *and* open to rigorously-tested, risk-managed strategies. It's the whole spirit of this knowledge base.

🔬 **Testable claim:** "This pattern predicts price." The evidence needed is a large, out-of-sample,
cost-and-slippage-adjusted test showing reliably positive [expectancy](../07-risk-management/README.md#5-expectancy--the-master-formula) —
because in a *mostly* efficient market, most apparent patterns are noise or already arbitraged. See
[Backtesting](../12-backtesting-and-statistics/README.md).

---

## 9. Checklist & common mistakes

### ⚠️ Price-behavior mistakes
| Mistake | Reality |
|---|---|
| "More buyers than sellers moved it" | Every trade is one buyer + one seller; *aggression/imbalance* moves price |
| Trading the headline, not the surprise | Price already embeds expectations; the *delta* matters |
| Assuming volume ⇒ direction | High volume occurs on up, down, and flat days alike |
| Ignoring positioning | Forced flows (margin, redemptions, rebalancing) drive many sharp moves |
| Believing markets are perfectly efficient *or* totally beatable | Both extremes are wrong; reality is "efficient enough" |
| Thinking a stock has one "true price" | There's a *book of intentions* + a *record of trades*, not a single number |

### 🤔 Questions to test yourself
- Explain, in book terms, how a modest amount of aggressive buying prints a new higher price.
- Give an example where "good news" *should* make a stock fall.
- Why might a heavily-crowded long trade fall hard on *minor* bad news?

---

### Related sections
- [01 How Markets Work](../01-how-markets-work/README.md) — the order book and matching mechanics behind price.
- [15 Market Microstructure](../15-market-microstructure/README.md) — order-flow imbalance and market impact, in depth.
- [05 Technical Analysis](../05-technical-analysis/README.md) — reading price behavior on charts, skeptically.
- [11 Trading Psychology](../11-trading-psychology/README.md) — the sentiment side of price.
- [Glossary](../glossary/README.md) — price discovery, arbitrage, market maker, order-flow imbalance, EMH.

> Next: [04 — Fundamental Analysis](../04-fundamental-analysis/README.md) →
