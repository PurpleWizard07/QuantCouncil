# Glossary

> ⬅ Back to [README](../README.md)

An alphabetical reference. Each entry follows: **Simple** definition → **Technical** definition →
**Example** → **Related**. Terms link back into the relevant sections. Where a fact is date-sensitive
(fees, taxes, rules), see [Indian Markets](../17-indian-markets/README.md) and verify current sources.

Jump: [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [K](#k) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [R](#r) · [S](#s) · [T](#t) · [V](#v) · [W](#w)

---

## A

### Arbitrage
**Simple:** Profiting from the same thing being priced differently in two places, with little/no risk.
**Technical:** Simultaneously buying and selling related instruments to capture a price discrepancy;
the force that keeps related prices consistent. **Example:** If NIFTY futures trade far above the
NIFTY spot basket, arbitrageurs sell futures and buy the basket until the gap closes. **Related:**
[price discovery](#price-discovery), [basis](#basis), [Futures](../09-futures/README.md).

### Ask (Offer)
**Simple:** The lowest price a seller will accept right now. **Technical:** The best (lowest) resting
sell limit order in the [order book](#order-book). **Example:** Best ask ₹500.20 means you can buy
immediately at ₹500.20. **Related:** [bid](#bid), [spread](#spread), [order book](#order-book).

### ATR (Average True Range)
**Simple:** How much a price typically moves in a period. **Technical:** Average of the True Range
(max of high−low, |high−prev close|, |low−prev close|) over *n* periods; a volatility measure in price
units. **Example:** Daily ATR ₹25 → set a stop 2×ATR = ₹50 away. **Related:**
[volatility](#volatility), [volatility-adjusted sizing](../07-risk-management/README.md#8-volatility-adjusted-sizing), [ATR detail](../05-technical-analysis/README.md#atr-average-true-range).

---

## B

### Backtest
**Simple:** Testing a strategy on past data. **Technical:** Simulating a rule set over historical
prices to estimate performance, ideally with costs, slippage, and out-of-sample validation.
**Example:** Running a 20/50 SMA crossover over 10 years of NIFTY data. **Related:**
[overfitting](#overfitting), [walk-forward](#walk-forward-analysis), [Backtesting](../12-backtesting-and-statistics/README.md).

### Basis
**Simple:** The gap between a futures price and the spot price. **Technical:** Basis = Futures − Spot;
converges to zero at expiry. **Example:** NIFTY spot 24,000, near-month future 24,080 → basis +80.
**Related:** [contango](#contango-and-backwardation), [Futures](../09-futures/README.md).

### Bid
**Simple:** The highest price a buyer will pay right now. **Technical:** The best (highest) resting buy
limit order in the [order book](#order-book). **Example:** Best bid ₹499.80 means you can sell
immediately at ₹499.80. **Related:** [ask](#ask-offer), [spread](#spread).

### Bollinger Bands
**Simple:** A moving average with volatility bands above and below. **Technical:** Middle SMA with
upper/lower bands at ±k standard deviations (often 20-period, k=2); widen with volatility. **Example:**
A "squeeze" (narrow bands) may precede a breakout. **Related:** [volatility](#volatility),
[TA indicators](../05-technical-analysis/README.md#bollinger-bands).

---

## C

### CAGR (Compound Annual Growth Rate)
**Simple:** The steady yearly rate that would produce your actual multi-year growth. **Technical:**
$(P_{end}/P_{start})^{1/n} - 1$; the geometric growth rate. **Example:** ₹1L → ₹2L over 6 years →
CAGR ≈ 12.2%. **Related:** [compounding](#compounding), [return](#return), [Foundations](../00-foundations/README.md#6-return).

### Calmar ratio
**Simple:** Return divided by worst drawdown. **Technical:** Annualized return ÷ |max drawdown|;
rewards smooth growth. **Example:** 12% return with −10% MDD → Calmar 1.2. **Related:**
[drawdown](#drawdown-maximum-drawdown), [Sharpe ratio](#sharpe-ratio).

### Clearing corporation
**Simple:** The middleman that guarantees your trade completes. **Technical:** Central counterparty
(CCP) that steps between buyer and seller, nets obligations, and removes counterparty risk. **Example:**
NSE Clearing (NCL) / ICCL in India. **Related:** [settlement](#settlement), [How Markets Work](../01-how-markets-work/README.md#1-the-institutions-and-who-does-what).

### Compounding
**Simple:** Earning returns on your past returns. **Technical:** Exponential growth $FV = PV(1+r)^n$;
also compounds costs and losses against you. **Example:** ₹1L at 12% for 30y ≈ ₹30L. **Related:**
[CAGR](#cagr-compound-annual-growth-rate), [Foundations](../00-foundations/README.md#7-compounding).

### Contango and Backwardation
**Simple:** Whether futures are priced above (contango) or below (backwardation) spot. **Technical:**
Contango = futures > spot (typical for cost-of-carry); backwardation = futures < spot. **Example:**
Commodity futures in contango roll at a cost over time. **Related:** [basis](#basis), [Futures](../09-futures/README.md).

### Correlation
**Simple:** How much two things move together (−1 to +1). **Technical:** Standardized covariance;
+1 perfectly together, −1 perfectly opposite, 0 no linear relationship. **Example:** Two large private
banks are highly positively correlated. **Related:** [diversification](#diversification), [Foundations](../00-foundations/README.md#correlation).

---

## D

### Delta
**Simple:** How much an option's price moves per ₹1 in the underlying. **Technical:** ∂(option price)/
∂(underlying); 0→1 for calls, 0→−1 for puts; roughly approximates probability of finishing ITM.
**Example:** A 0.4-delta call gains ~₹0.40 per ₹1 rise. **Related:** [gamma](#gamma), [Greeks](../10-options/README.md#4-the-greeks).

### Demat account
**Simple:** Where your shares are held electronically. **Technical:** Dematerialized securities account
at a depository (NSDL/CDSL), serviced by a DP. **Example:** Buying INFY credits shares to your demat on
settlement. **Related:** [depository](#depository), [DP charges](#dp-charges), [Indian Markets](../17-indian-markets/README.md#2-accounts-demat-trading-bank).

### Depository
**Simple:** The institution that stores shares as ledger entries. **Technical:** Holds securities
electronically and records ownership; India has NSDL and CDSL. **Related:** [demat account](#demat-account),
[clearing corporation](#clearing-corporation).

### Diversification
**Simple:** Not putting all your eggs in one basket. **Technical:** Combining *uncorrelated* assets to
reduce portfolio risk without proportionally reducing expected return. **Example:** Spreading across
sectors and asset classes, not ten bank stocks. **Related:** [correlation](#correlation), [Foundations](../00-foundations/README.md#diversification).

### DP charges
**Simple:** A flat fee when you sell delivery shares. **Technical:** Depository Participant charge on
demat *debits*, ~₹13–20 + GST per ISIN per day (delivery sell); not on intraday/F&O. 🗓️ **Related:**
[cost stack](../17-indian-markets/README.md#the-cost-stack).

### Drawdown (Maximum Drawdown)
**Simple:** How far you've fallen from your peak. **Technical:** Peak-to-trough decline in equity;
**max drawdown** is the largest such fall. Recovery is asymmetric (−50% needs +100%). **Example:**
Equity ₹1.2L → ₹0.9L is a −25% drawdown. **Related:** [risk of ruin](#risk-of-ruin), [Risk Management](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin).

---

## E

### EMH (Efficient Market Hypothesis)
**Simple:** Prices already reflect known information, so beating the market is hard. **Technical:**
The claim that asset prices incorporate available information; strong/semi-strong/weak forms.
**Example:** Most active funds underperform index funds after fees. **Related:** [price discovery](#price-discovery),
[Price behavior](../03-price-and-market-behavior/README.md#8-how-efficient-are-markets-really).

### ELM (Extreme Loss Margin)
**Simple:** Extra margin buffer for bad-case moves. **Technical:** A margin component covering losses
beyond standard (VaR/SPAN) margins; raised near F&O expiry under SEBI rules. 🗓️ **Related:**
[margin](#margin), [F&O overhaul](../17-indian-markets/README.md#the-sebi-fo-overhaul-2024-2026).

### Expectancy
**Simple:** Average profit per trade. **Technical:** $E = W \cdot A_w - L \cdot A_l$ (or in R units);
the number that decides if a strategy makes money. **Example:** 45% win, +₹8k avg win, −₹4k avg loss →
E = ₹1,400/trade (before costs). **Related:** [win rate](#win-rate), [R multiple](#r-multiple),
[Risk Management](../07-risk-management/README.md#5-expectancy--the-master-formula).

---

## F

### Free float
**Simple:** Shares actually available to trade publicly. **Technical:** Shares outstanding minus
locked-in/promoter/strategic holdings; used to weight indices. **Example:** A company may be large by
market cap but have low free float. **Related:** [market capitalization](#market-capitalization),
[index](#index), [Assets](../02-assets-and-instruments/README.md).

### Futures
**Simple:** A contract to buy/sell something at a set price on a future date. **Technical:**
Standardized, exchange-traded, margined, marked-to-market forward contract. **Example:** One NIFTY
future controls a large notional with a fraction posted as margin. **Related:** [margin](#margin),
[basis](#basis), [Futures](../09-futures/README.md).

---

## G

### Gamma
**Simple:** How fast an option's delta changes. **Technical:** ∂delta/∂(underlying); highest ATM near
expiry; short options have negative gamma (losses accelerate). **Example:** A short straddle's delta
swings violently against you on a big move. **Related:** [delta](#delta), [Greeks](../10-options/README.md#4-the-greeks).

### Gap
**Simple:** When price opens far from the previous close. **Technical:** A discontinuity (no trades
between) often from overnight news; makes stops slip. **Example:** A stock closes ₹500, opens ₹460
after bad results. **Related:** [slippage](#slippage), [stop loss](#stop-loss).

### Greeks
**Simple:** Numbers describing how an option reacts to price, time, volatility, and rates. **Technical:**
Delta, gamma, theta, vega, rho — partial derivatives of option value. **Related:** [Options](../10-options/README.md#4-the-greeks).

---

## H

### Hedging
**Simple:** Taking a position to reduce risk in another. **Technical:** Offsetting exposure via a
negatively-correlated instrument (e.g. a protective put). **Example:** An investor buys index puts to
protect a stock portfolio. **Related:** [Options strategies](../10-options/README.md#8-strategies-and-their-payoffs), [Futures](../09-futures/README.md).

### HFT (High-Frequency Trading)
**Simple:** Ultra-fast automated trading. **Technical:** Latency-sensitive strategies (market making,
arbitrage) executing in microseconds. **Example:** Firms co-locate servers next to the exchange.
**Related:** [market maker](#market-maker), [microstructure](../15-market-microstructure/README.md).

---

## I

### Implied Volatility (IV)
**Simple:** The volatility "baked into" an option's price. **Technical:** The volatility input that
makes a pricing model match the market premium; forward-looking, an opinion. **Example:** IV spikes
before earnings, then collapses ("vol crush"). **Related:** [vega](#vega), [historical volatility](#volatility),
[Options → IV](../10-options/README.md#5-volatility-implied-vs-historical-smile-skew).

### Index
**Simple:** A basket of stocks summarised by one number. **Technical:** A rules-based, usually
free-float market-cap-weighted portfolio. **Example:** NIFTY 50, SENSEX, BANKNIFTY. **Related:**
[free float](#free-float), [Indian Markets](../17-indian-markets/README.md#4-indices-nifty-sensex-banknifty-sectoral).

### Intrinsic value (options)
**Simple:** What an option is worth if exercised now. **Technical:** Call: max(Spot−Strike,0); Put:
max(Strike−Spot,0); never negative. **Example:** 24000 call with spot 24,150 → intrinsic 150.
**Related:** [time value](#time-value-extrinsic-value), [moneyness](#moneyness).

---

## K

### Kelly criterion
**Simple:** The bet size that maximizes long-run growth. **Technical:** $f^* = (bp-q)/b$; forbids
betting a negative-edge game; usually applied fractionally (¼–½). **Example:** p=0.55, b=1 → f*=10%,
but bet ~5% (half-Kelly). **Related:** [risk of ruin](#risk-of-ruin), [position sizing](#position-sizing),
[Risk Management](../07-risk-management/README.md#9-the-kelly-criterion-and-why-to-use-a-fraction-of-it).

---

## L

### Leverage
**Simple:** Using borrowed money/margin to trade bigger. **Technical:** Controlling a position larger
than your capital; multiplies gains *and* losses; introduces margin calls. **Example:** 5× leverage
turns a 10% move into a 50% P&L swing. **Related:** [margin](#margin), [risk of ruin](#risk-of-ruin).

### Limit order
**Simple:** Buy/sell only at your price or better. **Technical:** An order that rests in the book until
matched at the specified price or better; guarantees price, not execution. **Example:** "Buy 100 @ ₹499"
waits for a seller at ₹499. **Related:** [market order](#market-order), [order book](#order-book).

### Liquidity
**Simple:** How easily you can trade without moving the price. **Technical:** Depth and tightness of
the market; ability to transact size near fair value quickly. **Example:** RELIANCE is liquid; a thin
smallcap is not. **Related:** [spread](#spread), [depth](#market-depth), [Foundations](../00-foundations/README.md#9-liquidity).

### Log return
**Simple:** A return measured with logarithms; adds up over time. **Technical:** $\ln(P_t/P_{t-1})$;
time-additive and better-behaved than simple returns. **Example:** ₹100→₹110 log return ≈ 9.53%.
**Related:** [return](#return), [Backtesting](../12-backtesting-and-statistics/README.md#2-returns-and-log-returns).

---

## M

### Margin
**Simple:** Collateral you post to hold a leveraged position. **Technical:** Funds required by the
broker/exchange (e.g. SPAN + exposure + ELM); a **margin call** demands more or force-liquidates.
**Example:** ₹1L margin controls a ₹5L position. **Related:** [leverage](#leverage), [ELM](#elm-extreme-loss-margin).

### Market capitalization
**Simple:** The total value of a company's shares. **Technical:** Share price × total shares
outstanding. **Example:** ₹1,400 × 6.7B shares ≈ ₹9.4L crore. **Related:** [free float](#free-float),
[Assets](../02-assets-and-instruments/README.md).

### Market depth
**Simple:** How much size is available at each price. **Technical:** The quantities resting at each
level of the order book; determines price impact of orders. **Example:** Only 400 shares at the best
ask → a 2,000 order walks the book. **Related:** [order book](#order-book), [slippage](#slippage),
[How Markets Work](../01-how-markets-work/README.md#4-market-depth-and-liquidity).

### Market maker
**Simple:** A trader who always quotes both a buy and sell price. **Technical:** A liquidity provider
earning the spread for continuously posting bids and asks; withdraws in stress. **Related:**
[spread](#spread), [HFT](#hft-high-frequency-trading), [microstructure](../15-market-microstructure/README.md).

### Market order
**Simple:** Buy/sell immediately at the best available price. **Technical:** An order that crosses the
spread and consumes resting liquidity; guarantees execution, not price. **Example:** "Buy 100 at
market" fills at the best ask(s). **Related:** [limit order](#limit-order), [slippage](#slippage).

### Moneyness
**Simple:** Whether an option has intrinsic value. **Technical:** ITM (in the money), ATM (at the
money), OTM (out of the money) relative to strike vs spot. **Example:** With spot 24,150, a 24,000 call
is ITM. **Related:** [intrinsic value](#intrinsic-value-options), [Options](../10-options/README.md#2-intrinsic-vs-time-value-moneyness).

### Monte Carlo simulation
**Simple:** Running many "what if" random scenarios. **Technical:** Repeatedly resampling/shuffling to
estimate the distribution of outcomes (e.g. drawdowns). **Example:** Shuffle trade order 5,000× to see
worst-case equity paths. **Related:** [bootstrap](#backtesting--statistics-terms), [Backtesting](../12-backtesting-and-statistics/README.md#9-monte-carlo-and-the-bootstrap).

### MWPL (Market-Wide Position Limit)
**Simple:** A cap on total F&O positions in a stock. **Technical:** When aggregate open interest
crosses ~95% of MWPL, the stock enters an **F&O ban** (no fresh positions). 🗓️ **Related:**
[F&O overhaul](../17-indian-markets/README.md#the-sebi-fo-overhaul-2024-2026).

---

## N

### NAV (Net Asset Value)
**Simple:** The per-unit value of a fund's holdings. **Technical:** (Assets − liabilities) / units;
ETFs trade near NAV via creation/redemption. **Example:** A mutual fund unit is bought/sold at NAV.
**Related:** [ETF](#etfs) *(see [Assets](../02-assets-and-instruments/README.md))*, [tracking error](#tracking-error).

---

## O

### Open interest (OI)
**Simple:** How many derivative contracts are currently open. **Technical:** Total outstanding
(unclosed) contracts; differs from volume (trades). **Example:** Rising OI + rising price is often read
as fresh longs (with caveats). **Related:** [PCR](#put-call-ratio-pcr), [Options](../10-options/README.md#7-open-interest--the-put-call-ratio).

### Order book
**Simple:** The live list of all buy and sell orders. **Technical:** The limit order book: bids and
asks sorted by price and time. **Example:** Best bid ₹499.80 / best ask ₹500.20. **Related:**
[bid](#bid), [ask](#ask-offer), [depth](#market-depth), [How Markets Work](../01-how-markets-work/README.md#3-the-order-book-bid-ask-and-spread).

### Overfitting
**Simple:** A model that memorizes the past and predicts nothing. **Technical:** Fitting noise rather
than signal; too many parameters/trials relative to data. **Example:** Tweaking rules until the
backtest is perfect, then failing live. **Related:** [data snooping](#backtesting--statistics-terms),
[walk-forward](#walk-forward-analysis), [Backtesting](../12-backtesting-and-statistics/README.md#backtesting-pitfalls).

---

## P

### PCR (Put-Call Ratio)
**Simple:** Puts vs calls outstanding/traded. **Technical:** Put OI (or volume) ÷ call OI; sometimes
read as a contrarian sentiment gauge (weak, regime-dependent). **Example:** High PCR = heavy put
positioning. **Related:** [open interest](#open-interest-oi), [Options](../10-options/README.md#7-open-interest--the-put-call-ratio).

### P/E ratio
**Simple:** Price paid per rupee of earnings. **Technical:** Price ÷ EPS; a valuation multiple that
misleads for cyclicals, loss-makers, and differing growth/quality. **Example:** ₹1,000 price, ₹50 EPS →
P/E 20. **Related:** [valuation](#valuation), [Fundamentals](../04-fundamental-analysis/README.md).

### Position sizing
**Simple:** How many shares/lots to trade. **Technical:** Quantity chosen so a stop-out loses a fixed
fraction of capital: Account × Risk% ÷ (Entry − Stop). **Example:** ₹5L × 1% ÷ ₹30 = 166 shares.
**Related:** [risk per trade](#risk-per-trade), [Kelly](#kelly-criterion), [Risk Management](../07-risk-management/README.md#2-risk-per-trade--position-sizing).

### Price discovery
**Simple:** How the market figures out a price. **Technical:** The process by which buying/selling
converges on a price reflecting available information. **Related:** [order book](#order-book),
[arbitrage](#arbitrage), [Price behavior](../03-price-and-market-behavior/README.md#5-price-discovery-arbitrage-and-market-makers).

### Primary vs secondary market
**Simple:** Where securities are *created* vs where they *trade*. **Technical:** Primary: issuer sells
new securities (IPO), gets the money; secondary: investors trade existing securities among themselves.
**Example:** IPO (primary) vs buying INFY on NSE (secondary). **Related:** [IPO](#ipo), [How Markets Work](../01-how-markets-work/README.md#2-primary-vs-secondary-markets-ipos).

### IPO
**Simple:** A company's first public share sale. **Technical:** Initial Public Offering; a primary-market
issuance via prospectus and price band, funds blocked via ASBA/UPI. **Related:** [primary market](#primary-vs-secondary-market),
[Indian Markets](../17-indian-markets/README.md#5-etfs-and-ipos-in-india).

---

## R

### R multiple
**Simple:** Profit/loss measured in units of your risk. **Technical:** 1R = amount risked (entry−stop);
outcomes expressed as multiples (+2R, −1R). **Example:** Risk ₹5k, make ₹10k → +2R. **Related:**
[risk per trade](#risk-per-trade), [expectancy](#expectancy), [Risk Management](../07-risk-management/README.md#4-riskreward-and-the-r-multiple).

### Return
**Simple:** Your gain/loss as a percentage. **Technical:** (End − Start + Income)/Start; distinguish
arithmetic vs geometric (CAGR). **Example:** ₹200→₹230 + ₹4 dividend on ₹200 = 17%. **Related:**
[CAGR](#cagr-compound-annual-growth-rate), [Foundations](../00-foundations/README.md#6-return).

### Risk of ruin
**Simple:** The chance a losing streak wipes you out. **Technical:** Probability equity falls below a
non-recoverable threshold; driven by edge, bet size, and bankroll. **Example:** Risking 10%/trade makes
ordinary streaks catastrophic. **Related:** [drawdown](#drawdown-maximum-drawdown), [Kelly](#kelly-criterion),
[Risk Management](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin).

### Risk per trade
**Simple:** How much you'll lose if a trade hits its stop. **Technical:** A fixed fraction of capital
(commonly 0.5–2%) risked per position. **Example:** ₹5L account, 1% → ₹5,000 risk. **Related:**
[position sizing](#position-sizing), [stop loss](#stop-loss).

### RSI
**Simple:** A 0–100 gauge of recent gains vs losses. **Technical:** Relative Strength Index; >70
"overbought," <30 "oversold"; a mean-reversion bet that fails in strong trends. **Example:** RSI can
stay >70 for weeks in an uptrend. **Related:** [mean reversion](../06-trading-styles/README.md),
[TA indicators](../05-technical-analysis/README.md#rsi).

---

## S

### Settlement
**Simple:** The actual transfer of shares and cash. **Technical:** Post-trade pay-in/pay-out via
clearing corp and depositories; India: T+1 default, optional T+0 for top-500. 🗓️ **Example:** Buy
today, shares in demat on T+1. **Related:** [clearing corporation](#clearing-corporation),
[Indian Markets](../17-indian-markets/README.md#settlement).

### Sharpe ratio
**Simple:** Return per unit of risk (volatility). **Technical:** (R_p − R_f)/σ_p, usually annualized;
penalizes up and down volatility equally; gameable by tail-risk strategies. **Example:** 18% return,
12% vol, 6% Rf → 1.0. **Related:** [Sortino](#sortino-ratio), [Calmar](#calmar-ratio), [Backtesting](../12-backtesting-and-statistics/README.md#the-sharpe-ratio).

### Short selling
**Simple:** Betting a price will fall by selling first. **Technical:** Selling borrowed shares to buy
back later; loss is theoretically unbounded; squeeze risk. **Example:** Retail cash shorts in India are
usually intraday-only; multi-day via F&O/SLBM. **Related:** [margin](#margin), [How Markets Work](../01-how-markets-work/README.md#9-short-selling-borrowing-and-margin).

### Slippage
**Simple:** Getting a worse price than expected. **Technical:** Difference between expected and executed
price from thin depth, fast moves, or gaps. **Example:** Market buy fills at ₹500.24 vs the ₹500.20 you
saw. **Related:** [market order](#market-order), [depth](#market-depth), [How Markets Work](../01-how-markets-work/README.md#6-partial-fills-and-slippage).

### Sortino ratio
**Simple:** Sharpe, but only counting downside swings. **Technical:** (R_p − R_f)/σ_downside; better
for asymmetric strategies. **Related:** [Sharpe](#sharpe-ratio), [Backtesting](../12-backtesting-and-statistics/README.md#the-sharpe-ratio).

### Spread (Bid-Ask)
**Simple:** The gap between the best buy and sell prices. **Technical:** Ask − Bid; a real round-trip
cost; wide in illiquid names. **Example:** Bid 499.80 / Ask 500.20 → spread 0.40. **Related:**
[bid](#bid), [ask](#ask-offer), [liquidity](#liquidity).

### Stop loss
**Simple:** A pre-set exit that caps a loss. **Technical:** Stop-market (guarantees exit, not price) or
stop-limit (guarantees price, not fill); placed where the thesis is wrong. **Example:** Long at ₹1,400,
stop ₹1,370. **Related:** [risk per trade](#risk-per-trade), [gap](#gap), [Risk Management](../07-risk-management/README.md#3-stop-losses-done-properly).

### STT (Securities Transaction Tax)
**Simple:** A government tax on trades. **Technical:** Charged on turnover/premium by segment; e.g.
delivery 0.1% both sides, options 0.15% on premium (sell) — **rates change** (last revised 1 Apr 2026).
🗓️ **Related:** [cost stack](../17-indian-markets/README.md#the-cost-stack).

### Straddle / Strangle
**Simple:** Buying (or selling) both a call and a put to bet on volatility. **Technical:** Straddle =
same strike; strangle = OTM strikes; long = bet on a big move, short = bet on calm (undefined risk).
**Example:** Long ATM straddle profits on a large move either way. **Related:** [gamma](#gamma),
[Options strategies](../10-options/README.md#8-strategies-and-their-payoffs).

---

## T

### T+1 / T+0
**Simple:** How many days until a trade settles. **Technical:** T+1 = one business day (India default
since 2023); T+0 = same day (optional, top-500). 🗓️ **Related:** [settlement](#settlement),
[Indian Markets](../17-indian-markets/README.md#settlement).

### Theta
**Simple:** How much an option loses to time each day. **Technical:** ∂(option price)/∂time; negative
for long options (decay), positive for sellers; accelerates near expiry. **Example:** An ATM weekly
bleeds value over a flat weekend. **Related:** [Greeks](../10-options/README.md#4-the-greeks).

### Time value (Extrinsic value)
**Simple:** The part of an option's price that isn't intrinsic. **Technical:** Premium − intrinsic;
the market's price for future possibility; decays to zero at expiry. **Example:** OTM options are all
time value. **Related:** [intrinsic value](#intrinsic-value-options), [theta](#theta).

### Tracking error
**Simple:** How far an ETF/fund drifts from its index. **Technical:** Std deviation of the fund's
return minus the benchmark's. **Example:** A NIFTY ETF slightly lagging NIFTY. **Related:**
[ETFs](../02-assets-and-instruments/README.md), [NAV](#nav-net-asset-value).

---

## V

### Valuation
**Simple:** Estimating what a business is worth. **Technical:** DCF (present value of future cash flows)
and relative multiples (P/E, EV/EBITDA); assumption-sensitive. **Related:** [P/E](#pe-ratio),
[Fundamentals](../04-fundamental-analysis/README.md).

### Vega
**Simple:** How much an option's price moves per 1-point change in IV. **Technical:** ∂(option price)/
∂(implied vol); positive for long options; source of "right direction, still lost" via vol crush.
**Related:** [implied volatility](#implied-volatility-iv), [Greeks](../10-options/README.md#4-the-greeks).

### Volatility
**Simple:** How much prices swing around. **Technical:** Std deviation of returns; historical
(realized) vs implied; clusters over time. **Example:** India VIX gauges expected NIFTY volatility.
**Related:** [ATR](#atr-average-true-range), [Foundations](../00-foundations/README.md#10-volatility).

### VWAP
**Simple:** The volume-weighted average price of the day. **Technical:** Σ(price×volume)/Σ(volume),
resets each session; an institutional execution benchmark. **Related:** [TA → VWAP](../05-technical-analysis/README.md#vwap).

---

## W

### Walk-forward analysis
**Simple:** Repeatedly optimizing on the past and testing on the next slice. **Technical:** Rolling
train/test windows stitched into an out-of-sample curve; the gold standard of validation. **Related:**
[overfitting](#overfitting), [Backtesting](../12-backtesting-and-statistics/README.md#8-validation-traintest-walk-forward-out-of-sample).

### Win rate
**Simple:** The fraction of trades that are winners. **Technical:** Wins ÷ total trades; *meaningless
without* average win/loss sizes. **Example:** A 70% win rate can still lose money. **Related:**
[expectancy](#expectancy), [R multiple](#r-multiple), [Risk Management](../07-risk-management/README.md#6-why-a-40-win-rate-can-win-and-a-70-win-rate-can-lose).

---

### Backtesting & statistics terms
Additional terms — **data snooping** (testing many things and keeping the lucky winner),
**survivorship bias** (excluding dead/delisted names), **look-ahead bias** (using unavailable-yet
data), **bootstrap** (resampling returns for confidence intervals), **fat tails** (extremes more common
than the normal distribution predicts) — are defined in context in
[Backtesting & Statistics → pitfalls](../12-backtesting-and-statistics/README.md#backtesting-pitfalls).

---

> ⬅ Back to [README](../README.md) · See also [Resources](../resources/README.md)
