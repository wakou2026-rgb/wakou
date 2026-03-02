<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { getEvents, markEventsRead, type Event } from "@/api/events";
import { ElMessage } from "element-plus";

defineOptions({
  name: "EventsIndex"
});

const loading = ref(true);
const events = ref<Event[]>([]);
let refreshInterval: any = null;

const loadData = async (showLoading = true) => {
  try {
    if (showLoading) loading.value = true;
    const res = await getEvents();
    const payload = (res as any)?.data ?? res;
    events.value = Array.isArray(payload)
      ? payload
      : Array.isArray(payload?.items)
        ? payload.items
        : [];
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入系統日誌");
  } finally {
    if (showLoading) loading.value = false;
  }
};

const handleMarkAllRead = async () => {
  try {
    await markEventsRead();
    ElMessage.success("全部標為已讀成功");
    loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "操作失敗");
  }
};

onMounted(() => {
  loadData();
  refreshInterval = setInterval(() => {
    loadData(false);
  }, 30000); // 30s auto-refresh
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<template>
  <div class="p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>系統日誌</span>
          <el-button type="primary" @click="handleMarkAllRead">全部標為已讀</el-button>
        </div>
      </template>

      <el-table :data="events" v-loading="loading" style="width: 100%" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="actor_email" label="操作者" width="220" />
        <el-table-column prop="event_type" label="事件類型" width="220">
          <template #default="{ row }">
            <el-tag size="small">{{ row.event_type || "-" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="內容">
          <template #default="{ row }">
            <div class="font-semibold">{{ row.title || "-" }}</div>
            <div class="text-xs text-gray-500">{{ row.detail || "" }}</div>
            <div class="text-xs text-gray-400">Order #{{ row.order_id ?? "-" }} · Room #{{ row.room_id ?? "-" }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="時間" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
