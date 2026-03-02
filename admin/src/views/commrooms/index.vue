<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import {
  getCommRooms,
  getCommRoom,
  postAdminMessage,
  setRoomStatus,
  setFinalQuote,
  getNotificationConfig,
  saveNotificationConfig,
  type CommRoom,
  type NotificationConfig
} from "@/api/commRooms";
import { ElMessage } from "element-plus";
import { useRoute } from "vue-router";

defineOptions({ name: "CommRoomsIndex" });
const route = useRoute();

const activeTab = ref("rooms");
const roomsLoading = ref(false);
const rooms = ref<CommRoom[]>([]);
const selectedRoom = ref<CommRoom | null>(null);
const roomLoading = ref(false);
const replyText = ref("");
const replyImageUrl = ref("");
const replyOfferPrice = ref<number | null>(null);
const replyImageName = ref("");
const replySending = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

const quoteForm = ref({
  final_price_twd: 0,
  shipping_fee_twd: 0,
  discount_twd: 0,
  shipping_carrier: "",
  tracking_number: ""
});
const quoteSaving = ref(false);

const quotedTotal = computed(() =>
  (quoteForm.value.final_price_twd || 0) +
  (quoteForm.value.shipping_fee_twd || 0) -
  (quoteForm.value.discount_twd || 0)
);

const notifConfig = ref<Partial<NotificationConfig>>({
  discord_webhook_url: "",
  line_notify_token: "",
  email_recipients: ""
});
const notifSaving = ref(false);
let roomRefreshTimer: ReturnType<typeof setInterval> | null = null;

const formatNTD = (n: number | null | undefined) =>
  n != null ? "NT$" + n.toLocaleString() : "—";

const loadRooms = async () => {
  try {
    roomsLoading.value = true;
    const res: any = await getCommRooms();
    rooms.value = Array.isArray(res) ? res : res?.data || res?.items || [];
  } catch (e: any) {
    ElMessage.error(e?.message || "無法載入對話室列表");
  } finally {
    roomsLoading.value = false;
  }
};

const selectRoom = async (room: CommRoom) => {
  try {
    roomLoading.value = true;
    const res: any = await getCommRoom(room.id);
    const raw = res?.data ?? res;
    // Synthesize an `order` object from the flat room fields so the template
    // can use selectedRoom.order regardless of backend nesting.
    if (raw && !raw.order) {
      raw.order = {
        id: raw.order_id,
        amount_twd: raw.amount_twd ?? null,
        discount_twd: raw.discount_twd ?? 0,
        final_price_twd: raw.final_price_twd ?? null,
        shipping_fee_twd: raw.shipping_fee_twd ?? 0,
        final_amount_twd: raw.final_amount_twd ?? null,
        shipping_carrier: raw.shipping_carrier ?? null,
        tracking_number: raw.tracking_number ?? null,
        status: raw.status
      };
    }
    selectedRoom.value = raw;
    // populate quote form from order data
    const order = selectedRoom.value?.order;
    if (order) {
      quoteForm.value = {
        final_price_twd: order.final_price_twd ?? 0,
        shipping_fee_twd: order.shipping_fee_twd ?? 0,
        discount_twd: order.discount_twd ?? 0,
        shipping_carrier: order.shipping_carrier ?? "",
        tracking_number: order.tracking_number ?? ""
      };
    }
    await nextTick();
    scrollToBottom();
  } catch (e: any) {
    ElMessage.error(e?.message || "無法載入對話");
  } finally {
    roomLoading.value = false;
  }
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const sendReply = async () => {
  if (!selectedRoom.value) return;
  if (!replyText.value.trim() && !replyImageUrl.value.trim() && !replyOfferPrice.value) return;
  try {
    replySending.value = true;
    await postAdminMessage(selectedRoom.value.id, {
      message: replyText.value.trim(),
      image_url: replyImageUrl.value.trim() || undefined,
      offer_price_twd: replyOfferPrice.value || undefined
    });
    replyText.value = "";
    replyImageUrl.value = "";
    replyOfferPrice.value = null;
    replyImageName.value = "";
    await selectRoom(selectedRoom.value);
  } catch (e: any) {
    ElMessage.error(e?.message || "傳送失敗");
  } finally {
    replySending.value = false;
  }
};

const onReplyFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input?.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    ElMessage.error("請選擇圖片檔案");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    replyImageUrl.value = typeof reader.result === "string" ? reader.result : "";
    replyImageName.value = file.name;
  };
  reader.readAsDataURL(file);
};

