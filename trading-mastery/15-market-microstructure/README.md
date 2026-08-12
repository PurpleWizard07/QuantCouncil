# 15 — Market Microstructure

> ⬅ Back to [README](../README.md) · Prev: [14 Quantitative Trading](../14-quantitative-trading/README.md) · Next: [16 Advanced Topics](../16-advanced-topics/README.md)

> 💡 **Key takeaway:** Microstructure is the study of **how the mechanics of trading itself affect
> price** — the order book, who's on the other side of your trade, and how much your own order moves
> the market. It's the fine-grained "plumbing" layer underneath the broader price-behavior ideas in
> [03](../03-price-and-market-behavior/README.md).

**Learning objectives:** understand order-flow imbalance, market impact, adverse selection, and what
high-frequency trading actually does.

*This section is a substantive outline. It can be expanded to flagship depth — e.g. a worked order-book
simulation — on request.*

---

## 1. Order-flow imbalance

The order book (see [01](../01-how-markets-work/README.md#3-the-order-book-bid-ask-and-spread)) isn't
static — it's a constant stream of new orders, cancellations, and fills. **Order-flow imbalance (OFI)**
measures whether aggressive buying or selling pressure currently dominates (e.g., more market buy orders
hitting the ask than market sell orders hitting the bid).

> 🔬 **Testable claim:** Persistent OFI in one direction tends to predict very short-term price moves
> in the same direction — a genuine, widely-studied microstructure effect. It decays over seconds to
> minutes and is heavily exploited by HFT, so it is *not* generally an exploitable retail edge.

---

## 2. Market impact

Every trade — even a resting limit order getting filled — reveals information and consumes liquidity.

| Impact type | What it means |
|---|---|
| **Temporary impact** | Price moves against you while you trade, then partially reverts once you stop |
| **Permanent impact** | Part of the move persists — your trade revealed information (or absorbed real supply/demand) |

**Why this matters for sizing:** a retail order of a few lakh rupees in a liquid large-cap has
negligible impact. A crore-sized order in a mid-cap can move the price meaningfully against the trader —
this is *why* execution algorithms exist (see [13](../13-algorithmic-trading/README.md#3-execution-algorithms-the-how-not-the-what)).

> ⚠️ **Common mistake:** Backtesting a strategy assuming you can execute unlimited size at the last
> traded price. Real fills degrade with size — see
> [Backtesting pitfalls](../12-backtesting-and-statistics/README.md#backtesting-pitfalls).

---

## 3. Adverse selection

**The problem:** if you post a *resting limit order*, you get filled *precisely when* someone with
better/faster information decides your price is wrong — i.e., you tend to get filled right before the
market moves against you. This is why market makers widen spreads when they suspect informed flow is
present (e.g., right before a results announcement).

> 🤔 **Think about this:** This is a structural reason retail limit orders sometimes get "picked off"
> right before news, and a structural reason spreads widen exactly when you most want to trade — see
> [Spread](../01-how-markets-work/README.md#3-the-order-book-bid-ask-and-spread).

---

## 4. High-frequency trading (HFT) — what it actually does

| Common perception | More accurate picture |
|---|---|
| "HFT front-runs retail orders" | Mostly market-making and statistical arbitrage at very short holding periods; direct front-running is illegal in most markets and different from latency-based market making |
| "HFT causes crashes" | Can amplify moves during stress (liquidity withdrawal), but is one factor among many — flash crashes have multiple causes |
| "HFT firms always win" | Margins per trade are tiny; the business model is volume × consistency, competing heavily on infrastructure cost, not "always right" |

**What HFT firms actually compete on:** colocation (servers physically near the exchange), specialized
hardware/network paths, and highly optimized order-routing logic — an infrastructure and capital game
that is not accessible to, or a sensible goal for, most retail traders.

---

## 5. Why this matters even if you never build an HFT system

- It explains **why your fills aren't always exactly the price you saw** (the price you saw is already
  stale by the time your order arrives — see [Slippage](../01-how-markets-work/README.md#6-partial-fills-and-slippage)).
- It explains **why liquidity vanishes exactly when you need it** (in stress, market makers widen or
  pull quotes to avoid adverse selection).
- It grounds the [order-book anatomy of a price move](../03-price-and-market-behavior/README.md#2-why-buyers-vs-sellers-is-a-bad-explanation) in the mechanics of who's providing liquidity and why.

---

✅ **Ready to move on when:** you can explain adverse selection in your own words, describe the
difference between temporary and permanent market impact, and give one accurate and one inaccurate
popular belief about HFT.

**Related sections:** [01 How Markets Work](../01-how-markets-work/README.md) ·
[03 Price & Market Behavior](../03-price-and-market-behavior/README.md) ·
[13 Algorithmic Trading](../13-algorithmic-trading/README.md) ·
[09 Futures](../09-futures/README.md) · [10 Options](../10-options/README.md)

**Next →** [16 Advanced Topics](../16-advanced-topics/README.md)
