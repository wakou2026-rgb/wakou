import { http } from "@/utils/http";

export type Event = {
  id: number;
  actor: string;
  action: string;
  target: string;
  created_at: string;
};

export const getEvents = () => {
  return http.request<Event[]>("get", "/api/v1/admin/events");
};

export const markEventsRead = () => {
  return http.request("post", "/api/v1/admin/events/read");
};
