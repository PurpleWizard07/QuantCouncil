/**
 * QuantCouncil API client. One `request<T>` core, plus a typed helper for
 * every endpoint group so page agents never need to touch this file or
 * hand-roll a fetch call. No retry logic by design (keep it simple; a page
 * that wants a retry button calls the same helper again from its ErrorState).
 */

import type {
  AssetsResponse,
  BacktestDetailResponse,
  BacktestRunResponse,
  BacktestsListResponse,
  CommitteeBacktestEvaluationsResponse,
  CommitteeEvaluateResponse,
  CreateOrderResponse,
  CreateStrategyResponse,
  DailyCycleResponse,
  FundamentalsResponse,
  HealthDbResponse,
  HealthResponse,
  IndicatorsResponse,
  JournalResponse,
  MarkToMarketResponse,
  NavHistoryResponse,
  OhlcvResponse,
  PaperOrdersResponse,
  PaperPortfolio,
  PaperPortfoliosResponse,
  PaperPositionsResponse,
  RiskEvaluateResponse,
  RiskEvaluationDetailResponse,
  RiskEvaluationsListResponse,
  RiskOffResetResponse,
  StrategiesResponse,
} from "./types";

// NEXT_PUBLIC_ variables are inlined at build time by Next.js. Keep this
// exact name -- it is the project-wide convention, documented in .env.example.
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/** Normalized API error. FastAPI error bodies carry `{"detail": ...}`. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(ApiError.formatMessage(status, detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  private static formatMessage(status: number, detail: unknown): string {
    if (typeof detail === "string" && detail.length > 0) return detail;
    if (detail != null) {
      try {
        return JSON.stringify(detail);
      } catch {
        // fall through
      }
    }
    return `Request failed with status ${status}`;
  }
}

/** Drops undefined/null values so callers can pass optional query params directly. */
function toQueryString(params?: Record<string, string | number | boolean | undefined | null>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null);
  if (entries.length === 0) return "";
  const search = new URLSearchParams();
  for (const [key, value] of entries) search.set(key, String(value));
  return `?${search.toString()}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch (cause) {
    // Network failure (API down, CORS, DNS, offline...): normalize to ApiError
    // status 0 so callers can branch on a single error type.
    throw new ApiError(0, `Could not reach the API at ${API_BASE}: ${String(cause)}`);
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let body: unknown = undefined;
  if (text.length > 0) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    const detail =
      body && typeof body === "object" && "detail" in (body as Record<string, unknown>)
        ? (body as Record<string, unknown>).detail
        : body;
    throw new ApiError(res.status, detail);
  }

  return body as T;
}

function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

// ---------------------------------------------------------------------------
// health
// ---------------------------------------------------------------------------

export function getHealth(): Promise<HealthResponse> {
  return get<HealthResponse>("/health");
}

export function getHealthDb(): Promise<HealthDbResponse> {
  return get<HealthDbResponse>("/health/db");
}

// ---------------------------------------------------------------------------
// assets
// ---------------------------------------------------------------------------

export function getAssets(): Promise<AssetsResponse> {
  return get<AssetsResponse>("/assets");
}

// A type alias (not an interface) so it satisfies toQueryString's implicit
// index signature check.
export type DateRangeParams = {
  start_date?: string;
  end_date?: string;
  timeframe?: string;
};

export function getOhlcv(symbol: string, params: DateRangeParams = {}): Promise<OhlcvResponse> {
  return get<OhlcvResponse>(`/assets/${encodeURIComponent(symbol)}/ohlcv${toQueryString(params)}`);
}

export function getIndicators(
  symbol: string,
  params: DateRangeParams = {},
): Promise<IndicatorsResponse> {
  return get<IndicatorsResponse>(
    `/assets/${encodeURIComponent(symbol)}/indicators${toQueryString(params)}`,
  );
}

/** GET /assets/{symbol}/fundamentals -- no query params (a company snapshot, not a range). */
export function getFundamentals(symbol: string): Promise<FundamentalsResponse> {
  return get<FundamentalsResponse>(`/assets/${encodeURIComponent(symbol)}/fundamentals`);
}

// ---------------------------------------------------------------------------
// strategies
// ---------------------------------------------------------------------------

export function getStrategies(): Promise<StrategiesResponse> {
  return get<StrategiesResponse>("/strategies");
}

export function createStrategy(definition: Record<string, unknown>): Promise<CreateStrategyResponse> {
  return post<CreateStrategyResponse>("/strategies", definition);
}

// ---------------------------------------------------------------------------
// backtests
// ---------------------------------------------------------------------------

export interface RunBacktestBody {
  strategy?: Record<string, unknown>;
  strategy_id?: string;
  symbol: string;
  start_date?: string;
  end_date?: string;
  persist?: boolean;
}

export function runBacktest(body: RunBacktestBody): Promise<BacktestRunResponse> {
  return post<BacktestRunResponse>("/backtests/run", body);
}

export function getBacktest(id: string): Promise<BacktestDetailResponse> {
  return get<BacktestDetailResponse>(`/backtests/${encodeURIComponent(id)}`);
}

export function listBacktests(limit?: number): Promise<BacktestsListResponse> {
  return get<BacktestsListResponse>(`/backtests${toQueryString({ limit })}`);
}

// ---------------------------------------------------------------------------
// risk
// ---------------------------------------------------------------------------

export interface EvaluateRiskInline {
  metrics: Record<string, unknown>;
  strategy: Record<string, unknown>;
  trades?: Record<string, unknown>[];
  config?: Record<string, unknown>;
}

export type EvaluateRiskBody = { backtest_id: string } | EvaluateRiskInline;

export function evaluateRisk(body: EvaluateRiskBody): Promise<RiskEvaluateResponse> {
  return post<RiskEvaluateResponse>("/risk/evaluate", body);
}

export function getRiskEvaluation(id: string): Promise<RiskEvaluationDetailResponse> {
  return get<RiskEvaluationDetailResponse>(`/risk/evaluations/${encodeURIComponent(id)}`);
}

/** GET /backtests/{id}/risk -- the latest persisted risk evaluation for a backtest. */
export function getLatestRiskForBacktest(backtestId: string): Promise<RiskEvaluationDetailResponse> {
  return get<RiskEvaluationDetailResponse>(`/backtests/${encodeURIComponent(backtestId)}/risk`);
}

export function listRiskEvaluations(limit?: number): Promise<RiskEvaluationsListResponse> {
  return get<RiskEvaluationsListResponse>(`/risk/evaluations${toQueryString({ limit })}`);
}

// ---------------------------------------------------------------------------
// committee
// ---------------------------------------------------------------------------

export interface EvaluateCommitteeBody {
  backtest_id: string;
  risk_evaluation_id: string;
  provider?: string;
}

export function evaluateCommittee(body: EvaluateCommitteeBody): Promise<CommitteeEvaluateResponse> {
  return post<CommitteeEvaluateResponse>("/committee/evaluate", body);
}

/** GET /committee/backtests/{id} -- persisted committee evaluations for a backtest. */
export function getCommitteeForBacktest(
  backtestId: string,
): Promise<CommitteeBacktestEvaluationsResponse> {
  return get<CommitteeBacktestEvaluationsResponse>(
    `/committee/backtests/${encodeURIComponent(backtestId)}`,
  );
}

// ---------------------------------------------------------------------------
// paper
// ---------------------------------------------------------------------------

export function getPortfolios(): Promise<PaperPortfoliosResponse> {
  return get<PaperPortfoliosResponse>("/paper/portfolios");
}

export function getPortfolio(id: string): Promise<PaperPortfolio> {
  return get<PaperPortfolio>(`/paper/portfolios/${encodeURIComponent(id)}`);
}

export interface CreatePortfolioBody {
  name?: string;
  starting_capital?: number;
}

export function createPortfolio(body: CreatePortfolioBody = {}): Promise<PaperPortfolio> {
  return post<PaperPortfolio>("/paper/portfolios", body);
}

export interface CreatePaperOrderBody {
  portfolio_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  thesis?: string;
  backtest_id?: string;
  risk_evaluation_id?: string;
  price_reference?: number;
  stop_loss_price?: number;
  exit_reason?: string;
}

export function createPaperOrder(body: CreatePaperOrderBody): Promise<CreateOrderResponse> {
  return post<CreateOrderResponse>("/paper/orders", body);
}

export function getOrders(portfolioId?: string): Promise<PaperOrdersResponse> {
  return get<PaperOrdersResponse>(`/paper/orders${toQueryString({ portfolio_id: portfolioId })}`);
}

export function getPositions(portfolioId?: string): Promise<PaperPositionsResponse> {
  return get<PaperPositionsResponse>(
    `/paper/positions${toQueryString({ portfolio_id: portfolioId })}`,
  );
}

export function markToMarket(portfolioId: string): Promise<MarkToMarketResponse> {
  return post<MarkToMarketResponse>(
    `/paper/portfolios/${encodeURIComponent(portfolioId)}/mark-to-market`,
  );
}

export function getJournal(portfolioId?: string): Promise<JournalResponse> {
  return get<JournalResponse>(`/paper/journal${toQueryString({ portfolio_id: portfolioId })}`);
}

/** POST /paper/portfolios/{id}/daily-cycle -- stop-loss sweep -> mark-to-market -> NAV snapshot. */
export function runDailyCycle(portfolioId: string): Promise<DailyCycleResponse> {
  return post<DailyCycleResponse>(
    `/paper/portfolios/${encodeURIComponent(portfolioId)}/daily-cycle`,
  );
}

/** GET /paper/portfolios/{id}/nav-history -- snapshots ordered oldest -> newest. */
export function getNavHistory(portfolioId: string, limit?: number): Promise<NavHistoryResponse> {
  return get<NavHistoryResponse>(
    `/paper/portfolios/${encodeURIComponent(portfolioId)}/nav-history${toQueryString({ limit })}`,
  );
}

/** POST /paper/portfolios/{id}/risk-off/reset -- manual, journaled risk-off clear. */
export function resetRiskOff(portfolioId: string, note: string): Promise<RiskOffResetResponse> {
  return post<RiskOffResetResponse>(
    `/paper/portfolios/${encodeURIComponent(portfolioId)}/risk-off/reset`,
    { note },
  );
}
