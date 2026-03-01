<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  addShipmentEvent,
  getOrderShipmentEvents,
  getShipments,
  type ShipmentSummary,
  type ShipmentEventPayload
} from "@/api/shipping";

defineOptions({ name: "ShippingIndex" });

const loading = ref(false);
const detailLoading = ref(false);
const saving = ref(false);
const shipments = ref<ShipmentSummary[]>([]);
const selectedOrderId = ref<number | null>(null);
const detail = ref<{ order_id: number; product_name: string; buyer_email: string; events: any[] } | null>(null);

const statusOptions = [
  "payment_confirmed",
  "preparing",
  "shipped_jp",
  "in_transit",
  "customs_tw",
  "shipped_tw",
  "delivered"
];

const defaultTitleMap: Record<string, string> = {
  payment_confirmed: "付款確認",
  preparing: "備貨中",
  shipped_jp: "已從日本出貨",
  in_transit: "國際運送中",
  customs_tw: "台灣海關清關",
  shipped_tw: "台灣境內配送",
  delivered: "已送達"
};

function toDatetimeLocal(value: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`;
}

function toIsoFromLocal(value: string) {
  if (!value) return "";
  return new Date(value).toISOString();
}

const form = reactive({
  status: "payment_confirmed",
  title: defaultTitleMap.payment_confirmed,
  description: "",
  location: "",
  event_time: toDatetimeLocal(new Date())
});

const selectedShipment = computed(() => {
  if (selectedOrderId.value == null) return null;
  return shipments.value.find((item) => item.order_id === selectedOrderId.value) || null;
});

watch(
  () => form.status,
  (nextStatus) => {
    form.title = defaultTitleMap[nextStatus] || form.title;
  }
);

async function loadShipments() {
  loading.value = true;
  try {
    const response: any = await getShipments();
    const payload = response?.data ?? response;
    shipments.value = Array.isArray(payload?.items) ? payload.items : [];

    if (!shipments.value.length) {
      selectedOrderId.value = null;
      detail.value = null;
      return;
    }

    if (!selectedOrderId.value) {
      selectedOrderId.value = shipments.value[0].order_id;
    }
    await loadDetail(selectedOrderId.value);
  } catch (error: any) {
    ElMessage.error(error?.message || "載入出貨列表失敗");
  } finally {
    loading.value = false;
  }
}

async function loadDetail(orderId: number | null) {
  if (!orderId) return;
  detailLoading.value = true;
  try {
    const response: any = await getOrderShipmentEvents(orderId);
    const payload = response?.data ?? response;
    detail.value = {
      order_id: payload?.order_id,
      product_name: payload?.product_name,
      buyer_email: payload?.buyer_email,
      events: Array.isArray(payload?.events) ? payload.events : []
    };
  } catch (error: any) {
    ElMessage.error(error?.message || "載入出貨事件失敗");
  } finally {
    detailLoading.value = false;
  }
}

async function handleSelect(orderId: number) {
  selectedOrderId.value = orderId;
  await loadDetail(orderId);
}

async function submitEvent() {
  if (!selectedOrderId.value) return;
  if (!form.status.trim() || !form.title.trim()) {
    ElMessage.warning("請先填寫狀態與標題");
    return;
  }

  const payload: ShipmentEventPayload = {
    status: form.status.trim(),
    title: form.title.trim(),
    description: form.description.trim() || undefined,
    location: form.location.trim() || undefined,
    event_time: toIsoFromLocal(form.event_time)
  };

  saving.value = true;
  try {
    await addShipmentEvent(selectedOrderId.value, payload);
    ElMessage.success("出貨節點已新增");
    await loadDetail(selectedOrderId.value);
    await loadShipments();
    form.event_time = toDatetimeLocal(new Date());
    form.description = "";
    form.location = "";
  } catch (error: any) {
    ElMessage.error(error?.message || "新增出貨節點失敗");
  } finally {
    saving.value = false;
  }
}

onMounted(loadShipments);
</script>

<template>
  <div class="shipping-page p-4">
    <el-row :gutter="16" style="height: calc(100vh - 160px)">
      <el-col :span="8" style="height: 100%">
        <el-card shadow="never" style="height: 100%">
          <template #header>
            <span class="font-bold">出貨管理訂單</span>
          </template>
          <div v-loading="loading" class="list-panel">
            <div
              v-for="item in shipments"
              :key="item.order_id"
              class="shipment-item"
              :class="{ active: selectedOrderId === item.order_id }"
              @click="handleSelect(item.order_id)"
            >
              <div class="item-head">
                <strong>#{{ item.order_id }}</strong>
                <el-tag size="small" type="info">{{ item.latest_title || item.order_status }}</el-tag>
              </div>
              <p class="item-buyer">{{ item.buyer_email }}</p>
              <p class="item-product">{{ item.product_name }}</p>
              <p class="item-meta">事件 {{ item.event_count }} 筆</p>
            </div>
            <el-empty v-if="!loading && shipments.length === 0" description="暫無可管理出貨訂單" :image-size="64" />
          </div>
        </el-card>
      </el-col>

      <el-col :span="16" style="height: 100%">
        <el-card shadow="never" style="height: 100%">
          <template #header>
            <div v-if="selectedShipment" class="detail-header">
              <div>
                <strong>訂單 #{{ selectedShipment.order_id }}</strong>
                <p class="subline">{{ selectedShipment.product_name }} · {{ selectedShipment.buyer_email }}</p>
              </div>
            </div>
            <span v-else class="text-gray-400">請先選擇訂單</span>
          </template>

          <div v-if="selectedOrderId" v-loading="detailLoading" class="detail-body">
            <el-timeline>
              <el-timeline-item
                v-for="event in detail?.events || []"
                :key="`${event.status}-${event.event_time}`"
                :timestamp="event.event_time"
                placement="top"
              >
                <div class="timeline-card">
                  <div class="timeline-title">{{ event.title }}</div>
                  <div class="timeline-status">{{ defaultTitleMap[event.status] || event.status }}</div>
                  <div v-if="event.description" class="timeline-desc">{{ event.description }}</div>
                  <div v-if="event.location" class="timeline-location">{{ event.location }}</div>
                </div>
              </el-timeline-item>
            </el-timeline>

            <el-empty v-if="(detail?.events || []).length === 0" description="尚無出貨事件" :image-size="56" />

            <el-divider />

            <el-form :model="form" label-width="120px" class="event-form">
              <el-form-item label="狀態">
                <el-select v-model="form.status" style="width: 100%">
                  <el-option v-for="status in statusOptions" :key="status" :label="defaultTitleMap[status] || status" :value="status" />
                </el-select>
              </el-form-item>
              <el-form-item label="標題">
                <el-input v-model="form.title" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="form.description" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="地點">
                <el-input v-model="form.location" />
              </el-form-item>
              <el-form-item label="事件時間">
                <el-input v-model="form.event_time" type="datetime-local" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="submitEvent">新增出貨事件</el-button>
              </el-form-item>
            </el-form>
          </div>

          <el-empty v-else description="請從左側選擇訂單" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.list-panel {
  overflow-y: auto;
  height: calc(100% - 12px);
  padding-right: 4px;
}

.shipment-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.shipment-item:hover {
  border-color: #b3d8ff;
  background: #f5f9ff;
}

.shipment-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.item-buyer,
.item-product,
.item-meta,
.subline,
.timeline-status,
.timeline-desc,
.timeline-location {
  margin: 4px 0 0;
}

.item-buyer,
.timeline-status {
  font-size: 12px;
  color: #606266;
}

.item-product {
  font-size: 13px;
  color: #303133;
}

.item-meta,
.subline,
.timeline-desc,
.timeline-location {
  font-size: 12px;
  color: #909399;
}

.detail-body {
  height: calc(100% - 12px);
  overflow-y: auto;
  padding-right: 4px;
}

.timeline-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
}

.timeline-title {
  font-weight: 600;
  color: #303133;
}
</style>
