// ---------------------------------------------------------------------------
// Admin console service – thin wrappers around the admin API endpoints.
// ---------------------------------------------------------------------------

/** Locally create a product stub (used for in-memory/test scenarios). */
export function createProduct(params: {
  sku: string;
  grade: string;
  priceTwd: number;
}) {
  return {
    id: Date.now(),
    sku: params.sku,
    grade: params.grade,
    priceTwd: params.priceTwd,
    status: "draft",
  };
}

/** Create a seed order stub (used for in-memory/test scenarios). */
export function createSeedOrder() {
  return {
    id: Date.now(),
    status: "waiting_quote",
    buyerEmail: "seed@example.com",
    amountTwd: 10000,
  };
}

/** Locally update order status (used for in-memory/test scenarios). */
export function updateOrderStatus(orderId: number, newStatus: string) {
  return {
    id: orderId,
    status: newStatus,
  };
}

// ---------------------------------------------------------------------------
// Async fetch helpers
// ---------------------------------------------------------------------------

async function jsonGet(url: string) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`fetch ${url} failed (${response.status})`);
  }
  return response.json();
}

export async function fetchAdminConsoleConfig() {
  return jsonGet("/api/v1/admin/console-config");
}

export async function fetchAdminOverview() {
  return jsonGet("/api/v1/admin/overview");
}

export async function fetchAdminOrders() {
  return jsonGet("/api/v1/admin/orders");
}

export async function fetchAdminProducts() {
  return jsonGet("/api/v1/admin/products");
}

export async function fetchAdminUsers() {
  return jsonGet("/api/v1/admin/users");
}

export async function fetchAdminMagazines() {
  return jsonGet("/api/v1/magazines");
}
