/**
 * TypeScript types mirroring the QuantCouncil API's REAL response shapes.
 *
 * Every field here was read directly off the FastAPI routers
 * (apps/api/app/routers/{assets,strategies,backtests,risk,committee,paper,health}.py)
 * and the service/repository layers they call into
 * (app/services/{committee_service,paper_engine}.py, app/db/repositories.py) --
 * not guessed. Do not add fields the backend doesn't actually return; do not
 * rename a field to something "nicer" -- the response dict keys ARE the
 * contract. If the backend adds a field, add it here; don't invent ahead of it.
 */

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------

/** ISO date string, "YYYY-MM-DD". */
export type IsoDate = string;
/** ISO 8601 datetime string. */
export type IsoDateTime = string;
/** Stringified UUID. */
export type UUID = string;

// ---------------------------------------------------------------------------
// health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface HealthDbResponse {
  database: string; // "ok" | "unreachable"
}

// ---------------------------------------------------------------------------
// assets
// ---------------------------------------------------------------------------

export interface AssetRecord {
  symbol: string;
  name: string;
  exchange: string;
  sector: string | null;
  yfinance_symbol?: string;
}

export interface AssetsResponse {
  count: number;
  assets: AssetRecord[];
}

export interface OhlcvBar {
  date: IsoDate;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface OhlcvResponse {
  symbol: string;
  timeframe: string;
  start_date: IsoDate;
  end_date: IsoDate;
  rows: number;
  data: OhlcvBar[];
}

export interface IndicatorRow {
  date: IsoDate;
  close: number | null;
  sma_20: number | null;
  sma_50: number | null;
  ema_20: number | null;
  rsi_14: number | null;
  atr_14: number | null;
  volume_sma_20: number | null;
  rolling_high_20: number | null;
  rolling_low_20: number | null;
  daily_returns: number | null;
  volatility_20: number | null;
}

export interface IndicatorsResponse {
  symbol: string;
  start_date: IsoDate;
  end_date: IsoDate;
  rows: number;
  indicators: IndicatorRow[];
}

// ---------------------------------------------------------------------------
// strategies
// ---------------------------------------------------------------------------

/**
 * Full strategy definition per docs/strategy-format.md, plus the API's
 * metadata fields. Entry/exit rule internals are intentionally loose
 * (`unknown`) here -- pages that need to render/edit rule trees should
 * consult docs/strategy-format.md directly rather than over-fitting this
 * shared type.
 */
export interface StrategyRecord {
  name: string;
  description?: string | null;
  universe: string[];
  timeframe: string;
  direction: string;
  entry_rules?: unknown;
  exit_rules?: unknown;
  risk?: unknown;
  source: "builtin" | "persisted";
  id?: string;
  status?: string;
  created_at?: IsoDateTime;
  [key: string]: unknown;
}

export interface StrategiesResponse {
  count: number;
  strategies: StrategyRecord[];
  warning?: string;
}

export interface CreateStrategyResponse {
  id: UUID;
  name: string;
  status: string;
  source: "persisted";
  created_at: IsoDateTime;
}

// ---------------------------------------------------------------------------
// backtests
// ---------------------------------------------------------------------------

export interface BacktestMetrics {
  total_return: number | null;
  cagr: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  profit_factor: number | null;
  num_trades: number | null;
  exposure_time: number | null;
  sharpe: number | null;
  best_trade: number | null;
  worst_trade: number | null;
  starting_capital: number | null;
  final_equity: number | null;
}

/** Metrics subset returned by the GET /backtests list endpoint. */
export interface BacktestMetricsSubset {
  total_return: number | null;
  max_drawdown: number | null;
  sharpe: number | null;
  num_trades: number | null;
}

export interface EquityCurvePoint {
  date: IsoDate;
  equity: number | null;
}

export interface TradeRecord {
  symbol: string;
  entry_date: IsoDate;
  entry_price: number | null;
  exit_date: IsoDate;
  exit_price: number | null;
  quantity: number;
  pnl: number | null;
  return_pct: number | null;
  exit_reason: string;
}

export interface BacktestConfig {
  initial_capital: number;
  slippage_pct: number;
  transaction_cost_pct: number;
  max_allocation_pct: number;
}

/** Response of POST /backtests/run. */
export interface BacktestRunResponse {
  strategy_name: string;
  symbol: string;
  timeframe: string;
  start_date: IsoDate;
  end_date: IsoDate;
  config: BacktestConfig;
  metrics: BacktestMetrics;
  equity_curve: EquityCurvePoint[];
  trades: TradeRecord[];
  persisted: boolean;
  backtest_id: UUID | null;
  note?: string;
}

/** Response of GET /backtests/{id}. */
export interface BacktestDetailResponse {
  backtest_id: UUID;
  strategy_id: UUID;
  strategy_name: string | null;
  symbol: string | null;
  timeframe: string | null;
  config: BacktestConfig;
  start_date: IsoDate;
  end_date: IsoDate;
  status: string;
  created_at: IsoDateTime | null;
  completed_at: IsoDateTime | null;
  metrics: BacktestMetrics | null;
  equity_curve: EquityCurvePoint[];
  trades: TradeRecord[];
  persisted: true;
}

/** One item of GET /backtests. */
export interface BacktestListItem {
  backtest_id: UUID;
  strategy_id: UUID;
  strategy_name: string | null;
  symbol: string | null;
  timeframe: string | null;
  start_date: IsoDate;
  end_date: IsoDate;
  status: string;
  created_at: IsoDateTime | null;
  metrics: BacktestMetricsSubset;
}

export interface BacktestsListResponse {
  count: number;
  backtests: BacktestListItem[];
}

// ---------------------------------------------------------------------------
// risk
// ---------------------------------------------------------------------------

export type RiskDecision = "APPROVED" | "REJECTED" | "NEEDS_REVIEW";

/** Shared fields of the full RiskEvaluationResult contract. */
export interface RiskEvaluationResult {
  decision: RiskDecision;
  approved: boolean;
  risk_score: number;
  policy_version: string;
  reasons: unknown[];
  failed_rules: unknown[];
  warnings: unknown[];
  metrics_snapshot: Record<string, unknown> | null;
  policy_snapshot: Record<string, unknown> | null;
}

/** Response of POST /risk/evaluate. */
export interface RiskEvaluateResponse extends RiskEvaluationResult {
  risk_evaluation_id: UUID | null;
  backtest_id: UUID | null;
  persisted: boolean;
  note?: string;
}

/** Response of GET /risk/evaluations/{id} and GET /backtests/{id}/risk. */
export interface RiskEvaluationDetailResponse extends RiskEvaluationResult {
  risk_evaluation_id: UUID;
  backtest_id: UUID;
  strategy_id: UUID;
  created_at: IsoDateTime;
  persisted: true;
}

/** One item of GET /risk/evaluations. */
export interface RiskEvaluationListItem {
  risk_evaluation_id: UUID;
  backtest_run_id: UUID;
  decision: RiskDecision;
  approved: boolean;
  risk_score: number;
  policy_version: string;
  created_at: IsoDateTime;
}

export interface RiskEvaluationsListResponse {
  count: number;
  evaluations: RiskEvaluationListItem[];
}

// ---------------------------------------------------------------------------
// committee
// ---------------------------------------------------------------------------

export type TechnicalView = "BULLISH" | "BEARISH" | "NEUTRAL" | "MIXED";
export type StrategyQuality = "STRONG" | "ACCEPTABLE" | "WEAK" | "INVALID";
export type CioDecision = "PAPER_TRADE" | "NO_TRADE" | "WATCHLIST";

export interface TechnicalAnalystOutput {
  view: TechnicalView;
  confidence: number;
  signals: string[];
  warnings: string[];
  summary: string;
}

export interface QuantResearcherOutput {
  strategy_quality: StrategyQuality;
  rule_interpretation: string;
  strengths: string[];
  weaknesses: string[];
  improvement_ideas: string[];
  summary: string;
}

export interface BullCaseOutput {
  case_strength: number;
  arguments: string[];
  best_case_scenario: string;
  summary: string;
}

export interface BearCaseOutput {
  case_strength: number;
  risks: string[];
  failure_modes: string[];
  worst_case_scenario: string;
  summary: string;
}

export interface RiskNarratorOutput {
  risk_summary: string;
  failed_rules_explained: string[];
  warnings_explained: string[];
  plain_english_verdict: string;
}

export interface CioAuditRefs {
  backtest_id: string;
  risk_evaluation_id: string;
  agent_decision_ids: string[];
}

/** The FINAL, veto-checked CIO decision -- authoritative. */
export interface CioDecisionOutput {
  decision: CioDecision;
  approved_by_risk: boolean;
  summary: string;
  reason: string;
  conditions_to_reconsider: string[];
  audit_refs: CioAuditRefs;
  override_warning?: string | null;
}

/** The RAW, untrusted CIO call, for audit only -- never the decision of record. */
export interface CioRawOutput {
  decision: CioDecision;
  summary: string;
  reason: string;
  conditions_to_reconsider: string[];
}

/** Response of POST /committee/evaluate. */
export interface CommitteeEvaluateResponse {
  backtest_id: UUID;
  risk_evaluation_id: UUID;
  requested_provider: string;
  selected_provider: string;
  technical_analyst: TechnicalAnalystOutput;
  quant_researcher: QuantResearcherOutput;
  bull_case: BullCaseOutput;
  bear_case: BearCaseOutput;
  risk_narrator: RiskNarratorOutput;
  cio: CioDecisionOutput;
  cio_raw: CioRawOutput;
  override_warning: string | null;
  agent_decision_ids: UUID[];
}

export interface AgentDecisionRecord {
  id: UUID;
  agent_role: string;
  model: string | null;
  output: Record<string, unknown>;
  created_at: IsoDateTime;
}

/** Response of GET /committee/backtests/{id}. */
export interface CommitteeBacktestEvaluationsResponse {
  backtest_id: UUID;
  count: number;
  decisions: AgentDecisionRecord[];
}

// ---------------------------------------------------------------------------
// paper
// ---------------------------------------------------------------------------

export type RiskMode = "NORMAL" | "RISK_OFF";

export interface PaperPortfolio {
  id: UUID;
  name: string;
  starting_capital: number;
  current_cash: number;
  current_nav: number;
  peak_nav: number | null;
  risk_mode: RiskMode;
  settings: Record<string, unknown> | null;
  created_at: IsoDateTime | null;
  updated_at: IsoDateTime | null;
}

export interface PaperPortfoliosResponse {
  count: number;
  portfolios: PaperPortfolio[];
}

export type OrderSide = "BUY" | "SELL";
export type OrderStatus = "FILLED" | "PENDING" | "CANCELLED" | "REJECTED";

export interface PaperOrder {
  id: UUID;
  portfolio_id: UUID;
  asset_id: number;
  strategy_id: UUID | null;
  backtest_run_id: UUID | null;
  risk_evaluation_id: UUID | null;
  side: OrderSide;
  quantity: number;
  order_type: string;
  status: OrderStatus;
  limit_price: number | null;
  fill_price: number | null;
  stop_loss: number | null;
  created_at: IsoDateTime | null;
  filled_at: IsoDateTime | null;
}

export interface PaperOrdersResponse {
  count: number;
  orders: PaperOrder[];
}

export type PositionStatus = "OPEN" | "CLOSED";

export interface PaperPosition {
  id: UUID;
  portfolio_id: UUID;
  asset_id: number;
  strategy_id: UUID | null;
  quantity: number;
  avg_entry_price: number;
  stop_loss: number;
  status: PositionStatus;
  last_price: number | null;
  unrealized_pnl: number | null;
  realized_pnl: number | null;
  opened_at: IsoDateTime | null;
  closed_at: IsoDateTime | null;
}

export interface PaperPositionsResponse {
  count: number;
  positions: PaperPosition[];
}

export interface FillInfo {
  reference_price: number;
  fill_price: number;
  slippage_pct: number;
  transaction_cost_pct: number;
  cost: number;
  total_debit?: number;
  proceeds?: number;
  realized_pnl_this_sale?: number;
  position_closed?: boolean;
}

/** Response of POST /paper/orders. */
export interface CreateOrderResponse {
  order: PaperOrder;
  position: PaperPosition;
  portfolio: PaperPortfolio;
  journal_entry_id: UUID;
  fill: FillInfo;
}

/** Response of POST /paper/portfolios/{id}/mark-to-market. */
export interface MarkToMarketResponse {
  portfolio_id: UUID;
  nav: number;
  cash: number;
  peak_nav: number;
  drawdown: number;
  risk_off: boolean;
  positions: PaperPosition[];
}

export interface NavSnapshot {
  date: IsoDate;
  nav: number;
  cash: number;
  drawdown: number;
  risk_off: boolean;
}

/** Response of GET /paper/portfolios/{id}/nav-history. Ordered oldest -> newest. */
export interface NavHistoryResponse {
  portfolio_id: UUID;
  count: number;
  snapshots: NavSnapshot[];
}

/** One stop-loss sweep fill executed inside a daily-cycle run. */
export interface StopTriggered {
  position_id: UUID;
  symbol: string;
  quantity: number;
  stop_loss: number;
  close: number;
  order_id: UUID;
}

/** Response of POST /paper/portfolios/{id}/daily-cycle: stop-loss sweep -> mark-to-market -> NAV snapshot. */
export interface DailyCycleResponse {
  portfolio_id: UUID;
  date: IsoDate;
  stops_triggered: StopTriggered[];
  mark_to_market: MarkToMarketResponse;
  snapshot: NavSnapshot;
}

/** Response of POST /paper/portfolios/{id}/risk-off/reset -- portfolio summary (same shape as PaperPortfolio) plus a journaled flag. */
export interface RiskOffResetResponse extends PaperPortfolio {
  journaled: true;
}

export type JournalEntryType = "DECISION" | "FILL" | "NOTE" | "RISK_EVENT";

export interface JournalEntry {
  id: UUID;
  portfolio_id: UUID;
  order_id: UUID | null;
  position_id: UUID | null;
  strategy_id: UUID | null;
  entry_type: JournalEntryType | string;
  title: string;
  body: string;
  refs: Record<string, unknown> | null;
  created_at: IsoDateTime | null;
}

export interface JournalResponse {
  count: number;
  journal: JournalEntry[];
}

// ---------------------------------------------------------------------------
// Generic strategy lifecycle / status vocabularies (for DecisionBadge)
// ---------------------------------------------------------------------------

export type StrategyLifecycleStatus =
  | "DRAFT"
  | "BACKTESTED"
  | "RISK_EVALUATED"
  | "RISK_APPROVED"
  | "PAPER_TRADING"
  | "RETIRED";