const refreshSelectedRoomSilently = async () => {
  if (!selectedRoom.value || roomLoading.value || replySending.value || quoteSaving.value) return;
  try {
    const res: any = await getCommRoom(selectedRoom.value.id);
    const raw = res?.data ?? res;
    if (raw && !raw.order) {
      raw.order = {
        id: raw.order_id,
        amount_twd: raw.amount_twd ?? null,
        discount_twd: raw.discount_twd ?? 0,
        final_price_twd: raw.final_price_twd ?? null,
        shipping_fee_twd: raw.shipping_fee_twd ?? 0,
        final_amount_twd: raw.final_amount_twd ?? null,
        shipping_carrier: raw.shipping_carrier ?? null,
        tracking_number: raw.tracking_number ?? null,
        status: raw.status
      };
    }
    selectedRoom.value = raw;
    await loadRooms();
    await nextTick();
    scrollToBottom();
  } catch (_) {
    // silent poll - ignore transient failures
  }
};

const toggleStatus = async (room: CommRoom) => {
  const newStatus = room.status === "open" ? "closed" : "open";
  try {
    await setRoomStatus(room.id, newStatus);
    ElMessage.success(`對話已${newStatus === "closed" ? "關閉" : "開啟"}`);
    if (selectedRoom.value?.id === room.id) {
      selectedRoom.value = { ...selectedRoom.value, status: newStatus };
    }
    await loadRooms();
  } catch (e: any) {
    ElMessage.error(e?.message || "狀態更新失敗");
  }
};

const submitQuote = async () => {
  if (!selectedRoom.value) return;
  try {
    quoteSaving.value = true;
    await setFinalQuote(selectedRoom.value.id, {
      final_price_twd: quoteForm.value.final_price_twd,
      shipping_fee_twd: quoteForm.value.shipping_fee_twd,
      discount_twd: quoteForm.value.discount_twd,
      shipping_carrier: quoteForm.value.shipping_carrier || undefined,
      tracking_number: quoteForm.value.tracking_number || undefined
    });
    ElMessage.success("報價已送出");
    await selectRoom(selectedRoom.value);
  } catch (e: any) {
    ElMessage.error(e?.message || "送出失敗");
  } finally {
    quoteSaving.value = false;
  }
};

const loadNotifConfig = async () => {
  try {
    const res: any = await getNotificationConfig();
    notifConfig.value = res?.data ?? res ?? {};
  } catch (_) {
    // config may not exist yet — ignore
  }
};

const saveNotif = async () => {
  try {
    notifSaving.value = true;
    await saveNotificationConfig(notifConfig.value);
    ElMessage.success("通知設定已儲存");
  } catch (e: any) {
    ElMessage.error(e?.message || "儲存失敗");
  } finally {
    notifSaving.value = false;
  }
};

onMounted(async () => {
  await loadRooms();
  const roomId = Number(route.query.room || 0);
  if (roomId > 0) {
    const target = rooms.value.find(item => item.id === roomId);
    if (target) {
      await selectRoom(target);
    }
  }
  loadNotifConfig();
  roomRefreshTimer = setInterval(() => {
    refreshSelectedRoomSilently();
  }, 5000);
});

onUnmounted(() => {
  if (roomRefreshTimer) {
    clearInterval(roomRefreshTimer);
    roomRefreshTimer = null;
  }
});
</script>

