<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useAuthStore } from "../../modules/auth/store";
import { fetchMyCommRooms, fetchMyOrders, fetchPrivateSalon, fetchUserGrowth, updateMyDisplayName } from "../../modules/account/service";
import { deriveMembershipSnapshot } from "../../modules/account/membership";

const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

const loading = ref(true);
const isError = ref(false);
const statusText = ref("");
const salon = ref({
  membership: { level: "初見", progress: 0, next_level: null, remaining_twd: 0, total_spent_twd: 0 },
  points: { balance: 0, items: [] },
  notifications: { unread: 0, items: [] },
  timeline: [],
  privileges: [],
  orders: [],
  rooms: [],
  focus_order: null,
});

const profileForm = reactive({
  displayName: authStore.displayName || "",
});

const levelProgress = computed(() => Number(salon.value.membership?.progress || 0));
const roomCount = computed(() => salon.value.rooms?.length || 0);
const orderCount = computed(() => salon.value.orders?.length || 0);
const unreadCount = computed(() => salon.value.notifications?.unread || 0);
const recentOrders = computed(() => (salon.value.orders || []).slice(0, 6));
const recentNotifications = computed(() => (salon.value.notifications?.items || []).slice(0, 6));
const membershipSnapshot = computed(() => deriveMembershipSnapshot({
  membership: salon.value.membership,
  orders: salon.value.orders,
}));

function isUnauthorizedError(error) {
  if (!error || typeof error !== "object") return false;
  if ("status" in error && Number(error.status) === 401) {
    return true;
  }
  if (error instanceof Error) {
    return error.message.includes("(401)");
  }
  return false;
}

