import { http } from "@/utils/http";

export type Order = {
  id: number;
  buyer_email: string;
  status: string;
  amount_twd: number;
  created_at: string;
};

export const getOrders = () => {
  return http.request<Order[]>("get", "/api/v1/admin/orders");
};

export const updateOrderStatus = (id: number, status: string) => {
  return http.request("patch", `/api/v1/admin/orders/${id}/status`, { data: { status } });
};

export const exportOrdersCsv = () => {
  return http.request("get", "/api/v1/admin/orders/export.csv", {
    responseType: "blob"
  });
};
