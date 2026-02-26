import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

import HomeView from "../../src/app/views/HomeView.vue";

describe("home discover section", () => {
  it("links latest journal and arrival cards to real detail routes", async () => {
    const fetchMock = globalThis.fetch;

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      if (typeof input === "string" && input.startsWith("/api/v1/magazines")) {
        return new Response(
          JSON.stringify({
            articles: [
              {
                article_id: 7,
                slug: "spring-story",
                title: { "zh-Hant": "春季特刊" },
                published_at: "2026-02-20",
                image_url: "https://cdn.example.com/mag-7.jpg"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      if (typeof input === "string" && input.startsWith("/api/v1/products")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 22,
                sku: "WK-22",
                category: "outer",
                name: "Nanamica Gore-Tex",
                description: "desc",
                image_urls: ["https://cdn.example.com/p-22.jpg"],
                price_twd: 24000,
                grade: "A"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      return new Response("not found", { status: 404 });
    }) as typeof fetch;

    const wrapper = mount(HomeView, {
      global: {
        mocks: {
          $t: (key: string) => key
        },
        stubs: {
          RouterLink: {
            props: ["to"],
            template: '<a :href="to"><slot /></a>'
          }
        }
      }
    });

    await flushPromises();

    const journalLink = wrapper.find('a[href="/magazine/7-spring-story"]');
    expect(journalLink.exists()).toBe(true);

    const arrivalLink = wrapper.find('a[href="/catalog/22"]');
    expect(arrivalLink.exists()).toBe(true);

    globalThis.fetch = fetchMock;
  });
});
