<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getUsers, getBuyerHistory, addBuyerNote, awardBuyerPoints, getCommRoom, postCommMessage, setCommRoomStatus, type User, type BuyerHistory, type CommRoom, type CommMessage } from "@/api/crm";
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

const chatLoading = ref(false);

const chatVisible = ref(false);
const chatOrder = ref<any>(null);
const chatInput = ref("");
const chatMessages = ref<any[]>([]);

const openChat = async (order: any) => {
  chatOrder.value = order;
  chatMessages.value = [];
  chatVisible.value = true;
  const roomId = order.comm_room_id || order.id;
  try {
    chatLoading.value = true;
    const res = await getCommRoom(roomId);
    const room = (res as any).data || res;
    chatMessages.value = room.messages || [];
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入對話紀錄");
  } finally {
    chatLoading.value = false;
  }
};

const sendMessage = async () => {
  if (!chatInput.value.trim() || !chatOrder.value) return;
  const roomId = chatOrder.value.comm_room_id || chatOrder.value.id;
  try {
    await postCommMessage(roomId, chatInput.value);
    chatInput.value = "";
    const res = await getCommRoom(roomId);
    const room = (res as any).data || res;
    chatMessages.value = room.messages || [];
  } catch (error: any) {
    ElMessage.error(error?.message || "傳送失敗");
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

onMounted(() => {
  loadData();
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
            <el-table-column prop="role" label="角色" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.role }}</el-tag>
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
            </div>
          </div>
          <div v-if="chatMessages.length === 0" class="absolute inset-0 flex items-center justify-center text-gray-400">
            目前沒有對話紀錄
          </div>
        </div>
        <div class="flex gap-2">
          <el-input
            v-model="chatInput"
            placeholder="輸入對話內容..."
            @keyup.enter="sendMessage"
          />
          <el-button type="primary" @click="sendMessage">傳送</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>
