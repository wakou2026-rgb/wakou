<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { getUsers, getBuyerHistory, addBuyerNote, awardBuyerPoints, banUser, changeUserRole, getCommRoom, postCommMessageRich, setCommRoomStatus, setFinalQuote, type User, type BuyerHistory } from "@/api/crm";
import { ElMessage } from "element-plus";

defineOptions({
  name: "CRMIndex"
});

const loading = ref(true);
const users = ref<User[]>([]);
const selectedUser = ref<User | null>(null);

const historyLoading = ref(false);
const buyerHistory = ref<BuyerHistory>({ orders: [], notes: [] });

const noteText = ref("");
const rewardPoints = ref(0);
const roleOptions = ["buyer", "admin", "sales", "maintenance"];

const chatLoading = ref(false);

const chatVisible = ref(false);
const chatOrder = ref<any>(null);
const chatRoom = ref<any>(null);
const chatInput = ref("");
const chatImageUrl = ref("");
const chatImageName = ref("");
const chatOfferPrice = ref<number | null>(null);
const chatMessages = ref<any[]>([]);

const quoteForm = ref({
  final_price_twd: 0,
  shipping_fee_twd: 0,
  discount_twd: 0,
  shipping_carrier: "",
  tracking_number: ""
});

let chatRefreshTimer: ReturnType<typeof setInterval> | null = null;

const openChat = async (order: any) => {
  chatOrder.value = order;
  chatRoom.value = null;
  chatMessages.value = [];
  chatVisible.value = true;
  const roomId = order.comm_room_id || order.id;
  try {
    chatLoading.value = true;
    const res = await getCommRoom(roomId);
    const room = (res as any).data || res;
    chatRoom.value = room;
    chatMessages.value = room.messages || [];
    quoteForm.value.final_price_twd = room.final_price_twd || order.total_price || 0;
    quoteForm.value.shipping_fee_twd = room.shipping_fee_twd || 0;
    quoteForm.value.discount_twd = room.discount_twd || 0;
    quoteForm.value.shipping_carrier = room.shipping_carrier || "";
    quoteForm.value.tracking_number = room.tracking_number || "";
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入對話紀錄");
  } finally {
    chatLoading.value = false;
  }
};

const sendMessage = async () => {
  if (!chatOrder.value) return;
  if (!chatInput.value.trim() && !chatImageUrl.value.trim() && !chatOfferPrice.value) return;
  const roomId = chatOrder.value.comm_room_id || chatOrder.value.id;
  try {
    await postCommMessageRich(roomId, {
      message: chatInput.value.trim(),
      image_url: chatImageUrl.value.trim() || undefined,
      offer_price_twd: chatOfferPrice.value || undefined
    });
    chatInput.value = "";
    chatImageUrl.value = "";
    chatImageName.value = "";
    chatOfferPrice.value = null;
    const res = await getCommRoom(roomId);
    const room = (res as any).data || res;
    chatRoom.value = room;
    chatMessages.value = room.messages || [];
  } catch (error: any) {
    ElMessage.error(error?.message || "傳送失敗");
  }
};

const onChatImageFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input?.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    ElMessage.error("請選擇圖片檔案");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    chatImageUrl.value = typeof reader.result === "string" ? reader.result : "";
    chatImageName.value = file.name;
  };
  reader.readAsDataURL(file);
};

const submitFinalPrice = async () => {
  if (!chatOrder.value) return;
  const roomId = chatOrder.value.comm_room_id || chatOrder.value.id;
  try {
    await setFinalQuote(roomId, {
      final_price_twd: quoteForm.value.final_price_twd,
      shipping_fee_twd: quoteForm.value.shipping_fee_twd,
      discount_twd: quoteForm.value.discount_twd,
      shipping_carrier: quoteForm.value.shipping_carrier || undefined,
      tracking_number: quoteForm.value.tracking_number || undefined
    });
    ElMessage.success("已確認最終價格並通知買家付款");
    const res = await getCommRoom(roomId);
    const room = (res as any).data || res;
    chatRoom.value = room;
    chatMessages.value = room.messages || [];
  } catch (error: any) {
    ElMessage.error(error?.message || "最終價格確認失敗");
  }
};

