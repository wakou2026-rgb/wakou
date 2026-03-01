import { http } from "@/utils/http";

export type ShipmentSummary = {
  order_id: number;
  buyer_email: string;
  product_name: string;
  order_status: string;
  latest_status: string | null;
  latest_title: string | null;
  latest_event_time: string | null;
  event_count: number;
};

export type ShipmentEvent = {
  order_id: number;
  status: string;
  title: string;
  description: string | null;
  location: string | null;
  event_time: string;
};

export type ShipmentEventPayload = {
  status: string;
  title: string;
  description?: string;
  location?: string;
  event_time?: string;
};

export type OrderShipmentDetail = {
  order_id: number;
  product_name: string;
  buyer_email: string;
  events: ShipmentEvent[];
};

export const getShipments = () => {
  return http.request<{ items: ShipmentSummary[] }>("get", "/api/v1/admin/shipments");
};

export const getOrderShipmentEvents = (orderId: number) => {
  return http.request<OrderShipmentDetail>("get", `/api/v1/admin/orders/${orderId}/shipment-events`);
};

export const addShipmentEvent = (orderId: number, payload: ShipmentEventPayload) => {
  return http.request<ShipmentEvent>("post", `/api/v1/admin/orders/${orderId}/shipment-events`, {
    data: payload
  });
};
