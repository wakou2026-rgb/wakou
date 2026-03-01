<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, nextTick } from "vue";
import {
  TrendCharts,
  PieChart,
  DataAnalysis,
  ShoppingCart,
  Plus,
  Download
} from "@element-plus/icons-vue";
import * as XLSX from "xlsx";
import {
  getReportSummary,
  getMonthlyReport,
  getCosts,
  getCategoryBreakdown,
  addCost,
  addRevenue,
  type ReportSummary,
  type MonthlyReport,
  type CostEntry,
  type CategoryBreakdownItem
} from "@/api/finance";
import { useECharts } from "@pureadmin/utils";
import { ElMessage } from "element-plus";

defineOptions({ name: "FinanceIndex" });

// ─── State ────────────────────────────────────────────────────────────────────
const summaryLoading = ref(true);
const summary = ref<ReportSummary>({
  total_revenue: 0,
  total_cost: 0,
  profit_margin: 0,
  profit_twd: 0,
  order_count: 0
});

const costsLoading = ref(true);
const costs = ref<CostEntry[]>([]);

const monthlyData = ref<MonthlyReport[]>([]);
const categoryData = ref<CategoryBreakdownItem[]>([]);

const dialogVisible = ref(false);
const formLoading = ref(false);
const formData = ref<Partial<CostEntry & { category: string; amount: number }>>({
  category: "",
  amount: 0,
  note: "",
  cost_type: "misc",
  product_id: null
});

// ─── Revenue Dialog ──────────────────────────────────────────────────────────
const revenueDialogVisible = ref(false);
const revenueFormLoading = ref(false);
const revenueFormData = ref<{ title: string; amount_twd: number; recorded_at: string; note: string }>({
  title: "",
  amount_twd: 0,
  recorded_at: new Date().toISOString().slice(0, 10),
  note: "",
});

// ─── Charts ───────────────────────────────────────────────────────────────────
const trendChartRef = ref<HTMLDivElement | null>(null);
const pieChartRef = ref<HTMLDivElement | null>(null);
const {
  setOptions: setTrendOptions,
  getInstance: getTrendInstance,
  resize: resizeTrendChart
} = useECharts(trendChartRef as any);
const {
  setOptions: setPieOptions,
  getInstance: getPieInstance,
  resize: resizePieChart
} = useECharts(pieChartRef as any);
let resizeTimer: ReturnType<typeof setTimeout> | null = null;
let chartsResizeObserver: ResizeObserver | null = null;

const monthLabels = computed(() =>
  monthlyData.value.map(d => `${d.month}月`)
);

function renderTrendChart() {
  if (!trendChartRef.value) return;
  const data = monthlyData.value;
  setTrendOptions({
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        return (
          params[0].name +
          "<br/>" +
          params
            .map(
              (p: any) =>
                `${p.marker}${p.seriesName}: NT$${Number(p.value).toLocaleString()}`
            )
            .join("<br/>")
        );
      }
    },
    legend: {
      data: ["收入", "成本", "利潤"],
      top: 8,
      textStyle: { fontSize: 13 }
    },
    grid: { left: 60, right: 24, top: 48, bottom: 36 },
    xAxis: {
      type: "category",
      data: monthLabels.value,
      axisLine: { lineStyle: { color: "#e0e0e0" } },
      axisTick: { show: false }
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: (v: number) =>
          v >= 1000 ? `${Math.round(v / 1000)}k` : String(v)
      },
      splitLine: { lineStyle: { color: "#f0f0f0" } }
    },
    series: [
      {
        name: "收入",
        type: "line",
        smooth: true,
        data: data.map(d => d.revenue),
        itemStyle: { color: "#5b8ff9" },
        areaStyle: { color: "rgba(91,143,249,0.08)" },
        symbol: "circle",
        symbolSize: 6
      },
      {
        name: "成本",
        type: "line",
        smooth: true,
        data: data.map(d => d.cost),
        itemStyle: { color: "#ff7875" },
        areaStyle: { color: "rgba(255,120,117,0.07)" },
        symbol: "circle",
        symbolSize: 6
      },
      {
        name: "利潤",
        type: "line",
        smooth: true,
        data: data.map(d => (d.profit ?? d.revenue - d.cost)),
        itemStyle: { color: "#73d13d" },
        areaStyle: { color: "rgba(115,209,61,0.08)" },
        symbol: "circle",
        symbolSize: 6
      }
    ]
  });
}

