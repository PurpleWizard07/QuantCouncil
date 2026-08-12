# 10 — Options

> ⬅ Back to [README](../README.md) · Prev: [09 Futures](../09-futures/README.md) · Next: [11 Trading Psychology](../11-trading-psychology/README.md)

> 💡 **Key takeaway:** An option is a *conditional* contract whose value depends on price, **time**,
> and **volatility** simultaneously. That third dimension — volatility — is what makes options
> powerful and what makes most beginners lose: they get the *direction* right and still lose money
> because time decay and a volatility crush worked against them.

**Contents**
1. [The building blocks](#1-the-building-blocks)
2. [Intrinsic vs time value; moneyness](#2-intrinsic-vs-time-value-moneyness)
3. [Payoff diagrams — the four basic positions](#3-payoff-diagrams--the-four-basic-positions)
4. [The Greeks](#4-the-greeks)
5. [Volatility: implied vs historical, smile, skew](#5-volatility-implied-vs-historical-smile-skew)
6. [Reading an option chain (NIFTY example)](#6-reading-an-option-chain-nifty-example)
7. [Open interest & the put-call ratio](#7-open-interest--the-put-call-ratio)
8. [Strategies and their payoffs](#8-strategies-and-their-payoffs)
9. [Why selling options is NOT free money](#why-selling-options-is-not-free-money)
10. [Indian-market specifics](#10-indian-market-specifics)
11. [Checklist & common mistakes](#11-checklist--common-mistakes)

---

## 1. The building blocks

An **option** gives its **buyer the right, but not the obligation**, to buy or sell an underlying
asset at a fixed price, on or before a fixed date. The **seller (writer)** takes the *obligation* to
honour that right if the buyer exercises, in exchange for a payment (**premium**) received up front.

| Term | Meaning | Indian example |
|---|---|---|
| **Call** | Right to **buy** the underlying at the strike | NIFTY 24000 CE |
| **Put** | Right to **sell** the underlying at the strike | NIFTY 24000 PE |
| **Strike** | The fixed price at which the right can be exercised | 24000 |
| **Premium** | Price paid by buyer / received by seller, *per unit* | ₹120 |
| **Expiry** | Last date the right is valid | Last Thursday of the month (index monthly) |
| **Lot size** | Units per contract (options trade in lots) | NIFTY lot = 75 (revised to 65) 🗓️ |
| **Underlying** | The asset the option is on | NIFTY 50 index |

**Buyer vs seller — the fundamental asymmetry:**

| | Option **buyer** | Option **seller (writer)** |
|---|---|---|
| Pays/receives premium | Pays it (cash out) | Receives it (cash in) |
| Maximum loss | Limited to premium paid | **Large / "unlimited"** (for naked calls) |
| Maximum gain | Large (calls) / large (puts) | Limited to premium received |
| Wants | A **big** move (and/or rising volatility) | A **small/no** move (and/or falling volatility) |
| Time works | **Against** them (decay) | **For** them (decay) |
| Probability of profit | Often **low** per trade | Often **high** per trade |

> ⚠️ **Common mistake:** Reading the table above and concluding "selling is obviously better —
> high probability, collect premium." That intuition is exactly the trap dismantled in
> [§9](#why-selling-options-is-not-free-money). High probability of a *small* gain is paired with low
> probability of a *large* loss. Remember the payoff shape from
> [Risk Management → 70% win rate that loses](../07-risk-management/README.md#6-why-a-40-win-rate-can-win-and-a-70-win-rate-can-lose).

---

## 2. Intrinsic vs time value; moneyness

Premium = **intrinsic value** + **time (extrinsic) value**.

- **Intrinsic value** = the profit if exercised *right now* (never negative).
  - Call intrinsic = `max(Spot − Strike, 0)`. Put intrinsic = `max(Strike − Spot, 0)`.
- **Time value** = everything else in the premium — the market's price for the *possibility* of
  favourable moves before expiry. It decays to zero at expiry.

**Example (NIFTY spot = 24,150):**

| Option | Strike | Premium | Intrinsic | Time value |
|---|---|---|---|---|
| 24000 CE | 24,000 | ₹210 | `24,150 − 24,000 = 150` | `210 − 150 = 60` |
| 24200 CE | 24,200 | ₹95 | 0 (spot below strike) | 95 |
| 24000 PE | 24,000 | ₹55 | 0 | 55 |

**Moneyness:**

| Term | Call | Put | Meaning |
|---|---|---|---|
| **ITM** (in the money) | Spot > Strike | Spot < Strike | Has intrinsic value |
| **ATM** (at the money) | Spot ≈ Strike | Spot ≈ Strike | Mostly time value; highest gamma/theta |
| **OTM** (out of the money) | Spot < Strike | Spot > Strike | Pure time value; cheap, low probability |

> 💡 **Key takeaway:** When you buy an OTM option you are buying **pure time value** — a wasting
> asset. If the underlying just sits still, you lose *every day* as time value bleeds out, even
> though you were "not wrong" about direction.

🤔 **Think about this:** You buy an OTM call, the stock rises modestly, and you *still lose money*.
How? (The rise wasn't enough to offset the time decay and/or a drop in implied volatility. Being
directionally right is necessary, not sufficient.)

---

## 3. Payoff diagrams — the four basic positions

Payoff at **expiry** (ignoring premium timing), where `K` = strike, `S` = spot at expiry.

### Long Call — pay premium, profit if S rises well above K
```text
 P/L
  |                         /
  |                        /
0 |----------------____/----------------  S
  |               K
 -p|______________/         (max loss = premium p)
```
- Max loss = premium. Break-even = `K + premium`. Upside large.

### Long Put — pay premium, profit if S falls well below K
```text
 P/L
  |\
  | \
  |  \
0 |----\____________________-----------  S
  |     K
 -p|      (max loss = premium p; break-even = K − premium)
```

### Short Call (naked) — receive premium, lose badly if S rises
```text
 P/L
 +p|______________
  |               \
0 |----------------\____________________  S
  |               K \
  |                  \   (loss grows without bound as S rises)
```
- 🚩 Max gain = premium; max loss = **unbounded**. This is the most dangerous single option position.

### Short Put — receive premium, lose if S falls
```text
 P/L
 +p|              ______________________
  |             /
0 |-----------/-------------------------  S
  |          /K
  |         /   (loss grows as S falls toward zero)
```
- Max gain = premium; max loss = `Strike − premium` (large; = you effectively agreed to *buy* the
  stock at the strike no matter how far it falls).

> ⚠️ **Common mistake:** Drawing only the pretty capped side of a short-option payoff and forgetting
> the long, ugly tail. The tail is where the account dies. Every serious options trader learns to
> *always* draw the full picture and to prefer **defined-risk** structures ([§8](#8-strategies-and-their-payoffs)).

---

## 4. The Greeks

The Greeks measure how an option's price responds to changes in the variables that drive it. They
are **sensitivities** (partial derivatives). You don't need calculus to *use* them, but the
intuition matters.

| Greek | Measures sensitivity to… | Sign for long call | Sign for long put | Plain-English |
|---|---|---|---|---|
| **Delta (Δ)** | Underlying price | + (0 → 1) | − (0 → −1) | "How many rupees the option moves per ₹1 in the underlying." |
| **Gamma (Γ)** | *Change in delta* | + | + | "How fast delta itself changes." Highest ATM near expiry. |
| **Theta (Θ)** | Passage of time | − | − | "Rupees lost per day to time decay." Sellers *earn* it. |
| **Vega (ν)** | Implied volatility | + | + | "Rupees gained per 1-point rise in IV." Buyers *want* IV up. |
| **Rho (ρ)** | Interest rates | + | − | Usually minor for short-dated options. |

### Delta — directional exposure (and a rough probability gauge)
- A call with Δ = 0.40 gains ≈ ₹0.40 for each ₹1 the underlying rises. ATM ≈ 0.5, deep ITM → 1, deep
  OTM → 0. Delta also *approximates* the risk-neutral probability of finishing ITM (a **rough** heuristic, not a promise).
- **Example:** You're long 2 lots of a 0.30-delta NIFTY call (lot 75). If NIFTY rises 50 points, the
  option gains ≈ `0.30 × 50 = ₹15` per unit → `15 × 75 × 2 = ₹2,250` (before other Greeks move).

### Gamma — why "small move" positions blow up on big moves
- Gamma is the *acceleration*. When you are **short** options (negative gamma), a fast move makes
  your delta swing violently *against* you — losses accelerate. This is precisely why option-selling
  strategies that look calm for weeks can lose catastrophically in a single gap. Long options have
  **positive gamma** (moves accelerate in your favour), which is what you pay theta for.

### Theta — the price of time
- Theta is the daily rent the buyer pays and the seller collects. It **accelerates as expiry nears**
  for ATM options. A NIFTY ATM weekly with 2 days left can lose a large fraction of its value to
  theta over a weekend even if NIFTY is flat.
- **The core tension:** buyers have positive gamma / negative theta (pay rent, hope for a big move);
  sellers have negative gamma / positive theta (collect rent, hope for calm). *You are always
  trading one against the other.*

### Vega — the volatility bet you didn't know you made
- Every option position is *also* a volatility position. Buy options → long vega → you profit if IV
  rises and lose if IV falls (a "vol crush"), **independent of direction.**
- **Example — the earnings/event trap:** Before a big event, IV is high (options expensive). You buy
  a call expecting a jump. The event happens, the stock moves *your way a bit* — but IV collapses
  post-event, vega losses swamp your small delta gain, and you lose. This is the classic
  "I was right and still lost" experience, now explained.

> 💡 **Key takeaway:** Price, time, and volatility move an option *simultaneously.* A profitable
> options trade requires the **net** of delta + theta + vega to be in your favour — not just
> direction. Beginners model only delta and are blindsided by the other two.

🔬 **Testable claim:** "Buying options before earnings is a good strategy." Test it: measure the
average post-event IV crush against the average post-event move for a basket of Indian stocks over
many events; a strategy is only viable if the delta gains reliably exceed the vega losses net of
costs. (Historically, this is a hard bet — the crush is real.)

---

## 5. Volatility: implied vs historical, smile, skew

- **Historical (realized) volatility (HV):** how much the underlying *actually* moved, measured from
  past prices. Backward-looking, a fact.
- **Implied volatility (IV):** the volatility the *option's price implies* via a pricing model
  (Black–Scholes and its descendants). Forward-looking, an *opinion* baked into the premium. India's
  **India VIX** is a widely watched index of NIFTY option IV — a "fear gauge."
- **The relationship you trade:** if IV ≫ HV, options are "expensive" relative to how the asset has
  actually moved (favours sellers *if* the future resembles the past); if IV ≪ HV, "cheap" (favours
  buyers). But IV is high *for a reason* (an event, uncertainty) — it is not a free lunch.

**Volatility smile / skew.** In theory, all strikes on one expiry would share one IV. In reality they
don't:
- **Skew:** in equity indices, downside puts usually carry *higher* IV than upside calls, because
  investors pay up for crash protection and markets fall faster than they rise. So a NIFTY 5%-OTM put
  is typically priced at a higher IV than a 5%-OTM call.
- **Smile:** in some markets IV rises for *both* deep-OTM calls and puts, forming a smile.

> ⚠️ **Common mistake:** Treating IV as a prediction of the actual future move. IV is the *price of
> insurance*, set by supply and demand for protection and leverage — often persistently **above**
> realized vol (the "variance risk premium"). That premium is *why* selling options can have an
> edge — and the fat left tail is why that edge is dangerous ([§9](#why-selling-options-is-not-free-money)).

---

## 6. Reading an option chain (NIFTY example)

An **option chain** lists, for one expiry, every strike with its calls (left) and puts (right).
Illustrative snapshot with **NIFTY spot ≈ 24,150**:

| CALL OI | CALL LTP | **Strike** | PUT LTP | PUT OI |
|---:|---:|:---:|---:|---:|
| 42,10,000 | 305 | 23,900 | 42 | 18,50,000 |
| 55,30,000 | 210 | **24,000** | 55 | 60,20,000 |
| 38,90,000 | 130 | 24,100 | 95 | 33,40,000 |
| **71,60,000** | 78 | 24,200 | 150 | 21,10,000 |
| 40,20,000 | 42 | 24,300 | 245 | 12,30,000 |

How to read it:
- The strike nearest spot (24,100–24,200) is **ATM**; premiums there are mostly time value.
- Above spot, **calls are OTM / puts are ITM**; below spot it's reversed.
- **OI** (open interest, [§7](#7-open-interest--the-put-call-ratio)) shows where positions are
  concentrated. Large call OI at 24,200 and large put OI at 24,000 are sometimes read as a *rough*
  expected range ("max pain" / support-resistance folklore) — treat this as ⚔️ **contested** market
  lore, not established fact.

> 💡 **Key takeaway:** The chain is a *cross-section of prices and positioning*, not a forecast. Use
> it to see what a move is *priced at* (e.g., "a 24,200 call costs ₹78, so the market prices a
> meaningful chance NIFTY closes above 24,278"), not as a signal in itself.

---

## 7. Open interest & the put-call ratio

- **Open interest (OI):** the number of option contracts currently *open* (not yet closed or
  expired). Unlike volume (which counts trades), OI counts *outstanding positions*. Rising OI + rising
  price is often read as fresh money entering; falling OI as positions unwinding — but every OI story
  has *two* sides (a buyer and a seller), so causal readings are 🚩 often overstated.
- **Put-Call Ratio (PCR):** total put OI (or volume) ÷ total call OI. High PCR is conventionally
  called "bearish positioning" and sometimes read as a *contrarian bullish* signal (everyone's
  hedged/short, so who's left to sell?). This is ⚔️ **contested** — PCR's predictive value is weak
  and regime-dependent.

> ⚠️ **Common mistake:** Treating OI/PCR levels as mechanical buy/sell triggers. They describe
> *positioning*, which is context, not a strategy. Any claim that "PCR > X ⇒ market rises" is a
> 🔬 **testable claim** that usually fails out-of-sample.

---

## 8. Strategies and their payoffs

Strategies combine options (and sometimes the underlying) to **shape a payoff** — capping risk,
lowering cost, or expressing a view on direction *and* volatility. Grouped by intent:

### Income / covered (you own or will own the underlying)
| Strategy | Construction | View | Max loss | Max gain |
|---|---|---|---|---|
| **Covered call** | Long stock + short OTM call | Mildly bullish / neutral | Stock falls (minus premium) | Capped at strike + premium |
| **Cash-secured put** | Short put + cash to buy | Willing to buy lower | Strike − premium (stock → 0) | Premium |
| **Protective put** | Long stock + long put | Bullish but want insurance | Premium + gap to strike | Unlimited (minus premium) |

### Vertical spreads (defined risk **and** defined reward — the workhorses)
| Strategy | Construction | View | Character |
|---|---|---|---|
| **Bull call spread** | Buy lower-strike call, sell higher-strike call | Moderately bullish | Debit; cheaper than a naked call, capped upside |
| **Bear put spread** | Buy higher-strike put, sell lower-strike put | Moderately bearish | Debit; capped |
| **Bull put spread** | Sell higher-strike put, buy lower-strike put | Neutral-to-bullish | **Credit**; defined risk (a *safer* way to be a seller) |
| **Bear call spread** | Sell lower-strike call, buy higher-strike call | Neutral-to-bearish | Credit; defined risk |

**Worked example — Bull call spread on NIFTY (spot 24,150):** Buy 24,200 CE @ ₹78, sell 24,400 CE @
₹30. Net debit = ₹48/unit. Max loss = ₹48 (if NIFTY ≤ 24,200 at expiry). Max gain = `(24,400 −
24,200) − 48 = 152`/unit (if NIFTY ≥ 24,400). Break-even = `24,200 + 48 = 24,248`. Per lot (75):
risk ₹3,600 to make up to ₹11,400. You gave up the tail upside above 24,400 in exchange for paying
much less than the ₹78 naked call.

### Volatility structures (bet on *how much* it moves, not which way)
| Strategy | Construction | You profit if… | You lose if… |
|---|---|---|---|
| **Long straddle** | Buy ATM call + ATM put | Big move *either* way (or IV rises) | It sits still / IV falls (theta bleeds you) |
| **Long strangle** | Buy OTM call + OTM put | Very big move; cheaper than straddle | Small move; both expire worthless |
| **Short straddle** | Sell ATM call + ATM put | It barely moves (collect both premiums) | 🚩 **Big move either way — large/unbounded loss** |
| **Iron condor** | Sell OTM put spread + sell OTM call spread | Stays in a range | Breaks out (but loss is **capped** — the defined-risk condor) |
| **Butterfly** | Buy 1 low + sell 2 mid + buy 1 high (calls or puts) | Pins near the middle strike | Moves away; cheap, low-probability payoff |
| **Calendar spread** | Sell near-dated, buy longer-dated (same strike) | Time decay + IV behave as expected | Complex — a bet on term structure of vol |

> 💡 **Key takeaway:** **Spreads and condors are "defined-risk" — you always know your worst case
> before you enter.** Naked short options (short straddle/strangle, naked calls/puts) are
> "undefined-risk" — one bad gap can exceed months of gains. For most traders, most of the time,
> defined-risk is the adult choice. This ties directly to
> [Risk Management → portfolio heat](../07-risk-management/README.md#10-portfolio-level-risk-correlation-exposure-leverage).

---

## Why selling options is NOT free money

This deserves its own section because it is the most seductive and most account-destroying idea in
retail derivatives.

**The pitch:** "Most options expire worthless, so *sell* them, collect premium, and win ~80–90% of
the time. Time decay is on your side. Free money."

**Why the pitch is misleading:**

1. **The payoff shape is 'win small, lose huge.'** A short option collects a small premium most of
   the time and pays out a large loss rarely. This is exactly the
   [70%-win-rate-that-loses payoff](../07-risk-management/README.md#6-why-a-40-win-rate-can-win-and-a-70-win-rate-can-lose):
   high win *rate*, negative *expectancy* if the tail losses are big enough. Win rate ≠ profitability.

2. **"Most options expire worthless" is survivorship-flavoured spin.** Many that expire worthless
   were *bought as hedges* (the buyer was happy to "lose" the premium, like an insurance customer
   glad they didn't crash). And the ones that *don't* expire worthless are precisely the big-mover
   cases that hand the seller the large loss. The statistic says nothing about *expectancy*.

3. **Negative gamma means losses accelerate.** As the market moves against a short option, its delta
   swings against you and losses grow *faster and faster* — the opposite of a comfortable, linear
   position. A single gap (results, an RBI surprise, a global shock) can inflict a loss larger than
   many months of collected premium. Indian traders have repeatedly been wiped out by overnight gaps
   and gap-through-stop moves on short straddles around events and expiries.

4. **You are selling insurance.** There *is* a real edge here — the **variance risk premium**: IV
   tends to sit above realized vol, so sellers are, on average, paid for bearing tail risk (like an
   insurer). But an insurer who sells hurricane policies without reinsurance and without capital goes
   bankrupt in the first big storm. **The edge is real *and* the ruin risk is real** — and the ruin
   arrives all at once. Retail sellers who ignore the tail are un-capitalized insurers.

5. **Leverage and margin turn a bad day into a forced exit.** Short options tie up margin that
   *expands* as the market moves against you, triggering margin calls and forced liquidation at the
   worst price. SEBI's 2024–2026 rules (larger lots, higher near-expiry margins, upfront premium)
   exist *specifically because* retail option-selling losses were systemic — see
   [Indian Markets → F&O overhaul](../17-indian-markets/README.md#the-sebi-fo-overhaul-2024-2026).

> ⚠️ **Common mistake:** "80% win rate, what could go wrong?" The 20% is where the money is. A naked
> short-straddle seller can win 15 weeks straight and give it all back (plus more) in week 16. **The
> question is never the win rate — it is: how big is the loss when I'm wrong, and can I survive it?**

**The responsible version.** Selling options is a legitimate strategy — but only with **defined
risk** (spreads, iron condors), **small size**, **respect for events/gaps**, and full awareness that
you are being paid to take tail risk. That is a world apart from "free money."

🤔 **Think about this:** If selling options were free money, why do sophisticated, well-capitalized
institutions *buy* tail protection from these sellers — happily paying that premium year after year?
(Because they know the tail is real, and they'd rather pay the premium than own the disaster.)

---

## 10. Indian-market specifics

🗓️ *Rates and rules below reflect current sources at the time of writing; verify before trading —
they change with SEBI circulars and the Union Budget. Full detail in
[Indian Markets](../17-indian-markets/README.md).*

- **Index vs stock options.** NIFTY, BANKNIFTY, FINNIFTY, etc. are **cash-settled** (no delivery of
  an index). Single-stock options are **physically settled** on expiry if held ITM — meaning you can
  end up obligated to give/take *delivery of shares*, which surprises many retail traders. Always
  square off single-stock options before expiry unless you intend delivery.
- **Expiry rationalization.** SEBI limited weekly expiries to **one benchmark index per exchange**
  (NSE: NIFTY weekly; BSE: SENSEX weekly), effective from late 2024 — Bank Nifty and others moved to
  monthly-only weeklies. This reshaped the popular weekly-option-selling landscape.
- **Contract size.** SEBI raised index derivative notional from ~₹5 lakh toward ₹15–20 lakh; NIFTY
  lot size moved to 75 and has since been revised (e.g. 65) based on index levels. Bigger lots =
  more capital and more risk per lot.
- **Costs.** Options **STT is charged on the sell side on the premium** (raised to **0.15%** from
  1 Apr 2026), plus **0.15% on intrinsic value if exercised** — so letting an ITM option get
  exercised can incur an ugly STT bill. Add brokerage (flat ₹20/order at discount brokers), exchange
  charges, SEBI fee, GST, and stamp duty. See [cost stack](../17-indian-markets/README.md#the-cost-stack).
- **Upfront premium & margin.** Buyers must pay premium upfront; sellers post (and may have to top
  up) margin that grows near expiry.

---

## 11. Checklist & common mistakes

### ✅ Before any options trade
- [ ] I can draw the **full payoff** (both tails) of this position.
- [ ] I know my **max loss in rupees** and it fits my [risk-per-trade](../07-risk-management/README.md#2-risk-per-trade--position-sizing).
- [ ] I've accounted for **theta** (am I paying or collecting rent?) and **vega** (is IV high/low, is
      an event coming?).
- [ ] For single-stock options near expiry, I've planned to avoid **unwanted physical settlement**.
- [ ] If selling, it is **defined-risk** (spread/condor), not naked, unless I truly understand and
      can fund the tail.
- [ ] I've included **Indian costs** in my break-even.

### ⚠️ Classic option mistakes
| Mistake | Reality |
|---|---|
| "I was right on direction, why did I lose?" | Theta and/or a vega crush beat your small delta gain. |
| Buying cheap deep-OTM options as "lottery tickets" | Usually a slow bleed; low probability, high decay. |
| Selling naked options for "high win rate" | Win small, lose huge; negative gamma; ruin risk. |
| Ignoring implied volatility before events | You overpaid for IV that then collapsed. |
| Holding ITM single-stock options into expiry | Physical settlement / delivery obligation surprise. |
| Confusing volume with open interest | They measure different things; OI = outstanding positions. |
| Treating PCR/OI as buy/sell signals | Positioning ≠ strategy; predictive value is weak. |

---

### Related sections
- [09 Futures](../09-futures/README.md) — the linear cousin; understand leverage/margin first.
- [07 Risk Management](../07-risk-management/README.md) — the win-rate/expectancy math that governs option selling.
- [05 Technical Analysis → ATR](../05-technical-analysis/README.md#atr-average-true-range) — sizing volatility.
- [17 Indian Markets](../17-indian-markets/README.md) — F&O rules, lot sizes, costs, taxation.
- [19 Case Studies → a realistic options trade](../19-case-studies/README.md) — worked end-to-end.
- [Glossary](../glossary/README.md) — delta, gamma, theta, vega, IV, straddle, iron condor.

> Next: [11 — Trading Psychology](../11-trading-psychology/README.md) →
