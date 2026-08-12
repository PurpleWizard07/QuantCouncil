# 18 — Practical Trading

> ⬅ Back to [README](../README.md) · Prev: [17 Indian Markets](../17-indian-markets/README.md) · Next: [19 Case Studies](../19-case-studies/README.md)

> 💡 **Key takeaway:** Everything in this knowledge base is theory until it survives contact with real
> execution, real emotions, and real (small) money. This section is about the **path from zero to live
> trading** — paper trading, position-sizing your *learning*, broker selection, and journaling — the
> practical scaffolding around [07 Risk Management](../07-risk-management/README.md) and
> [11 Psychology](../11-trading-psychology/README.md).

**Learning objectives:** build a realistic capital-progression plan, choose a broker sensibly, and set
up a journaling habit that actually improves your trading.

*This section is a substantive outline. It can be expanded to flagship depth — e.g. a full journal
template, a broker comparison table — on request.*

---

## 1. The capital progression: paper → tiny → larger

| Stage | Purpose | Move on when |
|---|---|---|
| **Paper trading** | Learn platform mechanics, test strategy logic with zero financial risk | You can execute your plan without hesitation and your paper results roughly match your backtest |
| **Tiny real capital** (smallest meaningful size — 1 share, 1 lot, whatever your instrument allows) | Learn what *real* emotions (not paper-trading emotions) do to your decisions | You've taken 20-30+ trades at this size following your rules, and can show a journal proving it |
| **Gradually scale** | Increase size only as a function of *proven, repeated process discipline* — not confidence or a winning streak | Never scale up after a win because you feel good — scale on a pre-defined schedule tied to demonstrated consistency |

> 🚩 **Red flag:** Jumping from paper trading straight to "meaningful" capital. Paper trading cannot
> replicate the psychological weight of real money — see
> [Psychology](../11-trading-psychology/README.md). The "tiny real capital" stage exists specifically to
> surface that gap safely.

> ⚠️ **Common mistake:** Scaling up size *because* of a winning streak. Position size should scale with
> **proven process**, tracked in a journal, not with a streak that could easily be variance
> (see [Expectancy](../07-risk-management/README.md#5-expectancy--the-master-formula)).

---

## 2. Choosing a broker (India-specific considerations)

| Factor | What to check |
|---|---|
| **Brokerage structure** | Flat-fee discount broker vs. percentage-based full-service — matters a lot at small size |
| **Platform reliability** | Order execution speed, uptime during volatile sessions, mobile app quality |
| **API access** | If you plan to automate ([13](../13-algorithmic-trading/README.md)), check API availability, rate limits, documentation quality |
| **Margin/leverage policy** | How margin is calculated for F&O, intraday leverage offered |
| **Charges transparency** | Full charge breakdown (see [Cost stack](../17-indian-markets/README.md#the-cost-stack)) — not just headline brokerage |
| **Regulatory standing** | SEBI-registered, member of NSE/BSE — verify on [SEBI's](https://www.sebi.gov.in) and the exchanges' own sites |

> 🧭 This list is a checklist, not a recommendation of any specific broker — see
> [Resources → how to evaluate any source](../resources/README.md) for the same evaluative mindset applied
> to broker marketing claims.

---

## 3. Journaling — the habit that actually compounds

A trading journal isn't a diary of feelings; it's a **dataset about your own edge and your own
execution quality**.

**Minimum fields per trade:**

| Field | Why it matters |
|---|---|
| Setup / rule triggered | Lets you compute expectancy *per setup*, not just overall |
| Planned entry, stop, target | Lets you measure plan-adherence separately from outcome |
| Actual entry, exit, size | The real numbers — including slippage from plan |
| R multiple achieved | Standardizes across trades of different size — see [R multiple](../07-risk-management/README.md#4-riskreward-and-the-r-multiple) |
| Rule-followed? (Y/N) | The single most important psychological data point — see [11](../11-trading-psychology/README.md) |
| Notes on emotional state | Surfaces patterns (e.g., "I break rules mostly after 2 losses in a row") |

> 🤔 **Think about this:** If you can't tell, from your journal, whether your last 20 losing trades
> were "the strategy having a normal losing streak" (see
> [Drawdowns](../07-risk-management/README.md#7-drawdown-losing-streaks-and-risk-of-ruin)) or "me
> abandoning the rules," you don't yet have the data to improve.

---

## 4. A realistic weekly review routine

1. Tally trades taken vs. trades the *rules* called for (plan adherence).
2. Compute realized expectancy for the period; compare to backtested expectancy.
3. Review the 2-3 worst trades in detail — rule failure or genuine bad luck?
4. Check position sizing was followed exactly — no "just this once" oversizing.
5. Note one specific, small process change for next week — not a wholesale strategy overhaul.

---

✅ **Ready to move on when:** you have a written capital-progression plan with explicit "move on when"
criteria, a broker-evaluation checklist you've actually used, and a journal template with all six fields
above populated for at least a handful of real (even tiny) trades.

**Related sections:** [07 Risk Management](../07-risk-management/README.md) ·
[11 Trading Psychology](../11-trading-psychology/README.md) ·
[06 Trading Styles](../06-trading-styles/README.md) · [08 Strategy Development](../08-strategy-development/README.md)

**Next →** [19 Case Studies](../19-case-studies/README.md)