const refreshChatSilently = async () => {
  if (!chatVisible.value || !chatOrder.value || chatLoading.value) return;
  const roomId = chatOrder.value.comm_room_id || chatOrder.value.id;
  try {
    const res = await getCommRoom(roomId);
    const room = (res as any).data || res;
    chatRoom.value = room;
    chatMessages.value = room.messages || [];

    if (selectedUser.value) {
      const history = await getBuyerHistory(selectedUser.value.email);
      buyerHistory.value = history as any;
      const latestOrder = (buyerHistory.value.orders || []).find((o: any) => (o.comm_room_id || o.id) === roomId);
      if (latestOrder) {
        chatOrder.value = latestOrder;
      }
    }
  } catch (_) {
    // silent polling
  }
};

const closeCommRoom = async () => {
  if (!chatOrder.value) return;
  const roomId = chatOrder.value.comm_room_id || chatOrder.value.id;
  try {
    await setCommRoomStatus(roomId, "closed");
    ElMessage.success("對話已關閉");
    chatVisible.value = false;
  } catch (error: any) {
    ElMessage.error(error?.message || "關閉對話失敗");
  }
};

const loadData = async () => {
  try {
    loading.value = true;
    const res = await getUsers();
    users.value = Array.isArray(res) ? res : ((res as any).items || (res as any).data || []);
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入會員列表");
  } finally {
    loading.value = false;
  }
};

const handleSelectUser = async (user: User) => {
  selectedUser.value = user;
  try {
    historyLoading.value = true;
    const res = await getBuyerHistory(user.email);
    buyerHistory.value = res as any;
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入會員歷史紀錄");
  } finally {
    historyLoading.value = false;
  }
};

const handleAddNote = async () => {
  if (!selectedUser.value || !noteText.value.trim()) return;
  try {
    await addBuyerNote(selectedUser.value.email, noteText.value.trim());
    ElMessage.success("新增備註成功");
    noteText.value = "";
    handleSelectUser(selectedUser.value);
  } catch (error: any) {
    ElMessage.error(error?.message || "新增備註失敗");
  }
};

const handleAwardPoints = async () => {
  if (!selectedUser.value || rewardPoints.value <= 0) return;
  try {
    await awardBuyerPoints(selectedUser.value.email, rewardPoints.value);
    ElMessage.success("發放點數成功");
    rewardPoints.value = 0;
  } catch (error: any) {
    ElMessage.error(error?.message || "發放點數失敗");
  }
};

const getRoleTagType = (role: string) => {
  if (role === "admin" || role === "super_admin") return "danger";
  if (role === "sales") return "warning";
  if (role === "maintenance") return "info";
  return "success";
};

const handleRoleChange = async (user: User, role: string | number | boolean) => {
  const targetRole = String(role);
  const previousRole = user.role;
  user.role = targetRole;
  try {
    const response = await changeUserRole(user.id, targetRole);
    const nextRole = (response as any)?.role || (response as any)?.data?.role || targetRole;
    user.role = nextRole;
    ElMessage.success("角色更新成功");
  } catch (error: any) {
    user.role = previousRole;
    ElMessage.error(error?.message || "角色更新失敗");
  }
};

const handleBanChange = async (user: User, banned: string | number | boolean) => {
  const targetBanned = Boolean(banned);
  const previous = user.is_banned;
  user.is_banned = targetBanned;
  try {
    const response = await banUser(user.id, targetBanned);
    const nextBanned = (response as any)?.is_banned ?? (response as any)?.data?.is_banned;
    user.is_banned = typeof nextBanned === "boolean" ? nextBanned : targetBanned;
    ElMessage.success(user.is_banned ? "已封鎖會員" : "已解除封鎖");
  } catch (error: any) {
    user.is_banned = previous;
    ElMessage.error(error?.message || "封鎖狀態更新失敗");
  }
};

