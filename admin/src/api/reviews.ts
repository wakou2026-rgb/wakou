import { http } from "@/utils/http";

export type Review = {
  id: number;
  buyer_email: string;
  product_id: number;
  rating: number;
  comment: string;
  hidden: boolean;
};

export const getReviews = () => {
  return http.request<Review[]>("get", "/api/v1/admin/reviews");
};

export const toggleReviewHidden = (id: number) => {
  return http.request("patch", `/api/v1/admin/reviews/${id}`);
};
