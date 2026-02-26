const products = [];
const orders = [];
let nextProductId = 1;
let nextOrderId = 1;

function getAccessToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("wakou_access_token") || "";
}

async function parseJsonResponse(response, errorPrefix) {
  if (!response.ok) {
    throw new Error(`${errorPrefix} (${response.status})`);
  }
  return response.json();
}

async function parseTextResponse(response, errorPrefix) {
  if (!response.ok) {
    throw new Error(`${errorPrefix} (${response.status})`);
  }
  return response.text();
}

export async function createProductApi(payload) {
  const response = await fetch("/api/v1/admin/products", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "create product failed");
}

export async function exportOrdersCsv() {
  const response = await fetch("/api/v1/admin/orders/export.csv", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseTextResponse(response, "export orders failed");
}

export async function fetchAdminConsoleConfig() {
  const response = await fetch("/api/v1/admin/console-config", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin console config failed");
}

export async function fetchAdminOverview() {
  const response = await fetch("/api/v1/admin/overview", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin overview failed");
}

export async function fetchAdminOrders() {
  const response = await fetch("/api/v1/admin/orders", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin orders failed");
}

export async function fetchAdminProducts() {
  const response = await fetch("/api/v1/admin/products", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin products failed");
}

export async function updateAdminProduct(productId, payload) {
  const response = await fetch(`/api/v1/admin/products/${productId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "update admin product failed");
}

export async function deleteAdminProduct(productId) {
  const response = await fetch(`/api/v1/admin/products/${productId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "delete admin product failed");
}

export function createProduct(payload) {
  const product = {
    id: nextProductId,
    sku: payload.sku,
    grade: payload.grade,
    priceTwd: payload.priceTwd
  };
  nextProductId += 1;
  products.push(product);
  return product;
}

export function createSeedOrder() {
  const order = {
    id: nextOrderId,
    status: "created"
  };
  nextOrderId += 1;
  orders.push(order);
  return order;
}

export function updateOrderStatus(orderId, status) {
  const target = orders.find((item) => item.id === orderId);
  if (!target) {
    throw new Error("order not found");
  }
  target.status = status;
  return target;
}

export async function fetchAdminUsers() {
  const response = await fetch("/api/v1/admin/users", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin users failed");
}

export async function fetchAdminMagazines() {
  const response = await fetch("/api/v1/magazines", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin magazines failed");
}

export async function fetchAdminMagazineArticles() {
  const response = await fetch("/api/v1/admin/magazines/articles", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin magazine articles failed");
}

export async function createAdminMagazineArticle(payload) {
  const response = await fetch("/api/v1/admin/magazines/articles", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "create magazine article failed");
}

export async function updateAdminMagazineArticle(articleId, payload) {
  const response = await fetch(`/api/v1/admin/magazines/articles/${articleId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "update magazine article failed");
}

export async function deleteAdminMagazineArticle(articleId) {
  const response = await fetch(`/api/v1/admin/magazines/articles/${articleId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "delete magazine article failed");
}

export async function fetchAdminCosts() {
  const response = await fetch("/api/v1/admin/costs", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin costs failed");
}

export async function createAdminCost(payload) {
  const response = await fetch("/api/v1/admin/costs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "create admin cost failed");
}

export async function fetchAdminPointsPolicy() {
  const response = await fetch("/api/v1/admin/points-policy", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load points policy failed");
}

export async function updateAdminPointsPolicy(payload) {
  const response = await fetch("/api/v1/admin/points-policy", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "update points policy failed");
}

export async function fetchAdminReportSummary() {
  const response = await fetch("/api/v1/admin/report/summary", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load report summary failed");
}

export async function fetchAdminReviews() {
  const response = await fetch("/api/v1/admin/reviews", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin reviews failed");
}

export async function updateAdminReview(reviewId, payload) {
  const response = await fetch(`/api/v1/admin/reviews/${reviewId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "update admin review failed");
}

export async function fetchAdminWorkflowQueues() {
  const response = await fetch("/api/v1/admin/workflow-queues", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load workflow queues failed");
}

export async function patchAdminOrderStatus(orderId, payload) {
  const response = await fetch(`/api/v1/admin/orders/${orderId}/status`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "update order status failed");
}

export async function fetchAdminEvents() {
  const response = await fetch("/api/v1/admin/events", {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load admin events failed");
}

export async function markAdminEventsRead(lastEventId) {
  const response = await fetch("/api/v1/admin/events/read", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ last_event_id: lastEventId })
  });
  return parseJsonResponse(response, "mark events read failed");
}

export async function fetchBuyerHistory(email) {
  const response = await fetch(`/api/v1/admin/crm/buyers/${encodeURIComponent(email)}/history`, {
    method: "GET",
    headers: { Authorization: `Bearer ${getAccessToken()}` }
  });
  return parseJsonResponse(response, "load buyer history failed");
}

export async function addBuyerNote(email, payload) {
  const response = await fetch(`/api/v1/admin/crm/buyers/${encodeURIComponent(email)}/notes`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "add buyer note failed");
}

export async function rewardBuyerPoints(email, payload) {
  const response = await fetch(`/api/v1/admin/crm/buyers/${encodeURIComponent(email)}/reward`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse(response, "reward buyer failed");
}
