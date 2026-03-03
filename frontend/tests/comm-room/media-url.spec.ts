import { describe, expect, it } from "vitest";

import { normalizeMediaUrl } from "../../src/modules/comm-room/media-url";

describe("normalizeMediaUrl", () => {
  it("keeps absolute http URL", () => {
    expect(normalizeMediaUrl("https://example.com/proof.jpg")).toBe("https://example.com/proof.jpg");
  });

  it("normalizes uploads path without leading slash", () => {
    expect(normalizeMediaUrl("uploads/proofs/a.jpg")).toBe("/uploads/proofs/a.jpg");
  });

  it("normalizes protocol-relative URL", () => {
    expect(normalizeMediaUrl("//cdn.example.com/proof.jpg")).toBe("https://cdn.example.com/proof.jpg");
  });

  it("returns empty string for invalid URL", () => {
    expect(normalizeMediaUrl("123")).toBe("");
  });
});
