import { http } from "@/utils/http";

export type Event = {
  id: number;
  actor_email?: string;
  actor_role?: string;
  event_type?: string;
  title?: string;
  detail?: string;
  order_id?: number | null;
  room_id?: number | null;
  created_at: string;
};

export const getEvents = () => {
  return http.request<Event[]>("get", "/api/v1/admin/events");
};

export const markEventsRead = () => {
  return http.request("post", "/api/v1/admin/events/read");
};
