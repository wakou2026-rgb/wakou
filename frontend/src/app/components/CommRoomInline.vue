<script setup>
import { defineProps, defineEmits } from "vue";
const props = defineProps({
  roomId: {
    type: Number,
    required: true
  }
});
const emit = defineEmits(["close"]);

import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { 
  fetchCommRoom, 
  sendMessage, 
  submitFinalQuote, 
  acceptQuote, 
  uploadTransferProof,
  confirmPayment
} from "../../modules/comm-room/service";
import { useAuthStore } from "../../modules/auth/store";

const route = useRoute();
const authStore = useAuthStore();
const room = ref(null);
const statusText = ref("");
const isError = ref(false);
const isManager = computed(() => ["admin", "super_admin", "sales"].includes(authStore.role));

const messageForm = reactive({
  message: "",
  image_url: ""
});

const quoteForm = reactive({
  final_price_twd: 0,
  shipping_fee_twd: 0,
  discount_twd: 0
});

const proofForm = reactive({
  transfer_proof_url: ""
});

const isProcessing = ref(false);

async function loadRoom() {
  if (!props.roomId) return;
  isError.value = false;
  try {
    room.value = await fetchCommRoom(props.roomId);
    if (isManager.value && room.value) {
      quoteForm.final_price_twd = room.value.order?.final_price_twd || room.value.order?.amount_twd || 0;
      quoteForm.shipping_fee_twd = room.value.order?.shipping_fee_twd || 0;
      quoteForm.discount_twd = room.value.order?.discount_twd || 0;
    }
  } catch (error) {
    isError.value = true;
    statusText.value = "目前無法讀取此溝通室。請先從個人後台建立訂單後再進入。";
  }
}

async function sendChat() {
  if (!messageForm.message.trim() && !messageForm.image_url.trim()) return;
  isProcessing.value = true;
  isError.value = false;
  try {
    await sendMessage(props.roomId, {
      message: messageForm.message,
      image_url: messageForm.image_url
    });
    messageForm.message = "";
    messageForm.image_url = "";
    await loadRoom();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Send failed";
  } finally {
    isProcessing.value = false;
  }
}

async function submitQuote() {
  isProcessing.value = true;
  isError.value = false;
  try {
    await submitFinalQuote(props.roomId, quoteForm);
    statusText.value = "報價已更新並送出給買家。";
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
    await acceptQuote(props.roomId);
    statusText.value = "已接受報價，請繼續上傳匯款證明。";
    await loadRoom();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Accept failed";
  } finally {
    isProcessing.value = false;
  }
}

async function submitProof() {
  if (!proofForm.transfer_proof_url.trim()) return;
  isProcessing.value = true;
  isError.value = false;
  try {
    await uploadTransferProof(props.roomId, { transfer_proof_url: proofForm.transfer_proof_url });
    statusText.value = "匯款證明已上傳，等待管理員確認。";
    await loadRoom();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Upload proof failed";
  } finally {
    isProcessing.value = false;
  }
}

