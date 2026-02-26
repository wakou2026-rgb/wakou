import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useAuthStore } from "../../src/modules/auth/store";

describe("auth login", () => {
  it("login stores jwt token and redirects to home", async () => {
    const fetchMock = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/v1/auth/login") {
        expect(init?.method).toBe("POST");
        return new Response(
          JSON.stringify({ access_token: "token-1", refresh_token: "refresh-1" }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (typeof input === "string" && input === "/api/v1/auth/me") {
        expect(init?.method).toBe("GET");
        expect(init?.headers).toBeTruthy();
        return new Response(JSON.stringify({ email: "user@example.com", role: "buyer" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }
      return new Response("not found", { status: 404 });
    }) as typeof fetch;

    setActivePinia(createPinia());
    const store = useAuthStore();

    let redirectedTo = "";
    await store.login(
      { email: "user@example.com", password: "Pass123!" },
      { push: (path: string) => { redirectedTo = path; } }
    );

    expect(store.accessToken).toBe("token-1");
    expect(store.refreshToken).toBe("refresh-1");
    expect(store.email).toBe("user@example.com");
    expect(redirectedTo).toBe("/");

    globalThis.fetch = fetchMock;
  });
});
