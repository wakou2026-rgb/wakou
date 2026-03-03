const ABSOLUTE_URL_PATTERN = /^https?:\/\//i;
const DOMAIN_LIKE_PATTERN = /^[a-z0-9.-]+\.[a-z]{2,}(\/.*)?$/i;

export function normalizeMediaUrl(rawUrl: unknown): string {
  const value = typeof rawUrl === "string" ? rawUrl.trim() : "";
  if (!value) {
    return "";
  }

  if (value.startsWith("data:") || value.startsWith("blob:")) {
    return value;
  }

  if (ABSOLUTE_URL_PATTERN.test(value)) {
    return value;
  }

  if (value.startsWith("//")) {
    return `https:${value}`;
  }

  if (value.startsWith("/")) {
    return value;
  }

  if (value.startsWith("uploads/")) {
    return `/${value}`;
  }

  if (DOMAIN_LIKE_PATTERN.test(value)) {
    return `https://${value}`;
  }

  return "";
}