<template>
  <div class="p-4">
    <el-tabs v-model="activeTab">
      <!-- Tab 1: Rooms -->
      <el-tab-pane label="對話管理" name="rooms">
        <el-row :gutter="16" style="height: calc(100vh - 200px)">
          <!-- Left: Room List -->
          <el-col :span="8" style="height: 100%; overflow-y: auto">
            <el-card shadow="never" style="height: 100%">
              <template #header>
                <span class="font-bold">對話室列表</span>
              </template>
              <div v-loading="roomsLoading">
                <div
                  v-for="room in rooms"
                  :key="room.id"
                  class="room-item"
                  :class="{ active: selectedRoom?.id === room.id }"
                  @click="selectRoom(room)"
                >
                  <div class="flex justify-between items-start">
                    <div class="flex-1 min-w-0">
                      <div class="font-medium text-sm truncate">
                        {{ room.buyer_email }}
                      </div>
                      <div class="text-xs text-gray-500 truncate">
                        {{ room.product_name || `訂單 #${room.order_id}` }}
                      </div>
                    </div>
                    <el-tag
                      :type="room.status === 'open' ? 'success' : 'info'"
                      size="small"
                      class="ml-2 flex-shrink-0"
                    >
                      {{ room.status === "open" ? "進行中" : "已關閉" }}
                    </el-tag>
                  </div>
                </div>
                <el-empty
                  v-if="!roomsLoading && rooms.length === 0"
                  description="目前無對話"
                  :image-size="60"
                />
              </div>
            </el-card>
          </el-col>

          <!-- Right: Chat + Order Detail Panel -->
          <el-col :span="16" style="height: 100%; overflow-y: auto">
            <el-card shadow="never" style="min-height: 100%">
              <template v-if="selectedRoom" #header>
                <div class="flex justify-between items-center">
                  <div>
                    <span class="font-bold">{{ selectedRoom.buyer_email }}</span>
                    <span class="text-gray-500 text-sm ml-2">
                      {{ selectedRoom.product_name }}
                    </span>
                  </div>
                  <el-button
                    :type="selectedRoom.status === 'open' ? 'warning' : 'success'"
                    size="small"
                    @click="toggleStatus(selectedRoom)"
                  >
                    {{ selectedRoom.status === "open" ? "關閉對話" : "重新開啟" }}
                  </el-button>
                </div>
              </template>
              <template v-else #header>
                <span class="text-gray-400">請從左側選擇對話</span>
              </template>

              <div
                v-if="selectedRoom"
                v-loading="roomLoading"
                class="chat-wrapper"
              >
                <!-- Messages -->
                <div ref="messagesContainer" class="messages-area">
                  <div
                    v-for="msg in selectedRoom.messages"
                    :key="msg.id"
                    class="msg-row"
                    :class="
                      msg.from === 'admin' ? 'msg-admin' : 'msg-buyer'
                    "
                  >
                    <div class="msg-meta">
                      {{ msg.from === "admin" ? "客服" : msg.sender_email }} ·
                      {{ new Date(msg.timestamp).toLocaleString() }}
                    </div>
                    <div
                      class="msg-bubble"
                      :class="
                        msg.from === 'admin' ? 'bubble-admin' : 'bubble-buyer'
                      "
                    >
                      {{ msg.message }}
                      <div v-if="msg.offer_price_twd" class="offer-pill">
                        議價提案：NT$ {{ Number(msg.offer_price_twd).toLocaleString() }}
                      </div>
                      <img v-if="msg.image_url" :src="msg.image_url" alt="msg-image" class="msg-image" />
                    </div>
                  </div>
                  <div
                    v-if="selectedRoom.messages.length === 0"
                    class="empty-chat"
                  >
                    目前沒有對話紀錄
                  </div>
                </div>

                <!-- Reply area -->
                <div
                  v-if="selectedRoom.status === 'open'"
                  class="reply-area"
                >
                  <div class="reply-aux">
                    <el-input v-model="replyImageUrl" placeholder="圖片網址（選填）" />
                    <el-input-number v-model="replyOfferPrice" :min="0" :step="100" placeholder="議價金額" />
                  </div>
                  <div class="reply-aux">
                    <input type="file" accept="image/*" @change="onReplyFileChange" />
                    <span v-if="replyImageName" class="reply-file-name">已選：{{ replyImageName }}</span>
                  </div>
                  <div class="reply-main">
                    <el-input
                      v-model="replyText"
                      placeholder="輸入回覆..."
                      @keyup.enter.exact="sendReply"
                    />
                    <el-button
                      type="primary"
                      :loading="replySending"
                      @click="sendReply"
                    >
                      傳送
                    </el-button>
                  </div>
                </div>
                <div v-else class="closed-notice">此對話已關閉</div>

                <!-- Order Detail Card -->
                <div v-if="selectedRoom.order" class="order-detail-card">
                  <div class="order-detail-title">📦 訂單報價詳情</div>

                  <!-- Read-only info row -->
                  <div class="order-info-row">
                    <span class="order-label">商品原價</span>
                    <span class="order-value">{{ formatNTD(selectedRoom.order.amount_twd) }}</span>
                  </div>
                  <div class="order-info-row">
                    <span class="order-label">訂單狀態</span>
                    <span class="order-value">
                      <el-tag size="small" type="info">{{ selectedRoom.order.status }}</el-tag>
                    </span>
                  </div>

                  <el-divider style="margin: 10px 0" />

                  <!-- Editable quote fields -->
                  <div class="quote-form">
                    <div class="quote-row">
                      <label class="quote-label">最終商品價 (NT$)</label>
                      <el-input-number
                        v-model="quoteForm.final_price_twd"
                        :min="0"
                        :step="1000"
                        controls-position="right"
                        style="width: 160px"
                      />
                    </div>
                    <div class="quote-row">
                      <label class="quote-label">運費 (NT$)</label>
                      <el-input-number
                        v-model="quoteForm.shipping_fee_twd"
                        :min="0"
                        :step="100"
                        controls-position="right"
                        style="width: 160px"
                      />
                    </div>
                    <div class="quote-row">
                      <label class="quote-label">折扣 (NT$)</label>
                      <el-input-number
                        v-model="quoteForm.discount_twd"
                        :min="0"
                        :step="100"
                        controls-position="right"
                        style="width: 160px"
                      />
                    </div>
                    <div class="quote-row total-row">
                      <label class="quote-label">合計應付</label>
                      <span class="total-value">{{ formatNTD(quotedTotal) }}</span>
                    </div>

                    <el-divider style="margin: 10px 0" />

                    <div class="quote-row">
                      <label class="quote-label">物流商</label>
                      <el-input
                        v-model="quoteForm.shipping_carrier"
                        placeholder="例：黑貓宅急便"
                        style="width: 200px"
                      />
                    </div>
                    <div class="quote-row">
                      <label class="quote-label">追蹤單號</label>
                      <el-input
                        v-model="quoteForm.tracking_number"
                        placeholder="例：799123456789"
                        style="width: 200px"
                      />
                    </div>

                    <div class="quote-actions">
                      <el-button
                        type="primary"
                        :loading="quoteSaving"
                        @click="submitQuote"
                      >
                        送出報價
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>

              <el-empty v-else description="請從左側選擇對話" />
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- Tab 2: Notification Config -->
      <el-tab-pane label="通知設定" name="notifications">
        <el-card shadow="never" style="max-width: 600px">
          <el-form :model="notifConfig" label-width="160px">
            <el-form-item label="Discord Webhook URL">
              <el-input
                v-model="notifConfig.discord_webhook_url"
                placeholder="https://discord.com/api/webhooks/..."
              />
            </el-form-item>
            <el-form-item label="LINE Notify Token">
              <el-input
                v-model="notifConfig.line_notify_token"
                placeholder="LINE Notify Access Token"
              />
            </el-form-item>
            <el-form-item label="Email 收件人">
              <el-input
                v-model="notifConfig.email_recipients"
                placeholder="多個以逗號分隔"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="notifSaving"
                @click="saveNotif"
              >
                儲存設定
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.room-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 6px;
  border: 1px solid #f0f0f0;
  transition: background 0.15s;
}
.room-item:hover {
  background: #f5f7fa;
}
.room-item.active {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.chat-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
  max-height: 340px;
}
.msg-row {
  display: flex;
  flex-direction: column;
  max-width: 75%;
}
.msg-admin {
  align-self: flex-end;
  align-items: flex-end;
}
.msg-buyer {
  align-self: flex-start;
  align-items: flex-start;
}
.msg-meta {
  font-size: 11px;
  color: #999;
  margin-bottom: 4px;
}
.msg-bubble {
  padding: 8px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}
