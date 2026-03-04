<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, nextTick, reactive } from "vue";
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
import {
  getLedger,
  createLedgerItem,
  markSold,
  deleteLedgerItem,
  setDistributions,
  getInvestors,
  createInvestor,
  updateInvestor,
  addContribution,
  getInvestorsSummary,
  type LedgerItem,
  type Investor,
  type InvestorSummary,
  type LedgerCreatePayload,
  type DistributionsPayload,
  type InvestorCreatePayload,
  type InvestorUpdatePayload,
  type ContributionPayload
} from "@/api/ledger";
import { useECharts } from "@pureadmin/utils";
import * as echarts from 'echarts/core';
import { BarChart, PieChart as EcPieChart } from 'echarts/charts';
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
echarts.use([BarChart, EcPieChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer]);
import { ElMessage, ElMessageBox } from "element-plus";

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
const costsPage = ref(1);
const costsPageSize = ref(10);

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

// ─── Ledger Charts ───────────────────────────────────────────────────────────
const ledgerBarRef = ref<HTMLDivElement | null>(null);
const investorPieRef = ref<HTMLDivElement | null>(null);
const investorBarRef = ref<HTMLDivElement | null>(null);
let ledgerBarChart: echarts.ECharts | null = null;
let investorPieChart: echarts.ECharts | null = null;
let investorBarChart: echarts.ECharts | null = null;

function getLedgerBarChart(): echarts.ECharts | null {
  if (!ledgerBarRef.value) return null;
  if (!ledgerBarChart || ledgerBarChart.getDom() !== ledgerBarRef.value) {
    ledgerBarChart?.dispose();
    ledgerBarChart = echarts.init(ledgerBarRef.value);
  }
  return ledgerBarChart;
}

function getInvestorPieChart(): echarts.ECharts | null {
  if (!investorPieRef.value) return null;
  if (!investorPieChart || investorPieChart.getDom() !== investorPieRef.value) {
    investorPieChart?.dispose();
    investorPieChart = echarts.init(investorPieRef.value);
  }
  return investorPieChart;
}

function getInvestorBarChart(): echarts.ECharts | null {
  if (!investorBarRef.value) return null;
  if (!investorBarChart || investorBarChart.getDom() !== investorBarRef.value) {
    investorBarChart?.dispose();
    investorBarChart = echarts.init(investorBarRef.value);
  }
  return investorBarChart;
}

function renderLedgerBarChart() {
  const chart = getLedgerBarChart();
  if (!chart) return;
  const items = ledgerItems.value;
  if (!items.length) return;
  const names = items.map(i => i.item_name.length > 10 ? i.item_name.slice(0, 10) + '\u2026' : i.item_name);
  const purchases = items.map(i => i.cost_twd);
  const revenues = items.map(i => i.sold && i.actual_price_twd ? i.actual_price_twd : 0);
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any[]) =>
        params[0].name + '<br/>' +
        params.map((p: any) => `${p.marker}${p.seriesName}: NT$${Number(p.value).toLocaleString()}`).join('<br/>')
    },
    legend: { data: ['進貨成本', '售出收入'], top: 6, textStyle: { fontSize: 12 } },
    grid: { left: 12, right: 12, top: 40, bottom: 40, containLabel: true },
    xAxis: { type: 'category', data: names, axisLabel: { fontSize: 11, interval: 0, rotate: names.length > 6 ? 30 : 0 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => v >= 1000 ? `${Math.round(v / 1000)}k` : String(v) }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      { name: '進貨成本', type: 'bar', data: purchases, itemStyle: { color: '#ff7875', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 40 },
      { name: '售出收入', type: 'bar', data: revenues, itemStyle: { color: '#73d13d', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 40 }
    ]
  }, true);
}

