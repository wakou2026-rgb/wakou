<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Box, Clock, ShoppingCart, TrendCharts } from "@element-plus/icons-vue";
import {
  getDashboardOverview,
  getOrderStatusStats,
  getRecentOrders,
  type DashboardRecentOrder,
  type OrderStatusStat
} from "@/api/admin";
import { getMonthlyReport } from "@/api/finance";
import { useECharts } from "@pureadmin/utils";
import { ElMessage } from "element-plus";

defineOptions({ name: "DashboardIndex" });

type DashboardStats = {
  total_orders: number;
  revenue: number;
  pending_orders: number;
  active_products: number;
};

const router = useRouter();
const loading = ref(true);
const stats = ref<DashboardStats>({
  total_orders: 0,
  revenue: 0,
  pending_orders: 0,
  active_products: 0
});
const recentOrders = ref<DashboardRecentOrder[]>([]);
const statusStats = ref<OrderStatusStat[]>([]);
const monthlyRevenue = ref<Array<{ label: string; value: number }>>([]);

const revenueChartRef = ref<HTMLDivElement | null>(null);
const statusChartRef = ref<HTMLDivElement | null>(null);
const { setOptions: setRevenueOptions, resize: resizeRevenueChart } = useECharts(
  revenueChartRef as any
);
const { setOptions: setStatusOptions, resize: resizeStatusChart } = useECharts(
  statusChartRef as any
);

let resizeTimer: ReturnType<typeof setTimeout> | null = null;

const quickActions = [
  {
    title: "前往訂單管理",
    desc: "處理最新訂單與更新狀態",
    path: "/orders/index",
    type: "primary"
  },
  {
    title: "前往商品管理",
    desc: "維護上架商品與庫存資訊",
    path: "/products/index",
    type: "success"
  },
  {
    title: "前往財務報表",
    desc: "查看收支與月度趨勢",
    path: "/finance/index",
    type: "warning"
  },
  {
    title: "前往會員管理",
    desc: "追蹤重要客戶互動紀錄",
    path: "/crm/index",
    type: "info"
  }
] as const;

const statusLabelMap: Record<string, string> = {
  pending: "待處理",
  waiting_quote: "待報價",
  quoted: "已報價",
  paid: "已付款",
  shipped: "已出貨",
  completed: "已完成",
  cancelled: "已取消"
};

const statusTypeMap: Record<string, "warning" | "primary" | "success" | "danger" | "info"> = {
  pending: "warning",
  waiting_quote: "warning",
  quoted: "primary",
  paid: "success",
  shipped: "primary",
  completed: "success",
  cancelled: "danger"
};

const pendingHighlightClass = computed(() =>
  stats.value.pending_orders > 0 ? "stat-value-pending" : ""
);

const normalizeStatusForPie = (status: string) => {
  if (status === "waiting_quote" || status === "quoted") return "pending";
  if (["pending", "paid", "shipped", "completed", "cancelled"].includes(status)) {
    return status;
  }
  return "pending";
};

const getStatusLabel = (status: string) => statusLabelMap[status] ?? status;

const getStatusType = (status: string) => statusTypeMap[status] ?? "info";

const formatCurrency = (v: number) => `NT$${Number(v ?? 0).toLocaleString("zh-TW")}`;

const formatOrderAmount = (order: DashboardRecentOrder) =>
  formatCurrency(Number(order.final_amount_twd ?? order.amount_twd ?? 0));

const formatOrderDate = (value: string) => {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("zh-TW");
};

const formatBuyer = (email: string) => email?.split("@")[0] || "-";

const buildPieData = (items: OrderStatusStat[]) => {
  const grouped: Record<string, number> = {
    pending: 0,
    paid: 0,
    shipped: 0,
    completed: 0,
    cancelled: 0
  };

  items.forEach(item => {
    const status = normalizeStatusForPie(item.status);
    grouped[status] += Number(item.count || 0);
  });

  return [
    { name: "待處理", value: grouped.pending },
    { name: "已付款", value: grouped.paid },
    { name: "已出貨", value: grouped.shipped },
    { name: "已完成", value: grouped.completed },
    { name: "已取消", value: grouped.cancelled }
  ];
};