function formatCurrency(value) {
  return `NT$ ${Number(value || 0).toLocaleString()}`;
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function statusTone(status) {
  const map = {
    inquiring: t("dashboard.status_pending"),
    waiting_quote: t("dashboard.status_pending"),
    quoted: t("dashboard.status_quoted"),
    buyer_accepted: t("dashboard.status_buyer_accepted"),
    proof_uploaded: t("dashboard.status_proof_uploaded"),
    paid: t("dashboard.status_paid"),
    completed: t("dashboard.status_completed"),
  };
  return map[String(status || "")] || String(status || "-");
}

function openRoom(roomId) {
  const id = Number(roomId);
  if (!Number.isInteger(id) || id <= 0) return;
  router.push(`/comm-room/${id}?from=dashboard`);
}

function browseCollections() {
  router.push("/collections");
}

function navigateBoard(section) {
  router.push(`/dashboard/${section}`);
}

async function loadSalon() {
  loading.value = true;
  isError.value = false;
  statusText.value = "";
  try {
    const result = await fetchPrivateSalon();
    salon.value = {
      ...salon.value,
      ...result,
    };
    if (typeof window !== "undefined") {
      window.localStorage.setItem("wakou_unread_count", String(result.notifications?.unread || 0));
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : t("dashboard.load_failed");
    if (isUnauthorizedError(error)) {
      authStore.logout();
      await router.push("/login");
      return;
    }
    try {
      const [growth, orderResp, roomResp] = await Promise.all([fetchUserGrowth(), fetchMyOrders(), fetchMyCommRooms()]);
      salon.value.membership = growth.membership || salon.value.membership;
      salon.value.points = growth.points || salon.value.points;
      salon.value.orders = orderResp.items || [];
      salon.value.rooms = roomResp.items || [];
      statusText.value = "私人藏室延伸資料載入中，已先顯示核心資訊。";
      isError.value = false;
    } catch (fallbackError) {
      if (isUnauthorizedError(fallbackError)) {
        authStore.logout();
        await router.push("/login");
        return;
      }
      isError.value = true;
      statusText.value = message;
    }
  } finally {
    loading.value = false;
  }
}

async function saveDisplayName() {
  const next = profileForm.displayName.trim();
  if (!next) {
    isError.value = true;
    statusText.value = t("dashboard.display_name_empty");
    return;
  }
  isError.value = false;
  statusText.value = "";
  try {
    const updated = await updateMyDisplayName(next);
    const name = updated?.display_name || next;
    authStore.setDisplayName(name);
    profileForm.displayName = name;
    statusText.value = t("dashboard.updated");
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : t("dashboard.update_failed");
  }
}

onMounted(loadSalon);
</script>

<template>
  <div class="salon container">
    <header class="head">
      <p class="head-ja">{{ authStore.displayName || $t('dashboard.member_default') }}{{ $t('dashboard.my_page') }}</p>
      <p class="head-en">My Page</p>
    </header>

    <section class="point-card" aria-label="my points">
      <p class="point-label">{{ $t('dashboard.points_label') }}</p>
      <p class="point-value">{{ salon.points?.balance || 0 }}<span>pt</span></p>
      <p class="point-meta">{{ $t('dashboard.level_label') }}{{ membershipSnapshot.level }}</p>
      <p class="point-spent">{{ $t('dashboard.spent_label') }}{{ Number(membershipSnapshot.totalSpentTwd || 0).toLocaleString() }}</p>
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

    <section class="member-edit" aria-label="member info">
      <p class="member-mail">{{ authStore.email }}</p>
      <div class="member-form">
        <input v-model="profileForm.displayName" class="member-field" type="text" maxlength="24" :placeholder="$t('dashboard.display_name_placeholder')" />
        <button class="member-btn" type="button" @click="saveDisplayName">{{ $t('dashboard.update_btn') }}</button>
      </div>
      <p v-if="statusText" class="status" :class="isError ? 'error' : 'ok'">{{ statusText }}</p>
    </section>

    <section class="board" aria-label="dashboard rows">
      <article class="board-row" role="button" tabindex="0" @click="navigateBoard('timeline')" @keydown.enter="navigateBoard('timeline')">
        <div class="row-head">
          <p class="row-ja">{{ $t('dashboard.timeline_title') }}</p>
          <p class="row-en">Purchase history</p>
        </div>
        <p class="row-desc">{{ (salon.timeline || []).length === 0 ? $t('dashboard.timeline_empty') : $t('dashboard.timeline_count', { n: (salon.timeline || []).length }) }}</p>
        <button class="row-link row-tail" type="button" @click.stop="navigateBoard('timeline')"><span class="row-count">{{ orderCount }} {{ $t('dashboard.unit_count') }}</span><span class="row-arrow">&gt;</span></button>
      </article>

      <article class="board-row" role="button" tabindex="0" @click="navigateBoard('rooms')" @keydown.enter="navigateBoard('rooms')">
        <div class="row-head">
          <p class="row-ja">{{ $t('dashboard.rooms_title') }}</p>
          <p class="row-en">Consultation rooms</p>
        </div>
        <p class="row-desc">{{ roomCount === 0 ? $t('dashboard.rooms_empty') : $t('dashboard.rooms_count', { n: roomCount }) }}</p>
        <button class="row-link row-tail" type="button" @click.stop="navigateBoard('rooms')"><span class="row-count">{{ roomCount }} {{ $t('dashboard.unit_room') }}</span><span class="row-arrow">&gt;</span></button>
      </article>

      <article class="board-row" role="button" tabindex="0" @click="navigateBoard('orders')" @keydown.enter="navigateBoard('orders')">
        <div class="row-head">
          <p class="row-ja">{{ $t('dashboard.orders_title') }}</p>
          <p class="row-en">Order history</p>
        </div>
        <p class="row-desc">{{ recentOrders.length === 0 ? $t('dashboard.orders_empty') : $t('dashboard.orders_count', { n: recentOrders.length }) }}</p>
        <button class="row-link row-tail" type="button" @click.stop="navigateBoard('orders')"><span class="row-count">{{ recentOrders.length }} {{ $t('dashboard.unit_count') }}</span><span class="row-arrow">&gt;</span></button>
      </article>

      <article class="board-row" role="button" tabindex="0" @click="navigateBoard('messages')" @keydown.enter="navigateBoard('messages')">
        <div class="row-head">
          <p class="row-ja">{{ $t('dashboard.messages_title') }}</p>
          <p class="row-en">Notifications</p>
        </div>
        <p class="row-desc">{{ recentNotifications.length === 0 ? $t('dashboard.messages_empty') : $t('dashboard.messages_count', { n: recentNotifications.length }) }}</p>
        <button class="row-link row-tail" type="button" @click.stop="navigateBoard('messages')"><span class="row-count">{{ unreadCount }} {{ $t('dashboard.unit_unread') }}</span><span class="row-arrow">&gt;</span></button>
      </article>

      <article class="board-row" role="button" tabindex="0" @click="navigateBoard('coupons')" @keydown.enter="navigateBoard('coupons')">
        <div class="row-head">
          <p class="row-ja">{{ $t('dashboard.coupons_title') }}</p>
          <p class="row-en">My coupons</p>
        </div>
        <p class="row-desc">{{ $t('dashboard.coupons_desc') }}</p>
        <button class="row-link" type="button" @click.stop="navigateBoard('coupons')">&gt;</button>
      </article>

      <article class="board-row" role="button" tabindex="0" @click="navigateBoard('gacha')" @keydown.enter="navigateBoard('gacha')">
        <div class="row-head">
          <p class="row-ja">{{ $t('dashboard.gacha_title') }}</p>
          <p class="row-en">Lucky draw</p>
        </div>
        <p class="row-desc">{{ $t('dashboard.gacha_desc') }}</p>
        <button class="row-link" type="button" @click.stop="navigateBoard('gacha')">&gt;</button>
      </article>

      <article class="board-row" role="button" tabindex="0" @click="navigateBoard('points')" @keydown.enter="navigateBoard('points')">
        <div class="row-head">
          <p class="row-ja">{{ $t('dashboard.points_title') }}</p>
          <p class="row-en">Point history</p>
        </div>
        <p class="row-desc">{{ (salon.points?.items || []).length === 0 ? $t('dashboard.points_empty') : $t('dashboard.points_count', { n: (salon.points?.items || []).length }) }}</p>
        <button class="row-link" type="button" @click.stop="navigateBoard('points')">&gt;</button>
      </article>

      <article class="board-row" role="button" tabindex="0" @click="router.push('/dashboard/timeline')" @keydown.enter="router.push('/dashboard/timeline')">
        <div class="row-head">
          <p class="row-ja">{{ $t('dashboard.shipment_title') }}</p>
          <p class="row-en">Shipment tracking</p>
        </div>
        <p class="row-desc">{{ $t('dashboard.shipment_desc') }}</p>
        <button class="row-link" type="button" @click.stop="router.push('/dashboard/timeline')">&gt;</button>
      </article>
    </section>

    <section v-if="loading" class="state-msg">{{ $t('dashboard.loading') }}</section>
    <section v-if="isError && statusText" class="state-msg error">{{ statusText }}</section>
  </div>
</template>

<style scoped>
.salon {
  color: #1b2740;
  display: grid;
  gap: 2.2rem;
  max-width: 980px;
  padding-bottom: 6rem;
  padding-top: 2.8rem;
}

.head {
  color: #1d2d4a;
  text-align: center;
}

.head-ja {
  font-family: var(--font-sans);
  font-size: 1.7rem;
  font-weight: 400;
  letter-spacing: 0.01em;
  margin: 0;
}

.head-en {
  color: #425a79;
  font-size: 0.96rem;
  margin: 0.35rem 0 0;
}

.point-card {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid #d4d9df;
  justify-self: center;
  max-width: 320px;
  padding: 2.2rem 2rem;
  text-align: center;
  width: 100%;
}

.point-label {
  color: #324765;
  font-size: 0.9rem;
  letter-spacing: 0.02em;
  margin: 0;
}

.point-value {
  font-family: var(--font-sans);
  font-size: 2.2rem;
  font-weight: 400;
  line-height: 1.1;
  margin: 0.6rem 0 0.4rem;
}

.point-value span {
  font-size: 1.25rem;
  margin-left: 0.2rem;
}

.point-meta {
  color: #4c5e78;
  font-size: 0.9rem;
  margin: 0;
}

.point-spent,
.point-upgrade {
  margin: 0.3rem 0 0;
}

.point-spent {
  color: #3a4d6a;
  font-size: 0.84rem;
}

.point-upgrade {
  color: #5d3f1f;
  font-size: 0.8rem;
}

.tier-track {
  margin-top: 0.9rem;
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
  text-align: left;
}

.tier-step.active {
  color: #253853;
}

.tier-step strong {
  font-size: 0.68rem;
  font-weight: 600;
}

.tier-step small {
  font-size: 0.62rem;
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

.member-edit {
  border-bottom: 1px solid #d4d9df;
  border-top: 1px solid #d4d9df;
  padding: 1rem 0 1.2rem;
}

.member-mail {
  color: #3d4f69;
  font-size: 0.98rem;
  margin: 0;
}

.member-form {
  border-top: 1px solid #d4d9df;
  display: grid;
  gap: 0.8rem;
  grid-template-columns: 1fr auto;
  margin-top: 0.8rem;
  padding-top: 0.8rem;
}

.member-field {
  background: transparent;
  border: 0;
  color: #1b2740;
  font-size: 1rem;
  outline: 0;
}

.member-btn {
  background: transparent;
  border: 1px solid #bcc5d1;
  color: #2b3e58;
  cursor: pointer;
  font-size: 0.82rem;
  letter-spacing: 0.06em;
  min-width: 92px;
  padding: 0.45rem 0.8rem;
}

.board {
  border-bottom: 1px solid #d4d9df;
  border-top: 1px solid #d4d9df;
}

.board-row {
  align-items: center;
  border-bottom: 1px solid #d4d9df;
  column-gap: 1.2rem;
  cursor: pointer;
  display: grid;
  grid-template-columns: minmax(180px, 1.05fr) minmax(260px, 1.7fr) auto;
  min-height: 88px;
  padding: 0.5rem 0;
}

.board-row:hover {
  background: rgba(255, 255, 255, 0.18);
}

.board-row:focus-visible {
  outline: 1px solid #bcc5d1;
  outline-offset: -1px;
}

.board-row:last-child {
  border-bottom: 0;
}

.row-head {
  display: grid;
  gap: 0.2rem;
}

.row-head-sub .row-ja {
  font-size: 1.1rem;
}

.row-ja {
  color: #182a47;
  font-size: 1.62rem;
  font-weight: 400;
  letter-spacing: 0.01em;
  line-height: 1.2;
  margin: 0;
}

.row-en {
  color: #3c506e;
  font-size: 0.9rem;
  letter-spacing: 0.01em;
  margin: 0;
}

.row-tail {
  align-items: center;
  display: flex;
  gap: 0.7rem;
}

.row-count {
  border: 1px solid #ced5df;
  color: #3f536f;
  font-size: 0.76rem;
  letter-spacing: 0.06em;
  padding: 0.24rem 0.46rem;
}

.row-arrow {
  color: #22395a;
  font-size: 0.9rem;
  line-height: 1;
}

.row-desc {
  color: #324867;
  font-size: 0.92rem;
  line-height: 1.55;
  margin: 0;
}

.row-link {
  background: transparent;
  border: 0;
  color: #22395a;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  font-size: 0.95rem;
  padding: 0;
}

.status,
.state-msg {
  font-size: 0.88rem;
  margin: 0;
}

.status.ok {
  color: #2f7d4b;
}

.status.error,
.state-msg.error {
  color: #bc3c2a;
}

@media (max-width: 900px) {
  .member-form,
  .board-row {
    grid-template-columns: 1fr;
  }

  .board-row {
    gap: 0.6rem;
    min-height: 0;
    padding: 1rem 0;
  }

  .row-ja {
    font-size: 1.28rem;
  }

  .tier-track-steps {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
