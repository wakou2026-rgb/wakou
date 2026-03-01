import { http } from "@/utils/http";

export type Category = {
  id: string;
  title: { "zh-Hant": string; ja: string; en: string };
  image: string;
  sort_order: number;
  is_active: boolean;
};

export const getCategories = () =>
  http.request<Category[]>("get", "/api/v1/admin/categories");

export const createCategory = (data: Partial<Category>) =>
  http.request<Category>("post", "/api/v1/admin/categories", { data });

export const updateCategory = (id: string, data: Partial<Category>) =>
  http.request<Category>("patch", `/api/v1/admin/categories/${id}`, { data });

export const deleteCategory = (id: string) =>
  http.request("delete", `/api/v1/admin/categories/${id}`);