async function handleConfirmPayment() {
  isProcessing.value = true;
  isError.value = false;
  try {
    await confirmPayment(room.value.order_id);
    statusText.value = "已確認收款，訂單完成。";
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

onMounted(loadRoom);
</script>

<template>
  <div class="room-page container" style="max-width: 1400px; padding-top: 2rem; height: 100%; display: flex; flex-direction: column;">
    <header class="page-header">
      <p class="eyebrow">Exclusive Service</p>
      <div class="header-actions" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
        <h1 class="page-title">{{ $t("nav.concierge") }}</h1>
        <button class="btn btn-muted" @click="emit('close')">關閉 (X)</button>
      </div>
      <p class="page-meta">專屬諮詢室：請於此確認商品細節、實物照及最終報價。</p>
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
          <p class="meta">原價: NT$ {{ (room.order?.amount_twd || 0).toLocaleString() }}</p>
          <div class="order-status-box">
            <span class="status-badge" :class="room.order?.status">{{ room.order?.status }}</span>
          </div>
        </div>

        <div class="quote-summary" v-if="room.order?.status !== 'inquiring' && room.order?.status !== 'waiting_quote'">
          <div class="quote-row">
            <span>議定商品價</span>
            <span>NT$ {{ (room.order?.final_price_twd || 0).toLocaleString() }}</span>
          </div>
          <div class="quote-row">
            <span>運費</span>
            <span>NT$ {{ (room.order?.shipping_fee_twd || 0).toLocaleString() }}</span>
          </div>
          <div class="quote-row discount" v-if="room.order?.discount_twd">
            <span>優惠折抵</span>
            <span>- NT$ {{ (room.order?.discount_twd || 0).toLocaleString() }}</span>
          </div>
          <div class="quote-row total">
            <span>總計</span>
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
              <span v-if="msg.from !== 'system'" class="msg-sender">{{ msg.from === 'admin' ? '官方客服' : '買家' }}</span>
              <div v-if="msg.from === 'system'" class="system-text">{{ msg.message }} <span class="time">{{ formatDate(msg.timestamp) }}</span></div>
              <div v-else class="msg-bubble">
                <p v-if="msg.message" class="msg-text">{{ msg.message }}</p>
                <div v-if="msg.image_url" class="msg-image-wrap">
                  <img :src="msg.image_url" alt="Attached image" class="msg-image" />
                  <div v-if="msg.from === 'admin'" class="cert-badge">✓ 官方認證實拍</div>
                </div>
                <span class="time-meta">{{ formatDate(msg.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-area" v-if="room.order?.status !== 'paid' && room.order?.status !== 'completed'">
          <form @submit.prevent="sendChat" class="chat-form">
            <input v-model="messageForm.image_url" type="text" class="field compact" placeholder="圖片網址 (選填)" />
            <div class="input-row">
              <input v-model="messageForm.message" type="text" class="field" placeholder="輸入訊息..." />
              <button class="btn btn-primary" type="submit" :disabled="isProcessing">發送</button>
            </div>
          </form>
        </div>
      </section>

      <aside class="action-column panel">
        <h3>交易操作</h3>
        <p v-if="statusText" class="status-msg" :class="isError ? 'status-err' : 'status-ok'">{{ statusText }}</p>

        <form v-if="isManager && (room.order?.status === 'inquiring' || room.order?.status === 'waiting_quote' || room.order?.status === 'quoted')" class="action-block" @submit.prevent="submitQuote">
          <h4>設定最終報價</h4>
          <div class="form-group">
            <label>議定商品價格 (NT$)</label>
            <input v-model.number="quoteForm.final_price_twd" class="field" type="number" min="0" required />
          </div>
          <div class="form-group">
            <label>運費 (NT$)</label>
            <input v-model.number="quoteForm.shipping_fee_twd" class="field" type="number" min="0" required />
          </div>
          <div class="form-group">
            <label>優惠折抵 (NT$)</label>
            <input v-model.number="quoteForm.discount_twd" class="field" type="number" min="0" />
          </div>
          <button class="btn btn-muted w-full" type="submit" :disabled="isProcessing">發送最終報價</button>
        </form>

        <div v-if="!isManager && room.order?.status === 'quoted'" class="action-block">
          <h4>管理員已提供最終報價</h4>
          <p class="meta mb-4">請確認左側總計金額，若同意請點擊下方按鈕。</p>
          <button class="btn btn-primary w-full" @click="handleAcceptQuote" :disabled="isProcessing">接受報價並前往付款</button>
        </div>

        <form v-if="!isManager && (room.order?.status === 'buyer_accepted' || room.order?.status === 'proof_uploaded')" class="action-block" @submit.prevent="submitProof">
          <h4>匯款資訊</h4>
          <div class="bank-details">
            <p>銀行：和光銀行 (808)</p>
            <p>帳號：1234-567-890123</p>
            <p>戶名：和光精選有限公司</p>
          </div>
          <p class="meta mt-2 mb-2">請完成匯款後，上傳匯款截圖或憑證網址。</p>
          <div class="form-group">
            <input v-model="proofForm.transfer_proof_url" class="field" type="text" placeholder="https://... (圖片網址)" required />
          </div>
          <button class="btn btn-primary w-full" type="submit" :disabled="isProcessing">
            {{ room.order?.status === 'proof_uploaded' ? '重新上傳憑證' : '送出匯款證明' }}
          </button>
        </form>

        <div v-if="isManager && room.order?.status === 'proof_uploaded'" class="action-block">
          <h4>買家已上傳匯款證明</h4>
          <p class="meta mb-2">憑證網址：</p>
          <a :href="room.order?.transfer_proof_url" target="_blank" class="proof-link">{{ room.order?.transfer_proof_url }}</a>
          <button class="btn btn-primary w-full mt-4" @click="handleConfirmPayment" :disabled="isProcessing">確認收款 (完成訂單)</button>
        </div>

        <div v-if="room.order?.status === 'paid' || room.order?.status === 'completed'" class="action-block success-block">
          <h4>交易已完成</h4>
          <p class="meta">款項已確認，商品將盡快安排出貨。</p>
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
  height: calc(100vh - 180px);
  overflow: hidden;
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
  height: 100%;
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
  background: var(--ink-800);
  color: white;
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
  color: rgba(255,255,255,0.6);
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
