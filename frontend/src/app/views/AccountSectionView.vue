<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../../modules/auth/store";
import { fetchPrivateSalon, markNotificationsRead, fetchMyCoupons, fetchGachaStatus, performGachaDraw } from "../../modules/account/service";
import { deriveMembershipSnapshot, shouldClearUnreadOnRoute } from "../../modules/account/membership";
import { hasCouponReward, shouldForceLogin } from "../../modules/account/gacha-view-state";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const loading = ref(true);
const errorText = ref("");
const salon = ref({
  timeline: [],
  rooms: [],
  orders: [],
  notifications: { items: [] },
  privileges: [],
  points: { items: [] },
  membership: { level: "初見", total_spent_twd: 0, next_level: null, remaining_twd: 0 },
});

const sectionMeta = {
  timeline: {
    title: "交易時間軸",
    subtitle: "Purchase history",
  },
  rooms: {
    title: "我的諮詢室",
    subtitle: "Consultation rooms",
  },
  orders: {
    title: "我的訂單",
    subtitle: "Order history",
  },
  messages: {
    title: "通知中心",
    subtitle: "Notifications",
  },
  coupons: {
    title: "我的折扣券",
    subtitle: "My coupons",
  },
  gacha: {
    title: "幸運抽獎",
    subtitle: "Lucky draw",
  },
  points: {
    title: "回饋點數紀錄",
    subtitle: "Point history",
  },
};

const section = computed(() => String(route.params.section || "timeline"));
const meta = computed(() => sectionMeta[section.value] || sectionMeta.timeline);
const navItems = [
  { key: "timeline", label: "交易時間軸", en: "Purchase history" },
  { key: "rooms", label: "我的諮詢室", en: "Consultation rooms" },
  { key: "orders", label: "我的訂單", en: "Order history" },
  { key: "messages", label: "通知中心", en: "Notifications" },
  { key: "coupons", label: "我的折扣券", en: "My coupons" },
  { key: "gacha", label: "幸運抽獎", en: "Lucky draw" },
  { key: "points", label: "回饋點數紀錄", en: "Point history" },
];

const sectionItems = computed(() => {
  if (section.value === "timeline") return salon.value.timeline || [];
  if (section.value === "rooms") return salon.value.rooms || [];
  if (section.value === "orders") return salon.value.orders || [];
  if (section.value === "messages") return salon.value.notifications?.items || [];
  if (section.value === "points") return salon.value.points?.items || [];
  return [];
});

const membershipSnapshot = computed(() => deriveMembershipSnapshot({
  membership: salon.value.membership,
  orders: salon.value.orders
}));

const coupons = ref([]);
const gachaStatus = ref({ draws_available: 0, pool: null });
const gachaResults = ref([]);
const isDrawing = ref(false);
const showResult = ref(false);

function syncUnreadStorage(unread) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem("wakou_unread_count", String(Number(unread || 0)));
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function formatCurrency(value) {
  return `NT$ ${Number(value || 0).toLocaleString()}`;
}

function openRoom(roomId) {
  const id = Number(roomId);
  if (!Number.isInteger(id) || id <= 0) return;
  router.push(`/comm-room/${id}?from=dashboard`);
}

function statusLabel(status) {
  const tone = {
    inquiring: "諮詢中",
    waiting_quote: "待報價",
    quoted: "待確認",
    buyer_accepted: "待匯款",
    proof_uploaded: "待核款",
    paid: "待出貨",
    completed: "已完成",
  };
  return tone[String(status || "")] || String(status || "處理中");
}

function rowTitle(item) {
  if (section.value === "timeline") return item.title || "交易節點";
  if (section.value === "rooms") return `Room #${item.id} ・ ${item.product_name || "Consultation"}`;
  if (section.value === "orders") return item.product_name || `Order #${item.id}`;
  if (section.value === "messages") return item.title || "系統通知";
  if (section.value === "points") return item.reason || "點數紀錄";
  return "紀錄";
}

function rowDesc(item) {
  if (section.value === "timeline") return `${item.detail || ""} ${formatDate(item.created_at)}`.trim();
  if (section.value === "rooms") return statusLabel(item.order?.status || item.status);
  if (section.value === "orders") return `${statusLabel(item.status)} ・ ${formatCurrency(item.final_amount_twd || item.amount_twd)}`;
  if (section.value === "messages") return `${item.detail || ""} ${formatDate(item.created_at)}`.trim();
  if (section.value === "points") return `${item.delta_points > 0 ? "+" : ""}${item.delta_points || 0} ・ ${formatDate(item.recorded_at)}`;
  return "";
}

function rowAction(item) {
  if (section.value === "rooms") {
    openRoom(item.id);
  }
}

function gotoSection(nextSection) {
  router.push(`/dashboard/${nextSection}`);
}

