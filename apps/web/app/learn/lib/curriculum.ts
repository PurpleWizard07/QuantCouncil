/**
 * Curriculum metadata for the Learn section: Course -> Module -> Lesson.
 * This is structured data, not content -- lesson bodies live as MDX files
 * under content/learn/<module>/<lesson>.mdx. Keeping order/status/flags here
 * (rather than as MDX frontmatter) means the landing and module pages can
 * render the whole tree without reading 50 files.
 */

export type LessonStatus = "ready" | "outline";

export interface Lesson {
  slug: string;
  title: string;
  /** Source file(s) under trading-mastery/ this lesson was migrated from, for traceability. */
  sourceFiles: string[];
  status: LessonStatus;
  /** Shows the "Educational only -- not simulated in the paper engine" banner. */
  constitutionFlag?: boolean;
  /** Shows a "must read" emphasis treatment. */
  critical?: boolean;
}

export interface Module {
  slug: string;
  title: string;
  levelLabel?: string;
  description: string;
  critical?: boolean;
  constitutionFlag?: boolean;
  lessons: Lesson[];
}

export const CURRICULUM: Module[] = [
  {
    slug: "foundations",
    title: "Foundations",
    levelLabel: "Level 1 · Market Literacy",
    description:
      "What money, assets, risk, and return actually are, and the plumbing that turns a click into a settled trade.",
    lessons: [
      { slug: "money-assets-markets", title: "Money, Assets & Why Markets Exist", sourceFiles: ["00-foundations/README.md §1-3"], status: "ready" },
      { slug: "investing-trading-speculation", title: "Investing vs. Trading vs. Speculation; Risk vs. Uncertainty", sourceFiles: ["00-foundations/README.md §4-5"], status: "ready" },
      { slug: "return-compounding-inflation", title: "Return, Compounding & Inflation", sourceFiles: ["00-foundations/README.md §6-8"], status: "ready" },
      { slug: "liquidity-volatility-correlation", title: "Liquidity, Volatility, Correlation & Diversification", sourceFiles: ["00-foundations/README.md §9-13"], status: "ready" },
      { slug: "institutions-and-ipos", title: "Who Runs a Market: Institutions & IPOs", sourceFiles: ["01-how-markets-work/README.md §1-2"], status: "ready" },
      { slug: "order-book-and-order-types", title: "The Order Book, Order Types & Slippage", sourceFiles: ["01-how-markets-work/README.md §3-6"], status: "ready" },
      { slug: "order-lifecycle-and-settlement", title: "What Happens After You Press Buy", sourceFiles: ["01-how-markets-work/README.md §7-8"], status: "ready" },
      { slug: "short-selling-margin-leverage", title: "Short Selling, Margin & Leverage", sourceFiles: ["01-how-markets-work/README.md §9"], status: "ready" },
      { slug: "assets-and-instruments", title: "Assets & Instruments Overview", sourceFiles: ["02-assets-and-instruments/README.md"], status: "outline" },
      { slug: "why-buyers-vs-sellers-is-wrong", title: "Why \"Buyers vs. Sellers\" Is a Bad Explanation", sourceFiles: ["03-price-and-market-behavior/README.md §1-3"], status: "ready" },
      { slug: "price-drivers-and-market-efficiency", title: "What Actually Moves Price; How Efficient Are Markets", sourceFiles: ["03-price-and-market-behavior/README.md §4-8"], status: "ready" },
    ],
  },
  {
    slug: "analysis",
    title: "Analysis",
    levelLabel: "Level 2",
    description: "Reading a business from its financial statements, and reading price honestly from a chart.",
    lessons: [
      { slug: "fundamental-analysis", title: "Reading the Three Financial Statements & Key Ratios", sourceFiles: ["04-fundamental-analysis/README.md"], status: "outline" },
      { slug: "ta-honest-framing", title: "Technical Analysis: The Honest Framing", sourceFiles: ["05-technical-analysis/README.md §1-5"], status: "ready" },
      { slug: "ta-indicator-reference", title: "Indicator Reference: SMA/EMA, VWAP, RSI, MACD, Bollinger, ATR, Stochastic, ADX", sourceFiles: ["05-technical-analysis/README.md §6"], status: "ready" },
      { slug: "chart-patterns-and-testing", title: "Chart Patterns & How to Test Any TA Idea", sourceFiles: ["05-technical-analysis/README.md §7-9"], status: "ready" },
      { slug: "trading-styles", title: "Choosing a Trading Style", sourceFiles: ["06-trading-styles/README.md"], status: "outline" },
    ],
  },
  {
    slug: "risk-management",
    title: "Risk Management",
    levelLabel: "Level 3 · Do Not Skip",
    description:
      "The most important module in this course. More traders are destroyed by weak risk management than by weak analysis.",
    critical: true,
    lessons: [
      { slug: "position-sizing", title: "Why Risk Management Comes First; Position Sizing", sourceFiles: ["07-risk-management/README.md §1-2"], status: "ready", critical: true },
      { slug: "stops-and-r-multiple", title: "Stop Losses & the R Multiple", sourceFiles: ["07-risk-management/README.md §3-4"], status: "ready" },
      { slug: "expectancy", title: "Expectancy — the Master Formula", sourceFiles: ["07-risk-management/README.md §5-6"], status: "ready", critical: true },
      { slug: "drawdown-and-risk-of-ruin", title: "Drawdown & Risk of Ruin", sourceFiles: ["07-risk-management/README.md §7"], status: "ready" },
      { slug: "kelly-criterion", title: "Volatility-Adjusted Sizing & the Kelly Criterion", sourceFiles: ["07-risk-management/README.md §8-9"], status: "ready" },
      { slug: "portfolio-risk-correlation-leverage", title: "Portfolio-Level Risk: Correlation & Leverage", sourceFiles: ["07-risk-management/README.md §10-11"], status: "ready" },
    ],
  },
  {
    slug: "strategy-development",
    title: "Strategy Development",
    levelLabel: "Level 4",
    description: "Turning \"this looks good\" into a precisely defined, testable system.",
    lessons: [
      { slug: "ten-components-of-a-strategy", title: "The 10 Components of a Complete Strategy; Trading Plan & Journal", sourceFiles: ["08-strategy-development/README.md"], status: "outline" },
    ],
  },
  {
    slug: "derivatives",
    title: "Derivatives",
    levelLabel: "Level 5",
    description: "Futures and options: leverage, the Greeks, and why selling options is not free money.",
    constitutionFlag: true,
    lessons: [
      { slug: "futures-mechanics", title: "Futures: Mechanics, Basis, Mark-to-Market, Hedging", sourceFiles: ["09-futures/README.md"], status: "outline", constitutionFlag: true },
      { slug: "options-building-blocks-and-greeks", title: "Options: Building Blocks & the Greeks", sourceFiles: ["10-options/README.md §1-4"], status: "ready", constitutionFlag: true },
      { slug: "volatility-chain-open-interest", title: "Volatility, the Option Chain & Open Interest", sourceFiles: ["10-options/README.md §5-7"], status: "ready", constitutionFlag: true },
      { slug: "options-strategies-and-payoffs", title: "Options Strategies & Payoffs", sourceFiles: ["10-options/README.md §8"], status: "ready", constitutionFlag: true },
      { slug: "why-selling-options-is-not-free-money", title: "Why Selling Options Is Not Free Money", sourceFiles: ["10-options/README.md §9"], status: "ready", constitutionFlag: true, critical: true },
      { slug: "options-in-india", title: "Options in India: Rules, Costs & Checklist", sourceFiles: ["10-options/README.md §10-11"], status: "ready", constitutionFlag: true },
    ],
  },
  {
    slug: "psychology",
    title: "Trading Psychology",
    description: "Why understanding probability doesn't stop you behaving irrationally, and how to build systems that don't need willpower.",
    lessons: [
      { slug: "bias-catalogue-and-discipline-systems", title: "The Bias Catalogue & Building Discipline as a System", sourceFiles: ["11-trading-psychology/README.md"], status: "outline" },
    ],
  },
  {
    slug: "backtesting-statistics",
    title: "Backtesting & Statistics",
    levelLabel: "Level 6",
    description: "The bridge from discretionary trading to quant: measuring an edge honestly, and the ways backtests lie.",
    lessons: [
      { slug: "data-hazards-and-returns", title: "Data Hazards & Return Types", sourceFiles: ["12-backtesting-and-statistics/README.md §1-2"], status: "ready" },
      { slug: "core-statistics-and-fat-tails", title: "Core Statistics & Fat Tails", sourceFiles: ["12-backtesting-and-statistics/README.md §3-4"], status: "ready" },
      { slug: "performance-metrics", title: "Performance Metrics: Sharpe, Sortino, Drawdown, Calmar", sourceFiles: ["12-backtesting-and-statistics/README.md §5"], status: "ready" },
      { slug: "backtest-loop-and-pitfalls", title: "The Backtest Loop & the Pitfalls That Kill It", sourceFiles: ["12-backtesting-and-statistics/README.md §6-7"], status: "ready", critical: true },
      { slug: "validation-walkforward-montecarlo", title: "Validation: Walk-Forward, Monte Carlo & Significance", sourceFiles: ["12-backtesting-and-statistics/README.md §8-11"], status: "ready" },
    ],
  },
  {
    slug: "algorithmic-trading",
    title: "Algorithmic Trading",
    levelLabel: "Level 7",
    description: "Automation removes hesitation and fat-finger errors -- it does not remove the need for a validated edge.",
    lessons: [
      { slug: "automating-a-strategy", title: "Automating a Strategy: Execution Algos & System Architecture", sourceFiles: ["13-algorithmic-trading/README.md"], status: "outline" },
    ],
  },
  {
    slug: "quantitative-trading",
    title: "Quantitative Trading",
    levelLabel: "Level 8",
    description: "Factors, pairs trading, and honest skepticism about machine learning in markets.",
    lessons: [
      { slug: "factor-investing", title: "Factor Investing", sourceFiles: ["14-quantitative-trading/README.md §1-2"], status: "outline" },
      { slug: "pairs-trading-and-cointegration", title: "Pairs Trading, Cointegration & Why \"AI Trading\" Deserves Skepticism", sourceFiles: ["14-quantitative-trading/README.md §3-5"], status: "outline" },
    ],
  },
  {
    slug: "market-microstructure",
    title: "Market Microstructure",
    levelLabel: "Level 9",
    description: "The order book up close: order-flow imbalance, adverse selection, and what HFT actually does.",
    lessons: [
      { slug: "order-flow-and-market-impact", title: "Order-Flow Imbalance, Market Impact & What HFT Actually Does", sourceFiles: ["15-market-microstructure/README.md"], status: "outline" },
    ],
  },
  {
    slug: "advanced-topics",
    title: "Advanced Topics",
    levelLabel: "Level 10",
    description: "A map of what exists beyond the fundamentals -- regimes, volatility modeling, and portfolio construction.",
    lessons: [
      { slug: "regimes-volatility-portfolio-optimization", title: "Swaps, Regime Detection, Volatility Modeling & Portfolio Optimization", sourceFiles: ["16-advanced-topics/README.md"], status: "outline" },
    ],
  },
  {
    slug: "indian-markets",
    title: "Indian Markets",
    description: "SEBI, NSE/BSE, settlement, the full cost stack, and taxation. The most date-sensitive module in the course.",
    lessons: [
      { slug: "regulatory-stack-accounts-settlement", title: "The Regulatory Stack, Accounts & Settlement", sourceFiles: ["17-indian-markets/README.md §1-3"], status: "ready" },
      { slug: "indices-etfs-ipos", title: "Indices, ETFs & IPOs", sourceFiles: ["17-indian-markets/README.md §4-5"], status: "ready" },
      { slug: "sebi-fo-overhaul-and-retail-reality", title: "The SEBI F&O Overhaul & the Retail F&O Reality", sourceFiles: ["17-indian-markets/README.md §6-7"], status: "ready", critical: true },
      { slug: "cost-stack-and-stt", title: "The Cost Stack & STT", sourceFiles: ["17-indian-markets/README.md §8"], status: "ready" },
      { slug: "taxation", title: "Taxation (Framework, Not Advice)", sourceFiles: ["17-indian-markets/README.md §9-10"], status: "ready" },
    ],
  },
  {
    slug: "practical-trading",
    title: "Practical Trading",
    description: "The path from zero to live trading -- paper trading, broker selection, and journaling.",
    lessons: [
      { slug: "capital-progression-broker-journaling", title: "Capital Progression, Choosing a Broker & Journaling", sourceFiles: ["18-practical-trading/README.md"], status: "outline" },
    ],
  },
  {
    slug: "case-studies",
    title: "Case Studies",
    description: "Concrete stories of exactly how smart, well-resourced people lost enormous amounts of money.",
    lessons: [
      { slug: "overfit-backtest-ltcm-retail-losses", title: "An Overfit Backtest, LTCM 1998 & Retail F&O Losses in India", sourceFiles: ["19-case-studies/README.md"], status: "outline" },
    ],
  },
  {
    slug: "exercises",
    title: "Exercises & Practice",
    description: "Progressive problems with worked solutions, cross-linked from the module each one tests.",
    lessons: [
      { slug: "beginner", title: "Beginner Exercises", sourceFiles: ["20-exercises/README.md §Beginner"], status: "ready" },
      { slug: "intermediate", title: "Intermediate Exercises", sourceFiles: ["20-exercises/README.md §Intermediate"], status: "ready" },
      { slug: "advanced", title: "Advanced Exercises", sourceFiles: ["20-exercises/README.md §Advanced"], status: "ready" },
    ],
  },
];

