import { describe, expect, it } from "vitest";

import { fetchDashboardConfig } from "../../src/modules/account/service";

describe("dashboard config", () => {
  it("loads account navigation config", async () => {
    const fetchMock = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/v1/users/dashboard-config") {
        return new Response(
          JSON.stringify({
            account_nav: [{ key: "orders", title: "訂單歷史" }],
            quick_links: [{ key: "catalog", label: "繼續選購", path: "/catalog" }],
            role: "buyer"
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response("not found", { status: 404 });
    }) as typeof fetch;

    const result = await fetchDashboardConfig();
    expect(result.account_nav[0].key).toBe("orders");
    expect(result.role).toBe("buyer");

    globalThis.fetch = fetchMock;
  });
});