async function drawGacha() {
  if (isDrawing.value || gachaStatus.value.draws_available <= 0) return;
  isDrawing.value = true;
  showResult.value = false;
  errorText.value = "";
  try {
    const result = await performGachaDraw();
    gachaResults.value = result.results || [];
    gachaStatus.value.draws_available = result.draws_remaining;

    if (hasCouponReward(gachaResults.value)) {
      const couponData = await fetchMyCoupons();
      coupons.value = couponData.items || [];
    }

    showResult.value = true;
  } catch (error) {
    if (shouldForceLogin(error)) {
      authStore.logout();
      await router.push("/login");
      return;
    }
    errorText.value = error instanceof Error ? error.message : "抽獎失敗";
  } finally {
    isDrawing.value = false;
  }
}

function closeResultOverlay() {
  showResult.value = false;
}

async function loadSection() {
  loading.value = true;
  errorText.value = "";
  let salonFailed = false;
  try {
    const data = await fetchPrivateSalon();
    salon.value = {
      ...salon.value,
      ...data,
    };

    if (shouldClearUnreadOnRoute(route.fullPath)) {
      const rows = Array.isArray(salon.value.notifications?.items) ? salon.value.notifications.items : [];
      const lastEventId = rows.reduce((maxId, item) => {
        const value = Number(item?.id || 0);
        return value > maxId ? value : maxId;
      }, 0);
      if (lastEventId > 0) {
        await markNotificationsRead(lastEventId);
      }
      salon.value.notifications = {
        ...(salon.value.notifications || {}),
        unread: 0,
      };
      syncUnreadStorage(0);
    } else {
      syncUnreadStorage(salon.value.notifications?.unread || 0);
    }
  } catch (error) {
    if (error instanceof Error && error.message.includes("(401)")) {
      authStore.logout();
      await router.push("/login");
      return;
    }
    salonFailed = true;
    errorText.value = error instanceof Error ? error.message : "載入失敗";
    if (shouldClearUnreadOnRoute(route.fullPath)) {
      syncUnreadStorage(0);
    }
  }

  // Load section-specific data independently of private-salon
  try {
    if (section.value === "coupons") {
      const couponData = await fetchMyCoupons();
      coupons.value = couponData.items || [];
      if (salonFailed) errorText.value = "";
    }
    if (section.value === "gacha") {
      const status = await fetchGachaStatus();
      gachaStatus.value = status;
      if (salonFailed) errorText.value = "";
    }
  } catch (err) {
    if (err instanceof Error && err.message.includes("(401)")) {
      authStore.logout();
      await router.push("/login");
      return;
    }
    // non-critical — keep whatever errorText we have
  }

  loading.value = false;
}

onMounted(loadSection);

watch(
  () => route.params.section,
  () => {
    showResult.value = false;
    void loadSection();
  }
);
</script>