const renderRevenueChart = () => {
  setRevenueOptions({
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        const item = params?.[0];
        if (!item) return "";
        return `${item.name}<br/>${item.marker}收入: NT$${Number(item.value).toLocaleString("zh-TW")}`;
      }
    },
    grid: { left: 56, right: 24, top: 30, bottom: 40 },
    xAxis: {
      type: "category",
      data: monthlyRevenue.value.map(item => item.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "#e5e7eb" } }
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "#f1f5f9" } },
      axisLabel: {
        formatter: (value: number) =>
          value >= 1000 ? `${Math.round(value / 1000)}k` : String(value)
      }
    },
    series: [
      {
        name: "收入",
        type: "bar",
        barMaxWidth: 34,
        data: monthlyRevenue.value.map(item => item.value),
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: "#5b8ff9"
        }
      }
    ]
  });
};

const renderStatusChart = () => {
  const data = buildPieData(statusStats.value);
  setStatusOptions({
    tooltip: {
      trigger: "item",
      formatter: (p: any) =>
        `${p.name}<br/>${Number(p.value).toLocaleString("zh-TW")} 筆 (${p.percent}%)`
    },
    legend: {
      orient: "vertical",
      right: 8,
      top: "center",
      textStyle: { fontSize: 12 }
    },
    series: [
      {
        name: "訂單狀態",
        type: "pie",
        radius: ["42%", "68%"],
        center: ["35%", "50%"],
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
        label: { show: false },
        data
      }
    ]
  });
};

const renderCharts = async () => {
  await nextTick();
  renderRevenueChart();
  renderStatusChart();
  resizeRevenueChart();
  resizeStatusChart();
};

const handleResize = () => {
  if (resizeTimer) clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    resizeRevenueChart();
    resizeStatusChart();
  }, 200);
};

const goToPath = (path: string) => {
  router.push(path);
};

const loadData = async () => {
  try {
    loading.value = true;
    const [overviewRes, recentOrderRes, statusRes, monthlyRes] = await Promise.all([
      getDashboardOverview(),
      getRecentOrders(),
      getOrderStatusStats(),
      getMonthlyReport()
    ]);

    const metrics = overviewRes?.metrics ?? overviewRes ?? {};
    const recentMonths = [...monthlyRes]
      .slice(-6)
      .map(item => ({
        label: `${item.month}月`,
        value: Number(item.revenue ?? 0)
      }));
    const totalRevenueFromMonthly = recentMonths.reduce(
      (sum, item) => sum + Number(item.value || 0),
      0
    );

    stats.value = {
      total_orders: Number(metrics.total_orders ?? 0),
      revenue: Number(metrics.revenue ?? totalRevenueFromMonthly),
      pending_orders: Number(metrics.pending_orders ?? 0),
      active_products: Number(metrics.active_products ?? metrics.total_products ?? 0)
    };
    recentOrders.value = recentOrderRes.slice(0, 5);
    statusStats.value = statusRes;
    monthlyRevenue.value = recentMonths;

    await renderCharts();
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入儀表板資料");
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  if (typeof window !== "undefined") {
    window.addEventListener("resize", handleResize);
  }
  loadData();
});

onBeforeUnmount(() => {
  if (typeof window !== "undefined") {
    window.removeEventListener("resize", handleResize);
  }
  if (resizeTimer) {
    clearTimeout(resizeTimer);
    resizeTimer = null;
  }
});
</script>

