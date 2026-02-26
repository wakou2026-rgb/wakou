export async function fetchWarehouseTimeline() {
  const response = await fetch("/api/v1/warehouse/timeline", { method: "GET" });
  if (!response.ok) {
    throw new Error("load warehouse timeline failed");
  }
  const data = await response.json();
  return data.items;
}
