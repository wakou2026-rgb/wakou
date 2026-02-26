import { describe, expect, it } from "vitest";

import { deriveMembershipSnapshot } from "../../src/modules/account/membership";

describe("membership progress snapshot", () => {
  it("uses membership payload and computes next-tier reminder", () => {
    const snapshot = deriveMembershipSnapshot({
      membership: {
        total_spent_twd: 52000,
        remaining_twd: 98000
      },
      orders: []
    });

    expect(snapshot.level).toBe("免運會員");
    expect(snapshot.totalSpentTwd).toBe(52000);
    expect(snapshot.nextLevel).toBe("尊榮會員");
    expect(snapshot.remainingTwd).toBe(98000);
    expect(snapshot.upgradeHint).toContain("再消費 NT$ 98,000");
    expect(snapshot.unlockedPerks).toContain("免運券 1 張");
  });

  it("falls back to paid/completed orders when total_spent_twd is missing", () => {
    const snapshot = deriveMembershipSnapshot({
      membership: {
        level: "初見"
      },
      orders: [
        { status: "completed", final_amount_twd: 12000 },
        { status: "paid", amount_twd: 9000 },
        { status: "waiting_quote", final_amount_twd: 999999 }
      ]
    });

    expect(snapshot.totalSpentTwd).toBe(21000);
    expect(snapshot.level).toBe("生日禮遇");
    expect(snapshot.nextLevel).toBe("免運會員");
    expect(snapshot.remainingTwd).toBe(29000);
  });
});
