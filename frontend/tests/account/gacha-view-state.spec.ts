import { describe, expect, it } from "vitest";
import { hasCouponReward, shouldForceLogin } from "../../src/modules/account/gacha-view-state";

describe("gacha view state helpers", () => {
  it("detects auth failures from status-bearing errors", () => {
    const error = Object.assign(new Error("gacha draw failed (401)"), { status: 401 });
    expect(shouldForceLogin(error)).toBe(true);
  });

  it("detects auth failures from error message", () => {
    expect(shouldForceLogin(new Error("load failed (401)"))).toBe(true);
  });

  it("returns false for non-auth errors", () => {
    expect(shouldForceLogin(new Error("draw failed (400)"))).toBe(false);
  });

  it("detects coupon rewards in draw results", () => {
    const results = [
      { label: "再抽一次", coupon: null, is_redraw: true },
      { label: "-100", coupon: { id: 1 }, is_redraw: false }
    ];
    expect(hasCouponReward(results)).toBe(true);
  });
});
