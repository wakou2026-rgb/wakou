<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "../../modules/auth/store";

const { t, locale } = useI18n();
const authStore = useAuthStore();

const loading = ref(false);
const error = ref("");
const shipmentCards = ref([]);
const expandedCards = ref(new Set());

const stageSequence = [
  "payment_confirmed",
  "preparing",
  "shipped_jp",
  "in_transit",
  "customs_tw",
  "shipped_tw",
  "delivered"
];

const stageGroupOrder = [
  "payment_confirmed",
  "preparing",
  "shipped_jp",
  "in_transit",
  "customs_tw",
  "shipped_tw",
  "delivered"
];

function getAccessToken() {
  if (typeof window === "undefined") {
    return "";
  }
  // Always read from store (stays in sync after token refresh)
  return authStore.accessToken || window.localStorage.getItem("wakou_access_token") || "";
}

function authHeaders() {
  const token = getAccessToken();
  return { Authorization: `Bearer ${token}` };
}

function statusLabel(status) {
  const key = `shipment.status.${status || ""}`;
  const translated = t(key);
  return translated === key ? String(status || "-") : translated;
}

function formatEventTime(value) {
  if (!value) {
    return "";
  }
  const lang = locale.value === "ja" ? "ja-JP" : locale.value === "en" ? "en-US" : "zh-TW";
  return new Date(value).toLocaleString(lang, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function currentStageIndex(events) {
  let maxIndex = -1;
  for (const event of events) {
    const idx = stageSequence.indexOf(String(event?.status || ""));
    if (idx > maxIndex) {
      maxIndex = idx;
    }
  }
  return maxIndex;
}

function normalizeCard(order, events) {
  const latest = events.length ? events[events.length - 1] : null;
  const stageIndex = currentStageIndex(events);
  const steps = stageGroupOrder.map((stage, index) => {
    const eventForStage = [...events].reverse().find((event) => event.status === stage) || null;
    return {
      stage,
      completed: stageIndex >= index,
      current: stageIndex === index,
      event: eventForStage
    };
  });

  return {
    id: Number(order.id),
    productName: order.product_name,
    orderStatus: order.status,
    latestStatus: latest?.status || "",
    latestTitle: latest?.title || "",
    latestStageIndex: stageIndex,
    events,
    steps
  };
}

const hasCards = computed(() => shipmentCards.value.length > 0);

async function loadShipments() {
  loading.value = true;
  error.value = "";
  shipmentCards.value = [];

  try {
    let ordersResponse = await fetch("/api/v1/orders/me", {
      method: "GET",
      headers: authHeaders()
    });
    // Auto-refresh on 401 then retry once
    if (ordersResponse.status === 401) {
      const refreshed = await authStore.refreshTokens();
      if (!refreshed) {
        throw new Error("load orders failed (401)");
      }
      ordersResponse = await fetch("/api/v1/orders/me", {
        method: "GET",
        headers: authHeaders()
      });
    }
    if (!ordersResponse.ok) {
      throw new Error(`load orders failed (${ordersResponse.status})`);
    }
    const ordersData = await ordersResponse.json();
    const allOrders = Array.isArray(ordersData?.items) ? ordersData.items : [];
    const candidateOrders = allOrders.filter((order) => ["paid", "completed", "shipped"].includes(String(order?.status || "")));

    if (!candidateOrders.length) {
      shipmentCards.value = [];
      return;
    }

    const shipmentResults = await Promise.all(
      candidateOrders.map(async (order) => {
        const response = await fetch(`/api/v1/orders/${order.id}/shipment-events`, {
          method: "GET",
          headers: authHeaders()
        });
        if (!response.ok) {
          return { order, events: [] };
        }
        const payload = await response.json();
        const events = Array.isArray(payload?.events) ? payload.events : [];
        return { order, events };
      })
    );

    shipmentCards.value = shipmentResults
      .map(({ order, events }) => normalizeCard(order, events))
      .sort((left, right) => right.id - left.id);
    // Default: only expand the most recent card
    if (shipmentCards.value.length > 0) {
      expandedCards.value = new Set([shipmentCards.value[0].id]);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "load shipment failed";
  } finally {
    loading.value = false;
  }
}

function toggleCard(id) {
  if (expandedCards.value.has(id)) {
    expandedCards.value.delete(id);
  } else {
    expandedCards.value.add(id);
  }
  // trigger reactivity
  expandedCards.value = new Set(expandedCards.value);
}
onMounted(() => {
  if (authStore.isLoggedIn) {
    loadShipments();
  }
});
</script>

<template>
  <section class="shipment-page container">
    <header class="shipment-hero">
      <p class="hero-kicker">WAKOU SHIPMENT</p>
      <h1>{{ t("shipment.page_title") }}</h1>
      <p>{{ t("shipment.subtitle") }}</p>
    </header>

    <div v-if="!authStore.isLoggedIn" class="empty-panel">
      <p>{{ t("shipment.not_logged_in") }}</p>
      <RouterLink to="/login" class="login-link">{{ t("shipment.login_link") }}</RouterLink>
    </div>

    <div v-else-if="loading" class="empty-panel">Loading...</div>

    <div v-else-if="error" class="empty-panel error">{{ error }}</div>

    <div v-else-if="!hasCards" class="empty-panel">{{ t("shipment.no_orders") }}</div>

    <div v-else class="cards-grid">
      <article v-for="card in shipmentCards" :key="card.id" class="shipment-card">
        <!-- Card header: always visible, click to toggle -->
        <header class="card-head" role="button" tabindex="0" @click="toggleCard(card.id)" @keydown.enter="toggleCard(card.id)">
          <div class="head-title">
            <p class="product-label">{{ t("shipment.product") }}</p>
            <h2>{{ card.productName }}</h2>
          </div>
          <div class="head-meta">
            <p>{{ t("shipment.order_id") }} #{{ card.id }}</p>
            <span class="status-badge">
              {{ statusLabel(card.latestStatus || card.orderStatus) }}
            </span>
          </div>
          <button class="toggle-btn" type="button" :aria-expanded="expandedCards.has(card.id)" :aria-label="expandedCards.has(card.id) ? t('shipment.collapse') : t('shipment.expand')">
            <svg class="toggle-icon" :class="{ rotated: expandedCards.has(card.id) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
        </header>

        <!-- Latest step preview (always visible when collapsed) -->
        <div v-if="!expandedCards.has(card.id) && card.steps.some(s => s.current)" class="latest-preview">
          <template v-for="step in card.steps" :key="step.stage">
            <div v-if="step.current" class="preview-step">
              <span class="preview-dot"></span>
              <div class="preview-body">
                <p class="preview-title">{{ statusLabel(step.stage) }}</p>
                <p v-if="step.event?.description" class="preview-desc">{{ step.event.description }}</p>
                <p v-if="step.event?.event_time" class="preview-time">{{ formatEventTime(step.event.event_time) }}</p>
              </div>
            </div>
          </template>
        </div>

        <!-- Full timeline (expanded) -->
        <div v-if="expandedCards.has(card.id)">
          <p v-if="!card.events.length" class="no-events">{{ t("shipment.no_events") }}</p>
          <ol v-else class="timeline-list">
            <li
              v-for="step in card.steps"
              :key="`${card.id}-${step.stage}`"
              class="timeline-step"
              :class="{ completed: step.completed, current: step.current }"
            >
              <span class="step-dot"></span>
              <div class="step-body">
                <p class="step-title">{{ statusLabel(step.stage) }}</p>
                <p v-if="step.event?.title" class="step-detail">{{ step.event.title }}</p>
                <p v-if="step.event?.description" class="step-sub">{{ step.event.description }}</p>
                <p v-if="step.event?.location" class="step-meta">{{ step.event.location }}</p>
                <p v-if="step.event?.event_time" class="step-time">{{ formatEventTime(step.event.event_time) }}</p>
              </div>
            </li>
          </ol>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.shipment-page {
  min-height: calc(100vh - 8rem);
  padding-top: 2.2rem;
  padding-bottom: 4rem;
}

.shipment-hero {
  margin-bottom: 1.8rem;
  padding: 2rem 2.2rem;
  background: radial-gradient(circle at 20% 20%, rgba(225, 201, 161, 0.32), transparent 52%), var(--paper-100);
  border: 1px solid var(--paper-300);
}

.hero-kicker {
  margin: 0;
  font-family: var(--font-sans);
  letter-spacing: 0.2em;
  font-size: 0.72rem;
  color: var(--ink-500);
}

.shipment-hero h1 {
  margin: 0.8rem 0 0.4rem;
  font-family: var(--font-serif);
  color: var(--ink-900);
  font-size: clamp(1.8rem, 2.5vw, 2.45rem);
}

.shipment-hero p {
  margin: 0;
  font-family: var(--font-sans);
  color: var(--ink-600);
}

.empty-panel {
  border: 1px solid var(--paper-300);
  background: var(--paper-100);
  padding: 1.5rem;
  color: var(--ink-600);
  font-family: var(--font-sans);
}

.empty-panel.error {
  color: #b64534;
}

.login-link {
  display: inline-block;
  margin-top: 0.6rem;
  color: var(--accent-700);
  text-decoration: underline;
}

.cards-grid {
  display: grid;
  gap: 1rem;
}

.shipment-card {
  border: 1px solid var(--paper-300);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.74), rgba(255, 255, 255, 0.5)),
    radial-gradient(circle at top right, rgba(231, 210, 175, 0.35), transparent 45%),
    var(--paper-50);
  padding: 1.2rem;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0;
  cursor: pointer;
  padding-bottom: 0.9rem;
  user-select: none;
}

.product-label {
  margin: 0;
  font-size: 0.72rem;
  font-family: var(--font-sans);
  letter-spacing: 0.1em;
  color: var(--ink-500);
}

.head-title h2 {
  margin: 0.35rem 0 0;
  font-family: var(--font-serif);
  color: var(--ink-900);
  font-size: 1.25rem;
}

.head-meta {
  text-align: right;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  color: var(--ink-600);
}

.head-meta p {
  margin: 0;
}

.status-badge {
  display: inline-flex;
  margin-top: 0.45rem;
  border: 1px solid rgba(145, 116, 78, 0.4);
  padding: 0.2rem 0.55rem;
  color: var(--ink-800);
  background: rgba(238, 221, 196, 0.38);
}

.toggle-btn {
  background: transparent;
  border: 0;
  color: var(--ink-500);
  cursor: pointer;
  flex-shrink: 0;
  padding: 0.2rem;
  margin-top: 0.2rem;
}

.toggle-icon {
  display: block;
  height: 18px;
  width: 18px;
  transition: transform 0.22s ease;
}

.toggle-icon.rotated {
  transform: rotate(180deg);
}

.latest-preview {
  border-top: 1px solid var(--paper-300);
  padding-top: 0.7rem;
  display: flex;
  gap: 0.6rem;
  align-items: flex-start;
}

.preview-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #b29262;
  flex-shrink: 0;
  margin-top: 0.32rem;
  box-shadow: 0 0 0 3px rgba(178, 146, 98, 0.18);
}

