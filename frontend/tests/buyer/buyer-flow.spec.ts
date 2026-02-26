import { describe, expect, it } from "vitest";

import { browseCatalog } from "../../src/modules/catalog/service";
import { createCart } from "../../src/modules/cart/service";
import { checkoutInquiry } from "../../src/modules/checkout/service";
import { fetchCommRoom } from "../../src/modules/comm-room/service";

describe("buyer flow", () => {
  it("buyer can browse add to cart checkout and open comm room", async () => {
    const fetchMock = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      if (typeof input === "string" && input.startsWith("/api/v1/products")) {
        return new Response(
          JSON.stringify({
            items: [{ id: 99, sku: "API-ONLY", name: "From API", price_twd: 777, grade: "S" }]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (typeof input === "string" && input.startsWith("/api/v1/comm-rooms/123")) {
         return new Response(
          JSON.stringify({
            id: 123
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );       
      }
      return new Response("not found", { status: 404 });
    }) as typeof fetch;

    const products = await browseCatalog();
    const cart = createCart();
    cart.add(products[0]);

    const order = checkoutInquiry(cart.items());
    order.commRoomId = 123;
    const room = await fetchCommRoom(order.commRoomId);

    expect(products.length).toBeGreaterThan(0);
    expect(products[0].sku).toBe("API-ONLY");
    expect(order.status).toBe("waiting_quote");
    expect(room.id).toBe(order.commRoomId);

    globalThis.fetch = fetchMock;
  });
});
