import { http } from "@/utils/http";

export type DashboardMetrics = {
  total_orders?: number;
  revenue?: number;
  pending_orders?: number;
  active_products?: number;
  total_products?: number;
};

export type DashboardOverviewResult = {
  metrics?: DashboardMetrics;
} & DashboardMetrics;

export type DashboardRecentOrder = {
  id: number;
  buyer_email: string;
  product_name?: string;
  status: string;
  amount_twd?: number;
  final_amount_twd?: number;
  created_at: string;
};

export type OrderStatusStat = {
  status: string;
  count: number;
};

const normalizeOrders = (res: any): DashboardRecentOrder[] => {
  if (Array.isArray(res)) return res;
  if (Array.isArray(res?.items)) return res.items;
  if (Array.isArray(res?.data)) return res.data;
  return [];
};

export const getDashboardOverview = () => {
  return http.request<DashboardOverviewResult>("get", "/api/v1/admin/overview");
};

export const getRecentOrders = async () => {
  const res = await http.request<any>(
    "get",
    "/api/v1/admin/orders?limit=5&sort=-created_at"
  );
  return normalizeOrders(res);
};

export const getOrderStatusStats = async () => {
  const res = await http.request<any>(
    "get",
    "/api/v1/admin/orders?limit=100&sort=-created_at"
  );
  const orders = normalizeOrders(res);
  const map = new Map<string, number>();
  orders.forEach(order => {
    map.set(order.status, (map.get(order.status) ?? 0) + 1);
  });

  return Array.from(map.entries()).map(([status, count]) => ({
    status,
    count
  })) as OrderStatusStat[];
};