<template>
  <div class="account-section container">
    <header class="section-head">
      <button class="back-btn" type="button" @click="router.push('/dashboard')">&lt; My Page</button>
      <h1>{{ meta.title }}</h1>
      <p>{{ meta.subtitle }}</p>
    </header>

    <div v-if="!loading && !errorText" class="layout">
      <aside class="aside">
        <section class="point-box">
          <p class="point-label">可用點數 / My points</p>
          <p class="point-value">{{ salon.points?.balance || 0 }}<span>pt</span></p>
          <p class="point-sub">會員等級：{{ membershipSnapshot.level }}</p>
          <p class="point-spent">累計消費：NT$ {{ Number(membershipSnapshot.totalSpentTwd || 0).toLocaleString() }}</p>
          <p class="point-upgrade">{{ membershipSnapshot.upgradeHint }}</p>
          <div class="tier-track" aria-label="membership tier track">
            <div class="tier-track-bar">
              <span class="tier-track-fill" :style="{ width: `${membershipSnapshot.tierProgressPct}%` }"></span>
            </div>
            <div class="tier-track-steps">
              <span
                v-for="tier in membershipSnapshot.tiers"
                :key="tier.key"
                class="tier-step"
                :class="Number(membershipSnapshot.totalSpentTwd) >= Number(tier.threshold) ? 'active' : ''"
              >
                <strong>{{ tier.name }}</strong>
                <small>NT$ {{ Number(tier.threshold).toLocaleString() }}</small>
              </span>
            </div>
          </div>
          <div class="tier-benefits" aria-label="membership benefits by tier">
            <article
              v-for="tier in membershipSnapshot.tiers.filter((item) => Number(item.threshold) > 0)"
              :key="`benefit-${tier.key}`"
              class="tier-benefit-card"
              :class="Number(membershipSnapshot.totalSpentTwd) >= Number(tier.threshold) ? 'active' : ''"
            >
              <p class="tier-benefit-title">{{ tier.name }}（NT$ {{ Number(tier.threshold).toLocaleString() }}）</p>
              <p class="tier-benefit-desc">{{ tier.perks.join("／") }}</p>
            </article>
          </div>
        </section>

        <nav class="side-nav" aria-label="account sections">
          <button
            v-for="item in navItems"
            :key="item.key"
            type="button"
            class="side-link"
            :class="item.key === section ? 'active' : ''"
            @click="gotoSection(item.key)"
          >
            <span>{{ item.label }}</span>
            <small>{{ item.en }}</small>
          </button>
        </nav>
      </aside>

      <section class="main">
        <p v-if="sectionItems.length === 0 && section !== 'coupons' && section !== 'gacha'" class="state">目前尚無資料，可先透過下單或諮詢建立紀錄。</p>

        <!-- Orders: simplified card layout with image + order info -->
        <section v-else-if="section === 'orders'" class="order-list">
          <article v-for="item in sectionItems" :key="item.id" class="order-card">
            <div class="order-thumb">
              <img v-if="item.product_image" :src="item.product_image" :alt="item.product_name || ''" />
              <div v-else class="order-thumb-placeholder">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2ZM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5Z" fill="currentColor" /></svg>
              </div>
            </div>
            <div class="order-info">
              <p class="order-name">{{ item.product_name || `Order #${item.id}` }}</p>
              <p class="order-meta">{{ statusLabel(item.status) }} ・ {{ formatCurrency(item.final_amount_twd || item.amount_twd) }}</p>
              <p v-if="item.created_at" class="order-date">{{ formatDate(item.created_at) }}</p>
            </div>
          </article>
        </section>

        <!-- Timeline: transaction milestones with timeline visual -->
        <section v-else-if="section === 'timeline'" class="timeline-list">
          <article v-for="(item, idx) in sectionItems" :key="item.id || idx" class="timeline-node">
            <div class="timeline-dot-col">
              <span class="timeline-dot"></span>
              <span v-if="idx < sectionItems.length - 1" class="timeline-line"></span>
            </div>
            <div class="timeline-content">
              <p class="title">{{ rowTitle(item) }}</p>
              <p class="desc">{{ item.detail || "" }}</p>
              <p class="timestamp">{{ formatDate(item.created_at) }}</p>
            </div>
          </article>
        </section>

        <!-- Messages / Notifications: system notifications only -->
        <section v-else-if="section === 'messages'" class="notif-list">
          <article v-for="item in sectionItems" :key="item.id || item.title" class="notif-row">
            <div class="notif-icon-col">
              <svg class="notif-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2Zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2Z" fill="currentColor" />
              </svg>
            </div>
            <div>
              <p class="title">{{ item.title || "系統通知" }}</p>
              <p class="desc">{{ item.detail || "" }}</p>
              <p class="timestamp">{{ formatDate(item.created_at) }}</p>
            </div>
          </article>
        </section>

        <!-- Points: enhanced with expiry info -->
        <section v-else-if="section === 'points'" class="points-list">
          <article v-for="item in sectionItems" :key="item.id" class="points-row">
            <div>
              <p class="title">{{ item.reason || "點數紀錄" }}</p>
              <p class="desc">
                {{ item.delta_points > 0 ? "+" : "" }}{{ item.delta_points }} 點 ・ {{ formatDate(item.recorded_at) }}
              </p>
              <p v-if="item.delta_points > 0 && item.expires_at" class="expiry-hint">
                有效期限：{{ formatDate(item.expires_at) }}
              </p>
            </div>
          </article>
        </section>

        <!-- Coupons: user's discount vouchers -->
        <section v-else-if="section === 'coupons'" class="coupon-list">
          <p v-if="coupons.length === 0" class="state">目前沒有折扣券，可透過抽獎獲得。</p>
          <article v-for="item in coupons" :key="item.id" class="coupon-card" :class="{ used: item.is_used, expired: item.is_expired }">
            <div class="coupon-value">
              <span v-if="item.coupon.type === 'fixed'">-NT${{ item.coupon.value }}</span>
              <span v-else>{{ item.coupon.value }}折</span>
            </div>
            <div class="coupon-info">
              <p class="coupon-desc">{{ item.coupon.description }}</p>
              <p class="coupon-condition" v-if="item.coupon.min_order_twd > 0">滿 NT${{ Number(item.coupon.min_order_twd).toLocaleString() }} 可用</p>
              <p class="coupon-condition" v-else>無門檻</p>
              <p class="coupon-expiry">
                <template v-if="item.is_used">已使用</template>
                <template v-else-if="item.is_expired">已過期</template>
                <template v-else>有效期限：{{ formatDate(item.expires_at) }}</template>
              </p>
            </div>
          </article>
        </section>

        <!-- Gacha: lucky draw -->
        <section v-else-if="section === 'gacha'" class="gacha-section">
          <div class="gacha-dashboard">
            <div class="gacha-counter">
              <span class="gacha-counter-label">AVAILABLE DRAWS</span>
              <span class="gacha-counter-value">{{ gachaStatus.draws_available }}</span>
              <span class="gacha-counter-sub">每購買一件商品可獲得一次抽獎機會</span>
            </div>

            <div class="gacha-pool" v-if="gachaStatus.pool">
              <p class="pool-title">{{ gachaStatus.pool.name }}</p>
              <div class="prize-grid" :class="{ 'is-shuffling': isDrawing }">
                <div v-for="(prize, idx) in gachaStatus.pool.prizes" :key="idx" class="premium-card pool-card" :data-tier="prize.label" :style="`--card-idx: ${idx};`">
                  <div class="premium-card-inner">
                    <div class="premium-card-front">
                      <div class="card-pattern"></div>
                      <div class="card-logo-wrap"><span class="card-logo">WAKOU</span></div>
                    </div>
                    <div class="premium-card-back">
                      <div class="card-border"></div>
                      <span class="prize-label">{{ prize.label }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="gacha-action">
              <button
                class="gacha-draw-btn premium-btn"
                type="button"
                :disabled="isDrawing || gachaStatus.draws_available <= 0"
                @click="drawGacha"
                :class="{ 'is-drawing': isDrawing }"
              >
                <span class="btn-text">{{ isDrawing ? "DRAWING..." : gachaStatus.draws_available > 0 ? "開始抽獎" : "沒有抽獎次數" }}</span>
                <span class="btn-glare"></span>
              </button>
            </div>
          </div>

          <!-- Result Overlay -->
          <div v-if="showResult && gachaResults.length > 0" class="gacha-result-overlay" @click.self="closeResultOverlay">
            <div class="result-backdrop"></div>
            <div class="result-presentation">
              <!-- Text-based result summary (always visible, no animation dependency) -->
              <div class="result-summary-text">
                <template v-for="(result, idx) in gachaResults" :key="'summary-' + idx">
                  <p v-if="result.is_redraw" class="result-redraw-line">🔄 再抽一次！</p>
                </template>
                <template v-for="(result, idx) in gachaResults" :key="'prize-' + idx">
                  <template v-if="!result.is_redraw">
                    <p class="result-won-title">🎉 恭喜獲得</p>
                    <p class="result-won-prize">{{ result.label }}</p>
                    <p v-if="result.coupon" class="result-won-desc">{{ result.coupon.coupon.description }}</p>
                  </template>
                </template>
              </div>

              <div v-for="(result, idx) in gachaResults" :key="idx" class="premium-card result-card animated-flip" :data-tier="result.label" :class="{ redraw: result.is_redraw }">
                <div class="premium-card-inner">
                  <div class="premium-card-front">
                    <div class="card-pattern"></div>
                    <div class="card-logo-wrap"><span class="card-logo">WAKOU</span></div>
                  </div>
                  <div class="premium-card-back">
                    <div class="card-glare"></div>
                    <div class="card-particles"></div>
                    <div class="card-border"></div>
                    <div class="result-content">
                      <p class="result-headline">
                        <span class="headline-icon" v-if="result.is_redraw">
                          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none"><path d="M21.5 2v6h-6M2.13 15.57a9 9 0 1 0 3.87-11.1l5.5 5.5"/></svg>
                        </span>
                        <span class="headline-icon" v-else>
                          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                        </span>
                        {{ result.is_redraw ? "再抽一次！" : "恭喜獲得" }}
                      </p>
                      <p class="result-prize-text">{{ result.label }}</p>
                      <p v-if="result.coupon" class="result-detail-text">{{ result.coupon.coupon.description }}</p>
                    </div>
                  </div>
                </div>
              </div>
              <button class="return-btn premium-btn" type="button" @click="closeResultOverlay" v-if="gachaStatus.draws_available > 0">
                <span class="btn-text">繼續抽獎</span>
              </button>
              <button class="result-close" type="button" @click="closeResultOverlay">關閉結果</button>
              <p class="result-hint">點擊背景關閉</p>
            </div>
          </div>
        </section>

        <!-- Default list for rooms -->
        <section v-else class="list">
          <article
            v-for="item in sectionItems"
            :key="item.id || item.title || item.reason"
            class="list-row"
            :role="section === 'rooms' ? 'button' : undefined"
            :tabindex="section === 'rooms' ? 0 : undefined"
            @click="rowAction(item)"
            @keydown.enter="rowAction(item)"
          >
            <div>
              <p class="title">{{ rowTitle(item) }}</p>
              <p class="desc">{{ rowDesc(item) }}</p>
            </div>
            <span v-if="section === 'rooms'" class="arrow">&gt;</span>
          </article>
        </section>
      </section>
    </div>

    <p v-if="loading" class="state">載入中...</p>
    <p v-else-if="errorText" class="state error">{{ errorText }}</p>
  </div>
</template>

<style scoped>
.account-section {
  color: #1b2740;
  max-width: 980px;
  padding-bottom: 6rem;
  padding-top: 2.5rem;
}

.layout {
  column-gap: 1.8rem;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
}

.aside {
  display: grid;
  gap: 1rem;
}

.point-box {
  background: #f3f4f6;
  border: 1px solid #d4d9df;
  padding: 1rem;
}

.point-label,
.point-sub {
  color: #324867;
  margin: 0;
}

.point-spent,
.point-upgrade {
  color: #324867;
  margin: 0.22rem 0 0;
}

.point-spent {
  font-size: 0.86rem;
}

.point-upgrade {
  color: #5d3f1f;
  font-size: 0.8rem;
  line-height: 1.45;
}

.tier-track {
  margin-top: 0.75rem;
}

.tier-track-bar {
  background: #e6dfd5;
  border-radius: 999px;
  height: 6px;
  overflow: hidden;
}

.tier-track-fill {
  background: linear-gradient(90deg, #7f6a4c, #2b3e58);
  display: block;
  height: 100%;
  transition: width 0.35s ease;
}

.tier-track-steps {
  display: grid;
  gap: 0.35rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 0.45rem;
}

.tier-step {
  color: #7e8692;
  display: grid;
  gap: 0.1rem;
}

.tier-step.active {
  color: #253853;
}

.tier-step strong {
  font-size: 0.66rem;
  font-weight: 600;
  line-height: 1.2;
}

.tier-step small {
  font-size: 0.6rem;
}

.tier-benefits {
  display: grid;
  gap: 0.35rem;
  margin-top: 0.7rem;
}

.tier-benefit-card {
  background: rgba(255, 255, 255, 0.52);
  border: 1px solid #d8d1c7;
  padding: 0.42rem 0.48rem;
}

.tier-benefit-card.active {
  border-color: #927a57;
  box-shadow: inset 0 0 0 1px rgba(146, 122, 87, 0.18);
}

.tier-benefit-title,
.tier-benefit-desc {
  margin: 0;
}

.tier-benefit-title {
  color: #263954;
  font-size: 0.68rem;
  font-weight: 600;
}

.tier-benefit-desc {
  color: #3a4f6f;
  font-size: 0.65rem;
  margin-top: 0.16rem;
}

.point-value {
  color: #182a47;
  font-size: 2rem;
  margin: 0.35rem 0;
}

.point-value span {
  font-size: 1rem;
  margin-left: 0.15rem;
}

.side-nav {
  border: 1px solid #d4d9df;
}

.side-link {
  background: transparent;
  border: 0;
  border-bottom: 1px solid #d4d9df;
  color: #1f3150;
  cursor: pointer;
  display: grid;
  gap: 0.15rem;
  padding: 0.65rem 0.7rem;
  text-align: left;
  width: 100%;
}

.side-link:last-child {
  border-bottom: 0;
}

.side-link small {
  color: #4b5f7e;
}

.side-link.active {
  background: rgba(255, 255, 255, 0.6);
}

.main {
  min-width: 0;
}

.section-head {
  border-bottom: 1px solid #d4d9df;
  margin-bottom: 1rem;
  padding-bottom: 0.8rem;
}

.section-head h1 {
  color: #182a47;
  font-family: var(--font-sans);
  font-size: 1.75rem;
  font-weight: 400;
  margin: 0.5rem 0 0.2rem;
}

.section-head p {
  color: #3c506e;
  margin: 0;
}

.back-btn {
  background: transparent;
  border: 0;
  color: #2f4562;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0;
}

/* Default list */
.list {
  border-bottom: 1px solid #d4d9df;
  border-top: 1px solid #d4d9df;
}

.list-row {
  align-items: center;
  border-bottom: 1px solid #d4d9df;
  cursor: pointer;
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr auto;
  min-height: 76px;
  padding: 0.7rem 0;
}

.list-row:last-child {
  border-bottom: 0;
}

.list-row:hover {
  background: rgba(255, 255, 255, 0.18);
}

/* Order cards (simplified) */
.order-list {
  display: grid;
  gap: 0.8rem;
}

.order-card {
  align-items: center;
  border: 1px solid #d4d9df;
  display: grid;
  gap: 1.2rem;
  grid-template-columns: 80px 1fr;
  padding: 1rem;
  transition: background 0.2s;
}

.order-card:hover {
  background: rgba(255, 255, 255, 0.3);
}

.order-thumb {
  aspect-ratio: 1;
  background: #f0ede8;
  overflow: hidden;
  width: 80px;
}

.order-thumb img {
  height: 100%;
  object-fit: cover;
  width: 100%;
}

.order-thumb-placeholder {
  align-items: center;
  color: #b5afa6;
  display: flex;
  height: 100%;
  justify-content: center;
  width: 100%;
}

.order-thumb-placeholder svg {
  height: 32px;
  width: 32px;
}

.order-name {
  color: #182a47;
  font-size: 1.05rem;
  margin: 0;
}

.order-meta {
  color: #324867;
  font-size: 0.9rem;
  margin: 0.25rem 0 0;
}

.order-date {
  color: #7a8a9e;
  font-size: 0.8rem;
  margin: 0.2rem 0 0;
}

/* Timeline nodes */
.timeline-list {
  padding-left: 0.5rem;
}

.timeline-node {
  display: grid;
  gap: 1rem;
  grid-template-columns: 20px 1fr;
  min-height: 70px;
}

.timeline-dot-col {
  align-items: stretch;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 0.35rem;
}

.timeline-dot {
  background: #324867;
  border-radius: 999px;
  flex-shrink: 0;
  height: 10px;
  width: 10px;
}

.timeline-line {
  background: #d4d9df;
  flex: 1;
  margin-top: 0.3rem;
  width: 2px;
}

.timeline-content {
  padding-bottom: 1.5rem;
}

.timestamp {
  color: #7a8a9e;
  font-size: 0.8rem;
  margin: 0.25rem 0 0;
}

/* Notification rows */
.notif-list {
  border-top: 1px solid #d4d9df;
}

.notif-row {
  align-items: flex-start;
  border-bottom: 1px solid #d4d9df;
  display: grid;
  gap: 0.8rem;
  grid-template-columns: 28px 1fr;
  padding: 0.9rem 0;
}

.notif-icon-col {
  padding-top: 0.15rem;
}

.notif-icon {
  color: #8c7b6c;
  height: 1.2rem;
  width: 1.2rem;
}

.title {
  color: #182a47;
  font-size: 1.1rem;
  margin: 0;
}

.desc {
  color: #324867;
  margin: 0.2rem 0 0;
}

.arrow {
  color: #22395a;
}

.state {
  color: #324867;
  margin: 1rem 0;
}

.state.error {
  color: #bc3c2a;
}

/* Points list with expiry */
.points-list {
  border-top: 1px solid #d4d9df;
}

.points-row {
  border-bottom: 1px solid #d4d9df;
  padding: 0.8rem 0;
}

.points-row:last-child {
  border-bottom: 0;
}

.expiry-hint {
  color: #8c7b6c;
  font-size: 0.72rem;
  margin: 0.15rem 0 0;
}

/* Coupon cards */
.coupon-list {
  display: grid;
  gap: 0.8rem;
}

.coupon-card {
  align-items: center;
  border: 1px solid #d4d9df;
  display: grid;
  gap: 1rem;
  grid-template-columns: 100px 1fr;
  padding: 1rem;
  transition: background 0.2s;
}

.coupon-card.used,
.coupon-card.expired {
  opacity: 0.5;
}

.coupon-value {
  color: #5d3f1f;
  font-family: var(--font-sans);
  font-size: 1.4rem;
  font-weight: 600;
  text-align: center;
}

.coupon-info {
  min-width: 0;
}

.coupon-desc {
  color: #182a47;
  font-size: 1rem;
  margin: 0;
}

.coupon-condition {
  color: #324867;
  font-size: 0.82rem;
  margin: 0.2rem 0 0;
}

.coupon-expiry {
  color: #7a8a9e;
  font-size: 0.78rem;
  margin: 0.2rem 0 0;
}

/* Gacha section */
.gacha-section {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  position: relative;
  min-height: 500px;
}

.gacha-dashboard {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  align-items: center;
  z-index: 1;
}

.gacha-counter {
  text-align: center;
  background: linear-gradient(145deg, #1b2740, #182a47);
  border: 1px solid #324867;
  border-radius: 12px;
  padding: 1.5rem 3rem;
  box-shadow: 0 10px 30px rgba(24, 42, 71, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
  width: 100%;
  max-width: 400px;
}

.gacha-counter::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, #927a57, transparent);
}

.gacha-counter-label {
  display: block;
  color: #927a57;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.gacha-counter-value {
  display: block;
  color: #f3f4f6;
  font-size: 3.5rem;
  font-weight: 300;
  line-height: 1;
  font-family: var(--font-serif, serif);
  text-shadow: 0 2px 10px rgba(146, 122, 87, 0.3);
}

.gacha-counter-sub {
  display: block;
  color: #7a8a9e;
  font-size: 0.8rem;
  margin-top: 0.8rem;
}

.gacha-pool {
  width: 100%;
}

.pool-title {
  color: #182a47;
  font-size: 1.1rem;
  font-weight: 600;
  text-align: center;
  margin: 0 0 1.2rem;
  letter-spacing: 0.1em;
}

.prize-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.2rem;
  max-width: 600px;
  margin: 0 auto;
}

.premium-card {
  aspect-ratio: 2 / 3;
  perspective: 1000px;
  cursor: pointer;
  --tier-color: #927a57;
  --tier-bg: #182a47;
  --tier-glow: rgba(146, 122, 87, 0);
  --border-style: solid;
}

.premium-card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  text-align: center;
  transition: transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  transform-style: preserve-3d;
  -webkit-transform-style: preserve-3d;
}

.pool-card:hover .premium-card-inner {
  transform: rotateY(180deg);
  box-shadow: 0 10px 20px rgba(24, 42, 71, 0.2);
}

.result-card .premium-card-inner {
  transform: rotateY(0deg);
  animation: flipIn 1.2s 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

@keyframes flipIn {
  0% { transform: rotateY(0deg) scale(0.8); opacity: 0; }
  50% { transform: rotateY(90deg) scale(1.1); opacity: 1; }
  100% { transform: rotateY(180deg) scale(1); opacity: 1; }
}

.premium-card-front, .premium-card-back {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.premium-card-front {
  background: #182a47;
  border: 2px solid #2b3e58;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-pattern {
  position: absolute;
  inset: 4px;
  border: 1px solid rgba(146, 122, 87, 0.3);
  background-image: repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(146, 122, 87, 0.05) 10px, rgba(146, 122, 87, 0.05) 20px);
}

.card-logo-wrap {
  background: #182a47;
  padding: 10px;
  border: 1px solid #927a57;
  z-index: 2;
  box-shadow: 0 0 20px rgba(0,0,0,0.5);
}

.card-logo {
  color: #927a57;
  font-family: var(--font-serif, serif);
  font-size: 0.9rem;
  letter-spacing: 0.2em;
}

.premium-card-back {
  background: #f3f4f6;
  color: #182a47;
  transform: rotateY(180deg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px var(--border-style) var(--tier-color);
  box-shadow: 0 0 20px var(--tier-glow), inset 0 0 20px var(--tier-glow);
  padding: 1rem;
}

.card-border {
  position: absolute;
  inset: 6px;
  border: 1px solid var(--tier-color);
  opacity: 0.5;
}

.prize-label {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--tier-color);
  z-index: 2;
  text-shadow: 0 1px 5px var(--tier-glow);
}

.is-shuffling .pool-card {
  animation: wobble 0.5s infinite;
}
.is-shuffling .pool-card:nth-child(even) {
  animation-direction: reverse;
  animation-duration: 0.4s;
}

@keyframes wobble {
  0% { transform: translateX(0) rotate(0); }
  25% { transform: translateX(-2px) rotate(-1deg); }
  50% { transform: translateX(0) rotate(0); }
  75% { transform: translateX(2px) rotate(1deg); }
  100% { transform: translateX(0) rotate(0); }
}

.gacha-action {
  width: 100%;
  max-width: 320px;
  margin-top: 1rem;
}

.premium-btn {
  width: 100%;
  padding: 1.2rem;
  background: linear-gradient(135deg, #182a47, #2b3e58);
  border: 1px solid #927a57;
  color: #f3f4f6;
  font-size: 1.1rem;
  letter-spacing: 0.1em;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  border-radius: 4px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(24, 42, 71, 0.3);
}

.premium-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(146, 122, 87, 0.3);
  background: linear-gradient(135deg, #1b2740, #324867);
}

.premium-btn:disabled {
  background: #2b3e58;
  border-color: #7a8a9e;
  color: #7a8a9e;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-glare {
  position: absolute;
  top: 0; left: -100%; width: 50%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transform: skewX(-20deg);
  transition: 0.5s;
}

.premium-btn:hover:not(:disabled) .btn-glare {
  left: 150%;
  transition: 0.7s ease-in-out;
}

.premium-btn.is-drawing {
  animation: pulseBtn 1.5s infinite;
}

@keyframes pulseBtn {
  0% { box-shadow: 0 0 0 0 rgba(146, 122, 87, 0.4); }
  70% { box-shadow: 0 0 0 15px rgba(146, 122, 87, 0); }
  100% { box-shadow: 0 0 0 0 rgba(146, 122, 87, 0); }
}

.gacha-result-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: fadeIn 0.3s forwards;
}

.result-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(24, 42, 71, 0.85);
  backdrop-filter: blur(8px);
  pointer-events: none;
}

.result-presentation {
  position: relative;
  z-index: 11;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  width: 100%;
  pointer-events: auto;
}
.result-summary-text {
  text-align: center;
  color: #f3f4f6;
  z-index: 12;
  margin-bottom: 0.5rem;
}
.result-won-title {
  font-size: 1.1rem;
  color: #e6dfd5;
  margin: 0;
}
.result-won-prize {
  font-size: 3rem;
  font-weight: 700;
  color: #927a57;
  margin: 0.5rem 0;
  text-shadow: 0 2px 10px rgba(146, 122, 87, 0.5);
}
.result-won-desc {
  font-size: 1rem;
  color: #d4d9df;
  margin: 0;
}
.result-redraw-line {
  font-size: 1rem;
  color: #a3aab5;
  margin: 0 0 0.5rem;
}


.result-card {
  width: 260px;
  height: 390px;
  max-width: 90vw;
}

.result-card .premium-card-back {
  background: linear-gradient(135deg, #ffffff, #f3f4f6);
}

.result-content {
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.result-headline {
  font-size: 0.9rem;
  color: #7a8a9e;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.headline-icon {
  display: inline-flex;
  color: var(--tier-color);
}

.result-prize-text {
  font-size: 2.8rem;
  font-weight: 700;
  color: var(--tier-color);
  margin: 0;
  text-shadow: 0 2px 10px var(--tier-glow);
}

.result-detail-text {
  font-size: 0.95rem;
  color: #324867;
  margin: 0;
  padding: 0.6rem 1.2rem;
  background: rgba(255,255,255,0.7);
  border-radius: 20px;
  border: 1px solid rgba(146, 122, 87, 0.2);
}

.result-hint {
  color: #d4d9df;
  font-size: 0.85rem;
  opacity: 0.7;
  animation: pulseOpacity 2s infinite;
}

.return-btn {
  max-width: 220px;
  padding: 0.8rem;
  font-size: 1rem;
  background: transparent;
  border: 1px solid #927a57;
  color: #e6dfd5;
  box-shadow: none;
}

.return-btn:hover {
  background: rgba(146, 122, 87, 0.2);
  transform: translateY(-2px);
}

.result-close {
  background: transparent;
  border: 1px solid rgba(230, 223, 213, 0.7);
  color: #e6dfd5;
  cursor: pointer;
  font-size: 0.85rem;
  letter-spacing: 0.08em;
  padding: 0.45rem 1rem;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes pulseOpacity {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

/* Tiers */
.premium-card[data-tier="-100"] {
  --tier-color: #7a8a9e;
  --tier-glow: rgba(122, 138, 158, 0.2);
}

.premium-card[data-tier="再抽一次"] {
  --tier-color: #a3aab5;
  --tier-glow: rgba(163, 170, 181, 0.6);
}
.premium-card[data-tier="再抽一次"] .premium-card-back {
  background: linear-gradient(135deg, #ffffff, #e2e8f0);
}
.result-card[data-tier="再抽一次"] .headline-icon {
  animation: spinIcon 2s linear infinite;
}

@keyframes spinIcon {
  100% { transform: rotate(360deg); }
}

.premium-card[data-tier="-500"] {
  --tier-color: #cd7f32;
  --tier-glow: rgba(205, 127, 50, 0.4);
}

.premium-card[data-tier="95折"] {
  --tier-color: #d4af37;
  --tier-glow: rgba(212, 175, 55, 0.6);
}

.premium-card[data-tier="9折"] {
  --tier-color: #e5b300;
  --tier-glow: rgba(229, 179, 0, 0.8);
  --border-style: double;
}
.premium-card[data-tier="9折"] .premium-card-back {
  border-width: 4px;
}

.premium-card[data-tier="8折"] {
  --tier-color: #ff9d00;
  --tier-glow: rgba(255, 157, 0, 1);
  --border-style: dashed;
}
.result-card[data-tier="8折"] .premium-card-inner {
  animation: flipInLegendary 1.5s 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

@keyframes flipInLegendary {
  0% { transform: rotateY(0deg) scale(0.8); opacity: 0; }
  50% { transform: rotateY(180deg) scale(1.15); opacity: 1; filter: brightness(1.2) drop-shadow(0 0 20px rgba(255,157,0,0.8)); }
  100% { transform: rotateY(180deg) scale(1); opacity: 1; filter: brightness(1); }
}

.result-card[data-tier="8折"] .card-particles {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 50%, rgba(255, 157, 0, 0.25) 0%, transparent 60%);
  animation: legendaryPulse 2s infinite;
}

@keyframes legendaryPulse {
  0% { opacity: 0.5; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.1); }
  100% { opacity: 0.5; transform: scale(0.9); }
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .tier-track-steps {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .order-card {
    grid-template-columns: 64px 1fr;
    gap: 0.8rem;
  }

  .order-thumb {
    width: 64px;
  }
  .coupon-card {
    grid-template-columns: 80px 1fr;
  }

  .prize-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.8rem;
  }
  .gacha-counter {
    padding: 1rem 2rem;
  }
  .gacha-counter-value {
    font-size: 2.8rem;
  }
}
</style>
