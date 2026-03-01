import { http } from "@/utils/http";

export type CostEntry = {
  id: number;
  title: string;
  /** legacy alias kept for form compat */
  category?: string;
  amount_twd: number;
  /** legacy alias */
  amount?: number;
  note: string;
  recorded_at: string;
  product_id?: number | null;
  cost_type?: string;
};

export type ReportSummary = {
  total_revenue: number;
  total_cost: number;
  profit_margin: number;
  profit_twd?: number;
  order_count?: number;
};

export type MonthlyReport = {
  month: string | number;
  revenue: number;
  cost: number;
  profit?: number;
};

export type CategoryBreakdownItem = {
  category: string;
  total: number;
  count: number;
};

export const getCosts = async () => {
  const res = await http.request<any>("get", "/api/v1/admin/costs");
  const items = ((res as any).items ?? (res as any).data ?? res ?? []) as any[];
  // normalize: expose both amount_twd and legacy amount alias
  return items.map(c => ({ ...c, amount: c.amount_twd })) as CostEntry[];
};

export const addCost = (data: Partial<CostEntry>) =>
  http.request<CostEntry>("post", "/api/v1/admin/costs", {
    data: {
      title: (data as any).category ?? data.title ?? "",
      amount_twd: data.amount_twd ?? (data as any).amount ?? 0,
      recorded_at: data.recorded_at ?? new Date().toISOString().slice(0, 10),
      product_id: data.product_id ?? null,
      cost_type: data.cost_type ?? "misc",
    },
  });

export const getReportSummary = async () => {
  const res = await http.request<any>("get", "/api/v1/admin/report/summary");
  const raw = (res as any).data ?? res;
  if (raw?.totals) {
    const t = raw.totals;
    const margin =
      t.revenue_twd > 0
        ? Math.round(((t.revenue_twd - t.cost_twd) / t.revenue_twd) * 100)
        : 0;
    return {
      total_revenue: t.revenue_twd,
      total_cost: t.cost_twd,
      profit_margin: margin,
      profit_twd: t.profit_twd ?? t.revenue_twd - t.cost_twd,
      order_count: t.order_count ?? 0,
    } as ReportSummary;
  }
  return raw as ReportSummary;
};

export const getMonthlyReport = async () => {
  const res = await http.request<any>("get", "/api/v1/admin/report/monthly");
  const raw = (res as any).data ?? res;
  const months = raw?.months ?? raw ?? [];
  return months.map((m: any) => ({
    month: m.month,
    revenue: m.income_twd ?? m.revenue ?? 0,
    cost: m.cost_twd ?? m.cost ?? 0,
    profit: m.profit ?? 0,
  })) as MonthlyReport[];
};

export const getCategoryBreakdown = async () => {
  const res = await http.request<any>(
    "get",
    "/api/v1/admin/report/category-breakdown"
  );
  const raw = (res as any).data ?? res;
  const items = (raw?.items ?? []) as any[];
  return items.map(i => ({ ...i, total: Number(i.total) })) as CategoryBreakdownItem[];
};

export type RevenueEntry = {
  id: number;
  title: string;
  amount_twd: number;
  recorded_at: string;
  note?: string;
  type?: string;
};

export const addRevenue = (data: Partial<RevenueEntry>) =>
  http.request<RevenueEntry>("post", "/api/v1/admin/revenue", {
    data: {
      title: data.title ?? "",
      amount_twd: data.amount_twd ?? 0,
      recorded_at: data.recorded_at ?? new Date().toISOString().slice(0, 10),
      note: data.note ?? "",
    },
  });
