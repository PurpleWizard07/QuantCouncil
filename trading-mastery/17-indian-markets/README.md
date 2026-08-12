# 17 — Indian Markets

> ⬅ Back to [README](../README.md) · Prev: [16 Advanced Topics](../16-advanced-topics/README.md) · Next: [18 Practical Trading](../18-practical-trading/README.md)

> 🗓️ **This section contains date-sensitive facts (fees, taxes, settlement, F&O rules).** They were
> checked against current official and reputable sources at the time of writing, but **they change
> with every Union Budget and SEBI circular.** Treat every number here as a *snapshot to verify*, not
> a timeless truth. Where something is especially prone to change, it is flagged 🗓️. **Always confirm
> against your broker's contract note, exchange circulars, and SEBI/CBDT before it affects money.**

**Contents**
1. [The regulatory and institutional stack](#1-the-regulatory-and-institutional-stack)
2. [Accounts: demat, trading, bank](#2-accounts-demat-trading-bank)
3. [Settlement](#settlement)
4. [Indices: NIFTY, SENSEX, BANKNIFTY, sectoral](#4-indices-nifty-sensex-banknifty-sectoral)
5. [ETFs and IPOs in India](#5-etfs-and-ipos-in-india)
6. [The SEBI F&O overhaul (2024–2026)](#the-sebi-fo-overhaul-2024-2026)
7. [The retail F&O reality](#the-retail-fo-reality)
8. [The cost stack — every charge, explained](#the-cost-stack)
9. [Taxation (high level, verify current rules)](#9-taxation-high-level-verify-current-rules)
10. [Checklist & common mistakes](#10-checklist--common-mistakes)

---

## 1. The regulatory and institutional stack

(See [How Markets Work → institutions](../01-how-markets-work/README.md#1-the-institutions-and-who-does-what) for the general roles.)

| Body | Role in India |
|---|---|
| **SEBI** | The market regulator. Licenses intermediaries, writes the rulebook, protects investors, polices fraud/manipulation. |
| **NSE** (National Stock Exchange) | India's largest exchange by volume; home of NIFTY and most F&O activity. |
| **BSE** (Bombay Stock Exchange) | Asia's oldest exchange; home of SENSEX. |
| **NSE Clearing (NCL)** & **ICCL** (BSE) | Clearing corporations / central counterparties that guarantee and net settlement. |
| **NSDL** & **CDSL** | The two depositories that hold your shares in *dematerialized* (electronic) form. |
| **RBI** | The central bank; sets monetary policy and oversees the banking rails your money moves on. |
| **AMFI** | Industry body for mutual funds (standards, investor education). |

> 💡 **Key takeaway:** SEBI writes the rules; NSE/BSE run the venues; NCL/ICCL guarantee trades;
> NSDL/CDSL hold your shares. Your **broker** is your licensed gateway to all of it and usually also
> acts as your **Depository Participant (DP)**.

---

## 2. Accounts: demat, trading, bank

To trade Indian equities you typically link **three** accounts:

| Account | Holds / does | Provided by |
|---|---|---|
| **Bank account** | Your money | Your bank |
| **Trading account** | Places orders on the exchange | Your broker |
| **Demat account** | Holds your shares electronically | Depository (NSDL/CDSL) via your broker as DP |

Opening requires **KYC** (PAN, Aadhaar, bank proof, in-person/e-verification). The flow of a delivery
buy: money moves **bank → (via broker) → exchange settlement**, and shares land in your **demat**;
selling reverses it, with shares debited from demat (which triggers **DP charges**, see [§8](#the-cost-stack)).

> 💡 **Key takeaway:** "Trading account" ≠ "demat account." One *transacts*; the other *stores*. Many
> beginners are confused why they need both — the trading account is the remote control, the demat is
> the shelf where the shares actually sit.

---

## Settlement

🗓️ *India is actively shortening settlement — verify current status with NSE/BSE/SEBI.*

- **T+1 is the default cycle** for all equities, ETFs, REITs, and InvITs — a trade settles **one
  business day** later. India completed the move from T+2 to T+1 in **early 2023** (fully rolled out by
  end-January 2023), making it one of the fastest major markets in the world.
- **T+0 (same-day) settlement** launched as an **optional beta on 28 March 2024** and has been
  expanded in phases to the **top 500 stocks by market capitalization**; it runs *in addition to* T+1.
  SEBI has also been piloting an even faster **instant settlement** mechanism (near-real-time,
  UPI-funded).
- **Practical implications:** funds and shares free up faster (good for capital efficiency), but you
  must fund your account **sooner**; a failed pay-in (insufficient funds at settlement) triggers
  penalties and short-delivery auction handling.

See the mechanics in [How Markets Work → settlement](../01-how-markets-work/README.md#8-settlement-t1--t0).

---

## 4. Indices: NIFTY, SENSEX, BANKNIFTY, sectoral

An **index** is a rules-based basket of stocks summarising a slice of the market with one number.

| Index | What it tracks | Notes |
|---|---|---|
| **NIFTY 50** | 50 large NSE-listed companies | India's benchmark; the most-traded F&O underlying |
| **SENSEX** | 30 large BSE-listed companies | The oldest Indian index; BSE benchmark |
| **NIFTY BANK (BANKNIFTY)** | Major banking stocks | Historically the highest-volume options underlying |
| **FINNIFTY** | Financial services | Banks + NBFCs + insurers |
| **Sectoral indices** | NIFTY IT, NIFTY Pharma, NIFTY Auto, NIFTY FMCG, etc. | Track individual sectors |
| **Broad indices** | NIFTY Next 50, NIFTY Midcap 150, NIFTY Smallcap 250 | Beyond the largest names |

Indices are usually **free-float market-cap weighted** — bigger, more freely-traded companies count
more (see [Assets → free float](../02-assets-and-instruments/README.md)). You can't trade an index
directly, but you can trade its **futures, options, and ETFs**.

> ⚠️ **Common mistake:** Assuming "NIFTY up 1%" means *your* stocks are up 1%. An index is a weighted
> average — a handful of heavyweights (a few large financials, RELIANCE, top IT names) can drive it
> while most constituents go the other way (poor **market breadth**). See [Price behavior](../03-price-and-market-behavior/README.md).

---

## 5. ETFs and IPOs in India

- **ETFs (Exchange-Traded Funds)** track an index/asset and trade like a stock on NSE/BSE (e.g. NIFTY
  ETFs, gold ETFs). They offer cheap, liquid, diversified exposure. Watch for **tracking error** and,
  in thin ETFs, **wide spreads** (trade near NAV; use limit orders). Deep dive in [Assets → ETFs](../02-assets-and-instruments/README.md).
- **IPOs.** A company files a **DRHP** with SEBI, sets a **price band**, and opens a bidding window.
  You apply via **ASBA/UPI**, which **blocks** (not debits) funds in your bank; money is debited only
  if shares are **allotted**. Oversubscribed IPOs allot by lottery/proportion. Listing follows a few
  days later. IPO investing is closer to **speculation** than investing — pricing is set by the seller
  with an incentive to maximize proceeds, and "listing pop" is far from guaranteed. See [Foundations → investing vs speculation](../00-foundations/README.md#4-investing-vs-trading-vs-speculation).

---

## The SEBI F&O overhaul (2024–2026)

🗓️ *This is one of the most consequential recent changes to Indian trading. Details and effective
dates below are from current sources; verify specifics with SEBI/exchange circulars.*

Concerned by mounting retail losses in derivatives, SEBI rolled out a sweeping tightening of the
**index derivatives** framework, phased in from late 2024 through 2026. The headline measures:

| Change | What it does | Roughly effective |
|---|---|---|
| **Bigger contract size** | Minimum index-derivative notional raised from ~₹5–10 lakh toward **₹15–20 lakh** — more capital and more risk per lot. NIFTY lot size moved to **75**, since revised (e.g. **65**) as index levels changed. | From **20 Nov 2024**; lot revisions ongoing (e.g. end-Dec 2025) |
| **Fewer weekly expiries** | Only **one weekly-expiry benchmark per exchange** — **NSE: NIFTY weekly**, **BSE: SENSEX weekly**. Bank Nifty / FinNifty / others moved to **monthly-only**. | From **20 Nov 2024** |
| **Upfront option premium** | Buyers must pay the **full premium upfront** (no intraday leverage on long options). | From **~1 Feb 2025** |
| **No expiry-day calendar-spread margin benefit** | Removes the margin offset for calendar spreads **on the expiry day** of the near leg. | From **~Feb 2025** |
| **Extra margin near expiry** | Additional **Extreme Loss Margin (ELM)** on expiry-day short options — the highest-risk window. | Phased |
| **Intraday position monitoring** | Exchanges check position limits via **random intraday snapshots**, not just end-of-day — you can't quietly breach limits intraday and unwind before close. | From **~1 Apr 2025** |
| **Algo-trading framework for retail** | Registration/tagging framework for API-based/automated retail strategies. | Rolling out **2025–2026** |

**Observed effect:** total F&O turnover **declined markedly** — reported to fall from ~**₹490 trillion
(CY2024)** to ~**₹391 trillion (CY2025)** — consistent with SEBI's goal of reducing speculative
churn. A side effect noted by market participants: somewhat **wider spreads** and harder execution in
places, as speculative liquidity thinned.

> 💡 **Key takeaway:** The regulator's clear message is that **F&O is a capital-intensive, high-risk
> professional activity**, not a small-account get-rich-quick vehicle. If you trade derivatives, budget
> for larger lots, higher margins, and fewer weekly-expiry playgrounds than the pre-2024 era.

---

## The retail F&O reality

This belongs in a serious trading reference precisely because it is so often hidden by hype.

**SEBI's own studies (2023–2024)** of individual traders in equity **F&O** found that a **large
majority lost money** over multi-year periods, with losses concentrated in **short-dated options**
and heavy expiry-day activity. Aggregate retail losses ran into very large sums, and the *typical*
active F&O trader was a net loser after costs. This is the empirical basis for the
[overhaul above](#the-sebi-fo-overhaul-2024-2026).

> 🔬 **Testable claim, already tested:** "Retail F&O trading is, on average, profitable." SEBI's
> large-sample studies say the opposite — most lose, and costs make it worse. Any influencer promising
> easy F&O riches is contradicting the regulator's own data. See [Resources → SEBI](../resources/README.md).

> ⚠️ **Common mistake:** Believing you are the exception before you have *any* evidence you are. The
> base rate is brutal; respect it. Start with [paper trading and tiny capital](../18-practical-trading/README.md),
> defined-risk structures ([Options → strategies](../10-options/README.md#8-strategies-and-their-payoffs)),
> and ruthless [risk management](../07-risk-management/README.md).

---

## The cost stack

🗓️ *Rates below reflect current sources at the time of writing. Brokerage varies by broker; statutory
charges change via Budget/SEBI/exchange circulars and by state (stamp duty). Verify on your contract note.*

Every Indian trade carries **layers** of charges beyond the price. Knowing them is essential to
computing your true **breakeven** and **net [expectancy](../07-risk-management/README.md#5-expectancy--the-master-formula)**.

### The charges, one by one

| Charge | Who levies it | Typical current basis 🗓️ |
|---|---|---|
| **Brokerage** | Your broker | Discount brokers: **₹0** on equity delivery; **flat ₹20 (or ~0.03%, whichever lower)** per executed order for intraday/F&O; **flat ₹20** per options order. Full-service brokers charge a percentage. |
| **STT** (Securities Transaction Tax) | Government | See STT table below — a major cost, unavoidable, charged on turnover/premium. |
| **Exchange transaction charge** | NSE/BSE | Roughly **~0.00297%–0.00345%** of turnover on NSE equity; **BSE varies by scrip group**. (Exchanges moved to flat per-crore style rates around Oct 2024.) F&O has its own rates. |
| **SEBI turnover fee** | SEBI | **₹10 per crore** (0.0001%) of turnover, both sides. |
| **GST** | Government | **18%** on **(brokerage + exchange transaction charge + SEBI fee)** — *not* on your profits. |
| **Stamp duty** | State govts (uniform since 1 Jul 2020) | **Buy side only**: delivery **0.015%**, intraday **0.003%**, futures **0.002%**, options **0.003%**, currency ~**0.0001%**. |
| **DP charges** | Depository + DP | Flat **~₹13–20 + GST per ISIN per day** on **delivery *sell*** (demat debit). **Not** charged on intraday or F&O. |
| **Others** | Various | Tiny NSE **IPFT** fee; annual **demat AMC** (~₹300–500 + GST); auction/penalty charges for short delivery. |

### STT — the current rates 🗓️

STT changed again from **1 April 2026** (Budget 2026–27), continuing hikes that began in 2024. Current
rates (verify before relying on them):

| Segment | STT (current) 🗓️ | Side |
|---|---|---|
| **Equity delivery** | **0.1%** | Both buy **and** sell |
| **Equity intraday** | **0.025%** | **Sell** side only |
| **Equity futures** | **0.05%** *(raised from 0.02% on 1 Apr 2026)* | **Sell** side only |
| **Equity options** | **0.15%** on the **premium** *(raised from 0.1%)*; **0.15%** on **intrinsic value** if the option is **exercised** | **Sell** side (and on exercise) |
| **ETFs (equity)** | ~**0.1%** (treated like delivery) | Both sides |
| **Equity MF units** | **0.001%** | Sell side |

> ⚠️ **Common mistake #1:** Letting an **ITM option get exercised** rather than squaring off. Exercise
> triggers STT **on intrinsic value (0.15%)**, which can be a nasty surprise — often square off instead.
> **Common mistake #2:** Ignoring costs when backtesting or when a strategy has small per-trade edge.
> For active intraday/F&O trading, **round-trip costs of ₹100–₹500+ per trade** are normal; a strategy
> with a tiny gross edge is often *net negative*. See [Backtesting → costs](../12-backtesting-and-statistics/README.md#backtesting-pitfalls).

### Worked example — a ₹1,00,000 delivery round trip
Buy ₹1,00,000, sell ₹1,00,000 (flat, for illustration), discount broker (₹0 delivery brokerage):
- STT: 0.1% × 1,00,000 (buy) + 0.1% × 1,00,000 (sell) = ₹100 + ₹100 = **₹200**
- Stamp duty (buy): 0.015% × 1,00,000 = **₹15**
- Exchange + SEBI + GST: a few rupees total
- DP charge (on sell): ~**₹15–20 + GST**
- **Total ≈ ₹235–₹250** → you need roughly a **~0.25% gain just to break even** on delivery — and much
  more, proportionally, for small trades or frequent intraday/F&O churn.

> 💡 **Key takeaway:** In India, **STT + the charge stack materially raise your breakeven**, and they
> scale with *turnover*, not profit — so high-frequency retail strategies fight a strong cost headwind.
> Always compute costs *before* deciding a strategy is worth trading.

---

## 9. Taxation (high level, verify current rules)

> 🗓️ **Taxation is the most change-prone topic here and this is NOT tax advice.** Rules, rates, and
> thresholds change with each Union Budget and differ by your situation (residency, income heads,
> business-vs-capital classification). **Consult a qualified CA/tax professional and current CBDT/ITD
> guidance before filing or trading decisions.** The below reflects the framework after the **23 July
> 2024** changes, as per current sources.

### Capital gains on listed equity / equity MFs (with STT paid)

| Type | Holding period | Current rate 🗓️ | Notes |
|---|---|---|---|
| **STCG** (Section **111A**) | **≤ 12 months** | **20% flat** *(raised from 15% on 23 Jul 2024)* + 4% cess | No slab benefit; no Chapter VI-A deductions against it |
| **LTCG** (Section **112A**) | **> 12 months** | **12.5%** on gains **above ₹1.25 lakh/year** *(was 10% above ₹1 lakh)*; **no indexation** + 4% cess | Gains up to ₹1.25 lakh/yr exempt |

- **Grandfathering:** for shares/units acquired **before 31 Jan 2018**, cost is taken as the *higher*
  of actual cost or the 31 Jan 2018 fair market value (protects pre-2018 gains). 🗓️
- **Date of sale matters:** transfers **before 23 Jul 2024** follow the **old** rates (15%/10%).

### Other treatments (framework, verify)
- **Intraday equity** is typically treated as **speculative business income**, and **F&O** as
  **non-speculative business income** — taxed at your **slab rate**, with the ability to deduct
  expenses and (subject to rules) carry forward losses. Turnover thresholds can trigger **tax audit**
  requirements. These classifications have real consequences and nuances — **get professional advice.**
- **Dividends** are taxable in the investor's hands at slab rates (with TDS above thresholds).
- **STCL/LTCL set-off & carry-forward:** short-term capital *losses* can offset both STCG and LTCG;
  long-term losses offset only LTCG; unabsorbed losses carry forward (commonly up to 8 assessment
  years) — subject to timely return filing. 🗓️

> 💡 **Key takeaway:** How your trading is *taxed* can change your real returns as much as your
> strategy does — and the classification (capital gains vs business income) depends on *how* you trade.
> Budget every year for the possibility of rule changes, keep clean records, and use a professional.

---

## 10. Checklist & common mistakes

### ✅ Indian-market operating checklist
- [ ] Three accounts linked (bank, trading, demat) and KYC complete.
- [ ] I know my product's **settlement cycle** (T+1 default; T+0 where available) and keep funds ready.
- [ ] I've computed my **all-in costs** (STT + exchange + SEBI + GST + stamp + DP) into breakeven.
- [ ] For F&O, I've accounted for the **new lot sizes, margins, and single weekly-expiry benchmark**.
- [ ] I avoid letting **ITM single-stock options** go to physical settlement unintentionally.
- [ ] I keep **records** for taxation and know my likely **classification** (get a CA's view).
- [ ] I have internalized the **retail F&O base rate** and manage risk accordingly.

### ⚠️ Uniquely-Indian pitfalls
| Pitfall | Reality |
|---|---|
| Ignoring STT/charge stack | Raises breakeven; scales with turnover, not profit |
| Chasing weekly-option selling like it's 2023 | Rules changed: bigger lots, higher margins, one weekly benchmark/exchange |
| Letting ITM stock options expire | Physical settlement → delivery obligation |
| Treating tax rules as fixed | They change every Budget; classification depends on how you trade |
| Assuming "NIFTY up" = "my stocks up" | Index is weighted; breadth can diverge |
| Believing easy-F&O-riches influencers | SEBI's data: most retail F&O traders lose money |

---

### Related sections
- [01 How Markets Work](../01-how-markets-work/README.md) — the general plumbing these institutions implement.
- [10 Options](../10-options/README.md) & [09 Futures](../09-futures/README.md) — the instruments most affected by SEBI's F&O rules.
- [07 Risk Management](../07-risk-management/README.md) — why costs and the F&O base rate demand strict risk control.
- [18 Practical Trading](../18-practical-trading/README.md) — opening accounts, placing orders, scaling capital.
- [Resources](../resources/README.md) — official SEBI/NSE/BSE/CBDT sources to verify everything here.
- [Glossary](../glossary/README.md) — STT, demat, DP, T+1, ELM, MWPL.

> Next: [18 — Practical Trading](../18-practical-trading/README.md) →
