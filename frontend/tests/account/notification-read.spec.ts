import { describe, expect, it } from "vitest";

import { markNotificationsRead } from "../../src/modules/account/service";
import { shouldClearUnreadOnRoute } from "../../src/modules/account/membership";

describe("notification read behavior", () => {
  it("clears unread only on messages route", () => {
    expect(shouldClearUnreadOnRoute("/dashboard/messages")).toBe(true);
    expect(shouldClearUnreadOnRoute("/dashboard/orders")).toBe(false);
  });

  it("sends last_event_id to read endpoint", async () => {
    const fetchMock = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/v1/users/notifications/read") {
        expect(init?.method).toBe("POST");
        expect(init?.body).toBe(JSON.stringify({ last_event_id: 99 }));
        return new Response(JSON.stringify({ ok: true, last_event_id: 99 }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }
      return new Response("not found", { status: 404 });
    }) as typeof fetch;

    const result = await markNotificationsRead(99);
    expect(result.ok).toBe(true);
    expect(result.last_event_id).toBe(99);

    globalThis.fetch = fetchMock;
  });
});
