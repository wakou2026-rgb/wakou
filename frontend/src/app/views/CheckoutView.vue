<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { getCartItems, clearCartItems } from "../../modules/cart/service";
import { createOrder, createEcpayPayment } from "../../modules/checkout/service";

const router = useRouter();
const { t } = useI18n();
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

const product = computed(() => cartItems.value[0] || null);
const productName = computed(() => {
  const n = product.value?.name;
  if (!n) return "商品";
  if (typeof n === "string") return n;
  return n["zh-Hant"] || n["en"] || Object.values(n)[0] || "商品";
});
const productPrice = computed(() => Number(product.value?.priceTwd || product.value?.price_twd || 0));
const productImage = computed(() => {
  const urls = product.value?.imageUrls || product.value?.image_urls || [];
  return urls[0] || "/logo-transparent.png";
});

const selectedCoupon = computed(() => {
  if (!selectedCouponId.value) return null;
  return availableCoupons.value.find(c => c.id === selectedCouponId.value) || null;
});

const couponDiscount = computed(() => {
  const c = selectedCoupon.value;
  if (!c) return 0;
  const t = c.coupon;
  if (t.type === "fixed") return t.value;
  if (t.type === "percentage") return productPrice.value - Math.floor(productPrice.value * t.value / 100);
  return 0;
});

const pointsDiscount = computed(() => {
  const pts = Math.max(0, Math.min(pointsToRedeem.value || 0, userPointsBalance.value));
  return pts;
});

const totalDiscount = computed(() => couponDiscount.value + pointsDiscount.value);
const finalAmount = computed(() => Math.max(productPrice.value - totalDiscount.value, 0));

