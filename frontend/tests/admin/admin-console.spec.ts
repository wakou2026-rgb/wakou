import { describe, expect, it } from "vitest";
import {
  createProduct,
  createSeedOrder,
  fetchAdminConsoleConfig,
  fetchAdminOrders,
  fetchAdminOverview,
  fetchAdminProducts,
  fetchAdminUsers,
  fetchAdminMagazines,
  updateOrderStatus
} from "../../src/modules/admin/service";

describe("admin console", () => {
  it("admin can create product and update order status", () => {
    const product = createProduct({ sku: "WK-001", grade: "A", priceTwd: 12800 });
    const order = createSeedOrder();
    const updated = updateOrderStatus(order.id, "paid");

    expect(product.sku).toBe("WK-001");
    expect(updated.status).toBe("paid");
  });

  it("fetches admin console config payload", async () => {
    const fetchMock = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/v1/admin/console-config") {
        return new Response(
          JSON.stringify({
            role: "admin",
            menu: [{ key: "dashboard", title: "儀表板" }],
            feature_flags: { can_manage_products: true }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response("not found", { status: 404 });
    }) as typeof fetch;

    const data = await fetchAdminConsoleConfig();
    expect(data.role).toBe("admin");
    expect(data.menu[0].key).toBe("dashboard");

    globalThis.fetch = fetchMock;
  });

  it("fetches admin overview datasets", async () => {
    const fetchMock = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      if (typeof input !== "string") {
        return new Response("not found", { status: 404 });
      }
      if (input === "/api/v1/admin/overview") {
        return new Response(
          JSON.stringify({ metrics: { total_orders: 2 }, recent_orders: [{ id: 1, status: "paid" }] }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (input === "/api/v1/admin/orders") {
        return new Response(JSON.stringify({ items: [{ id: 1, status: "paid" }] }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }
      if (input === "/api/v1/admin/products") {
        return new Response(JSON.stringify({ items: [{ id: 1, sku: "WK-001" }] }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }
      if (input === "/api/v1/admin/users") {
        return new Response(JSON.stringify({ items: [{ email: "test@example.com" }] }), {
          status: 200, headers: { "Content-Type": "application/json" }
        });
      }
      if (input === "/api/v1/magazines") {
        return new Response(JSON.stringify({ items: [{ brand: "Rolex", contents: [] }] }), {
          status: 200, headers: { "Content-Type": "application/json" }
        });
      }
      return new Response("not found", { status: 404 });
    }) as typeof fetch;

    const [overview, orders, products, users, mags] = await Promise.all([
      fetchAdminOverview(),
      fetchAdminOrders(),
      fetchAdminProducts(),
      fetchAdminUsers(),
      fetchAdminMagazines()
    ]);
    expect(overview.metrics.total_orders).toBe(2);
    expect(orders.items[0].id).toBe(1);
    expect(products.items[0].sku).toBe("WK-001");
    expect(users.items[0].email).toBe("test@example.com");
    expect(mags.items[0].brand).toBe("Rolex");

    globalThis.fetch = fetchMock;
  });
});
