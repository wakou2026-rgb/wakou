export const MEMBERSHIP_TIERS = [
  { key: "entry", name: "初見", threshold: 0, perks: ["一般會員權益"] },
  { key: "first", name: "生日禮遇", threshold: 20000, perks: ["生日禮金 NT$ 500"] },
  { key: "second", name: "免運會員", threshold: 50000, perks: ["免運券 1 張"] },
  { key: "third", name: "尊榮會員", threshold: 150000, perks: ["全站 95 折", "不限次數免運"] }
];

function isSettledOrder(status) {
  return status === "paid" || status === "completed";
}

function computeTotalFromOrders(orders) {
  const rows = Array.isArray(orders) ? orders : [];
  return rows.reduce((sum, item) => {
    if (!isSettledOrder(String(item?.status || ""))) {
      return sum;
    }
    const amount = Number(item?.final_amount_twd ?? item?.amount_twd ?? 0);
    return sum + (Number.isFinite(amount) ? amount : 0);
  }, 0);
}

function resolveTierBySpent(totalSpentTwd) {
  let current = MEMBERSHIP_TIERS[0];
  let next = null;

  for (const tier of MEMBERSHIP_TIERS) {
    if (totalSpentTwd >= tier.threshold) {
      current = tier;
      continue;
    }
    next = tier;
    break;
  }

  return {
    current,
    next,
    remainingTwd: next ? Math.max(next.threshold - totalSpentTwd, 0) : 0
  };
}

function resolveTrackProgress(totalSpentTwd) {
  const maxThreshold = MEMBERSHIP_TIERS[MEMBERSHIP_TIERS.length - 1].threshold;
  if (maxThreshold <= 0) {
    return 0;
  }
  return Math.max(0, Math.min((totalSpentTwd / maxThreshold) * 100, 100));
}

function resolveTierBenefits(totalSpentTwd) {
  const unlocked = MEMBERSHIP_TIERS.filter((tier) => totalSpentTwd >= tier.threshold);
  return unlocked.flatMap((tier) => tier.perks);
}

export function shouldClearUnreadOnRoute(path) {
  return /^\/dashboard\/messages(?:$|[/?#])/.test(String(path || ""));
}

export function deriveMembershipSnapshot({ membership, orders } = {}) {
  const payload = membership || {};
  const fallbackSpent = computeTotalFromOrders(orders);
  const payloadSpent = Number(payload?.total_spent_twd);
  const totalSpentTwd = Number.isFinite(payloadSpent) && payloadSpent >= 0 ? payloadSpent : fallbackSpent;

  const tierInfo = resolveTierBySpent(totalSpentTwd);
  const level = tierInfo.current.name;
  const nextLevel = tierInfo.next?.name || null;

  const payloadRemaining = Number(payload?.remaining_twd);
  const remainingTwd = Number.isFinite(payloadRemaining) && payloadRemaining >= 0
    ? payloadRemaining
    : tierInfo.remainingTwd;

  const upgradeHint = nextLevel
    ? `再消費 NT$ ${Number(remainingTwd || 0).toLocaleString()} 可升級至 ${nextLevel}`
    : "已達最高會員等級";

  const tierProgressPct = resolveTrackProgress(totalSpentTwd);
  const unlockedPerks = resolveTierBenefits(totalSpentTwd);

  return {
    tierKey: tierInfo.current.key,
    tiers: MEMBERSHIP_TIERS,
    level,
    totalSpentTwd,
    nextLevel,
    remainingTwd,
    upgradeHint,
    tierProgressPct,
    unlockedPerks,
  };
}
