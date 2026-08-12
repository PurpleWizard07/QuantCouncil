# 20 — Exercises

> ⬅ Back to [README](../README.md) · Prev: [19 Case Studies](../19-case-studies/README.md)

> 💡 **Key takeaway:** Reading about compounding, expectancy, and cointegration is not the same as
> being able to compute them under pressure with real numbers. These exercises are deliberately
> calculation- and judgment-heavy, not multiple-choice — the [10-level learning path](../README.md) in
> the master README tells you when to attempt each tier.

*This section is a substantive outline. It can be expanded with more worked exercises and answer keys
on request.*

---

## Beginner

1. **Compounding.** You invest ₹1,00,000 at a 12% annual CAGR. Using the [Rule of 72](../00-foundations/README.md#6-return) and then the exact compound-interest formula, estimate and then calculate how long it takes to double. How much do the two answers differ, and why?
2. **Real vs. nominal return.** Your portfolio returned 9% nominal this year; inflation was 5.5%. Compute your approximate real return (see [Foundations](../00-foundations/README.md)). If you need real returns of 5%+ to meet a goal, what nominal return do you need at 5.5% inflation?
3. **Order book reading.** Given a hypothetical 5-level market depth snapshot for a NIFTY stock (you construct or are given bid/ask sizes and prices), determine: the current spread, and how many shares a ₹2,00,000 market buy order would consume before it started moving to worse price levels. See [Market depth](../01-how-markets-work/README.md#4-market-depth-and-liquidity).
4. **Order lifecycle.** Write out, in your own words and without looking at [01](../01-how-markets-work/README.md), every step between clicking "Buy" and shares appearing in your demat account. Then check your answer against the chapter and note what you missed.
5. **Position sizing.** Account size ₹5,00,000. You risk 1% per trade. Entry ₹250, stop ₹242. Calculate the correct position size in shares. See [Risk per trade](../07-risk-management/README.md#2-risk-per-trade--position-sizing).

---

## Intermediate

1. **Expectancy comparison.** Strategy A: 68% win rate, average win ₹800, average loss ₹1,900. Strategy B: 32% win rate, average win ₹3,900, average loss ₹900. Compute expectancy per trade for both (see [Expectancy](../07-risk-management/README.md#5-expectancy--the-master-formula)). Which would you trade, and what single piece of missing information (trade frequency, max drawdown) would most change your answer?
2. **Options payoff.** Construct the payoff diagram (by hand or spreadsheet) for a NIFTY iron condor with strikes of your choosing. At three different expiry spot prices, calculate the exact P&L. See [Options strategies](../10-options/README.md#8-strategies-and-their-payoffs).
3. **Greeks sensitivity.** For a near-the-money NIFTY call with 15 days to expiry, rank its Greeks (delta, gamma, theta, vega) by how much they'd change if (a) 5 days pass with no price move, (b) spot moves 2% instantly, (c) India VIX jumps 20%. See [The Greeks](../10-options/README.md#4-the-greeks).
4. **Backtest pitfall hunt.** Take a simple moving-average crossover backtest (write the code, or use provided pseudocode) and deliberately introduce, then detect and fix: (a) look-ahead bias, (b) ignored transaction costs, (c) survivorship bias in the universe selection. See [Backtesting pitfalls](../12-backtesting-and-statistics/README.md#backtesting-pitfalls).
5. **Cost-stack reality check.** For 30 intraday round-trip trades in a month, each ₹1,00,000 notional, calculate total costs using the [current cost stack](../17-indian-markets/README.md#the-cost-stack) (brokerage + STT + exchange charges + GST + stamp duty). What gross return do you need just to break even?

---

## Advanced

1. **Cointegration test.** Pick two related Indian stocks (e.g., two large private banks). Using historical price data, test for cointegration (ADF on each series, then Engle-Granger on the regression residual). Report whether the pair is cointegrated and over what lookback window the relationship holds. See [Pairs trading](../14-quantitative-trading/README.md#3-pairs-trading--cointegration).
2. **Walk-forward validation.** Take any strategy you've backtested in-sample. Implement proper walk-forward validation (rolling train/test windows) and compare in-sample vs. out-of-sample Sharpe ratios. Quantify the degradation. See [Validation](../12-backtesting-and-statistics/README.md#8-validation-traintest-walk-forward-out-of-sample).
3. **Volatility clustering.** Fit a GARCH(1,1) model to NIFTY daily returns and compare its volatility forecasts to a simple rolling-standard-deviation approach, out-of-sample. Which produced better-calibrated forecasts (e.g., via a simple backtesting of realized-vs-predicted variance)? See [Volatility modeling](../16-advanced-topics/README.md#3-volatility-modeling-garch-and-friends).
4. **Kelly under uncertainty.** For a strategy with an *estimated* (not certain) edge — win rate 55% ± 5%, payoff ratio 1.3 ± 0.2 — compute full Kelly and quarter-Kelly position sizes across the range of plausible parameters. How much does position size swing, and what does that imply about using fractional Kelly in practice? See [Kelly criterion](../07-risk-management/README.md#9-the-kelly-criterion-and-why-to-use-a-fraction-of-it).
5. **Build and stress-test an execution pipeline.** Implement (paper-trading only) the full pipeline from [13](../13-algorithmic-trading/README.md#4-building-blocks-of-a-retail-algo-system) — data feed, strategy logic, risk checks, OMS, logging — then deliberately kill the data feed mid-session and confirm your risk-check/kill-switch layer behaves safely.

---

✅ **Ready to move on when:** you've completed the exercises for your current level from the
[10-level learning path](../README.md) with actual numbers (not just conceptual answers), and can
explain *why* each answer is correct, not just what it is.

**Related sections:** every earlier chapter — each exercise links back to the specific concept it tests.

**Next →** back to [README](../README.md) — pick your next section, or revisit anything unclear.
