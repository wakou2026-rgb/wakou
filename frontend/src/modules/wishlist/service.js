import { handleUnauthorizedResponse } from "../auth/session";

function getAccessToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("wakou_access_token") || "";
}

function authHeaders() {
  return { Authorization: `Bearer ${getAccessToken()}` };
}

function normalizeListPayload(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.items)) {
    return payload.items;
  }
  return [];
}

export async function getWishlist() {
  const response = await fetch("/api/v1/wishlist", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error(`load wishlist failed (${response.status})`);
  }
  const data = await response.json();
  return normalizeListPayload(data);
}

export async function getWishlistProducts() {
  const response = await fetch("/api/v1/wishlist/products", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error(`load wishlist products failed (${response.status})`);
  }
  const data = await response.json();
  return normalizeListPayload(data);
}

export async function addToWishlist(productId) {
  const response = await fetch(`/api/v1/wishlist/${productId}`, {
    method: "POST",
    headers: authHeaders()
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error(`add to wishlist failed (${response.status})`);
  }
  return response.json();
}

export async function removeFromWishlist(productId) {
  const response = await fetch(`/api/v1/wishlist/${productId}`, {
    method: "DELETE",
    headers: authHeaders()
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error(`remove from wishlist failed (${response.status})`);
  }
  return response.json();
}