function formatCurrency(value) {
  return `NT$ ${Number(value || 0).toLocaleString()}`;
}

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
    statusText.value = t("checkout.cart_empty_msg");
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
    statusText.value = error instanceof Error ? error.message : t("checkout.checkout_failed");
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <div class="checkout-page container">
    <header class="page-header">
      <p class="eyebrow">Transaction Protocol</p>
      <h1 class="page-title">{{ $t('checkout.title') }}</h1>
      <p class="page-meta">{{ $t('checkout.subtitle') }}</p>
    </header>

    <div class="checkout-grid">
      <!-- Order Summary -->
      <section class="order-summary panel" v-if="product">
        <h2>{{ $t('checkout.order_summary') }}</h2>
        <div class="summary-product">
          <img :src="productImage" :alt="productName" class="summary-thumb" />
          <div class="summary-info">
            <p class="summary-name">{{ productName }}</p>
            <p class="summary-price">{{ formatCurrency(productPrice) }}</p>
          </div>
        </div>

        <div class="price-breakdown">
          <div class="breakdown-row">
            <span>{{ $t('checkout.product_amount') }}</span>
            <span>{{ formatCurrency(productPrice) }}</span>
          </div>
          <div class="breakdown-row discount" v-if="couponDiscount > 0">
            <span>{{ $t('checkout.coupon_discount_label') }} ({{ selectedCoupon.coupon.description }})</span>
            <span>-{{ formatCurrency(couponDiscount) }}</span>
          </div>
          <div class="breakdown-row discount" v-if="pointsDiscount > 0">
            <span>{{ $t('checkout.points_deduction_label') }} ({{ pointsDiscount }} 點)</span>
            <span>-{{ formatCurrency(pointsDiscount) }}</span>
          </div>
          <div class="breakdown-row total">
            <span>{{ $t('checkout.estimated_amount') }}</span>
            <span>{{ formatCurrency(finalAmount) }}</span>
          </div>
          <p class="breakdown-note">{{ $t('checkout.final_note') }}</p>
        </div>
      </section>

      <section class="protocol panel">
        <h2>{{ $t('checkout.steps_title') }}</h2>
        <ol>
          <li class="active"><span>01</span><div><strong>{{ $t('checkout.step1_title') }}</strong><p>{{ $t('checkout.step1_desc') }}</p></div></li>
          <li><span>02</span><div><strong>{{ $t('checkout.step2_title') }}</strong><p>{{ $t('checkout.step2_desc') }}</p></div></li>
          <li><span>03</span><div><strong>{{ $t('checkout.step3_title') }}</strong><p>{{ $t('checkout.step3_desc') }}</p></div></li>
          <li><span>04</span><div><strong>{{ $t('checkout.step4_title') }}</strong><p>{{ $t('checkout.step4_desc') }}</p></div></li>
        </ol>
      </section>

      <section class="action panel">
        <h2>{{ $t('checkout.create_order') }}</h2>

        <div class="mode-list">
          <button
            class="mode"
            :class="{ active: checkoutForm.mode === 'inquiry' }"
            type="button"
            @click="checkoutForm.mode = 'inquiry'"
          >
            <strong>{{ $t('checkout.mode_inquiry_title') }}</strong>
            <p>{{ $t('checkout.mode_inquiry_desc') }}</p>
          </button>

          <button
            class="mode"
            :class="{ active: checkoutForm.mode === 'buy_now' }"
            type="button"
            @click="checkoutForm.mode = 'buy_now'"
          >
            <strong>{{ $t('checkout.mode_buynow_title') }}</strong>
            <p>{{ $t('checkout.mode_buynow_desc') }}</p>
          </button>
        </div>

        <!-- Coupon & Points Section (always show if coupons or points exist) -->
        <div class="discount-section" v-if="availableCoupons.length > 0 || userPointsBalance > 0">
          <h3>{{ $t('checkout.discount_section') }}</h3>

          <!-- Coupon selection -->
          <div v-if="availableCoupons.length > 0" class="coupon-select">
            <label>{{ $t('checkout.select_coupon') }}</label>
            <select v-model="selectedCouponId">
              <option :value="null">{{ $t('checkout.no_coupon') }}</option>
              <option v-for="c in availableCoupons" :key="c.id" :value="c.id">
                {{ c.coupon.description }} ({{ $t('checkout.valid_until') }} {{ formatDate(c.expires_at) }})
              </option>
            </select>
            <p v-if="selectedCoupon" class="coupon-effect">
              折扣 <strong>{{ formatCurrency(couponDiscount) }}</strong>
            </p>
          </div>

          <!-- Points redemption -->
          <div v-if="userPointsBalance > 0" class="points-redeem">
            <label>{{ $t('checkout.use_points', { n: userPointsBalance }) }}</label>
            <input type="number" v-model.number="pointsToRedeem" :max="userPointsBalance" min="0" />
            <small>{{ $t('checkout.points_rate') }}</small>
          </div>

          <!-- Inline discount summary -->
          <div v-if="totalDiscount > 0" class="discount-total">
            <span>{{ $t('checkout.total_discount') }}</span>
            <strong>{{ formatCurrency(totalDiscount) }}</strong>
          </div>
        </div>

        <div class="action-footer">
          <RouterLink class="btn btn-muted w-full" to="/collections">{{ $t('checkout.continue_shopping') }}</RouterLink>
          <button class="btn btn-primary w-full" type="button" :disabled="isSubmitting || cartItems.length === 0" @click="submitCheckout">
            {{ isSubmitting ? $t('checkout.processing') : $t('checkout.confirm_btn') }}
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
  grid-template-columns: 1fr 1fr;
}

.order-summary h2,
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

.order-summary {
  grid-column: 1 / -1;
}

.summary-product {
  display: flex;
  gap: 1rem;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--paper-300);
  margin-bottom: 1rem;
}

.summary-thumb {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid var(--paper-300);
  background: #f3f4f6;
}

.summary-info {
  display: grid;
  gap: 0.25rem;
}

.summary-name {
  font-weight: 600;
  color: var(--ink-900);
  margin: 0;
  font-size: 1.05rem;
}

.summary-price {
  color: var(--accent-700);
  font-family: var(--font-serif);
  font-size: 1.2rem;
  font-weight: 700;
  margin: 0;
}

.price-breakdown {
  display: grid;
  gap: 0.5rem;
}

.breakdown-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.95rem;
  color: var(--ink-700);
}

.breakdown-row.discount {
  color: #16a34a;
}

.breakdown-row.total {
  border-top: 2px solid var(--ink-900);
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--ink-900);
  padding-top: 0.5rem;
  margin-top: 0.25rem;
}

.breakdown-note {
  color: var(--ink-500);
  font-size: 0.78rem;
  margin: 0.25rem 0 0;
}

.coupon-effect {
  color: #16a34a;
  font-size: 0.88rem;
  margin: 0.2rem 0 0;
}

.discount-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 0.8rem;
  background: rgba(22, 163, 74, 0.06);
  border: 1px solid rgba(22, 163, 74, 0.2);
  border-radius: 4px;
  color: #16a34a;
  font-size: 0.95rem;
}


@media (max-width: 900px) {
  .checkout-grid {
    grid-template-columns: 1fr;
  }
}
</style>
