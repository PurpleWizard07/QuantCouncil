import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "@/app/components/ui/Toast";
import type { AssetRecord, CreateOrderResponse } from "@/app/lib/types";

import { StepOrder } from "./StepOrder";

vi.mock("@/app/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  getPortfolios: vi.fn(() => Promise.resolve({ count: 0, portfolios: [] })),
  createPortfolio: vi.fn(),
  createPaperOrder: vi.fn(),
}));

const SYMBOL: AssetRecord = {
  symbol: "RELIANCE",
  name: "Reliance Industries",
  exchange: "NSE",
  sector: "Energy",
};

const BASE_PROPS = {
  symbol: SYMBOL,
  backtestId: "backtest-1",
  riskEvaluationId: "risk-eval-1",
  riskFailedRules: [] as unknown[],
  riskWarnings: [] as unknown[],
  riskReasons: [] as unknown[],
  onSuccess: vi.fn(),
};

const FILLED_RESULT: CreateOrderResponse = {
  order: {
    id: "order-1",
    portfolio_id: "portfolio-1",
    asset_id: 1,
    strategy_id: null,
    side: "BUY",
    quantity: 10,
    status: "FILLED",
  } as CreateOrderResponse["order"],
  position: {} as CreateOrderResponse["position"],
  portfolio: {
    id: "portfolio-1",
    name: "Default",
    starting_capital: 100000,
    current_cash: 90000,
    current_nav: 100500,
    peak_nav: 100500,
    risk_mode: "NORMAL",
    settings: null,
    created_at: null,
    updated_at: null,
  } as CreateOrderResponse["portfolio"],
  journal_entry_id: "journal-1",
  fill: {
    reference_price: 100,
    fill_price: 100.5,
    slippage_pct: 0.005,
    transaction_cost_pct: 0.001,
    cost: 1005,
  } as CreateOrderResponse["fill"],
};

function renderWithToast(ui: ReactElement) {
  return render(<ToastProvider>{ui}</ToastProvider>);
}

describe("StepOrder", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the veto seal and no order form when risk is not approved", () => {
    renderWithToast(
      <StepOrder
        {...BASE_PROPS}
        riskApproved={false}
        riskDecision="REJECTED"
        result={null}
      />,
    );

    expect(screen.getByText("REJECTED")).toBeInTheDocument();
    expect(
      screen.getByText(/no llm agent and no button in this ui can override the veto/i),
    ).toBeInTheDocument();

    expect(screen.queryByLabelText(/thesis/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/stop-loss price/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/quantity/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /place paper order/i })).not.toBeInTheDocument();
  });

  it("renders the order form fields when risk is approved and no result exists yet", async () => {
    const api = await import("@/app/lib/api");
    vi.mocked(api.getPortfolios).mockResolvedValue({
      count: 1,
      portfolios: [
        {
          id: "portfolio-1",
          name: "Default",
          starting_capital: 100000,
          current_cash: 100000,
          current_nav: 100000,
          peak_nav: 100000,
          risk_mode: "NORMAL",
          settings: null,
          created_at: null,
          updated_at: null,
        },
      ],
    });

    renderWithToast(
      <StepOrder
        {...BASE_PROPS}
        riskApproved={true}
        riskDecision="APPROVED"
        result={null}
      />,
    );

    expect(await screen.findByLabelText(/thesis/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/stop-loss price/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^quantity$/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /place paper order/i })).toBeInTheDocument();

    expect(screen.queryByText("REJECTED")).not.toBeInTheDocument();
    expect(screen.queryByText("NEEDS REVIEW")).not.toBeInTheDocument();
  });

  it("renders the filled-order summary instead of the form when a result already exists", () => {
    renderWithToast(
      <StepOrder
        {...BASE_PROPS}
        riskApproved={true}
        riskDecision="APPROVED"
        result={FILLED_RESULT}
      />,
    );

    expect(screen.getByText("Paper order filled")).toBeInTheDocument();
    expect(screen.queryByLabelText(/thesis/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /place paper order/i })).not.toBeInTheDocument();
  });
});
