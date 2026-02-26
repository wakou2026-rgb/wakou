import { beforeEach, describe, expect, it, vi } from "vitest";
import { createOrder } from "../../src/modules/checkout/service";

describe("createOrder", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.setItem("wakou_access_token", "token-123");
  });

  it("normalizes legacy payload keys before posting", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ order_id: 99 })
    } as Response);

    await createOrder({
      productId: "3",
      mode: "inquiry",
      couponId: "2",
      pointsToRedeem: "15"
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = fetchMock.mock.calls[0];
    expect(options?.method).toBe("POST");
    expect(options?.body).toBe(
      JSON.stringify({
        product_id: 3,
        mode: "inquiry",
        coupon_id: 2,
        points_to_redeem: 15
      })
    );
  });

  it("rejects invalid product id before network call", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");

    await expect(
      createOrder({
        mode: "inquiry",
        coupon_id: null,
        points_to_redeem: 0
      })
    ).rejects.toThrow("create order failed (invalid product id)");

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
