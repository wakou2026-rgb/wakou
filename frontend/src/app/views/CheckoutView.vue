<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { getCartItems, clearCartItems } from "../../modules/cart/service";
import { createOrder, createEcpayPayment } from "../../modules/checkout/service";

const router = useRouter();
const checkoutForm = reactive({ mode: "inquiry" });
const statusText = ref("");
const isError = ref(false);
const isSubmitting = ref(false);
const cartItems = computed(() => getCartItems() || []);

function getAuthHeaders() {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("wakou_access_token") || "" : "";
  return { Authorization: `Bearer ${token}` };
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

const availableCoupons = ref([]);
const selectedCouponId = ref(null);
const pointsToRedeem = ref(0);
const userPointsBalance = ref(0);

onMounted(async () => {
  try {
    const orderAmount = cartItems.value[0]?.priceTwd || cartItems.value[0]?.price_twd || 0;
    const [couponResp, growthResp] = await Promise.all([
      fetch("/api/v1/users/coupons/available?order_amount_twd=" + orderAmount, { headers: getAuthHeaders() }).then(r => r.json()),
      fetch("/api/v1/users/growth", { headers: getAuthHeaders() }).then(r => r.json()),
    ]);
    availableCoupons.value = couponResp.items || [];
    userPointsBalance.value = growthResp.points?.balance || 0;
  } catch { /* non-critical */ }
});

async function submitCheckout() {
  const items = getCartItems();
  if (!items || items.length === 0) {
    isError.value = true;
    statusText.value = "購物車為空。";
    return;
  }

  isError.value = false;
  statusText.value = "";
  isSubmitting.value = true;
  try {
    const created = await createOrder({
      product_id: items[0].id,
      mode: checkoutForm.mode,
      coupon_id: selectedCouponId.value,
      points_to_redeem: pointsToRedeem.value,
    });

    if (checkoutForm.mode === "buy_now") {
      const payment = await createEcpayPayment(created.order_id);
      statusText.value = `訂單建立完成，準備付款資料：${payment.payload}`;
      clearCartItems();
      return;
    } else {
      const commRoomId = Number(created?.comm_room_id ?? created?.commRoomId ?? 0);
      if (!Number.isInteger(commRoomId) || commRoomId <= 0) {
        throw new Error("create order succeeded but missing comm room id");
      }
      statusText.value = `訂單建立完成，正在進入專屬溝通室 #${commRoomId}...`;

      clearCartItems();
      setTimeout(async () => {
        await router.push(`/comm-room/${commRoomId}?from=dashboard`);
      }, 1200);
      return;
    }
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "結帳失敗";
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <div class="checkout-page container">
    <header class="page-header">
      <p class="eyebrow">Transaction Protocol</p>
      <h1 class="page-title">交易流程</h1>
      <p class="page-meta">先建立訂單，再由我們提供細節照與最終運費，確認後再進行付款。</p>
    </header>

    <div class="checkout-grid">
      <section class="protocol panel">
        <h2>四步驟確認機制</h2>
        <ol>
          <li class="active"><span>01</span><div><strong>建立訂單</strong><p>保留藏品並建立對話室。</p></div></li>
          <li><span>02</span><div><strong>細節確認</strong><p>職人提供近照與最終運費。</p></div></li>
          <li><span>03</span><div><strong>買家確認</strong><p>確認細節與費用後回覆同意。</p></div></li>
          <li><span>04</span><div><strong>安全付款</strong><p>導向 ECPay 完成付款。</p></div></li>
        </ol>
      </section>

      <section class="action panel">
        <h2>建立交易</h2>

        <div class="mode-list">
          <button
            class="mode"
            :class="{ active: checkoutForm.mode === 'inquiry' }"
            type="button"
            @click="checkoutForm.mode = 'inquiry'"
          >
            <strong>先溝通確認</strong>
            <p>先看細節照與運費，再決定付款。</p>
          </button>

          <button
            class="mode"
            :class="{ active: checkoutForm.mode === 'buy_now' }"
            type="button"
            @click="checkoutForm.mode = 'buy_now'"
          >
            <strong>直接結帳</strong>
            <p>直接建立付款流程，節省等待時間。</p>
          </button>
        </div>

        <!-- Coupon & Points Section -->
        <div class="discount-section" v-if="availableCoupons.length > 0 || userPointsBalance > 0">
          <h3>優惠折抵</h3>

          <!-- Coupon selection -->
          <div v-if="availableCoupons.length > 0" class="coupon-select">
            <label>選擇折扣券</label>
            <select v-model="selectedCouponId">
              <option :value="null">不使用折扣券</option>
              <option v-for="c in availableCoupons" :key="c.id" :value="c.id">
                {{ c.coupon.description }} (有效至 {{ formatDate(c.expires_at) }})
              </option>
            </select>
          </div>

          <!-- Points redemption -->
          <div v-if="userPointsBalance > 0" class="points-redeem">
            <label>使用回饋點數 (可用 {{ userPointsBalance }} 點)</label>
            <input type="number" v-model.number="pointsToRedeem" :max="userPointsBalance" min="0" />
            <small>1 點 = NT$1 折抵</small>
          </div>
        </div>

        <div class="action-footer">
          <RouterLink class="btn btn-muted w-full" to="/collections">繼續選購</RouterLink>
          <button class="btn btn-primary w-full" type="button" :disabled="isSubmitting || cartItems.length === 0" @click="submitCheckout">
            {{ isSubmitting ? "處理中..." : "確認並建立訂單" }}
          </button>
          <p v-if="statusText" class="status-msg" :class="isError ? 'status-err' : 'status-ok'">{{ statusText }}</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.checkout-page {
  max-width: 1200px;
}

.checkout-grid {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: 1.1fr 1fr;
}

.protocol h2,
.action h2 {
  margin-bottom: 1.3rem;
}

.protocol ol {
  display: grid;
  gap: 1.1rem;
  list-style: none;
}

.protocol li {
  border-bottom: 1px solid var(--paper-300);
  display: grid;
  gap: 1rem;
  grid-template-columns: 2.1rem 1fr;
  opacity: 0.55;
  padding-bottom: 1rem;
}

.protocol li.active {
  opacity: 1;
}

.protocol li span {
  color: var(--accent-700);
  font-family: var(--font-serif);
  font-size: 1.5rem;
}

.protocol li p {
  color: var(--ink-600);
  margin: 0;
}

.mode-list {
  display: grid;
  gap: 0.8rem;
}

.mode {
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid var(--paper-300);
  cursor: pointer;
  display: grid;
  gap: 0.35rem;
  padding: 1rem;
  text-align: left;
}

.mode.active {
  border-color: var(--ink-900);
}

.mode p {
  color: var(--ink-600);
  margin: 0;
}

.action-footer {
  display: grid;
  gap: 0.75rem;
  margin-top: 1.3rem;
}

.w-full {
  width: 100%;
}

.status-msg {
  margin: 0;
}

.discount-section {
  border: 1px solid var(--paper-300);
  display: grid;
  gap: 0.8rem;
  margin-top: 1rem;
  padding: 1rem;
}

.discount-section h3 {
  color: #182a47;
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.coupon-select,
.points-redeem {
  display: grid;
  gap: 0.3rem;
}

.coupon-select label,
.points-redeem label {
  color: #324867;
  font-size: 0.88rem;
}

.coupon-select select {
  background: #fff;
  border: 1px solid #d4d9df;
  color: #1b2740;
  font-size: 0.9rem;
  padding: 0.5rem;
  width: 100%;
}

.points-redeem input {
  background: #fff;
  border: 1px solid #d4d9df;
  color: #1b2740;
  font-size: 0.9rem;
  padding: 0.5rem;
  width: 100%;
}

.points-redeem small {
  color: #7a8a9e;
  font-size: 0.78rem;
}

@media (max-width: 900px) {
  .checkout-grid {
    grid-template-columns: 1fr;
  }
}
</style>
