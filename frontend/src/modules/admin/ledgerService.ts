const BASE = "/api/v1/admin";

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem("wakou_access_token") || ""
      : "";
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function apiGet(url: string) {
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error(`fetch ${url} failed (${res.status})`);
  return res.json();
}

async function apiPost(url: string, body: unknown) {
  const res = await fetch(url, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`post ${url} failed (${res.status})`);
  return res.json();
}

async function apiPatch(url: string, body: unknown) {
  const res = await fetch(url, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`patch ${url} failed (${res.status})`);
  return res.json();
}

async function apiDelete(url: string) {
  const res = await fetch(url, { method: "DELETE", headers: authHeaders() });
  if (!res.ok) throw new Error(`delete ${url} failed (${res.status})`);
}

// ── Ledger ──────────────────────────────────────────────────────────────────

export async function fetchLedger() {
  return apiGet(`${BASE}/ledger`);
}

export async function createLedgerItem(payload: {
  item_name: string;
  purchase_date: string;
  cost_jpy: number;
  exchange_rate: number;
  expected_price_twd?: number;
  grade?: string;
  box_and_papers?: string;
  location?: string;
  source?: string;
  customer_source?: string;
  note?: string;
  order_id?: number | null;
}) {
  return apiPost(`${BASE}/ledger`, payload);
}

export async function markItemSold(itemId: number, actual_price_twd: number, order_id?: number | null) {
  return apiPatch(`${BASE}/ledger/${itemId}/sold`, { actual_price_twd, order_id });
}

export async function deleteLedgerItem(itemId: number) {
  return apiDelete(`${BASE}/ledger/${itemId}`);
}

export async function setDistributions(
  itemId: number,
  distributions: Array<{ investor_id: number | null; label: string; amount_twd: number }>
) {
  return apiPost(`${BASE}/ledger/${itemId}/distributions`, { distributions });
}

// ── Investors ────────────────────────────────────────────────────────────────

export async function fetchInvestors() {
  return apiGet(`${BASE}/investors`);
}

export async function createInvestor(name: string, note?: string) {
  return apiPost(`${BASE}/investors`, { name, note: note ?? "" });
}

export async function addContribution(investorId: number, payload: {
  amount_twd: number;
  contributed_at: string;
  note?: string;
}) {
  return apiPost(`${BASE}/investors/${investorId}/contributions`, payload);
}

export async function fetchInvestorSummary() {
  return apiGet(`${BASE}/investors/summary`);
}
