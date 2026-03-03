const AUTH_KEYS = [
  "wakou_access_token",
  "wakou_refresh_token",
  "wakou_email",
  "wakou_display_name",
  "wakou_role"
];

function hasWindow() {
  return typeof window !== "undefined";
}

export function clearStoredAuth() {
  if (!hasWindow()) {
    return;
  }
  for (const key of AUTH_KEYS) {
    window.localStorage.removeItem(key);
  }
}

export function notifyAuthExpired() {
  if (!hasWindow()) {
    return;
  }
  window.dispatchEvent(new CustomEvent("wakou-auth-expired"));
}

export function handleUnauthorizedResponse(response) {
  if (response.status !== 401) {
    return false;
  }
  clearStoredAuth();
  notifyAuthExpired();
  return true;
}