onMounted(() => {
  loadData();
  chatRefreshTimer = setInterval(() => {
    refreshChatSilently();
  }, 5000);
});

onUnmounted(() => {
  if (chatRefreshTimer) {
    clearInterval(chatRefreshTimer);
    chatRefreshTimer = null;
  }
});
</script>

<template>
  <div class="p-4">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" header="會員列表">
          <el-table
            :data="users"
            v-loading="loading"
            style="width: 100%"
            border
            highlight-current-row
            @current-change="handleSelectUser"
          >
            <el-table-column prop="email" label="信箱" />
            <el-table-column prop="display_name" label="顯示名稱" />
            <el-table-column prop="role" label="角色" width="220">
              <template #default="{ row }">
                <div class="flex flex-col gap-2">
                  <el-tag size="small" :type="getRoleTagType(row.role)">{{ row.role }}</el-tag>
                  <el-select
                    v-model="row.role"
                    size="small"
                    @change="value => handleRoleChange(row, value)"
                    :disabled="row.role === 'super_admin'"
                  >
                    <el-option
                      v-if="row.role === 'super_admin'"
                      label="super_admin"
                      value="super_admin"
                    />
                    <el-option
                      v-for="option in roleOptions"
                      :key="option"
                      :label="option"
                      :value="option"
                    />
                  </el-select>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="is_banned" label="封鎖" width="140" align="center">
              <template #default="{ row }">
                <div class="flex flex-col items-center gap-2">
                  <el-tag size="small" :type="row.is_banned ? 'danger' : 'success'">
                    {{ row.is_banned ? "已封鎖" : "正常" }}
                  </el-tag>
                  <el-switch
                    v-model="row.is_banned"
                    @change="value => handleBanChange(row, value)"
                  />
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="never" header="會員詳情" v-if="selectedUser">
          <div v-loading="historyLoading">
            <h3 class="text-lg font-bold mb-4">{{ selectedUser.display_name }} ({{ selectedUser.email }})</h3>

            <div class="mb-6">
              <h4 class="font-bold mb-2">訂單歷史</h4>
              <el-table :data="buyerHistory.orders || []" size="small" border>
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="total_price" label="金額" width="80" />
                <el-table-column prop="status" label="狀態" width="100" />
                <el-table-column label="對話" width="100" fixed="right" align="center">
                  <template #default="{ row }">
                    <el-button type="primary" link @click="openChat(row)">
                      訂單對話
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="mb-6">
              <h4 class="font-bold mb-2">備註</h4>
              <el-timeline>
                <el-timeline-item
                  v-for="(note, index) in buyerHistory.notes || []"
                  :key="index"
                  :timestamp="note.created_at"
                >
                  {{ note.content || note }}
                </el-timeline-item>
              </el-timeline>
              <div class="flex gap-2 mt-2">
                <el-input v-model="noteText" placeholder="輸入備註內容" />
                <el-button type="primary" @click="handleAddNote">新增備註</el-button>
              </div>
            </div>

            <div>
              <h4 class="font-bold mb-2">發放點數</h4>
              <div class="flex gap-2">
                <el-input-number v-model="rewardPoints" :min="0" />
                <el-button type="success" @click="handleAwardPoints">發放</el-button>
              </div>
            </div>
          </div>
        </el-card>
        <el-card shadow="never" v-else>
          <el-empty description="請從左側選擇會員" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 訂單獨立對話 Drawer -->
    <el-drawer
      v-model="chatVisible"
      :title="`訂單對話 #${chatOrder?.id || ''}`"
      size="450px"
    >
      <template #header>
        <div class="flex items-center justify-between w-full">
          <span class="text-lg font-bold">訂單對話 #{{ chatOrder?.id || '' }}</span>
          <el-button type="danger" size="small" @click="closeCommRoom">關閉對話</el-button>
        </div>
      </template>
      <div class="flex flex-col h-full -mt-4">
        <!-- 買家資訊卡片 -->
        <div class="bg-gray-50 p-3 rounded mb-4 flex items-center justify-between border border-gray-100">
          <div>
            <div class="font-bold text-gray-700">{{ selectedUser?.display_name }}</div>
            <div class="text-xs text-gray-500">{{ selectedUser?.email }}</div>
            <div class="text-[11px] text-amber-700 mt-1">對話狀態：{{ chatRoom?.status || "-" }}</div>
          </div>
          <div class="text-right">
            <div class="text-xs text-gray-500">訂單金額</div>
            <div class="font-bold text-blue-600">¥{{ chatOrder?.total_price }}</div>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4 bg-gray-50 border border-gray-200 rounded-lg mb-4 flex flex-col gap-4 relative shadow-inner">
          <div
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            class="flex flex-col max-w-[85%]"
            :class="msg.from === 'admin' ? 'self-end' : 'self-start'"
          >
            <span
              class="text-[10px] text-gray-400 mb-1"
              :class="msg.from === 'admin' ? 'text-right' : 'text-left'"
            >
              {{ msg.from === 'admin' ? '客服 (您)' : selectedUser?.display_name }} • {{ msg.timestamp }}
            </span>
            <div
              class="px-4 py-2 rounded-2xl text-sm leading-relaxed shadow-sm"
              :class="msg.from === 'admin' 
                ? 'bg-blue-500 text-white rounded-tr-none' 
                : 'bg-white border border-gray-200 text-gray-800 rounded-tl-none'"
            >
              {{ msg.message }}
              <div v-if="msg.offer_price_twd" class="mt-2 inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                議價提案：NT$ {{ Number(msg.offer_price_twd).toLocaleString() }}
              </div>
              <img
                v-if="msg.image_url"
                :src="msg.image_url"
                alt="message image"
                class="mt-2 max-h-48 rounded border border-gray-200"
              />
            </div>
          </div>
          <div v-if="chatMessages.length === 0" class="absolute inset-0 flex items-center justify-center text-gray-400">
            目前沒有對話紀錄
          </div>
        </div>
        <div class="space-y-2">
          <div class="flex gap-2">
            <el-input v-model="chatImageUrl" placeholder="圖片網址（選填）" />
            <el-input-number v-model="chatOfferPrice" :min="0" :step="100" placeholder="議價金額" />
          </div>
          <div class="flex gap-2">
            <input type="file" accept="image/*" @change="onChatImageFileChange" />
            <span v-if="chatImageName" class="text-xs text-gray-500">已選：{{ chatImageName }}</span>
          </div>
        </div>
        <div class="flex gap-2 mt-2">
          <el-input
            v-model="chatInput"
            placeholder="輸入對話內容..."
            @keyup.enter="sendMessage"
          />
          <el-button type="primary" @click="sendMessage">傳送</el-button>
        </div>

        <div class="mt-4 rounded border border-gray-200 p-3 bg-gray-50">
          <div class="font-semibold mb-2">最終價格確認（管理員）</div>
          <div class="grid grid-cols-2 gap-2 mb-2">
            <el-input-number v-model="quoteForm.final_price_twd" :min="0" :step="1000" controls-position="right" />
            <el-input-number v-model="quoteForm.shipping_fee_twd" :min="0" :step="100" controls-position="right" />
            <el-input-number v-model="quoteForm.discount_twd" :min="0" :step="100" controls-position="right" />
            <el-input v-model="quoteForm.shipping_carrier" placeholder="物流商（選填）" />
            <el-input class="col-span-2" v-model="quoteForm.tracking_number" placeholder="追蹤單號（選填）" />
          </div>
          <el-button type="warning" @click="submitFinalPrice">確認最終價格並通知買家付款</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>
