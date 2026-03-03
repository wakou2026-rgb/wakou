import { http } from "@/utils/http";

// ── Ledger ─────────────────────────────────────────────────────────────────

export type LedgerItem = {
  id: number;
  item_name: string;
  grade: string;
  box_and_papers: string;
  location: string;
  source: string;
  customer_source: string;
  note: string;
  purchase_date: string;
  cost_jpy: number;
  exchange_rate: number;
  cost_twd: number;
  expected_price_twd: number;
  actual_price_twd: number | null;
  sold: boolean;
  order_id: number | null;
  profit_twd: number;
  profit_pct: number;
  expected_profit_twd: number;
  expected_profit_pct: number;
  created_at: string;
};

export type LedgerCreatePayload = {
  item_name: string;
  purchase_date: string; // YYYY-MM-DD
  cost_jpy: number;
  exchange_rate?: number;
  expected_price_twd?: number;
  grade?: string;
  box_and_papers?: string;
  location?: string;
  source?: string;
  customer_source?: string;
  note?: string;
  order_id?: number;
};

export type MarkSoldPayload = {
  actual_price_twd: number;
  order_id?: number;
};

export type ProfitDistribution = {
  id: number;
  investor_id: number | null;
  label: string;
  amount_twd: number;
  distributed_at: string;
};

export type DistributionEntry = {
  investor_id?: number | null;
  label: string;
  amount_twd: number;
};

// ── Investors ──────────────────────────────────────────────────────────────

export type Investor = {
  id: number;
  name: string;
  note: string | null;
  created_at: string;
};

export type InvestorSummary = Investor & {
  total_contributed_twd: number;
  total_distributed_twd: number;
  net_twd: number;
};

export type InvestorCreatePayload = {
  name: string;
  note?: string;
};

export type ContributionPayload = {
  amount_twd: number;
  contributed_at: string; // YYYY-MM-DD
  note?: string;
};

export type DistributionsPayload = {
  distributions: DistributionEntry[];
};

// ── API calls ──────────────────────────────────────────────────────────────

export const getLedger = () =>
  http.request<{ items: LedgerItem[] }>("get", "/api/v1/admin/ledger");

export const createLedgerItem = (payload: LedgerCreatePayload) =>
  http.request<LedgerItem>("post", "/api/v1/admin/ledger", { data: payload });

export const markSold = (itemId: number, payload: MarkSoldPayload) =>
  http.request<LedgerItem>("patch", `/api/v1/admin/ledger/${itemId}/sold`, {
    data: payload
  });

export const deleteLedgerItem = (itemId: number) =>
  http.request("delete", `/api/v1/admin/ledger/${itemId}`);

export const setDistributions = (
  itemId: number,
  payload: DistributionsPayload
) =>
  http.request<{ distributions: ProfitDistribution[] }>(
    "post",
    `/api/v1/admin/ledger/${itemId}/distributions`,
    { data: payload }
  );

export const getInvestors = () =>
  http.request<{ investors: Investor[] }>("get", "/api/v1/admin/investors");

export const createInvestor = (payload: InvestorCreatePayload) =>
  http.request<Investor>("post", "/api/v1/admin/investors", { data: payload });

export const addContribution = (
  investorId: number,
  payload: ContributionPayload
) =>
  http.request(
    "post",
    `/api/v1/admin/investors/${investorId}/contributions`,
    { data: payload }
  );

export const getInvestorsSummary = () =>
  http.request<{ investors: InvestorSummary[] }>(
    "get",
    "/api/v1/admin/investors/summary"
  );
