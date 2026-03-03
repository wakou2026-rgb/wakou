import { describe, expect, it, vi } from "vitest";

import { fetchPublicMagazines } from "../../src/modules/catalog/service";

describe("fetchPublicMagazines", () => {
  it("normalizes grouped items payload into flat articles", async () => {
    const fetchMock = globalThis.fetch;
    globalThis.fetch = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          items: [
            {
              brand: "Rolex",
              contents: [
                {
                  article_id: 11,
                  slug: "rolex-inside",
                  brand: "Rolex",
                  title: { "zh-Hant": "Rolex 特刊" },
                  description: { "zh-Hant": "編輯內容" },
                  image_url: "https://cdn.example.com/mag-11.jpg",
                  published: true
                }
              ]
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }) as typeof fetch;

    const data = await fetchPublicMagazines();

    expect(Array.isArray(data.articles)).toBe(true);
    expect(data.articles).toHaveLength(1);
    expect(data.articles[0].article_id).toBe(11);
    expect(data.articles[0].slug).toBe("rolex-inside");

    globalThis.fetch = fetchMock;
  });
});
