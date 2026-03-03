<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { 
  fetchCommRoom, 
  sendMessage, 
  submitFinalQuote, 
  acceptQuote, 
  uploadTransferProof,
  uploadTransferProofFile,
  confirmPayment
} from "../../modules/comm-room/service";
import { normalizeMediaUrl } from "../../modules/comm-room/media-url";
import { useAuthStore } from "../../modules/auth/store";

const route = useRoute();
const authStore = useAuthStore();
const { t } = useI18n();
const room = ref(null);
const statusText = ref("");
const isError = ref(false);
const isManager = computed(() => ["admin", "super_admin", "sales"].includes(authStore.role));

const messageForm = reactive({
  message: "",
  image_url: "",
  offer_price_twd: null
});

const selectedImageName = ref("");

const quoteForm = reactive({
  final_price_twd: 0,
  shipping_fee_twd: 0,
  discount_twd: 0
});

const proofForm = reactive({
  transfer_proof_url: ""
});
const selectedProofFile = ref(null);
const selectedProofFileName = ref("");
const normalizedProofUrl = computed(() =>
  normalizeMediaUrl(room.value?.order?.transfer_proof_url || room.value?.transfer_proof_url || "")
);

const isProcessing = ref(false);
let refreshTimer = null;

async function loadRoom() {
  isError.value = false;
  try {
    room.value = await fetchCommRoom(route.params.id);
    if (isManager.value && room.value) {
      quoteForm.final_price_twd = room.value.order?.final_price_twd || room.value.order?.amount_twd || 0;
      quoteForm.shipping_fee_twd = room.value.order?.shipping_fee_twd || 0;
      quoteForm.discount_twd = room.value.order?.discount_twd || 0;
    }
  } catch (error) {
    isError.value = true;
    statusText.value = t("comm_room.load_error");
  }
}

async function sendChat() {
  if (!messageForm.message.trim() && !messageForm.image_url.trim() && !messageForm.offer_price_twd) return;
  isProcessing.value = true;
  isError.value = false;
  try {
    await sendMessage(route.params.id, {
      message: messageForm.message,
      image_url: messageForm.image_url,
      offer_price_twd: messageForm.offer_price_twd
    });
    messageForm.message = "";
    messageForm.image_url = "";
    messageForm.offer_price_twd = null;
    selectedImageName.value = "";
    await loadRoom();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Send failed";
  } finally {
    isProcessing.value = false;
  }
}

async function refreshRoomSilently() {
  if (!room.value || isProcessing.value) return;
  try {
    const latest = await fetchCommRoom(route.params.id);
    const previousMessageCount = Array.isArray(room.value?.messages) ? room.value.messages.length : 0;
    room.value = latest;
    const latestCount = Array.isArray(latest?.messages) ? latest.messages.length : 0;
    if (latestCount > previousMessageCount) {
      statusText.value = "對話已同步最新內容";
    }
  } catch (_) {
    // silent refresh should not interrupt typing flow
  }
}

function handleImageFileChange(event) {
  const file = event?.target?.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    isError.value = true;
    statusText.value = "請選擇圖片檔案";
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    messageForm.image_url = typeof reader.result === "string" ? reader.result : "";
    selectedImageName.value = file.name;
  };
  reader.readAsDataURL(file);
}

async function submitQuote() {
  isProcessing.value = true;
  isError.value = false;
  try {
    await submitFinalQuote(route.params.id, quoteForm);
    statusText.value = t("comm_room.quote_sent");
    await loadRoom();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Quote failed";
  } finally {
    isProcessing.value = false;
  }
}

async function handleAcceptQuote() {
  isProcessing.value = true;
  isError.value = false;
  try {
    await acceptQuote(route.params.id);
    statusText.value = t("comm_room.quote_accepted");
    await loadRoom();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Accept failed";
  } finally {
    isProcessing.value = false;
  }
}

async function submitProof() {
  if (!proofForm.transfer_proof_url.trim() && !selectedProofFile.value) return;
  isProcessing.value = true;
  isError.value = false;
  try {
    if (selectedProofFile.value) {
      const uploaded = await uploadTransferProofFile(route.params.id, selectedProofFile.value);
      proofForm.transfer_proof_url = uploaded.transfer_proof_url || "";
      selectedProofFile.value = null;
      selectedProofFileName.value = "";
    } else {
      await uploadTransferProof(route.params.id, { transfer_proof_url: proofForm.transfer_proof_url });
    }
    statusText.value = t("comm_room.proof_uploaded_msg");
    await loadRoom();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Upload proof failed";
  } finally {
    isProcessing.value = false;
  }
}