const COST_TYPE_LABEL: Record<string, string> = {
  product: "商品採購",
  misc: "雜費",
  shipping: "運費",
  marketing: "行銷",
  other: "其他"
};

function renderPieChart() {
  const items = categoryData.value;
  if (!items.length || !pieChartRef.value) return;
  setPieOptions({
    tooltip: {
      trigger: "item",
      formatter: (p: any) =>
        `${p.name}<br/>NT$${Number(p.value).toLocaleString()} (${p.percent}%)`
    },
    legend: {
      orient: "vertical",
      right: 16,
      top: "center",
      textStyle: { fontSize: 12 }
    },
    series: [
      {
        name: "成本類別",
        type: "pie",
        radius: ["42%", "68%"],
        center: ["38%", "50%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 13, fontWeight: "bold" }
        },
        data: items.map(i => ({
          name: COST_TYPE_LABEL[i.category] ?? i.category,
          value: i.total
        }))
      }
    ]
  });
}

const waitForChartContainer = (elRef: typeof trendChartRef, maxFrames = 20) =>
  new Promise<void>(resolve => {
    let frame = 0;
    const check = () => {
      const el = elRef.value;
      if (!el) {
        resolve();
        return;
      }
      if (el.clientWidth > 0 && el.clientHeight > 0) {
        resolve();
        return;
      }
      frame += 1;
      if (frame >= maxFrames) {
        resolve();
        return;
      }
      requestAnimationFrame(check);
    };
    check();
  });

const resizeCharts = () => {
  if (getTrendInstance()) {
    resizeTrendChart();
  }
  if (getPieInstance()) {
    resizePieChart();
  }
};

const scheduleChartsResize = () => {
  if (resizeTimer) {
    clearTimeout(resizeTimer);
  }
  resizeTimer = setTimeout(() => {
    resizeCharts();
  }, 200);
};

const setupChartsResizeObserver = () => {
  if (typeof window === "undefined" || typeof ResizeObserver === "undefined") return;
  chartsResizeObserver?.disconnect();
  chartsResizeObserver = new ResizeObserver(() => {
    scheduleChartsResize();
  });
  if (trendChartRef.value) {
    chartsResizeObserver.observe(trendChartRef.value);
  }
  if (pieChartRef.value) {
    chartsResizeObserver.observe(pieChartRef.value);
  }
};

const renderCharts = async () => {
  await nextTick();
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  await waitForChartContainer(trendChartRef);
  await waitForChartContainer(pieChartRef);
  renderTrendChart();
  renderPieChart();
  await nextTick();
  resizeCharts();
  setupChartsResizeObserver();
};

// ─── Load ─────────────────────────────────────────────────────────────────────
const loadAll = async () => {
  summaryLoading.value = true;
  try {
    const [summaryRes, chartRes, catRes] = await Promise.all([
      getReportSummary(),
      getMonthlyReport(),
      getCategoryBreakdown()
    ]);
    summary.value = (summaryRes as any).data ?? summaryRes;
    monthlyData.value = Array.isArray(chartRes)
      ? chartRes
      : ((chartRes as any).data ?? []);
    categoryData.value = catRes;
  } catch (e: any) {
    ElMessage.error(e?.message ?? "無法載入報表");
  } finally {
    summaryLoading.value = false;
    await renderCharts();
  }
};

const loadCosts = async () => {
  costsLoading.value = true;
  try {
    const res = await getCosts();
    costs.value = Array.isArray(res) ? res : ((res as any).data ?? []);
  } catch (e: any) {
    ElMessage.error(e?.message ?? "無法載入成本紀錄");
  } finally {
    costsLoading.value = false;
  }
};

