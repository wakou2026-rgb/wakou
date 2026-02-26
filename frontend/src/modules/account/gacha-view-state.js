export function shouldForceLogin(error) {
  if (!error || typeof error !== "object") {
    return false;
  }

  const status = Number(error.status || 0);
  if (status === 401) {
    return true;
  }

  const message = error instanceof Error ? error.message : "";
  return message.includes("(401)");
}

export function hasCouponReward(results) {
  if (!Array.isArray(results)) {
    return false;
  }
  return results.some((item) => Boolean(item?.coupon));
}