function handleProofFileChange(event) {
  const file = event?.target?.files?.[0];
  if (!file) {
    selectedProofFile.value = null;
    selectedProofFileName.value = "";
    return;
  }
  if (!file.type.startsWith("image/")) {
    isError.value = true;
    statusText.value = "請選擇圖片檔案";
    selectedProofFile.value = null;
    selectedProofFileName.value = "";
    return;
  }
  selectedProofFile.value = file;
  selectedProofFileName.value = file.name;
}

async function handleConfirmPayment() {
  isProcessing.value = true;
  isError.value = false;
  try {
    await confirmPayment(room.value.order_id);
    statusText.value = t("comm_room.payment_confirmed");
    await loadRoom();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Confirm payment failed";
  } finally {
    isProcessing.value = false;
  }
}

function formatDate(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleString();
}

function messageImageUrl(message) {
  return normalizeMediaUrl(message?.image_url || "");
}

onMounted(async () => {
  await loadRoom();
  refreshTimer = setInterval(() => {
    refreshRoomSilently();
  }, 5000);
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
});
</script>

<template>
  <div class="room-page container">
    <header class="page-header">
      <p class="eyebrow">Exclusive Service</p>
      <h1 class="page-title">{{ $t("nav.concierge") }}</h1>
      <p class="page-meta">{{ $t('comm_room.page_meta') }}</p>
    </header>

    <div class="divider"></div>

    <div v-if="!room && !isError" class="state-msg">Loading communication thread...</div>
    <div v-else-if="isError && !room" class="state-msg error">{{ statusText }}</div>

    <div v-else class="room-layout">
      <aside class="product-column panel">
        <div class="product-thumb">
          <img :src="room.product_image_url || '/logo-transparent.png'" :alt="room.product_name" />
        </div>
        <div class="product-info">
          <h3>{{ room.product_name }}</h3>
          <p class="meta">{{ $t('comm_room.price_label') }}: NT$ {{ (room.order?.amount_twd || 0).toLocaleString() }}</p>
          <div class="order-status-box">
            <span class="status-badge" :class="room.order?.status">{{ room.order?.status }}</span>
          </div>
        </div>

        <div class="quote-summary" v-if="room.order?.status !== 'inquiring' && room.order?.status !== 'waiting_quote'">
          <div class="quote-row">
            <span>{{ $t('comm_room.thread_price_label') }}</span>
            <span>NT$ {{ (room.order?.final_price_twd || 0).toLocaleString() }}</span>
          </div>
          <div class="quote-row">
            <span>{{ $t('comm_room.shipping_label') }}</span>
            <span>NT$ {{ (room.order?.shipping_fee_twd || 0).toLocaleString() }}</span>
          </div>
          <div class="quote-row discount" v-if="room.order?.discount_twd">
            <span>{{ $t('comm_room.discount_label') }}</span>
            <span>- NT$ {{ (room.order?.discount_twd || 0).toLocaleString() }}</span>
          </div>
          <div class="quote-row total">
            <span>{{ $t('comm_room.total_label') }}</span>
            <span>NT$ {{ ((room.order?.final_price_twd || 0) + (room.order?.shipping_fee_twd || 0) - (room.order?.discount_twd || 0)).toLocaleString() }}</span>
          </div>
        </div>
      </aside>

      <section class="thread-column panel">
        <header class="thread-header">
          <div class="thread-meta">
            <span class="room-id">Room #{{ room.id }} (Order #{{ room.order_id }})</span>
            <span class="buyer-email">買家: {{ room.buyer_email }}</span>
          </div>
        </header>

        <div class="message-list">
          <div 
            v-for="msg in room.messages" 
            :key="msg.id"
            class="message"
            :class="msg.from === 'system' ? 'msg-system' : (msg.from === 'admin' ? 'msg-admin' : 'msg-buyer')"
          >
            <div v-if="msg.from !== 'system'" class="msg-avatar">{{ msg.from === 'admin' ? 'W' : 'B' }}</div>
            <div class="msg-body">
              <span v-if="msg.from !== 'system'" class="msg-sender">{{ msg.from === 'admin' ? $t('comm_room.official_service') : $t('comm_room.buyer_label') }}</span>
              <div v-if="msg.from === 'system'" class="system-text">{{ msg.message }} <span class="time">{{ formatDate(msg.timestamp) }}</span></div>
              <div v-else class="msg-bubble">
                <p v-if="msg.message" class="msg-text">{{ msg.message }}</p>
                <div v-if="msg.offer_price_twd" class="offer-tag">議價提案：NT$ {{ Number(msg.offer_price_twd).toLocaleString() }}</div>
                <div v-if="messageImageUrl(msg)" class="msg-image-wrap">
                  <img :src="messageImageUrl(msg)" alt="Attached image" class="msg-image" />
                  <div v-if="msg.from === 'admin'" class="cert-badge">{{ $t('comm_room.cert_badge') }}</div>
                </div>
                <span class="time-meta">{{ formatDate(msg.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-area" v-if="room.order?.status !== 'paid' && room.order?.status !== 'completed'">
          <form @submit.prevent="sendChat" class="chat-form">
            <input v-model="messageForm.image_url" type="text" class="field compact" :placeholder="$t('comm_room.placeholder_image')" />
            <div class="input-row">
              <input class="field" type="file" accept="image/*" @change="handleImageFileChange" />
              <input v-model.number="messageForm.offer_price_twd" type="number" min="0" class="field" placeholder="議價提案金額 (選填)" />
            </div>
            <p v-if="selectedImageName" class="file-hint">已選擇圖片：{{ selectedImageName }}</p>
            <div class="input-row">
              <input v-model="messageForm.message" type="text" class="field" :placeholder="$t('comm_room.placeholder_message')" />
              <button class="btn btn-primary" type="submit" :disabled="isProcessing">{{ $t('comm_room.send') }}</button>
            </div>
          </form>
        </div>
      </section>

      <aside class="action-column panel">
        <h3>{{ $t('comm_room.action_title') }}</h3>
        <p v-if="statusText" class="status-msg" :class="isError ? 'status-err' : 'status-ok'">{{ statusText }}</p>

        <form v-if="isManager && (room.order?.status === 'inquiring' || room.order?.status === 'waiting_quote' || room.order?.status === 'quoted')" class="action-block" @submit.prevent="submitQuote">
          <h4>{{ $t('comm_room.set_quote') }}</h4>
          <div class="form-group">
            <label>{{ $t('comm_room.price_field') }}</label>
            <input v-model.number="quoteForm.final_price_twd" class="field" type="number" min="0" required />
          </div>
          <div class="form-group">
            <label>{{ $t('comm_room.shipping_field') }}</label>
            <input v-model.number="quoteForm.shipping_fee_twd" class="field" type="number" min="0" required />
          </div>
          <div class="form-group">
            <label>{{ $t('comm_room.discount_field') }}</label>
            <input v-model.number="quoteForm.discount_twd" class="field" type="number" min="0" />
          </div>
          <button class="btn btn-muted w-full" type="submit" :disabled="isProcessing">{{ $t('comm_room.send_quote') }}</button>
        </form>

        <div v-if="!isManager && room.order?.status === 'quoted'" class="action-block">
          <h4>{{ $t('comm_room.accept_quote_title') }}</h4>
          <p class="meta mb-4">{{ $t('comm_room.accept_quote_hint') }}</p>
          <button class="btn btn-primary w-full" @click="handleAcceptQuote" :disabled="isProcessing">{{ $t('comm_room.accept_quote_btn') }}</button>
        </div>

        <form v-if="!isManager && (room.order?.status === 'buyer_accepted' || room.order?.status === 'proof_uploaded')" class="action-block" @submit.prevent="submitProof">
          <h4>{{ $t('comm_room.bank_title') }}</h4>
          <div class="bank-details">
            <p>{{ $t('comm_room.bank_name') }}</p>
            <p>{{ $t('comm_room.bank_account') }}</p>
            <p>{{ $t('comm_room.bank_holder') }}</p>
          </div>
          <p class="meta mt-2 mb-2">{{ $t('comm_room.upload_hint') }}</p>
          <div class="form-group">
            <input class="field" type="file" accept="image/*" @change="handleProofFileChange" />
            <p v-if="selectedProofFileName" class="file-hint">已選擇憑證圖片：{{ selectedProofFileName }}</p>
            <input v-model="proofForm.transfer_proof_url" class="field mt-2" type="text" placeholder="https://... (圖片網址，可選)" />
          </div>
          <button class="btn btn-primary w-full" type="submit" :disabled="isProcessing">
            {{ room.order?.status === 'proof_uploaded' ? $t('comm_room.reupload_proof') : $t('comm_room.upload_proof') }}
          </button>
        </form>

        <div v-if="isManager && room.order?.status === 'proof_uploaded'" class="action-block">
          <h4>{{ $t('comm_room.confirm_payment_title') }}</h4>
          <p class="meta mb-2">{{ $t('comm_room.proof_url_label') }}</p>
          <a v-if="normalizedProofUrl" :href="normalizedProofUrl" target="_blank" class="proof-link">{{ normalizedProofUrl }}</a>
          <p v-else class="meta">尚未提供可用圖片網址</p>
          <button class="btn btn-primary w-full mt-4" @click="handleConfirmPayment" :disabled="isProcessing">{{ $t('comm_room.confirm_payment_btn') }}</button>
        </div>

        <div v-if="room.order?.status === 'paid' || room.order?.status === 'completed'" class="action-block success-block">
          <h4>{{ $t('comm_room.completed_title') }}</h4>
          <p class="meta">{{ $t('comm_room.completed_desc') }}</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.room-layout {
  align-items: flex-start;
  display: grid;
  gap: 1.5rem;
  grid-template-columns: 260px 1fr 300px;
  padding-bottom: 4rem;
}

.product-thumb img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 4px;
}

.product-info {
  margin-top: 1rem;
}

.product-info h3 {
  font-size: 1.1rem;
  margin-bottom: 0.4rem;
}

.order-status-box {
  margin-top: 0.8rem;
}

.status-badge {
  background: var(--ink-200);
  color: var(--ink-800);
  padding: 0.3rem 0.6rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  border-radius: 4px;
}

.status-badge.paid, .status-badge.completed {
  background: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}

.status-badge.buyer_accepted, .status-badge.proof_uploaded {
  background: #fdf6ec;
  color: #e6a23c;
  border: 1px solid #faecd8;
}

.quote-summary {
  margin-top: 1.5rem;
  border-top: 1px solid var(--paper-200);
  padding-top: 1rem;
  display: grid;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.quote-row {
  display: flex;
  justify-content: space-between;
}

.quote-row.discount {
  color: var(--danger-500);
}

.quote-row.total {
  border-top: 1px solid var(--paper-200);
  padding-top: 0.5rem;
  font-weight: bold;
  font-size: 1.1rem;
}

.thread-column {
  display: flex;
  flex-direction: column;
  height: 700px;
  padding: 0;
}

.thread-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--paper-200);
}

.room-id {
  font-family: monospace;
  color: var(--ink-500);
  display: block;
}

.buyer-email {
  font-weight: 500;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  background: var(--paper-100);
}

.message {
  display: flex;
  gap: 0.8rem;
  max-width: 85%;
}

.msg-admin {
  align-self: flex-start;
}

.msg-buyer {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.msg-system {
  align-self: center;
  max-width: 100%;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--paper-300);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  flex-shrink: 0;
}

.msg-admin .msg-avatar {
  background: var(--ink-800);
  color: white;
}

.msg-buyer .msg-avatar {
  background: var(--ink-200);
}

.msg-body {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.msg-buyer .msg-body {
  align-items: flex-end;
}

.msg-sender {
  font-size: 0.75rem;
  color: var(--ink-500);
}

.msg-bubble {
  background: white;
  padding: 0.8rem 1rem;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.msg-buyer .msg-bubble {
  background: var(--paper-300);
  color: var(--ink-900);
}

.msg-text {
  margin: 0;
  line-height: 1.5;
  white-space: pre-wrap;
}

.msg-image-wrap {
  margin-top: 0.5rem;
}

.msg-image {
  max-width: 100%;
  border-radius: 4px;
}

.offer-tag {
  margin-top: 0.4rem;
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: #fdf6ec;
  color: #b88230;
  font-size: 0.75rem;
  font-weight: 600;
}

.cert-badge {
  font-size: 0.7rem;
  color: #e6a23c;
  margin-top: 0.3rem;
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

.time-meta {
  font-size: 0.65rem;
  color: var(--ink-400);
  display: block;
  text-align: right;
  margin-top: 0.3rem;
}

.msg-buyer .time-meta {
  color: var(--ink-500);
}

.system-text {
  font-size: 0.8rem;
  color: var(--ink-500);
  background: var(--paper-200);
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  text-align: center;
}

.system-text .time {
  font-size: 0.7rem;
  margin-left: 0.5rem;
  opacity: 0.7;
}

.chat-input-area {
  padding: 1rem 1.5rem;
  background: white;
  border-top: 1px solid var(--paper-200);
}

.chat-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.input-row {
  display: flex;
  gap: 0.5rem;
}

.input-row .field {
  flex: 1;
  margin: 0;
}

.field.compact {
  padding: 0.4rem 0.6rem;
  font-size: 0.8rem;
  margin: 0;
}

.file-hint {
  margin: 0;
  font-size: 0.72rem;
  color: var(--ink-500);
}

.action-column h3 {
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--paper-200);
}

.action-block {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--paper-100);
  border-radius: 4px;
}

.action-block h4 {
  margin-bottom: 0.8rem;
  font-size: 0.95rem;
}

.bank-details {
  background: white;
  padding: 0.8rem;
  border: 1px dashed var(--paper-300);
  font-family: monospace;
  font-size: 0.9rem;
  line-height: 1.6;
}

.proof-link {
  color: var(--ink-600);
  word-break: break-all;
  font-size: 0.85rem;
}

.success-block {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  color: #67c23a;
}

.w-full {
  width: 100%;
}
.mt-2 { margin-top: 0.5rem; }
.mt-4 { margin-top: 1rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-4 { margin-bottom: 1rem; }
</style>
