import { http } from "@/utils/http";

export interface Product {
  id: number;
  sku: string;
  category: string;
  name: string | { "zh-Hant": string; ja: string; en: string };
  description: string;
  description_zh?: string;
  description_ja?: string;
  description_en?: string;
  image_urls: string[];
  preview_images?: string[];
  detail_images?: string[];
  price_twd: number;
  grade: string;
  availability: string;
  tags: string[];
  brand?: string;
  size?: string;
  stock_qty?: number;
  cost_twd?: number;
}

export const getProducts = (params?: { q?: string }) => {
  return http.request<any>("get", "/api/v1/admin/products", { params });
};

export const createProduct = (data: Partial<Product>) => {
  return http.request<any>("post", "/api/v1/admin/products", { data });
};

export const updateProduct = (id: number, data: Partial<Product>) => {
  return http.request<any>("patch", `/api/v1/admin/products/${id}`, { data });
};

export const deleteProduct = (id: number) => {
  return http.request("delete", `/api/v1/admin/products/${id}`);
};