export function getModule(moduleSlug: string): Module | undefined {
  return CURRICULUM.find((m) => m.slug === moduleSlug);
}

export function getLesson(moduleSlug: string, lessonSlug: string): { module: Module; lesson: Lesson } | undefined {
  const module = getModule(moduleSlug);
  const lesson = module?.lessons.find((l) => l.slug === lessonSlug);
  if (!module || !lesson) return undefined;
  return { module, lesson };
}

/** Flat ordered list of every (moduleSlug, lessonSlug) pair, for prev/next nav and progress totals. */
export function allLessonRefs(): { moduleSlug: string; lessonSlug: string }[] {
  return CURRICULUM.flatMap((m) => m.lessons.map((l) => ({ moduleSlug: m.slug, lessonSlug: l.slug })));
}

export function adjacentLessons(moduleSlug: string, lessonSlug: string) {
  const refs = allLessonRefs();
  const index = refs.findIndex((r) => r.moduleSlug === moduleSlug && r.lessonSlug === lessonSlug);
  return {
    prev: index > 0 ? refs[index - 1] : null,
    next: index >= 0 && index < refs.length - 1 ? refs[index + 1] : null,
  };
}

export function totalLessonCount(): number {
  return CURRICULUM.reduce((sum, m) => sum + m.lessons.length, 0);
}

export function progressId(moduleSlug: string, lessonSlug: string): string {
  return `${moduleSlug}/${lessonSlug}`;
}
