# 19 — Case Studies

> ⬅ Back to [README](../README.md) · Prev: [18 Practical Trading](../18-practical-trading/README.md) · Next: [20 Exercises](../20-exercises/README.md)

> 💡 **Key takeaway:** Abstract principles ("manage risk," "avoid overfitting") are easy to nod along
> to and easy to ignore in the moment. Concrete stories of exactly how smart, well-resourced people lost
> enormous amounts of money make the failure modes memorable. Every case here maps back to a specific
> earlier chapter — that's the point.

**Learning objectives:** recognize the failure modes from earlier sections in real, high-stakes examples.

*This section is a substantive outline. It can be expanded with more detailed case narratives on request.*

---

## Case 1: An overfit backtest (illustrative, mechanism-focused)

**The setup:** A strategy is backtested on 5 years of NIFTY data with 8 tunable parameters (entry
threshold, stop distance, take-profit distance, moving-average lengths, time-of-day filters...). After
extensive tuning, it shows a beautiful equity curve — Sharpe ratio of 4, near-zero drawdown.

**What actually happened:** With 8 free parameters and one dataset, there are effectively thousands of
parameter combinations tested (even if not all explicitly) — and by chance, *some* combination fits
historical noise extremely well. This is
[data-snooping / overfitting](../12-backtesting-and-statistics/README.md#backtesting-pitfalls) in
action.

**What live trading showed:** performance decayed toward random almost immediately — because the
"edge" was never real, just noise that a flexible-enough model located.

**Mapped concepts:** [Overfitting](../12-backtesting-and-statistics/README.md#10-statistical-significance-and-overfitting) ·
[Walk-forward validation](../12-backtesting-and-statistics/README.md#8-validation-traintest-walk-forward-out-of-sample) ·
[Why a plausible mechanism matters](../14-quantitative-trading/README.md#1-what-makes-something-a-quant-strategy)

> 🔬 **Testable claim → guardrail:** A strategy with more free parameters needs proportionally *more*
> out-of-sample evidence before you trust it. "It fit the data very well" is weak evidence on its own —
> a random model with enough knobs will also fit the data very well.

---

## Case 2: Long-Term Capital Management (LTCM), 1998

**The setup:** LTCM was a hedge fund staffed by Nobel laureates and elite quants, running highly
leveraged relative-value and convertible-arbitrage strategies (see
[pairs trading / cointegration](../14-quantitative-trading/README.md#3-pairs-trading--cointegration))
across global bond and equity markets, with very high leverage (reportedly 25:1 or more on-balance-sheet,
with far higher notional exposure via derivatives).

**What went wrong:**
1. **Correlation assumptions broke down under stress.** Markets that were historically weakly related
   moved together during the 1998 Russian financial crisis — a widely observed pattern where
   diversification benefits shrink exactly when needed most.
2. **Leverage turned modest losses into existential ones.** Small adverse moves, multiplied by extreme
   leverage, produced enormous dollar losses — see
   [Risk of ruin](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin).
3. **Liquidity vanished.** As LTCM needed to unwind positions to meet margin calls, the very act of
   selling moved prices further against them — [market impact](../15-market-microstructure/README.md#2-market-impact)
   in its most extreme form.
4. **Positions were too large relative to market liquidity** — a fund with a "sound" strategy on paper
   became forced-seller into a market that couldn't absorb the size, at the worst possible time.

**Mapped concepts:** [Correlation & diversification](../00-foundations/README.md#correlation) ·
[Leverage](../07-risk-management/README.md#8-volatility-adjusted-sizing) ·
[Market impact & liquidity](../15-market-microstructure/README.md#2-market-impact) ·
[Drawdown/ruin math](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin)

> 🚩 **Red flag pattern to remember:** "Historically uncorrelated" + "highly leveraged" + "large
> relative to market liquidity" is a specific, recurring recipe for catastrophic loss — it has recurred
> in multiple crises since, not just 1998.

---

## Case 3: Retail F&O losses in India (structural, not anecdotal) 🗓️

SEBI's own studies of retail futures & options participation (2023–2024 data) found that a large
majority of individual traders lost money overall, with losses concentrated among the most active
traders in short-dated (especially expiry-day) options — see
[The retail F&O reality](../17-indian-markets/README.md#the-retail-fo-reality).

**Why this belongs here, not just as a statistic:** it's the aggregate, real-money version of several
mechanisms covered separately — [why selling options isn't free money](../10-options/README.md#why-selling-options-is-not-free-money),
[transaction cost drag at high frequency](../17-indian-markets/README.md#the-cost-stack), and
[the psychology of chasing quick wins](../11-trading-psychology/README.md). No single "gotcha" explains
the pattern; it's the compounding of small structural disadvantages, repeated very frequently.

---

✅ **Ready to move on when:** for each case, you can name the specific earlier-chapter mechanism(s)
responsible — not just "they took too much risk," but *which* risk-management or statistical principle
was violated and how.

**Related sections:** [07 Risk Management](../07-risk-management/README.md) ·
[12 Backtesting](../12-backtesting-and-statistics/README.md) ·
[14 Quantitative Trading](../14-quantitative-trading/README.md) ·
[15 Market Microstructure](../15-market-microstructure/README.md) ·
[17 Indian Markets](../17-indian-markets/README.md)

**Next →** [20 Exercises](../20-exercises/README.md)