<template>
  <div class="dashboard-page" v-loading="loading">
    <el-row :gutter="16" class="summary-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-orders">
          <div class="stat-icon">
            <el-icon size="28"><ShoppingCart /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">總訂單</div>
            <div class="stat-value">{{ stats.total_orders }}</div>
            <div class="stat-sub">累計訂單筆數</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-revenue">
          <div class="stat-icon">
            <el-icon size="28"><TrendCharts /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">總收入</div>
            <div class="stat-value">{{ formatCurrency(stats.revenue) }}</div>
            <div class="stat-sub">近月趨勢持續更新</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-pending">
          <div class="stat-icon">
            <el-icon size="28"><Clock /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">待處理訂單</div>
            <div class="stat-value" :class="pendingHighlightClass">
              {{ stats.pending_orders }}
            </div>
            <div class="stat-sub">需優先追蹤的訂單</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-products">
          <div class="stat-icon">
            <el-icon size="28"><Box /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">上架商品</div>
            <div class="stat-value">{{ stats.active_products }}</div>
            <div class="stat-sub">目前可售庫存</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="content-row">
      <el-col :xs="24" :lg="16">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">最近 6 個月收入趨勢</span>
            </div>
          </template>
          <div ref="revenueChartRef" class="chart-canvas" />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">訂單狀態分佈</span>
            </div>
          </template>
          <div ref="statusChartRef" class="chart-canvas" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="content-row">
      <el-col :xs="24" :lg="16">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">最近訂單（5 筆）</span>
            </div>
          </template>
          <el-table
            :data="recentOrders"
            stripe
            border
            style="width: 100%"
            :header-cell-style="{ background: '#fafafa', fontWeight: '600' }"
          >
            <el-table-column prop="id" label="訂單 ID" width="90" align="center" />
            <el-table-column label="買家" min-width="120">
              <template #default="{ row }">
                {{ formatBuyer(row.buyer_email) }}
              </template>
            </el-table-column>
            <el-table-column prop="product_name" label="商品" min-width="180" />
            <el-table-column label="狀態" width="120" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" effect="light" size="small">
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="金額" width="130" align="right">
              <template #default="{ row }">
                {{ formatOrderAmount(row) }}
              </template>
            </el-table-column>
            <el-table-column label="日期" width="130" align="center">
              <template #default="{ row }">
                {{ formatOrderDate(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="panel-card quick-actions-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">快速操作</span>
            </div>
          </template>

          <div class="quick-actions">
            <button
              v-for="item in quickActions"
              :key="item.path"
              type="button"
              class="quick-action-item"
              @click="goToPath(item.path)"
            >
              <el-tag :type="item.type" size="small" effect="light">捷徑</el-tag>
              <div class="quick-action-text">
                <div class="quick-action-title">{{ item.title }}</div>
                <div class="quick-action-desc">{{ item.desc }}</div>
              </div>
            </button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard-page {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-row,
.content-row {
  margin-bottom: 0 !important;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #f0f0f0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-orders .stat-icon {
  background: rgba(91, 143, 249, 0.12);
  color: #5b8ff9;
}

.stat-revenue .stat-icon {
  background: rgba(115, 209, 61, 0.12);
  color: #52c41a;
}

.stat-pending .stat-icon {
  background: rgba(250, 173, 20, 0.15);
  color: #fa8c16;
}

.stat-products .stat-icon {
  background: rgba(64, 169, 255, 0.12);
  color: #1890ff;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 13px;
  color: #8c8c8c;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
}

.stat-value-pending {
  color: #d97706;
}

.stat-sub {
  font-size: 12px;
  color: #bfbfbf;
  margin-top: 4px;
}

.panel-card {
  border-radius: 10px !important;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #262626;
}

.chart-canvas {
  width: 100%;
  min-height: 300px;
  height: 300px;
}

.quick-actions-card {
  height: 100%;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quick-action-item {
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  background: #fff;
  padding: 12px;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-action-item:hover {
  border-color: #dbeafe;
  background: #f8fbff;
}

.quick-action-text {
  min-width: 0;
}

.quick-action-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.quick-action-desc {
  margin-top: 3px;
  font-size: 12px;
  color: #6b7280;
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 14px;
  }

  .stat-card {
    padding: 16px;
  }

  .stat-value {
    font-size: 20px;
  }
}
</style>
