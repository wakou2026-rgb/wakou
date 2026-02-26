function getAccessToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("wakou_access_token") || "";
}

function authHeaders() {
  const token = getAccessToken();
  return { Authorization: `Bearer ${token}` };
}

function buildHttpError(action, status) {
  const error = new Error(`${action} failed (${status})`);
  error.status = status;
  return error;
}

export async function fetchMyOrders() {
  const response = await fetch("/api/v1/orders/me", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load orders", response.status);
  }
  return response.json();
}

export async function fetchMyCommRooms() {
  const response = await fetch("/api/v1/comm-rooms/me", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load communication rooms", response.status);
  }
  return response.json();
}

export async function updateMyDisplayName(displayName) {
  const response = await fetch("/api/v1/users/me", {
    method: "PATCH",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ display_name: displayName })
  });
  if (!response.ok) {
    throw buildHttpError("update profile", response.status);
  }
  return response.json();
}

export async function fetchDashboardConfig() {
  const response = await fetch("/api/v1/users/dashboard-config", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load dashboard config", response.status);
  }
  return response.json();
}

export async function fetchUserGrowth() {
  const response = await fetch("/api/v1/users/growth", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load growth center", response.status);
  }
  return response.json();
}

export async function fetchPrivateSalon() {
  const response = await fetch("/api/v1/users/private-salon", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load private salon", response.status);
  }
  return response.json();
}

export async function markNotificationsRead(lastEventId) {
  const response = await fetch("/api/v1/users/notifications/read", {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ last_event_id: Number(lastEventId || 0) })
  });
  if (!response.ok) {
    throw buildHttpError("mark notifications read", response.status);
  }
  return response.json();
}

export async function createReview(payload) {
  const response = await fetch("/api/v1/reviews", {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`create review failed (${response.status})`);
  }
  return response.json();
}

export async function fetchMyCoupons() {
  const response = await fetch("/api/v1/users/coupons", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load coupons", response.status);
  }
  return response.json();
}

export async function fetchGachaStatus() {
  const response = await fetch("/api/v1/gacha/status", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load gacha status", response.status);
  }
  return response.json();
}

export async function performGachaDraw(poolId) {
  const body = {};
  if (poolId) body.pool_id = poolId;
  const response = await fetch("/api/v1/gacha/draw", {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw buildHttpError("gacha draw", response.status);
  }
  return response.json();
}
