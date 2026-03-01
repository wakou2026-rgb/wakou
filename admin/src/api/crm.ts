import { http } from "@/utils/http";

export type User = {
  email: string;
  role: string;
  display_name: string;
};

export type BuyerHistory = {
  orders: any[];
  notes: any[];
};

export const getUsers = () => {
  return http.request<User[]>("get", "/api/v1/admin/users");
};

export const getBuyerHistory = (email: string) => {
  return http.request<BuyerHistory>("get", `/api/v1/admin/crm/buyers/${email}/history`);
};

export const addBuyerNote = (email: string, note: string) => {
  return http.request("post", `/api/v1/admin/crm/buyers/${email}/notes`, { data: { note } });
};

export const awardBuyerPoints = (email: string, points: number) => {
  return http.request("post", `/api/v1/admin/crm/buyers/${email}/reward`, { data: { points } });
};


export type CommMessage = {
  id: number;
  from: string;
  sender_email: string;
  message: string;
  image_url: string | null;
  timestamp: string;
};

export type CommRoom = {
  id: number;
  order_id: number;
  buyer_email: string;
  product_id: number | null;
  product_name: string;
  status: string;
  messages: CommMessage[];
};

export const getCommRoom = (roomId: number) =>
  http.request<CommRoom>("get", `/api/v1/admin/comm-rooms/${roomId}`);

export const postCommMessage = (roomId: number, message: string) =>
  http.request("post", `/api/v1/admin/comm-rooms/${roomId}/messages`, {
    data: { message, from: "admin" }
  });

export const setCommRoomStatus = (roomId: number, status: string) =>
  http.request("patch", `/api/v1/admin/comm-rooms/${roomId}/status`, {
    data: { status }
  });