// ─── Dialog ───────────────────────────────────────────────────────────────────
const handleAddCost = () => {
  formData.value = {
    category: "",
    amount: 0,
    note: "",
    cost_type: "misc",
    product_id: null
  };
  dialogVisible.value = true;
};

const submitForm = async () => {
  if (!formData.value.category || !(formData.value.amount! > 0)) {
    ElMessage.warning("請填寫必要欄位");
    return;
  }
  try {
    formLoading.value = true;
    await addCost(formData.value as any);
    ElMessage.success("新增成功");
    dialogVisible.value = false;
    await Promise.all([loadCosts(), loadAll()]);
  } catch (e: any) {
    ElMessage.error(e?.message ?? "儲存失敗");
  } finally {
    formLoading.value = false;
  }
};

const handleAddRevenue = () => {
  revenueFormData.value = {
    title: "",
    amount_twd: 0,
    recorded_at: new Date().toISOString().slice(0, 10),
    note: "",
  };
  revenueDialogVisible.value = true;
};

const submitRevenue = async () => {
  if (!revenueFormData.value.title || !(revenueFormData.value.amount_twd > 0)) {
    ElMessage.warning("請填寫必要欄位");
    return;
  }
  try {
    revenueFormLoading.value = true;
    await addRevenue(revenueFormData.value);
    ElMessage.success("收入紀錄新增成功");
    revenueDialogVisible.value = false;
    await loadAll();
  } catch (e: any) {
    ElMessage.error(e?.message ?? "儲存失敗");
  } finally {
    revenueFormLoading.value = false;
  }
};

// ─── Computed helpers ─────────────────────────────────────────────────────────
const profitClass = computed(() =>
  (summary.value.profit_twd ?? 0) >= 0 ? "profit-positive" : "profit-negative"
);

const formatCurrency = (v: number) =>
  "NT$" + Number(v ?? 0).toLocaleString("zh-TW");

const exportFinanceExcel = () => {
  try {
    const summarySheet = XLSX.utils.json_to_sheet([
      {
        total_revenue: summary.value.total_revenue ?? 0,
        total_cost: summary.value.total_cost ?? 0,
        profit: summary.value.profit_twd ?? (summary.value.total_revenue ?? 0) - (summary.value.total_cost ?? 0),
        margin: summary.value.profit_margin ?? 0,
        order_count: summary.value.order_count ?? 0
      }
    ]);

    const monthlySheet = XLSX.utils.json_to_sheet(
      monthlyData.value.map(item => ({
        month: item.month,
        revenue: item.revenue ?? 0,
        cost: item.cost ?? 0,
        profit: item.profit ?? (item.revenue ?? 0) - (item.cost ?? 0)
      }))
    );

    const costSheet = XLSX.utils.json_to_sheet(
      costs.value.map(item => ({
        id: item.id,
        title: item.title,
        cost_type: item.cost_type ?? "",
        amount_twd: item.amount_twd ?? item.amount ?? 0,
        note: item.note ?? "",
        recorded_at: item.recorded_at ?? ""
      }))
    );

    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, summarySheet, "財務摘要");
    XLSX.utils.book_append_sheet(workbook, monthlySheet, "月度報表");
    XLSX.utils.book_append_sheet(workbook, costSheet, "成本紀錄");
    const dateText = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(workbook, `和光精選_財務報表_${dateText}.xlsx`);
    ElMessage.success("Excel 導出成功");
  } catch (error: any) {
    ElMessage.error(error?.message ?? "Excel 導出失敗");
  }
};

onMounted(() => {
  if (typeof window !== "undefined") {
    window.addEventListener("resize", scheduleChartsResize);
  }
  loadAll();
  loadCosts();
});

onBeforeUnmount(() => {
  if (typeof window !== "undefined") {
    window.removeEventListener("resize", scheduleChartsResize);
  }
  if (resizeTimer) {
    clearTimeout(resizeTimer);
    resizeTimer = null;
  }
  chartsResizeObserver?.disconnect();
  chartsResizeObserver = null;
});
</script>

