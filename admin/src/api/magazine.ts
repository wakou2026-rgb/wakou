import { http } from "@/utils/http";

export type LocaleText = {
  "zh-Hant"?: string;
  zh_hant?: string;
  ja?: string;
  en?: string;
  [key: string]: string | undefined;
};

/** Get zh-Hant text regardless of key format (hyphen or underscore). */
export const zhHant = (locale: LocaleText | undefined): string => {
  if (!locale) return "";
  return locale["zh-Hant"] ?? locale["zh_hant"] ?? "";
};

export type Article = {
  article_id: number;
  slug: string;
  brand: string;
  title: LocaleText;
  description: LocaleText;
  body: LocaleText;
  image_url: string;
  gallery_urls: string[];
  published: boolean;
  sort_order: number;
  created_at: string;
  layout_blocks?: any[];
};

export type ArticleListResponse = {
  items: Article[];
  total: number;
};

export const getArticles = () => {
  return http.request<ArticleListResponse>("get", "/api/v1/admin/magazines/articles");
};

export const createArticle = (data: any) => {
  return http.request<Article>("post", "/api/v1/admin/magazines/articles", { data });
};

export const updateArticle = (id: number, data: any) => {
  return http.request<Article>("patch", `/api/v1/admin/magazines/articles/${id}`, { data });
};

export const deleteArticle = (id: number) => {
  return http.request("delete", `/api/v1/admin/magazines/articles/${id}`);
};

export const toggleArticlePublish = (id: number, published: boolean) => {
  return http.request("patch", `/api/v1/admin/magazines/articles/${id}/publish`, {
    params: { published }
  });
};