function renderInvestorPieChart() {
  const chart = getInvestorPieChart();
  if (!chart) return;
  const data = investorSummary.value
    .map(inv => ({ name: inv.name, value: inv.total_contributed_twd || 0 }))
    .filter(d => d.value > 0);
  if (!data.length) return;
  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}<br/>出資: NT$${Number(p.value).toLocaleString()}<br/>佔比: ${p.percent}%`
    },
    legend: { orient: 'vertical', right: 8, top: 'middle', textStyle: { fontSize: 12 } },
    series: [{
      name: '出資佔比',
      type: 'pie',
      radius: ['45%', '72%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: true,
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
      data
    }]
  }, true);
}

function renderInvestorBarChart() {
  const chart = getInvestorBarChart();
  if (!chart) return;
  const names = investorSummary.value.map(inv => inv.name);
  const contributed = investorSummary.value.map(inv => inv.total_contributed_twd || 0);
  const profits = investorSummary.value.map(inv => inv.total_distributed_twd || 0);
  if (!names.length) return;
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any[]) =>
        params[0].name + '<br/>' +
        params.map((p: any) => `${p.marker}${p.seriesName}: NT$${Number(p.value).toLocaleString()}`).join('<br/>')
    },
    legend: { data: ['總出資', '已分配利潤'], top: 6, textStyle: { fontSize: 12 } },
    grid: { left: 12, right: 12, top: 40, bottom: 20, containLabel: true },
    xAxis: { type: 'category', data: names, axisLabel: { fontSize: 12 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => v >= 1000 ? `${Math.round(v / 1000)}k` : String(v) }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      { name: '總出資', type: 'bar', data: contributed, itemStyle: { color: '#5b8ff9', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 50 },
      { name: '已分配利潤', type: 'bar', data: profits, itemStyle: { color: '#ffd666', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 50 }
    ]
  }, true);
}

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
  ledgerBarChart?.resize();
  investorPieChart?.resize();
  investorBarChart?.resize();
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
  if (ledgerBarRef.value) {
    chartsResizeObserver.observe(ledgerBarRef.value);
  }
  if (investorPieRef.value) {
    chartsResizeObserver.observe(investorPieRef.value);
  }
  if (investorBarRef.value) {
    chartsResizeObserver.observe(investorBarRef.value);
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
    costsPage.value = 1;
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

const pagedCosts = computed(() => {
  const start = (costsPage.value - 1) * costsPageSize.value;
  return costs.value.slice(start, start + costsPageSize.value);
});

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
  restoreInvestorRatioMap();
  loadAll();
  loadCosts();
  loadLedger();
  loadInvestors();
  loadInvestorSummary();
});

// ─── Ledger State ────────────────────────────────────────────────────────────
const ledgerTab = ref("ledger");

const ledgerLoading = ref(false);
const ledgerItems = ref<LedgerItem[]>([]);
const showAddLedgerForm = ref(false);
const addLedgerForm = reactive<LedgerCreatePayload>({
  item_name: "",
  purchase_date: new Date().toISOString().slice(0, 10),
  cost_jpy: 0,
  exchange_rate: 0.21,
  expected_price_twd: 0,
  grade: "A",
  location: "",
  source: "",
  note: ""
});
const addLedgerLoading = ref(false);

const unsoldItems = computed(() => ledgerItems.value.filter(i => !i.sold));
const soldItems = computed(() => ledgerItems.value.filter(i => i.sold));
const unsoldPage = ref(1);
const soldPage = ref(1);
const ledgerPageSize = ref(10);

const pagedUnsoldItems = computed(() => {
  const start = (unsoldPage.value - 1) * ledgerPageSize.value;
  return unsoldItems.value.slice(start, start + ledgerPageSize.value);
});

const pagedSoldItems = computed(() => {
  const start = (soldPage.value - 1) * ledgerPageSize.value;
  return soldItems.value.slice(start, start + ledgerPageSize.value);
});

async function loadLedger() {
  ledgerLoading.value = true;
  try {
    const res: any = await getLedger();
    const payload = res?.data ?? res;
    ledgerItems.value = Array.isArray(payload?.items) ? payload.items : [];
    unsoldPage.value = 1;
    soldPage.value = 1;
    await nextTick();
    renderLedgerBarChart();
  } catch (e: any) {
    ElMessage.error(e?.message || "載入帳本失敗");
  } finally {
    ledgerLoading.value = false;
  }
}

async function submitAddLedger() {
  if (!addLedgerForm.item_name.trim()) {
    ElMessage.warning("請填寫商品名稱");
    return;
  }
  addLedgerLoading.value = true;
  try {
    await createLedgerItem({
      item_name: addLedgerForm.item_name.trim(),
      purchase_date: addLedgerForm.purchase_date || new Date().toISOString().slice(0, 10),
      cost_jpy: Number(addLedgerForm.cost_jpy) || 0,
      exchange_rate: Number(addLedgerForm.exchange_rate) || 0.21,
      expected_price_twd: Number(addLedgerForm.expected_price_twd) || 0,
      grade: addLedgerForm.grade || "A",
      location: addLedgerForm.location?.trim() || undefined,
      source: addLedgerForm.source?.trim() || undefined,
      note: addLedgerForm.note?.trim() || undefined
    });
    ElMessage.success("帳本項目已新增");
    Object.assign(addLedgerForm, { item_name: "", purchase_date: new Date().toISOString().slice(0, 10), cost_jpy: 0, exchange_rate: 0.21, expected_price_twd: 0, grade: "A", location: "", source: "", note: "" });
    showAddLedgerForm.value = false;
    await loadLedger();
  } catch (e: any) {
    ElMessage.error(e?.message || "新增失敗");
  } finally {
    addLedgerLoading.value = false;
  }
}

async function handleMarkSold(item: LedgerItem) {
  const sellingPriceStr = await ElMessageBox.prompt(
    `請輸入「${item.item_name}」的售出價格（TWD）`,
    "標記售出",
    { confirmButtonText: "確認", cancelButtonText: "取消", inputPattern: /^\d+(\.(\d+))?$/, inputErrorMessage: "請輸入有效金額" }
  ).then(r => r.value).catch(() => null);
  if (!sellingPriceStr) return;
  try {
    await markSold(item.id, { actual_price_twd: Number(sellingPriceStr) });
    ElMessage.success("已標記售出");
    await loadLedger();
  } catch (e: any) {
    ElMessage.error(e?.message || "標記售出失敗");
  }
}

async function handleDeleteLedger(item: LedgerItem) {
  await ElMessageBox.confirm(`確定刪除「${item.item_name}」？`, "確認刪除", {
    confirmButtonText: "刪除", cancelButtonText: "取消", type: "warning"
  }).catch(() => { throw new Error("cancel"); });
  try {
    await deleteLedgerItem(item.id);
    ElMessage.success("已刪除");
    await loadLedger();
  } catch (e: any) {
    if (e?.message === "cancel") return;
    ElMessage.error(e?.message || "刪除失敗");
  }
}

// Distribution dialog
const distDialog = ref(false);
const distTargetItem = ref<LedgerItem | null>(null);
type DistributionDraft = {
  key: string;
  investor_id: number | null;
  label: string;
  ratio: number;
  amount: number;
};
const distRows = ref<DistributionDraft[]>([]);
const distLoading = ref(false);

const availableProfit = computed(() => {
  const value = Number(distTargetItem.value?.profit_twd ?? 0);
  return value > 0 ? value : 0;
});

const totalDistAmount = computed(() =>
  distRows.value.reduce((sum, row) => sum + (Number(row.amount) || 0), 0)
);

const totalDistRatio = computed(() =>
  distRows.value.reduce((sum, row) => sum + (Number(row.ratio) || 0), 0)
);

function toDistributionDraftFromInvestors(): DistributionDraft[] {
  const investorRows = investors.value.map(inv => {
    const ratio = getEffectiveInvestorRatio(inv.id);
    return {
      key: `inv-${inv.id}`,
      investor_id: inv.id,
      label: inv.name,
      ratio,
      amount: 0
    } as DistributionDraft;
  });
  investorRows.push({
    key: "tech-role",
    investor_id: null,
    label: "技術分紅",
    ratio: 0,
    amount: 0
  });
  return investorRows;
}

function applyRatioDistribution() {
  if (availableProfit.value <= 0) {
    ElMessage.warning("此商品利潤為 0，無可分配金額");
    return;
  }
  const candidates = distRows.value.filter(row => Number(row.ratio) > 0);
  const ratioTotal = candidates.reduce((sum, row) => sum + Number(row.ratio), 0);
  if (!ratioTotal) {
    ElMessage.warning("請先設定比例（總比例需大於 0）");
    return;
  }

  let remaining = availableProfit.value;
  const lastIndex = candidates.length - 1;
  candidates.forEach((row, idx) => {
    const amount =
      idx === lastIndex
        ? remaining
        : Math.floor((availableProfit.value * Number(row.ratio)) / ratioTotal);
    row.amount = amount;
    remaining -= amount;
  });

  distRows.value
    .filter(row => Number(row.ratio) <= 0)
    .forEach(row => {
      row.amount = 0;
    });
}

function openDistDialog(item: LedgerItem) {
  distTargetItem.value = item;
  distRows.value = toDistributionDraftFromInvestors();
  distDialog.value = true;
}

async function submitDistribution() {
  if (!distTargetItem.value) return;
  const payloadRows = distRows.value
    .filter(row => Number(row.amount) > 0)
    .map(row => ({
      investor_id: row.investor_id,
      label: row.label?.trim() || "利潤分配",
      amount_twd: Number(row.amount)
    }));

  if (!payloadRows.length) {
    ElMessage.warning("請至少設定一筆分配金額");
    return;
  }

  if (availableProfit.value > 0) {
    const total = payloadRows.reduce((sum, row) => sum + row.amount_twd, 0);
    if (total > availableProfit.value) {
      ElMessage.warning("分配總額不可超過此商品利潤");
      return;
    }
  }

  if (payloadRows.some(row => !row.label.trim())) {
    ElMessage.warning("分配標籤不可為空");
    return;
  }
  distLoading.value = true;
  try {
    await setDistributions(distTargetItem.value.id, {
      distributions: payloadRows
    } as DistributionsPayload);
    ElMessage.success("利潤分配已記錄");
    distDialog.value = false;
    await loadInvestorSummary();
  } catch (e: any) {
    ElMessage.error(e?.message || "分配失敗");
  } finally {
    distLoading.value = false;
  }
}

// Investors
const investorsLoading = ref(false);
const investors = ref<Investor[]>([]);
const investorRatioMap = ref<Record<number, number>>({});
const INVESTOR_RATIO_STORAGE_KEY = "wakou_finance_investor_ratio_map";
const showInvestorForm = ref(false);
const investorForm = reactive<InvestorCreatePayload>({ name: "", note: "" });
const investorAddLoading = ref(false);
const investorEditDialog = ref(false);
const investorEditLoading = ref(false);
const investorEditForm = reactive<{ id: number | null; name: string; note: string }>({
  id: null,
  name: "",
  note: ""
});
const contribDialog = ref(false);
const contribTarget = ref<Investor | null>(null);
const contribForm = reactive<ContributionPayload>({ amount_twd: 0, contributed_at: new Date().toISOString().slice(0, 10), note: "" });
const contribLoading = ref(false);

async function loadInvestors() {
  investorsLoading.value = true;
  try {
    const res: any = await getInvestors();
    const payload = res?.data ?? res;
    investors.value = Array.isArray(payload?.investors) ? payload.investors : [];
    const nextMap: Record<number, number> = {};
    investors.value.forEach(inv => {
      const ratio = investorRatioMap.value[inv.id];
      if (Number.isFinite(ratio)) {
        nextMap[inv.id] = Number(ratio);
      }
    });
    investorRatioMap.value = nextMap;
    persistInvestorRatioMap();
  } catch (e: any) {
    ElMessage.error(e?.message || "載入投資人失敗");
  } finally {
    investorsLoading.value = false;
  }
}

function restoreInvestorRatioMap() {
  if (typeof window === "undefined") return;
  try {
    const raw = window.localStorage.getItem(INVESTOR_RATIO_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return;
    const next: Record<number, number> = {};
    Object.entries(parsed as Record<string, unknown>).forEach(([key, value]) => {
      const investorId = Number(key);
      const ratio = Number(value);
      if (Number.isFinite(investorId) && Number.isFinite(ratio)) {
        next[investorId] = ratio;
      }
    });
    investorRatioMap.value = next;
  } catch {
    investorRatioMap.value = {};
  }
}

function persistInvestorRatioMap() {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(INVESTOR_RATIO_STORAGE_KEY, JSON.stringify(investorRatioMap.value));
}

function updateInvestorRatio(investorId: number, ratio: number) {
  investorRatioMap.value = {
    ...investorRatioMap.value,
    [investorId]: Number(ratio)
  };
  persistInvestorRatioMap();
}

function getCalculatedInvestorRatio(investorId: number) {
  const totalContributed = investorSummary.value.reduce(
    (sum, row) => sum + Number(row.total_contributed_twd || 0),
    0
  );
  if (totalContributed <= 0) return 0;
  const summaryRow = investorSummary.value.find(row => row.id === investorId);
  const contributed = Number(summaryRow?.total_contributed_twd || 0);
  return Number(((contributed / totalContributed) * 100).toFixed(2));
}

function getEffectiveInvestorRatio(investorId: number) {
  const configuredRatio = investorRatioMap.value[investorId];
  if (Number.isFinite(configuredRatio)) {
    return Number(configuredRatio);
  }
  return getCalculatedInvestorRatio(investorId);
}

async function submitInvestor() {
  if (!investorForm.name.trim()) {
    ElMessage.warning("請填寫投資人姓名");
    return;
  }
  investorAddLoading.value = true;
  try {
    await createInvestor({
      name: investorForm.name.trim(),
      note: investorForm.note?.trim() || undefined
    });
    ElMessage.success("投資人已新增");
    Object.assign(investorForm, { name: "", note: "" });
    showInvestorForm.value = false;
    await loadInvestors();
  } catch (e: any) {
    ElMessage.error(e?.message || "新增投資人失敗");
  } finally {
    investorAddLoading.value = false;
  }
}

function openEditInvestorDialog(investor: Investor) {
  Object.assign(investorEditForm, {
    id: investor.id,
    name: investor.name,
    note: investor.note || ""
  });
  investorEditDialog.value = true;
}

async function submitEditInvestor() {
  if (!investorEditForm.id) return;
  if (!investorEditForm.name.trim()) {
    ElMessage.warning("請填寫投資人姓名");
    return;
  }
  investorEditLoading.value = true;
  try {
    const payload: InvestorUpdatePayload = {
      name: investorEditForm.name.trim(),
      note: investorEditForm.note?.trim() || ""
    };
    await updateInvestor(investorEditForm.id, payload);
    ElMessage.success("投資人資料已更新");
    investorEditDialog.value = false;
    await loadInvestors();
    await loadInvestorSummary();
  } catch (e: any) {
    ElMessage.error(e?.message || "更新投資人失敗");
  } finally {
    investorEditLoading.value = false;
  }
}

function openContribDialog(investor: Investor) {
  contribTarget.value = investor;
  Object.assign(contribForm, { amount_twd: 0, contributed_at: new Date().toISOString().slice(0, 10), note: "" });
  contribDialog.value = true;
}

async function submitContribution() {
  if (!contribForm.amount_twd) {
    ElMessage.warning("請填寫出資金額");
    return;
  }
  contribLoading.value = true;
  try {
    await addContribution(contribTarget.value!.id, {
      amount_twd: Number(contribForm.amount_twd),
      contributed_at: contribForm.contributed_at || new Date().toISOString().slice(0, 10),
      note: contribForm.note || undefined
    });
    ElMessage.success("出資記錄已新增");
    contribDialog.value = false;
    await loadInvestorSummary();
  } catch (e: any) {
    ElMessage.error(e?.message || "新增出資失敗");
  } finally {
    contribLoading.value = false;
  }
}

// Summary
const summaryInvLoading = ref(false);
const investorSummary = ref<InvestorSummary[]>([]);

async function loadInvestorSummary() {
  summaryInvLoading.value = true;
  try {
    const res: any = await getInvestorsSummary();
    const payload = res?.data ?? res;
    investorSummary.value = Array.isArray(payload?.investors) ? payload.investors : [];
    await nextTick();
    renderInvestorPieChart();
    renderInvestorBarChart();
  } catch (e: any) {
    ElMessage.error(e?.message || "載入摘要失敗");
  } finally {
    summaryInvLoading.value = false;
  }
}

function handleLedgerTabChange(tab: string) {
  if (tab === "investors" && !investors.value.length) loadInvestors();
  if (tab === "inv-summary" && !investorSummary.value.length) loadInvestorSummary();
}

function formatNTD(v: number | null | undefined) {
  if (v == null) return "—";
  return `NT$${Number(v).toLocaleString()}`;
}

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
  ledgerBarChart?.dispose();
  ledgerBarChart = null;
  investorPieChart?.dispose();
  investorPieChart = null;
  investorBarChart?.dispose();
  investorBarChart = null;
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
        :data="pagedCosts"
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
      <div class="table-pagination" v-if="costs.length > costsPageSize">
        <el-pagination
          v-model:current-page="costsPage"
          v-model:page-size="costsPageSize"
          :page-sizes="[10, 20, 50, 100]"
          background
          layout="total, sizes, prev, pager, next"
          :total="costs.length"
        />
      </div>
    </el-card>

    <!-- ── 商品帳本 / 投資人 ──────────────────────────────── -->
    <el-card shadow="never" class="costs-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">帳本管理</span>
        </div>
      </template>


      <!-- ── 帳本圖表區 ──────────────────────────────── -->
      <el-row :gutter="16" class="ledger-chart-row">
        <!-- 商品帳本：進貨 vs 售出橯條圖 -->
        <el-col :xs="24" :lg="12">
          <div class="ledger-chart-card">
            <div class="ledger-chart-title">
              <span>📊 商品進貨 / 售出比較</span>
              <span class="ledger-chart-sub">{{ ledgerItems.length }} 筆商品</span>
            </div>
            <div v-if="ledgerItems.length" ref="ledgerBarRef" class="ledger-chart-canvas" />
            <el-empty v-else description="暫無帳本資料" class="chart-empty" />
          </div>
        </el-col>

        <!-- 投資人出資二分圖 -->
        <el-col :xs="24" :lg="6">
          <div class="ledger-chart-card">
            <div class="ledger-chart-title">
              <span>🧑‍🤝‍🧑 投資人出資佔比</span>
              <span class="ledger-chart-sub">{{ investorSummary.length }} 位投資人</span>
            </div>
            <div v-if="investorSummary.length" ref="investorPieRef" class="ledger-chart-canvas" />
            <el-empty v-else description="暫無投資人資料" class="chart-empty" />
          </div>
        </el-col>

        <!-- 投資摘要：出資 vs 分配利潤 -->
        <el-col :xs="24" :lg="6">
          <div class="ledger-chart-card">
            <div class="ledger-chart-title">
              <span>💰 出資 / 利潤回報</span>
              <span class="ledger-chart-sub">各投資人總筆</span>
            </div>
            <div v-if="investorSummary.length" ref="investorBarRef" class="ledger-chart-canvas" />
            <el-empty v-else description="暫無投資資料" class="chart-empty" />
          </div>
        </el-col>
      </el-row>

      <el-divider style="margin: 8px 0 16px;" />
      <el-alert
        type="info"
        show-icon
        :closable="false"
        title="帳本與成本/收入為兩套資料流：帳本商品進出貨不會自動寫入上方成本紀錄；若要進入財報總成本，請同步新增成本紀錄。"
        style="margin-bottom: 12px"
      />

      <el-tabs v-model="ledgerTab" @tab-change="handleLedgerTabChange">

        <!-- Tab 1: 商品帳本 -->
        <el-tab-pane label="商品帳本" name="ledger">
          <div class="tab-toolbar">
            <el-button type="primary" @click="showAddLedgerForm = !showAddLedgerForm">
              {{ showAddLedgerForm ? '收起' : '+ 新增帳本項目' }}
            </el-button>
            <el-button @click="loadLedger" :loading="ledgerLoading">重新整理</el-button>
          </div>
          <el-collapse-transition>
            <el-card v-if="showAddLedgerForm" shadow="never" class="add-card">
              <el-form :model="addLedgerForm" label-width="110px">
                <el-row :gutter="16">
                  <el-col :span="12">
                    <el-form-item label="商品名稱" required>
                      <el-input v-model="addLedgerForm.item_name" placeholder="例：COMME des Garçons 外套" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="進貨價（JPY）">
                      <el-input-number v-model="addLedgerForm.cost_jpy" :min="0" style="width:100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="匯率">
                      <el-input-number v-model="addLedgerForm.exchange_rate" :min="0" :step="0.01" :precision="4" style="width:100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="預計售價（TWD）">
                      <el-input-number v-model="addLedgerForm.expected_price_twd" :min="0" style="width:100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="入貨日期">
                      <el-input v-model="addLedgerForm.purchase_date" placeholder="YYYY-MM-DD" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="等級">
                      <el-input v-model="addLedgerForm.grade" placeholder="A/B/C" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="來源">
                      <el-input v-model="addLedgerForm.source" placeholder="蔦屋 / 其他" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="備註">
                      <el-input v-model="addLedgerForm.note" placeholder="備註說明" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-form-item>
                  <el-button type="primary" :loading="addLedgerLoading" @click="submitAddLedger">新增</el-button>
                  <el-button @click="showAddLedgerForm = false">取消</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-collapse-transition>

          <div v-loading="ledgerLoading">
            <div class="section-title">未售出（{{ unsoldItems.length }} 筆）</div>
            <el-table :data="pagedUnsoldItems" border stripe size="small" empty-text="暫無未售出項目">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="item_name" label="商品名稱" min-width="180" />
              <el-table-column label="進貨價" width="120">
                <template #default="{ row }">{{ formatNTD(row.cost_twd) }}</template>
              </el-table-column>
              <el-table-column label="預計售價" width="120">
                <template #default="{ row }">{{ formatNTD(row.expected_price_twd) }}</template>
              </el-table-column>
              <el-table-column label="建立日期" width="120">
                <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="success" size="small" @click="handleMarkSold(row)">標記售出</el-button>
                  <el-button type="danger" size="small" @click="handleDeleteLedger(row)">刪除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="table-pagination" v-if="unsoldItems.length > ledgerPageSize">
              <el-pagination
                v-model:current-page="unsoldPage"
                v-model:page-size="ledgerPageSize"
                :page-sizes="[10, 20, 50, 100]"
                background
                layout="total, sizes, prev, pager, next"
                :total="unsoldItems.length"
              />
            </div>

            <div class="section-title" style="margin-top:16px">已售出（{{ soldItems.length }} 筆）</div>
            <el-table :data="pagedSoldItems" border stripe size="small" empty-text="暫無已售出項目">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="item_name" label="商品名稱" min-width="180" />
              <el-table-column label="進貨價" width="110">
                <template #default="{ row }">{{ formatNTD(row.cost_twd) }}</template>
              </el-table-column>
              <el-table-column label="售出價" width="110">
                <template #default="{ row }">{{ formatNTD(row.actual_price_twd) }}</template>
              </el-table-column>
              <el-table-column label="利潤" width="110">
                <template #default="{ row }">
                  <span :class="(row.profit_twd ?? 0) >= 0 ? 'ledger-profit-pos' : 'ledger-profit-neg'">
                    {{ formatNTD(row.profit_twd) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" size="small" @click="openDistDialog(row)">分配利潤</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="table-pagination" v-if="soldItems.length > ledgerPageSize">
              <el-pagination
                v-model:current-page="soldPage"
                v-model:page-size="ledgerPageSize"
                :page-sizes="[10, 20, 50, 100]"
                background
                layout="total, sizes, prev, pager, next"
                :total="soldItems.length"
              />
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 2: 投資人管理 -->
        <el-tab-pane label="投資人管理" name="investors">
          <div class="tab-toolbar">
            <el-button type="primary" @click="showInvestorForm = !showInvestorForm">
              {{ showInvestorForm ? '收起' : '+ 新增投資人' }}
            </el-button>
            <el-button @click="loadInvestors" :loading="investorsLoading">重新整理</el-button>
          </div>
          <el-collapse-transition>
            <el-card v-if="showInvestorForm" shadow="never" class="add-card">
              <el-form :model="investorForm" label-width="90px">
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item label="姓名" required>
                      <el-input v-model="investorForm.name" placeholder="投資人姓名" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="備註">
                      <el-input v-model="investorForm.note" placeholder="備註（選填）" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-form-item>
                  <el-button type="primary" :loading="investorAddLoading" @click="submitInvestor">新增</el-button>
                  <el-button @click="showInvestorForm = false">取消</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-collapse-transition>
          <div v-loading="investorsLoading">
            <el-table :data="investors" border stripe size="small" empty-text="暫無投資人">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="name" label="姓名" min-width="120" />
              <el-table-column label="手動分配比(%)" width="160" align="center">
                <template #default="{ row }">
                  <el-input-number
                    :model-value="getEffectiveInvestorRatio(row.id)"
                    :min="0"
                    :max="100"
                    :step="0.5"
                    :precision="2"
                    size="small"
                    style="width: 120px"
                    @update:model-value="value => updateInvestorRatio(row.id, Number(value ?? 0))"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="note" label="備註" min-width="160">
                <template #default="{ row }">{{ row.note || '—' }}</template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button type="warning" size="small" @click="openEditInvestorDialog(row)">編輯</el-button>
                  <el-button type="primary" size="small" @click="openContribDialog(row)">新增出資</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- Tab 3: 投資摘要 -->
        <el-tab-pane label="投資摘要" name="inv-summary">
          <div class="tab-toolbar">
            <el-button @click="loadInvestorSummary" :loading="summaryInvLoading">重新整理</el-button>
          </div>
          <div v-loading="summaryInvLoading">
            <el-table :data="investorSummary" border stripe size="small" empty-text="暫無資料">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="name" label="投資人" min-width="120" />
              <el-table-column label="總出資額" width="140">
                <template #default="{ row }">{{ formatNTD(row.total_contributed_twd) }}</template>
              </el-table-column>
              <el-table-column label="總獲利分配" width="140">
                <template #default="{ row }">{{ formatNTD(row.total_distributed_twd) }}</template>
              </el-table-column>
              <el-table-column label="淨回報" width="140">
                <template #default="{ row }">
                  <span :class="(row.net_twd ?? 0) >= 0 ? 'ledger-profit-pos' : 'ledger-profit-neg'">
                    {{ formatNTD(row.net_twd) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- ── 分配利潤 Dialog ───────────────────────────────────────── -->
    <el-dialog v-model="distDialog" title="分配利潤" width="420px" destroy-on-close>
      <div class="dist-meta">
        <div>可分配利潤：<b>{{ formatNTD(availableProfit) }}</b></div>
        <div>目前分配總額：<b>{{ formatNTD(totalDistAmount) }}</b></div>
      </div>
      <div class="dist-toolbar">
        <el-button type="primary" plain size="small" @click="applyRatioDistribution">
          依比例自動計算
        </el-button>
        <span class="dist-ratio">總比例：{{ totalDistRatio.toFixed(2) }}%</span>
      </div>
      <el-table :data="distRows" border stripe size="small" empty-text="暫無可分配對象">
        <el-table-column label="對象" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.label" placeholder="分配標籤（例：技術分紅）" />
          </template>
        </el-table-column>
        <el-table-column label="比例(%)" width="110">
          <template #default="{ row }">
            <el-input-number v-model="row.ratio" :min="0" :max="100" :step="0.5" style="width:100%" />
          </template>
        </el-table-column>
        <el-table-column label="金額" width="130">
          <template #default="{ row }">
            <el-input-number v-model="row.amount" :min="0" :step="100" style="width:100%" />
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="distDialog = false">取消</el-button>
        <el-button type="primary" :loading="distLoading" @click="submitDistribution">確認分配</el-button>
      </template>
    </el-dialog>

    <!-- ── 新增出資 Dialog ─────────────────────────────────────── -->
    <el-dialog v-model="contribDialog" :title="`${contribTarget?.name || ''} — 新增出資`" width="380px" destroy-on-close>
      <el-form :model="contribForm" label-width="90px">
        <el-form-item label="出資金額">
          <el-input-number v-model="contribForm.amount_twd" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item label="出資日期">
          <el-input v-model="contribForm.contributed_at" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="備註">
          <el-input v-model="contribForm.note" placeholder="選填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="contribDialog = false">取消</el-button>
        <el-button type="primary" :loading="contribLoading" @click="submitContribution">確認</el-button>
      </template>
    </el-dialog>

    <!-- ── 編輯投資人 Dialog ───────────────────────────────────── -->
    <el-dialog v-model="investorEditDialog" title="編輯投資人" width="420px" destroy-on-close>
      <el-form :model="investorEditForm" label-width="90px">
        <el-form-item label="姓名" required>
          <el-input v-model="investorEditForm.name" placeholder="投資人姓名" />
        </el-form-item>
        <el-form-item label="備註">
          <el-input
            v-model="investorEditForm.note"
            type="textarea"
            :rows="3"
            placeholder="可記錄角色、分配說明或合約摘要"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="investorEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="investorEditLoading" @click="submitEditInvestor">儲存</el-button>
      </template>
    </el-dialog>

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

.table-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

/* ── Ledger Section ─────────────────────────────────── */
.tab-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.add-card {
  margin-bottom: 16px;
  border: 1px dashed #dcdfe6;
}

.section-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin: 12px 0 8px;
}

.ledger-profit-pos {
  color: #67c23a;
  font-weight: 600;
}

.ledger-profit-neg {
  color: #f56c6c;
  font-weight: 600;
}

/* ── Ledger Charts ─────────────────────────────────── */
.ledger-chart-row {
  margin-bottom: 16px;
}

.ledger-chart-card {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px 16px;
  height: 260px;
  display: flex;
  flex-direction: column;
}

.ledger-chart-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.ledger-chart-sub {
  font-size: 12px;
  color: #909399;
  font-weight: 400;
}

.ledger-chart-canvas {
  flex: 1;
  min-height: 0;
}

.dist-meta {
  margin-bottom: 10px;
  font-size: 13px;
  color: #606266;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.dist-toolbar {
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dist-ratio {
  font-size: 12px;
  color: #909399;
}
</style>
