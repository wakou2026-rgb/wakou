<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  getOrders,
  updateOrderStatus,
  exportOrdersCsv,
  refundOrder,
  bulkUpdateOrderStatus,
  type Order
} from "@/api/orders";
import { ElMessage } from "element-plus";

defineOptions({
  name: "OrdersIndex"
});

const loading = ref(true);
const orders = ref<Order[]>([]);
const selectedRows = ref<Order[]>([]);
const bulkStatus = ref("");
const bulkSubmitting = ref(false);
const refundDialogVisible = ref(false);
const refundSubmitting = ref(false);
const refundReason = ref("");
const refundTargetOrder = ref<Order | null>(null);

const loadData = async () => {
  try {
    loading.value = true;
    const res = await getOrders();
    // Support both wrapped { data: ... } and direct array response
    orders.value = Array.isArray(res) ? res : ((res as any).items || (res as any).data || []);
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入訂單");
  } finally {
    loading.value = false;
  }
};

const handleStatusChange = async (row: Order, newStatus: string) => {
  try {
    await updateOrderStatus(row.id, newStatus);
    ElMessage.success("狀態更新成功");
    row.status = newStatus;
  } catch (error: any) {
    ElMessage.error(error?.message || "更新失敗");
    await loadData(); // Reload to reset the dropdown value
  }
};

const handleExport = async () => {
  try {
    const res = await exportOrdersCsv();
    const blob = new Blob([res as any], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "orders.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (error: any) {
    ElMessage.error("匯出失敗");
  }
};

const handleSelectionChange = (rows: Order[]) => {
  selectedRows.value = rows;
};

const handleBulkStatusUpdate = async () => {
  if (!bulkStatus.value || selectedRows.value.length === 0) return;
  try {
    bulkSubmitting.value = true;
    await bulkUpdateOrderStatus(
      selectedRows.value.map(row => String(row.id)),
      bulkStatus.value
    );
    ElMessage.success("批量狀態更新成功");
    await loadData();
    selectedRows.value = [];
  } catch (error: any) {
    ElMessage.error(error?.message || "批量更新失敗");
  } finally {
    bulkSubmitting.value = false;
  }
};

const openRefundDialog = (row: Order) => {
  refundTargetOrder.value = row;
  refundReason.value = "";
  refundDialogVisible.value = true;
};

const handleRefund = async () => {
  const target = refundTargetOrder.value;
  if (!target) return;
  if (!refundReason.value.trim()) {
    ElMessage.warning("請輸入退款原因");
    return;
  }
  try {
    refundSubmitting.value = true;
    await refundOrder(String(target.id), refundReason.value.trim());
    ElMessage.success("退款處理成功");
    refundDialogVisible.value = false;
    await loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "退款失敗");
  } finally {
    refundSubmitting.value = false;
  }
};

const statusOptions = [
  { label: "待處理", value: "pending" },
  { label: "已完成", value: "completed" },
  { label: "已取消", value: "cancelled" },
  { label: "已退款", value: "refunded" }
];

const getStatusType = (status: string) => {
  if (status === "pending") return "warning";
  if (status === "completed") return "success";
  if (status === "refunded") return "danger";
  if (status === "cancelled") return "danger";
  return "info";
};

const getStatusLabel = (status: string) => {
  const opt = statusOptions.find(o => o.value === status);
  return opt ? opt.label : status;
};

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>訂單管理</span>
          <el-button type="primary" @click="handleExport">匯出 CSV</el-button>
        </div>
      </template>

      <div class="mb-4 flex items-center gap-2">
        <el-select v-model="bulkStatus" placeholder="批量更新狀態" style="width: 160px">
          <el-option
            v-for="opt in statusOptions"
            :key="`bulk-${opt.value}`"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-button
          type="primary"
          :disabled="selectedRows.length === 0 || !bulkStatus"
          :loading="bulkSubmitting"
          @click="handleBulkStatusUpdate"
        >
          套用到已選訂單
        </el-button>
      </div>

      <el-table
        :data="orders"
        v-loading="loading"
        style="width: 100%"
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="buyer_email" label="買家信箱" />
        <el-table-column label="狀態" width="150">
          <template #default="{ row }">
            <el-select
              v-model="row.status"
              size="small"
              @change="(val) => handleStatusChange(row, val)"
            >
              <el-option
                v-for="opt in statusOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              >
                <el-tag :type="getStatusType(opt.value)" size="small">
                  {{ opt.label }}
                </el-tag>
              </el-option>
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="amount_twd" label="金額" width="120">
          <template #default="{ row }">
            ${{ row.amount_twd }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="建立時間" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'refunded' && row.status !== 'cancelled'"
              type="danger"
              size="small"
              @click="openRefundDialog(row)"
            >
              退款
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="refundDialogVisible" title="訂單退款" width="520px">
      <el-input
        v-model="refundReason"
        type="textarea"
        :rows="4"
        placeholder="請輸入退款原因"
      />
      <template #footer>
        <el-button @click="refundDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="refundSubmitting" @click="handleRefund">確認退款</el-button>
      </template>
    </el-dialog>
  </div>
</template>
