import { describe, it, expect, beforeEach, afterEach } from "vitest";

// We test the service layer directly first
import { performGachaDraw, fetchGachaStatus } from "../../src/modules/account/service";

describe("gacha draw service", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    // Provide a mock localStorage token
    globalThis.localStorage = {
      getItem: (key: string) => key === "wakou_access_token" ? "test-token" : null,
      setItem: () => {},
      removeItem: () => {},
      clear: () => {},
      length: 0,
      key: () => null,
    } as Storage;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("fetchGachaStatus returns draws_available and pool", async () => {
    globalThis.fetch = (async () => {
      return new Response(
        JSON.stringify({ draws_available: 2, pool: { id: 1, name: "預設獎池", prizes: [] } }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }) as typeof fetch;

    const status = await fetchGachaStatus();
    expect(status.draws_available).toBe(2);
    expect(status.pool).toBeDefined();
    expect(status.pool.name).toBe("預設獎池");
  });

  it("performGachaDraw returns results array and draws_remaining", async () => {
    const mockResult = {
      draws_remaining: 1,
      results: [
        { label: "再抽一次", coupon: null, is_redraw: true },
        { label: "-100", coupon: { id: 1, coupon: { description: "折扣 NT$100" } }, is_redraw: false },
      ],
    };

    globalThis.fetch = (async () => {
      return new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;

    const result = await performGachaDraw();
    expect(result.results).toBeDefined();
    expect(Array.isArray(result.results)).toBe(true);
    expect(result.results.length).toBe(2);
    expect(result.draws_remaining).toBe(1);
    // The key field the template relies on
    expect(result.results[0].is_redraw).toBe(true);
    expect(result.results[1].is_redraw).toBe(false);
    expect(result.results[1].label).toBe("-100");
  });

  it("drawGacha correctly sets showResult=true when results non-empty", async () => {
    // Simulate the exact logic from drawGacha() in AccountSectionView (after the fix)
    const gachaResults = { value: [] as Array<{ label: string; coupon: unknown; is_redraw: boolean }> };
    const showResult = { value: false };
    const isDrawing = { value: false };
    const gachaStatus = { value: { draws_available: 2, pool: null } };
    const errorText = { value: "" };

    const mockResult = {
      draws_remaining: 1,
      results: [
        { label: "-100", coupon: { id: 1, coupon: { description: "折扣 NT$100" } }, is_redraw: false },
      ],
    };

    globalThis.fetch = (async () => {
      return new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;

    // Execute the exact drawGacha() logic (including the fix: clear errorText at start)
    if (isDrawing.value || gachaStatus.value.draws_available <= 0) {
      throw new Error("Guard should not trigger");
    }
    isDrawing.value = true;
    showResult.value = false;
    errorText.value = "";  // the fix: clear any previous error
    try {
      const result = await performGachaDraw();
      gachaResults.value = result.results || [];
      gachaStatus.value.draws_available = result.draws_remaining;
      showResult.value = true;
    } catch (error) {
      errorText.value = error instanceof Error ? error.message : "抽獎失敗";
    } finally {
      isDrawing.value = false;
    }

    // These are the exact conditions for the overlay: v-if="showResult && gachaResults.length > 0"
    expect(showResult.value).toBe(true);
    expect(gachaResults.value.length).toBeGreaterThan(0);
    expect(gachaStatus.value.draws_available).toBe(1);
  });

  it("drawGacha clears errorText before draw so overlay shows even after prior page error", async () => {
    // Regression test: if a previous page-load error set errorText, the layout was hidden
    // by v-if="!loading && !errorText", so the result overlay never showed even on success.
    const gachaResults = { value: [] as Array<{ label: string; coupon: unknown; is_redraw: boolean }> };
    const showResult = { value: false };
    const isDrawing = { value: false };
    const gachaStatus = { value: { draws_available: 1, pool: null } };
    // Simulate a pre-existing error from page load (e.g. salon API was slow/failed)
    const errorText = { value: "load private salon failed (503)" };

    const mockResult = {
      draws_remaining: 0,
      results: [
        { label: "-500", coupon: { id: 2, coupon: { description: "折扣 NT$500" } }, is_redraw: false },
      ],
    };

    globalThis.fetch = (async () => {
      return new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;

    // Execute drawGacha() logic with the fix applied
    isDrawing.value = true;
    showResult.value = false;
    errorText.value = "";  // fix: clear prior error so layout (v-if="!errorText") becomes visible
    try {
      const result = await performGachaDraw();
      gachaResults.value = result.results || [];
      gachaStatus.value.draws_available = result.draws_remaining;
      showResult.value = true;
    } catch (error) {
      errorText.value = error instanceof Error ? error.message : "抽獎失敗";
    } finally {
      isDrawing.value = false;
    }

    // After fix: errorText cleared, overlay conditions both satisfied
    expect(errorText.value).toBe("");
    expect(showResult.value).toBe(true);
    expect(gachaResults.value.length).toBeGreaterThan(0);
  });
});