<template>
  <div class="finance-page">
    <div class="summary-actions">
      <el-button type="primary" plain @click="exportFinanceExcel">
        <el-icon><Download /></el-icon>
        導出 Excel
      </el-button>
    </div>

    <!-- ── Summary Cards ─────────────────────────────────────── -->
    <el-row :gutter="16" class="summary-row" v-loading="summaryLoading">
      <!-- 總收入 -->
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-revenue">
          <div class="stat-icon">
            <i class="iconfont icon-revenue" />
            <el-icon size="28"><TrendCharts /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">總收入</div>
            <div class="stat-value">{{ formatCurrency(summary.total_revenue) }}</div>
            <div class="stat-sub">已付款 / 完成訂單</div>
          </div>
        </div>
      </el-col>

      <!-- 總成本 -->
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-cost">
          <div class="stat-icon">
            <el-icon size="28"><PieChart /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">總成本</div>
            <div class="stat-value">{{ formatCurrency(summary.total_cost) }}</div>
            <div class="stat-sub">累計成本支出</div>
          </div>
        </div>
      </el-col>

      <!-- 利潤 -->
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-profit">
          <div class="stat-icon">
            <el-icon size="28"><DataAnalysis /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">淨利潤</div>
            <div class="stat-value" :class="profitClass">
              {{ formatCurrency(summary.profit_twd ?? summary.total_revenue - summary.total_cost) }}
            </div>
            <div class="stat-sub">利潤率 {{ summary.profit_margin }}%</div>
          </div>
        </div>
      </el-col>

      <!-- 訂單數 -->
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-orders">
          <div class="stat-icon">
            <el-icon size="28"><ShoppingCart /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">完成訂單</div>
            <div class="stat-value">{{ summary.order_count ?? 0 }}</div>
            <div class="stat-sub">付款 / 完成狀態</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ── Charts Row ─────────────────────────────────────────── -->
    <el-row :gutter="16" class="chart-row">
      <!-- 趨勢折線圖 -->
      <el-col :xs="24" :lg="16">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">收入 / 成本 / 利潤趨勢</span>
              <span class="card-sub">2026 全年月報</span>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-canvas" />
        </el-card>
      </el-col>

      <!-- 成本類別圓餅圖 -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">成本類別分佈</span>
            </div>
          </template>
          <div
            v-if="categoryData.length"
            ref="pieChartRef"
            class="chart-canvas"
          />
          <el-empty v-else description="暫無成本資料" class="chart-empty" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ── Costs Table ────────────────────────────────────────── -->
    <el-card shadow="never" class="costs-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">成本紀錄</span>
          <div style="display:flex;gap:8px;">
            <el-button type="warning" size="small" @click="exportFinanceExcel">
              <el-icon><Download /></el-icon>
              導出 Excel
            </el-button>
            <el-button type="success" size="small" @click="handleAddRevenue">
              <el-icon><Plus /></el-icon>
              新增收入
            </el-button>
            <el-button type="primary" size="small" @click="handleAddCost">
              <el-icon><Plus /></el-icon>
              新增成本
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="costs"
        v-loading="costsLoading"
        style="width: 100%"
        stripe
        border
        :header-cell-style="{ background: '#fafafa', fontWeight: '600' }"
      >
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="title" label="名稱 / 類別" min-width="160" />
        <el-table-column prop="cost_type" label="成本類型" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.cost_type === 'product' ? 'primary' : 'info'"
              size="small"
              effect="light"
            >
              {{ COST_TYPE_LABEL[row.cost_type] ?? row.cost_type ?? '雜費' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金額 (TWD)" width="140" align="right">
          <template #default="{ row }">
            <span class="amount-cell">
              {{ formatCurrency(row.amount_twd ?? row.amount ?? 0) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="備註" min-width="120">
          <template #default="{ row }">
            <span class="note-cell">{{ row.note || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="記錄日期" width="140" align="center">
          <template #default="{ row }">
            {{ row.recorded_at ? new Date(row.recorded_at).toLocaleDateString("zh-TW") : "—" }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ── Add Cost Dialog ────────────────────────────────────── -->
    <el-dialog v-model="dialogVisible" title="新增成本紀錄" width="440px" draggable>
      <el-form :model="formData" label-width="90px" label-position="right">
        <el-form-item label="名稱" required>
          <el-input v-model="formData.category" placeholder="例：2月商品採購" clearable />
        </el-form-item>
        <el-form-item label="金額 (TWD)" required>
          <el-input-number
            v-model="formData.amount"
            :min="0"
            :step="1000"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="成本類型">
          <el-select v-model="formData.cost_type" style="width: 100%">
            <el-option value="misc" label="雜費" />
            <el-option value="product" label="商品採購" />
            <el-option value="shipping" label="運費" />
            <el-option value="marketing" label="行銷費用" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品 ID" v-if="formData.cost_type === 'product'">
          <el-input-number
            v-model="formData.product_id"
            :min="1"
            placeholder="關聯商品 ID"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="備註">
          <el-input
            v-model="formData.note"
            type="textarea"
            :rows="2"
            placeholder="選填"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="formLoading" @click="submitForm">
          確認新增
        </el-button>
      </template>
    </el-dialog>

    <!-- ── Add Revenue Dialog ────────────────────────────────────── -->
    <el-dialog v-model="revenueDialogVisible" title="新增收入紀錄" width="440px" draggable>
      <el-form :model="revenueFormData" label-width="90px" label-position="right">
        <el-form-item label="標題" required>
          <el-input v-model="revenueFormData.title" placeholder="例：訂單收款 / 手動入帳" clearable />
        </el-form-item>
        <el-form-item label="金額 (TWD)" required>
          <el-input-number
            v-model="revenueFormData.amount_twd"
            :min="0"
            :step="1000"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="日期">
          <el-input v-model="revenueFormData.recorded_at" placeholder="YYYY-MM-DD" clearable />
        </el-form-item>
        <el-form-item label="備註">
          <el-input
            v-model="revenueFormData.note"
            type="textarea"
            :rows="2"
            placeholder="選填"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="revenueDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="revenueFormLoading" @click="submitRevenue">
          確認新增
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.finance-page {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Summary Cards ─────────────────────────────────── */
.summary-row {
  margin-bottom: 0 !important;
}

.summary-actions {
  display: flex;
  justify-content: flex-end;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 20px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #f0f0f0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
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

.stat-revenue .stat-icon {
  background: rgba(91, 143, 249, 0.12);
  color: #5b8ff9;
}
.stat-cost .stat-icon {
  background: rgba(255, 120, 117, 0.12);
  color: #ff7875;
}
.stat-profit .stat-icon {
  background: rgba(115, 209, 61, 0.12);
  color: #52c41a;
}
.stat-orders .stat-icon {
  background: rgba(250, 173, 20, 0.12);
  color: #fa8c16;
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
  color: #1a1a1a;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-sub {
  font-size: 12px;
  color: #bfbfbf;
  margin-top: 4px;
}

.profit-positive {
  color: #52c41a !important;
}
.profit-negative {
  color: #ff4d4f !important;
}

/* ── Charts ────────────────────────────────────────── */
.chart-row {
  margin-bottom: 0 !important;
}

.chart-card {
  border-radius: 10px !important;
  margin-bottom: 16px;
}

.chart-canvas {
  width: 100%;
  height: 320px;
  min-height: 320px;
}

.chart-empty {
  height: 320px;
  min-height: 320px;
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

.card-sub {
  font-size: 12px;
  color: #8c8c8c;
}

/* ── Costs Table ────────────────────────────────────── */
.costs-card {
  border-radius: 10px !important;
}

.amount-cell {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  color: #cf1322;
}

.note-cell {
  color: #595959;
  font-size: 13px;
}
</style>
