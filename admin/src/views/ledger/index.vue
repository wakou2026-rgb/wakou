<script setup lang="ts">
import { onMounted, ref, reactive, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  getLedger,
  createLedgerItem,
  markSold,
  deleteLedgerItem,
  setDistributions,
  getInvestors,
  createInvestor,
  addContribution,
  getInvestorsSummary,
  type LedgerItem,
  type Investor,
  type InvestorSummary,
  type LedgerCreatePayload,
  type MarkSoldPayload,
  type DistributionsPayload,
  type InvestorCreatePayload,
  type ContributionPayload
} from "@/api/ledger";

defineOptions({ name: "LedgerIndex" });

// ── Tabs ────────────────────────────────────────────────────────────────────
const activeTab = ref("ledger");

// ── Ledger tab ───────────────────────────────────────────────────────────────
const ledgerLoading = ref(false);
const ledgerItems = ref<LedgerItem[]>([]);
const showAddForm = ref(false);
const addForm = reactive({
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
const addLoading = ref(false);

const unsoldItems = computed(() => ledgerItems.value.filter(i => !i.sold));
const soldItems = computed(() => ledgerItems.value.filter(i => i.sold));

async function loadLedger() {
  ledgerLoading.value = true;
  try {
    const res: any = await getLedger();
    const payload = res?.data ?? res;
    ledgerItems.value = Array.isArray(payload?.items) ? payload.items : [];
  } catch (e: any) {
    ElMessage.error(e?.message || "載入帳本失敗");
  } finally {
    ledgerLoading.value = false;
  }
}

async function submitAdd() {
  if (!addForm.item_name.trim()) {
    ElMessage.warning("請填寫商品名稱");
    return;
  }
  addLoading.value = true;
  try {
    await createLedgerItem({
      item_name: addForm.item_name.trim(),
      purchase_date: addForm.purchase_date,
      cost_jpy: Number(addForm.cost_jpy) || 0,
      exchange_rate: Number(addForm.exchange_rate) || 0.21,
      expected_price_twd: Number(addForm.expected_price_twd) || 0,
      grade: addForm.grade || "A",
      location: addForm.location?.trim() || undefined,
      source: addForm.source?.trim() || undefined,
      note: addForm.note?.trim() || undefined
    });
    ElMessage.success("帳本項目已新增");
    Object.assign(addForm, { item_name: "", purchase_date: new Date().toISOString().slice(0, 10), cost_jpy: 0, exchange_rate: 0.21, expected_price_twd: 0, grade: "A", location: "", source: "", note: "" });
    showAddForm.value = false;
    await loadLedger();
  } catch (e: any) {
    ElMessage.error(e?.message || "新增失敗");
  } finally {
    addLoading.value = false;
  }
}

async function handleMarkSold(item: LedgerItem) {
  const sellingPriceStr = await ElMessageBox.prompt(
    `請輸入「${item.item_name}」的售出價格（TWD）`,
    "標記售出",
    { confirmButtonText: "確認", cancelButtonText: "取消", inputPattern: /^\d+(\.\d+)?$/, inputErrorMessage: "請輸入有效金額" }
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

async function handleDelete(item: LedgerItem) {
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

// ── Distribution dialog ──────────────────────────────────────────────────────
const distDialog = ref(false);
const distTargetItem = ref<LedgerItem | null>(null);
const distForm = reactive<{ distributions: { investor_id?: number; label: string; amount_twd: number }[] }>({ distributions: [] });
const distLoading = ref(false);

function openDistDialog(item: LedgerItem) {
  distTargetItem.value = item;
  Object.assign(distForm, { distributions: [] });
  distDialog.value = true;
}

async function submitDistribution() {
  if (!distForm.distributions.length) {
    ElMessage.warning("請至少新增一筆分配");
    return;
  }
  distLoading.value = true;
  try {
    await setDistributions(distTargetItem.value!.id, {
      distributions: distForm.distributions
    });
    ElMessage.success("利潤分配已記錄");
    distDialog.value = false;
  } catch (e: any) {
    ElMessage.error(e?.message || "分配失敗");
  } finally {
    distLoading.value = false;
  }
}

// ── Investors tab ────────────────────────────────────────────────────────────
const investorsLoading = ref(false);
const investors = ref<Investor[]>([]);
const showInvestorForm = ref(false);
const investorForm = reactive<InvestorCreatePayload>({ name: "", note: "" });
const investorAddLoading = ref(false);

// Contribution dialog
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
  } catch (e: any) {
    ElMessage.error(e?.message || "載入投資人失敗");
  } finally {
    investorsLoading.value = false;
  }
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
  } catch (e: any) {
    ElMessage.error(e?.message || "新增出資失敗");
  } finally {
    contribLoading.value = false;
  }
}

// ── Summary tab ──────────────────────────────────────────────────────────────
const summaryLoading = ref(false);
const summary = ref<InvestorSummary[]>([]);

async function loadSummary() {
  summaryLoading.value = true;
  try {
    const res: any = await getInvestorsSummary();
    const payload = res?.data ?? res;
    summary.value = Array.isArray(payload?.investors) ? payload.investors : [];
  } catch (e: any) {
    ElMessage.error(e?.message || "載入摘要失敗");
  } finally {
    summaryLoading.value = false;
  }
}

function handleTabChange(tab: string) {
  if (tab === "ledger" && !ledgerItems.value.length) loadLedger();
  if (tab === "investors" && !investors.value.length) loadInvestors();
  if (tab === "summary") loadSummary();
}

function formatNTD(v: number | null | undefined) {
  if (v == null) return "—";
  return `NT$${Number(v).toLocaleString()}`;
}

onMounted(() => {
  loadLedger();
  loadInvestors();
});
</script>

<template>
  <div class="ledger-page p-4">
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <!-- ── Tab 1: 商品帳本 ──────────────────────────────────────────── -->
      <el-tab-pane label="商品帳本" name="ledger">
        <div class="tab-toolbar">
          <el-button type="primary" @click="showAddForm = !showAddForm">
            {{ showAddForm ? "收起" : "+ 新增帳本項目" }}
          </el-button>
          <el-button @click="loadLedger" :loading="ledgerLoading">重新整理</el-button>
        </div>

        <!-- Add form -->
        <el-collapse-transition>
          <el-card v-if="showAddForm" shadow="never" class="add-card">
            <el-form :model="addForm" label-width="110px" inline-message>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="商品名稱" required>
                    <el-input v-model="addForm.item_name" placeholder="例：COMME des GARÇONS 外套" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="進貨價（TWD）">
                    <el-input-number v-model="addForm.cost_jpy" :min="0" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="數量">
                    <el-input-number v-model="addForm.quantity" :min="1" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="預期售價（選填）">
                    <el-input-number v-model="addForm.expected_price_twd" :min="0" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="訂單 ID（選填）">
                    <el-input-number v-model="addForm.order_id" :min="1" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="備註">
                    <el-input v-model="addForm.note" placeholder="備註說明" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item>
                <el-button type="primary" :loading="addLoading" @click="submitAdd">新增</el-button>
                <el-button @click="showAddForm = false">取消</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-collapse-transition>

        <!-- Unsold items -->
        <div v-loading="ledgerLoading">
          <div class="section-title">未售出（{{ unsoldItems.length }} 筆）</div>
          <el-table :data="unsoldItems" border stripe size="small" empty-text="暫無未售出項目">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="item_name" label="商品名稱" min-width="180" />
            <el-table-column label="進貨價" width="120">
              <template #default="{ row }">{{ formatNTD(row.cost_twd) }}</template>
            </el-table-column>
            <el-table-column prop="quantity" label="數量" width="70" />
            <el-table-column label="備註" prop="note" min-width="120">
              <template #default="{ row }">{{ row.note || "—" }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="建立日期" width="120">
              <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="handleMarkSold(row)">標記售出</el-button>
                <el-button type="danger" size="small" @click="handleDelete(row)">刪除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- Sold items -->
          <div class="section-title mt-4">已售出（{{ soldItems.length }} 筆）</div>
          <el-table :data="soldItems" border stripe size="small" empty-text="暫無已售出項目">
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
                <span :class="row.profit_twd >= 0 ? 'profit-pos' : 'profit-neg'">
                  {{ formatNTD(row.profit_twd) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="order_id" label="訂單" width="80">
              <template #default="{ row }">{{ row.order_id || "—" }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="openDistDialog(row)">分配利潤</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- ── Tab 2: 投資人管理 ───────────────────────────────────────── -->
      <el-tab-pane label="投資人管理" name="investors">
        <div class="tab-toolbar">
          <el-button type="primary" @click="showInvestorForm = !showInvestorForm">
            {{ showInvestorForm ? "收起" : "+ 新增投資人" }}
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
                <el-col :span="16">
                  <el-form-item label="備註">
                    <el-input v-model="investorForm.note" placeholder="備註（選填）" />
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
            <el-table-column prop="note" label="備註" min-width="180">
              <template #default="{ row }">{{ row.email || "—" }}</template>
            </el-table-column>
            <el-table-column prop="note" label="備註" min-width="160">
              <template #default="{ row }">{{ row.note || "—" }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="建立日期" width="120">
              <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="openContribDialog(row)">新增出資</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- ── Tab 3: 投資摘要 ─────────────────────────────────────────── -->
      <el-tab-pane label="投資摘要" name="summary">
        <div class="tab-toolbar">
          <el-button @click="loadSummary" :loading="summaryLoading">重新整理</el-button>
        </div>
        <div v-loading="summaryLoading">
          <el-table :data="summary" border stripe size="small" empty-text="暫無資料">
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
                <span :class="row.net_twd >= 0 ? 'profit-pos' : 'profit-neg'">
                  {{ formatNTD(row.net_twd) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="備註" min-width="160">
              <template #default="{ row }">{{ row.note || "—" }}</template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ── 分配利潤 Dialog ──────────────────────────────────────────────── -->
    <el-dialog v-model="distDialog" title="分配利潤" width="420px" destroy-on-close>
      <el-form :model="distForm" label-width="90px">
        <el-form-item label="說明">請使用財務管理頁面的分配功能</el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="distDialog = false">取消</el-button>
        <el-button type="primary" :loading="distLoading" @click="submitDistribution">確認分配</el-button>
      </template>
    </el-dialog>

    <!-- ── 新增出資 Dialog ──────────────────────────────────────────────── -->
    <el-dialog v-model="contribDialog" :title="`${contribTarget?.name || ''} — 新增出資`" width="380px" destroy-on-close>
      <el-form :model="contribForm" label-width="90px">
        <el-form-item label="出資金額">
          <el-input-number v-model="contribForm.amount_twd" :min="0" style="width:100%" />
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
  </div>
</template>

<style scoped>
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

.mt-4 {
  margin-top: 16px;
}

.profit-pos {
  color: #67c23a;
  font-weight: 600;
}

.profit-neg {
  color: #f56c6c;
  font-weight: 600;
}
</style>
