import { beforeEach, describe, expect, it, vi } from "vitest";

import { createOrder } from "../../src/modules/checkout/service";
import { getWishlist } from "../../src/modules/wishlist/service";
import { fetchCommRoom, uploadTransferProofFile } from "../../src/modules/comm-room/service";

describe("auth expiry handling", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("wakou_access_token", "stale-token");
    window.localStorage.setItem("wakou_refresh_token", "stale-refresh");
    window.localStorage.setItem("wakou_email", "stale@example.com");
    window.localStorage.setItem("wakou_display_name", "stale");
    window.localStorage.setItem("wakou_role", "buyer");
  });

  it("clears stored auth and emits event when createOrder gets 401", async () => {
    const fetchMock = globalThis.fetch;
    const eventSpy = vi.fn();
    window.addEventListener("wakou-auth-expired", eventSpy);
    globalThis.fetch = vi.fn(async () => new Response("unauthorized", { status: 401 })) as typeof fetch;

    await expect(createOrder({ product_id: 1, mode: "inquiry" })).rejects.toThrow("login required");

    expect(window.localStorage.getItem("wakou_access_token")).toBeNull();
    expect(window.localStorage.getItem("wakou_refresh_token")).toBeNull();
    expect(eventSpy).toHaveBeenCalledTimes(1);

    window.removeEventListener("wakou-auth-expired", eventSpy);
    globalThis.fetch = fetchMock;
  });

  it("clears stored auth when wishlist fetch gets 401", async () => {
    const fetchMock = globalThis.fetch;
    globalThis.fetch = vi.fn(async () => new Response("unauthorized", { status: 401 })) as typeof fetch;

    await expect(getWishlist()).rejects.toThrow("login required");

    expect(window.localStorage.getItem("wakou_access_token")).toBeNull();
    expect(window.localStorage.getItem("wakou_role")).toBeNull();

    globalThis.fetch = fetchMock;
  });

  it("clears stored auth and emits event when comm-room fetch gets 401", async () => {
    const fetchMock = globalThis.fetch;
    const eventSpy = vi.fn();
    window.addEventListener("wakou-auth-expired", eventSpy);
    globalThis.fetch = vi.fn(async () => new Response("unauthorized", { status: 401 })) as typeof fetch;

    await expect(fetchCommRoom(99)).rejects.toThrow("login required");

    expect(window.localStorage.getItem("wakou_access_token")).toBeNull();
    expect(window.localStorage.getItem("wakou_refresh_token")).toBeNull();
    expect(eventSpy).toHaveBeenCalledTimes(1);

    window.removeEventListener("wakou-auth-expired", eventSpy);
    globalThis.fetch = fetchMock;
  });

  it("clears stored auth and emits event when proof file upload gets 401", async () => {
    const fetchMock = globalThis.fetch;
    const eventSpy = vi.fn();
    window.addEventListener("wakou-auth-expired", eventSpy);
    globalThis.fetch = vi.fn(async () => new Response("unauthorized", { status: 401 })) as typeof fetch;

    const file = new File(["dummy"], "proof.png", { type: "image/png" });
    await expect(uploadTransferProofFile(99, file)).rejects.toThrow("login required");

    expect(window.localStorage.getItem("wakou_access_token")).toBeNull();
    expect(window.localStorage.getItem("wakou_refresh_token")).toBeNull();
    expect(eventSpy).toHaveBeenCalledTimes(1);

    window.removeEventListener("wakou-auth-expired", eventSpy);
    globalThis.fetch = fetchMock;
  });
});
