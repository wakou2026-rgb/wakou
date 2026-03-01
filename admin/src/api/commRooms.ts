import { http } from "@/utils/http";

export type CommMessage = {
  id: number;
  from: string;
  sender_email: string;
  message: string;
  image_url: string | null;
  timestamp: string;
};

export type CommRoomOrder = {
  id: number;
  amount_twd: number;
  discount_twd: number;
  final_price_twd: number | null;
  shipping_fee_twd: number;
  final_amount_twd: number | null;
  shipping_carrier: string | null;
  tracking_number: string | null;
  status: string;
};

export type CommRoom = {
  id: number;
  order_id: number;
  buyer_email: string;
  product_id: number | null;
  product_name: string;
  status: string;
  final_price_twd: number | null;
  shipping_fee_twd: number | null;
  discount_twd: number;
  created_at: string;
  messages: CommMessage[];
  order?: CommRoomOrder;
};

export type NotificationConfig = {
  discord_webhook_url: string;
  line_notify_token: string;
  email_recipients: string;
};

export const getCommRooms = () =>
  http.request<CommRoom[]>("get", "/api/v1/admin/comm-rooms");

export const getCommRoom = (id: number) =>
  http.request<CommRoom>("get", `/api/v1/admin/comm-rooms/${id}`);

export const postAdminMessage = (id: number, message: string) =>
  http.request("post", `/api/v1/admin/comm-rooms/${id}/messages`, {
    data: { message, from: "admin" }
  });

export const setRoomStatus = (id: number, status: string) =>
  http.request("patch", `/api/v1/admin/comm-rooms/${id}/status`, {
    data: { status }
  });

export const setFinalQuote = (
  id: number,
  data: {
    final_price_twd: number;
    shipping_fee_twd: number;
    discount_twd?: number;
    shipping_carrier?: string;
    tracking_number?: string;
  }
) =>
  http.request("post", `/api/v1/comm-rooms/${id}/final-quote`, { data });

export const getNotificationConfig = () =>
  http.request<NotificationConfig>(
    "get",
    "/api/v1/admin/comm-rooms/notification-config"
  );

export const saveNotificationConfig = (data: Partial<NotificationConfig>) =>
  http.request("post", "/api/v1/admin/comm-rooms/notification-config", {
    data
  });