.preview-body {
  min-width: 0;
}

.preview-title {
  margin: 0;
  font-family: var(--font-sans);
  color: var(--ink-800);
  font-size: 0.9rem;
  font-weight: 600;
}

.preview-desc {
  margin: 0.15rem 0 0;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  color: var(--ink-600);
}

.preview-time {
  margin: 0.1rem 0 0;
  font-family: var(--font-sans);
  font-size: 0.74rem;
  color: var(--ink-500);
}
.no-events {
  margin: 0;
  font-family: var(--font-sans);
  color: var(--ink-500);
}

.timeline-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.timeline-step {
  position: relative;
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 0.7rem;
  padding-bottom: 0.9rem;
}

.timeline-step::after {
  content: "";
  position: absolute;
  top: 18px;
  left: 8px;
  width: 2px;
  height: calc(100% - 15px);
  background: var(--paper-300);
}

.timeline-step:last-child::after {
  display: none;
}

.step-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  margin-top: 2px;
  border: 1px solid var(--paper-300);
  background: var(--paper-50);
  transition: background 0.2s ease, border-color 0.2s ease;
}

.timeline-step.completed .step-dot {
  background: #b29262;
  border-color: #b29262;
}

.timeline-step.current .step-dot {
  box-shadow: 0 0 0 4px rgba(178, 146, 98, 0.2);
}

.step-title {
  margin: 0;
  font-family: var(--font-sans);
  color: var(--ink-700);
  font-size: 0.92rem;
}

.timeline-step.completed .step-title,
.timeline-step.current .step-title {
  color: var(--ink-900);
  font-weight: 600;
}

.step-detail,
.step-sub,
.step-meta,
.step-time {
  margin: 0.18rem 0 0;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  color: var(--ink-600);
}

.step-time {
  color: var(--ink-500);
  font-size: 0.75rem;
}

@media (max-width: 780px) {
  .shipment-page {
    padding-top: 1.3rem;
  }

  .shipment-hero {
    padding: 1.4rem;
  }

  .card-head {
    flex-direction: column;
  }

  .head-meta {
    text-align: left;
  }
}
</style>
