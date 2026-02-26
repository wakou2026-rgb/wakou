let nextOrderId = 1;
let nextRoomId = 1;

function getAccessToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("wakou_access_token") || "";
}

export async function createOrder(payload) {
  const token = getAccessToken();
  const productId = Number(payload?.product_id ?? payload?.productId ?? payload?.id);
  if (!Number.isInteger(productId) || productId <= 0) {
    throw new Error("create order failed (invalid product id)");
  }

  const mode = payload?.mode;
  if (mode !== "inquiry" && mode !== "buy_now") {
    throw new Error("create order failed (invalid mode)");
  }

  const couponRaw = payload?.coupon_id ?? payload?.couponId;
  const couponId = couponRaw == null || couponRaw === "" ? null : Number(couponRaw);
  const normalizedCouponId = Number.isInteger(couponId) && couponId > 0 ? couponId : null;

  const pointsRaw = Number(payload?.points_to_redeem ?? payload?.pointsToRedeem ?? 0);
  const pointsToRedeem = Number.isFinite(pointsRaw) && pointsRaw > 0 ? Math.trunc(pointsRaw) : 0;

  const response = await fetch("/api/v1/orders", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      product_id: productId,
      mode,
      coupon_id: normalizedCouponId,
      points_to_redeem: pointsToRedeem
    })
  });
  if (!response.ok) {
    throw new Error("create order failed");
  }
  return response.json();
}

export async function createEcpayPayment(orderId) {
  const token = getAccessToken();
  const response = await fetch(`/api/v1/payments/ecpay/${orderId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) {
    throw new Error("create payment failed");
  }
  return response.json();
}

export function checkoutInquiry(items) {
  if (items.length === 0) {
    throw new Error("cart is empty");
  }
  const orderId = nextOrderId;
  nextOrderId += 1;
  const commRoomId = nextRoomId;
  nextRoomId += 1;

  return {
    orderId,
    commRoomId,
    status: "waiting_quote"
  };
}