.bubble-admin {
  background: #409eff;
  color: white;
  border-top-right-radius: 4px;
}
.bubble-buyer {
  background: white;
  border: 1px solid #e4e7ed;
  color: #303133;
  border-top-left-radius: 4px;
}
.reply-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.reply-main {
  display: flex;
  gap: 8px;
}

.reply-main .el-input {
  flex: 1;
}

.reply-aux {
  display: flex;
  gap: 8px;
  align-items: center;
}

.reply-file-name {
  font-size: 12px;
  color: #909399;
}

.offer-pill {
  margin-top: 6px;
  display: inline-flex;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  background: #fdf6ec;
  color: #b88230;
}

.msg-image {
  margin-top: 6px;
  max-height: 180px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.closed-notice {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 8px;
  margin-bottom: 12px;
}
.empty-chat {
  text-align: center;
  color: #bbb;
  margin: auto;
}

/* Order Detail Card */
.order-detail-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  margin-top: 4px;
}
.order-detail-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 12px;
}
.order-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
}
.order-label {
  color: #606266;
}
.order-value {
  font-weight: 500;
  color: #303133;
}

.quote-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.quote-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.quote-label {
  color: #606266;
  min-width: 100px;
}
.total-row {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 6px 8px;
}
.total-value {
  font-size: 16px;
  font-weight: 700;
  color: #409eff;
}
.quote-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}
</style>
