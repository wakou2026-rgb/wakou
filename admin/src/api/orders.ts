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

export const refundOrder = (orderId: string, reason: string) => {
  return http.request("post", `/api/v1/admin/orders/${orderId}/refund`, { data: { reason } });
};

export const bulkUpdateOrderStatus = (orderIds: string[], status: string) => {
  return http.request("patch", "/api/v1/admin/orders/bulk-status", {
    data: { order_ids: orderIds, status }
  });
};

export const exportOrdersCsv = () => {
  return http.request("get", "/api/v1/admin/orders/export.csv", {
    responseType: "blob"
  });
};
