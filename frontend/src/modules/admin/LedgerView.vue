<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import {
  fetchLedger, createLedgerItem, markItemSold, deleteLedgerItem, setDistributions,
  fetchInvestors, createInvestor, addContribution, fetchInvestorSummary,
} from "./ledgerService";

type LedgerItem = {
  id: number; item_name: string; purchase_date: string;
  cost_jpy: number; exchange_rate: number; cost_twd: number;
  expected_price_twd: number; actual_price_twd: number | null;
  sold: boolean; profit_twd: number; profit_pct: number;
  expected_profit_twd: number; expected_profit_pct: number;
  grade: string; box_and_papers: string; location: string;
  source: string; customer_source: string; note: string;
  order_id: number | null; created_at: string;
};

type Investor = {
  id: number; name: string; note: string;
  total_contributed_twd: number;
  contributions: Array<{ id: number; amount_twd: number; contributed_at: string; note: string }>;
};

// ── State ──────────────────────────────────────────────────────────────────
const activeTab = ref<"ledger" | "investors" | "distributions">("ledger");
const loading = ref(false);
const statusMsg = ref("");
const isError = ref(false);

const ledgerItems = ref<LedgerItem[]>([]);
const investors = ref<Investor[]>([]);
const investorSummary = ref<Array<{ id: number; name: string; total_contributed_twd: number; total_distributed_twd: number; net_twd: number }>>([]);

// ── New ledger item form ───────────────────────────────────────────────────
const showAddForm = ref(false);
const newItem = reactive({
  item_name: "", purchase_date: "", cost_jpy: 0, exchange_rate: 0.21,
  expected_price_twd: 0, grade: "A", box_and_papers: "", location: "",
  source: "", customer_source: "", note: "",
});

// ── Mark sold overlay ─────────────────────────────────────────────────────
const soldTarget = ref<LedgerItem | null>(null);
const soldPrice = ref(0);

// ── Distribution editor ────────────────────────────────────────────────────
const distTarget = ref<LedgerItem | null>(null);
const distRows = ref<Array<{ investor_id: number | null; label: string; amount_twd: number }>>([]);

// ── Investor form ──────────────────────────────────────────────────────────
const showInvForm = ref(false);
const newInvName = ref("");
const newInvNote = ref("");

const showContribForm = ref<number | null>(null); // investor id
const contribAmount = ref(0);
const contribDate = ref("");
const contribNote = ref("");

// ── Computed ───────────────────────────────────────────────────────────────
const unsold = computed(() => ledgerItems.value.filter(i => !i.sold));
const sold = computed(() => ledgerItems.value.filter(i => i.sold));
const totalCostTwd = computed(() => ledgerItems.value.reduce((s, i) => s + i.cost_twd, 0));
const totalRevenueTwd = computed(() => sold.value.reduce((s, i) => s + (i.actual_price_twd ?? 0), 0));
const totalProfitTwd = computed(() => sold.value.reduce((s, i) => s + i.profit_twd, 0));

// ── Helpers ────────────────────────────────────────────────────────────────
function fmt(n: number) { return `NT$ ${Number(n).toLocaleString()}`; }
function fmtJpy(n: number) { return `¥${Number(n).toLocaleString()}`; }
function setStatus(msg: string, error = false) {
  statusMsg.value = msg; isError.value = error;
  if (!error) setTimeout(() => { statusMsg.value = ""; }, 3000);
}

// ── Load ───────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  try {
    const [ledgerResp, invResp, summaryResp] = await Promise.all([
      fetchLedger(), fetchInvestors(), fetchInvestorSummary(),
    ]);
    ledgerItems.value = ledgerResp.items ?? [];
    investors.value = invResp.investors ?? [];
    investorSummary.value = summaryResp.investors ?? [];
  } catch (e) {
    setStatus(e instanceof Error ? e.message : "載入失敗", true);
  } finally {
    loading.value = false;
  }
}

// ── Ledger actions ─────────────────────────────────────────────────────────
async function submitNewItem() {
  try {
    await createLedgerItem({ ...newItem });
    setStatus("已新增商品");
    showAddForm.value = false;
    Object.assign(newItem, {
      item_name: "", purchase_date: "", cost_jpy: 0, exchange_rate: 0.21,
      expected_price_twd: 0, grade: "A", box_and_papers: "", location: "",
      source: "", customer_source: "", note: "",
    });
    await load();
  } catch (e) {
    setStatus(e instanceof Error ? e.message : "新增失敗", true);
  }
}

async function confirmSold() {
  if (!soldTarget.value) return;
  try {
    await markItemSold(soldTarget.value.id, soldPrice.value);
    setStatus("已標記售出");
    soldTarget.value = null;
    soldPrice.value = 0;
    await load();
  } catch (e) {
    setStatus(e instanceof Error ? e.message : "標記失敗", true);
  }
}

async function deleteItem(item: LedgerItem) {
  if (!confirm(`確定刪除「${item.item_name}」？`)) return;
  try {
    await deleteLedgerItem(item.id);
    setStatus("已刪除");
    await load();
  } catch (e) {
    setStatus(e instanceof Error ? e.message : "刪除失敗", true);
  }
}

// ── Distribution actions ───────────────────────────────────────────────────
function openDist(item: LedgerItem) {
  distTarget.value = item;
  distRows.value = [{ investor_id: null, label: "", amount_twd: 0 }];
}

function addDistRow() {
  distRows.value.push({ investor_id: null, label: "", amount_twd: 0 });
}

function removeDistRow(idx: number) {
  distRows.value.splice(idx, 1);
}

async function saveDist() {
  if (!distTarget.value) return;
  try {
    await setDistributions(distTarget.value.id, distRows.value);
    setStatus("利潤分配已儲存");
    distTarget.value = null;
    distRows.value = [];
    await load();
  } catch (e) {
    setStatus(e instanceof Error ? e.message : "儲存失敗", true);
  }
}

// ── Investor actions ───────────────────────────────────────────────────────
async function submitInvestor() {
  try {
    await createInvestor(newInvName.value, newInvNote.value);
    setStatus("已新增投資人");
    showInvForm.value = false;
    newInvName.value = ""; newInvNote.value = "";
    await load();
  } catch (e) {
    setStatus(e instanceof Error ? e.message : "新增失敗", true);
  }
}

async function submitContrib(investorId: number) {
  try {
    await addContribution(investorId, {
      amount_twd: contribAmount.value,
      contributed_at: contribDate.value,
      note: contribNote.value,
    });
    setStatus("已記錄資本投入");
    showContribForm.value = null;
    contribAmount.value = 0; contribDate.value = ""; contribNote.value = "";
    await load();
  } catch (e) {
    setStatus(e instanceof Error ? e.message : "記錄失敗", true);
  }
}

onMounted(load);
</script>

<template>
  <div class="ledger-wrap container">
    <header class="page-head">
      <p class="page-title">商品帳本</p>
      <p class="page-sub">Product Ledger & Investors</p>
    </header>

    <!-- Tab nav -->
    <nav class="tab-nav">
      <button :class="['tab-btn', activeTab === 'ledger' ? 'active' : '']" @click="activeTab = 'ledger'">商品帳本</button>
      <button :class="['tab-btn', activeTab === 'investors' ? 'active' : '']" @click="activeTab = 'investors'">投資人</button>
      <button :class="['tab-btn', activeTab === 'distributions' ? 'active' : '']" @click="activeTab = 'distributions'">利潤分配</button>
    </nav>

    <p v-if="statusMsg" class="status-msg" :class="isError ? 'error' : 'ok'">{{ statusMsg }}</p>
    <p v-if="loading" class="loading-msg">載入中…</p>

    <!-- ── LEDGER TAB ── -->
    <section v-if="activeTab === 'ledger'">
      <!-- Summary row -->
      <div class="summary-row">
        <div class="summary-cell"><span>總成本</span><strong>{{ fmt(totalCostTwd) }}</strong></div>
        <div class="summary-cell"><span>已售出收入</span><strong>{{ fmt(totalRevenueTwd) }}</strong></div>
        <div class="summary-cell"><span>已實現利潤</span><strong :class="totalProfitTwd >= 0 ? 'profit' : 'loss'">{{ fmt(totalProfitTwd) }}</strong></div>
        <div class="summary-cell"><span>未售件數</span><strong>{{ unsold.length }}</strong></div>
      </div>

      <!-- Add button -->
      <div class="action-row">
        <button class="btn-primary" @click="showAddForm = !showAddForm">{{ showAddForm ? '✕ 取消' : '+ 新增商品' }}</button>
      </div>

      <!-- Add form -->
      <form v-if="showAddForm" class="item-form" @submit.prevent="submitNewItem">
        <div class="form-grid">
          <label>商品名稱 *<input v-model="newItem.item_name" required placeholder="e.g. Tudor Ranger 36mm" /></label>
          <label>購入日期 *<input v-model="newItem.purchase_date" type="date" required /></label>
          <label>買進日圓 (JPY)<input v-model.number="newItem.cost_jpy" type="number" min="0" /></label>
          <label>當日匯率<input v-model.number="newItem.exchange_rate" type="number" step="0.0001" /></label>
          <label>預期售價 (TWD)<input v-model.number="newItem.expected_price_twd" type="number" min="0" /></label>
          <label>成色
            <select v-model="newItem.grade">
              <option>S</option><option>A</option><option>B</option><option>C</option>
            </select>
          </label>
          <label>盒單
            <select v-model="newItem.box_and_papers">
              <option value="">未填</option>
              <option>有盒單</option><option>無盒單</option><option>有盒無單</option>
            </select>
          </label>
          <label>商品所在<input v-model="newItem.location" placeholder="日本" /></label>
          <label>貨源<input v-model="newItem.source" placeholder="メルカリ" /></label>
          <label>顧客來源<input v-model="newItem.customer_source" placeholder="Instagram" /></label>
          <label class="span2">備註<input v-model="newItem.note" /></label>
        </div>
        <p class="cost-preview" v-if="newItem.cost_jpy > 0">
          台幣成本預估：{{ fmt(Math.round(newItem.cost_jpy * newItem.exchange_rate)) }}
        </p>
        <button class="btn-primary" type="submit">儲存</button>
      </form>

      <!-- Table: unsold -->
      <h3 class="section-title">未售出（{{ unsold.length }}）</h3>
      <div class="table-wrap">
        <table class="ledger-table">
          <thead>
            <tr>
              <th>商品</th><th>購入日</th><th>JPY成本</th><th>TWD成本</th>
              <th>預期售價</th><th>預期利潤</th><th>成色</th><th>所在</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in unsold" :key="item.id">
              <td>{{ item.item_name }}</td>
              <td>{{ item.purchase_date }}</td>
              <td>{{ fmtJpy(item.cost_jpy) }}</td>
              <td>{{ fmt(item.cost_twd) }}</td>
              <td>{{ fmt(item.expected_price_twd) }}</td>
              <td :class="item.expected_profit_twd >= 0 ? 'profit' : 'loss'">
                {{ fmt(item.expected_profit_twd) }} ({{ item.expected_profit_pct }}%)
              </td>
              <td>{{ item.grade }}</td>
              <td>{{ item.location }}</td>
              <td class="action-cell">
                <button class="btn-sm" @click="soldTarget = item; soldPrice = item.expected_price_twd">標記售出</button>
                <button class="btn-sm btn-dist" @click="openDist(item)">分配</button>
                <button class="btn-sm btn-del" @click="deleteItem(item)">刪</button>
              </td>
            </tr>
            <tr v-if="unsold.length === 0"><td colspan="9" class="empty-row">尚無未售出商品</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Table: sold -->
      <h3 class="section-title">已售出（{{ sold.length }}）</h3>
      <div class="table-wrap">
        <table class="ledger-table">
          <thead>
            <tr>
              <th>商品</th><th>購入日</th><th>TWD成本</th>
              <th>實際售價</th><th>實際利潤</th><th>利潤率</th><th>顧客來源</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in sold" :key="item.id">
              <td>{{ item.item_name }}</td>
              <td>{{ item.purchase_date }}</td>
              <td>{{ fmt(item.cost_twd) }}</td>
              <td>{{ fmt(item.actual_price_twd ?? 0) }}</td>
              <td :class="item.profit_twd >= 0 ? 'profit' : 'loss'">{{ fmt(item.profit_twd) }}</td>
              <td :class="item.profit_pct >= 0 ? 'profit' : 'loss'">{{ item.profit_pct }}%</td>
              <td>{{ item.customer_source }}</td>
            </tr>
            <tr v-if="sold.length === 0"><td colspan="7" class="empty-row">尚無已售出商品</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── INVESTORS TAB ── -->
    <section v-if="activeTab === 'investors'">
      <!-- Summary -->
      <div class="inv-summary">
        <div v-for="inv in investorSummary" :key="inv.id" class="inv-card">
          <p class="inv-name">{{ inv.name }}</p>
          <p class="inv-stat">投入：{{ fmt(inv.total_contributed_twd) }}</p>
          <p class="inv-stat">分配：{{ fmt(inv.total_distributed_twd) }}</p>
          <p class="inv-stat" :class="inv.net_twd >= 0 ? 'profit' : 'loss'">
            淨收益：{{ fmt(inv.net_twd) }}
          </p>
        </div>
      </div>

      <div class="action-row">
        <button class="btn-primary" @click="showInvForm = !showInvForm">{{ showInvForm ? '✕ 取消' : '+ 新增投資人' }}</button>
      </div>

      <form v-if="showInvForm" class="item-form" @submit.prevent="submitInvestor">
        <div class="form-grid">
          <label>姓名 *<input v-model="newInvName" required /></label>
          <label>備註<input v-model="newInvNote" /></label>
        </div>
        <button class="btn-primary" type="submit">儲存</button>
      </form>

      <div v-for="inv in investors" :key="inv.id" class="inv-detail-card">
        <div class="inv-detail-head">
          <strong>{{ inv.name }}</strong>
          <span>總投入：{{ fmt(inv.total_contributed_twd) }}</span>
          <button class="btn-sm" @click="showContribForm = showContribForm === inv.id ? null : inv.id">+ 記錄投入</button>
        </div>
        <form v-if="showContribForm === inv.id" class="item-form" @submit.prevent="submitContrib(inv.id)">
          <div class="form-grid">
            <label>金額 (TWD)<input v-model.number="contribAmount" type="number" required /></label>
            <label>日期<input v-model="contribDate" type="date" required /></label>
            <label>備註<input v-model="contribNote" /></label>
          </div>
          <button class="btn-primary" type="submit">儲存</button>
        </form>
        <table class="ledger-table" v-if="inv.contributions.length > 0">
          <thead><tr><th>金額</th><th>日期</th><th>備註</th></tr></thead>
          <tbody>
            <tr v-for="c in inv.contributions" :key="c.id">
              <td>{{ fmt(c.amount_twd) }}</td>
              <td>{{ c.contributed_at }}</td>
              <td>{{ c.note }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── DISTRIBUTIONS TAB ── -->
    <section v-if="activeTab === 'distributions'">
      <p class="section-hint">選擇已售出商品，設定利潤分配給各投資人。</p>
      <div class="table-wrap">
        <table class="ledger-table">
          <thead>
            <tr><th>商品</th><th>售出日</th><th>實際利潤</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in sold" :key="item.id">
              <td>{{ item.item_name }}</td>
              <td>{{ item.purchase_date }}</td>
              <td :class="item.profit_twd >= 0 ? 'profit' : 'loss'">{{ fmt(item.profit_twd) }}</td>
              <td><button class="btn-sm" @click="openDist(item)">設定分配</button></td>
            </tr>
            <tr v-if="sold.length === 0"><td colspan="4" class="empty-row">尚無已售出商品</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── Mark Sold Overlay ── -->
    <div v-if="soldTarget" class="overlay" @click.self="soldTarget = null">
      <div class="overlay-card">
        <p class="overlay-title">標記售出：{{ soldTarget.item_name }}</p>
        <label>實際售價 (TWD)
          <input v-model.number="soldPrice" type="number" min="0" />
        </label>
        <div class="overlay-actions">
          <button class="btn-primary" @click="confirmSold">確認售出</button>
          <button class="btn-sm" @click="soldTarget = null">取消</button>
        </div>
      </div>
    </div>

    <!-- ── Distribution Overlay ── -->
    <div v-if="distTarget" class="overlay" @click.self="distTarget = null">
      <div class="overlay-card">
        <p class="overlay-title">利潤分配：{{ distTarget.item_name }}</p>
        <p class="overlay-sub">實際利潤 {{ fmt(distTarget.profit_twd) }}</p>
        <div v-for="(row, idx) in distRows" :key="idx" class="dist-row">
          <input v-model="row.label" placeholder="標籤 (e.g. 雷思翰 / 公積金)" />
          <input v-model.number="row.amount_twd" type="number" min="0" placeholder="金額 TWD" />
          <button class="btn-sm btn-del" @click="removeDistRow(idx)">✕</button>
        </div>
        <button class="btn-sm" @click="addDistRow">+ 新增行</button>
        <div class="overlay-actions">
          <button class="btn-primary" @click="saveDist">儲存分配</button>
          <button class="btn-sm" @click="distTarget = null">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ledger-wrap { max-width: 1200px; padding: 2.4rem 0 6rem; }
.page-head { text-align: center; margin-bottom: 2rem; }
.page-title { font-size: 1.7rem; font-weight: 400; margin: 0; color: #1b2740; }
.page-sub { font-size: 0.92rem; color: #425a79; margin: 0.3rem 0 0; }

.tab-nav { display: flex; gap: 0; border-bottom: 1px solid #d4d9df; margin-bottom: 1.6rem; }
.tab-btn { background: transparent; border: none; border-bottom: 2px solid transparent;
  color: #425a79; cursor: pointer; font-size: 0.95rem; padding: 0.6rem 1.4rem; }
.tab-btn.active { border-bottom-color: #2b3e58; color: #1b2740; font-weight: 600; }

.status-msg { font-size: 0.88rem; margin: 0.5rem 0; }
.status-msg.ok { color: #2f7d4b; }
.status-msg.error { color: #bc3c2a; }
.loading-msg { color: #425a79; font-size: 0.9rem; }

.summary-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.4rem; }
.summary-cell { background: rgba(255,255,255,0.5); border: 1px solid #d4d9df; padding: 1rem;
  display: flex; flex-direction: column; gap: 0.3rem; }
.summary-cell span { font-size: 0.8rem; color: #425a79; }
.summary-cell strong { font-size: 1.15rem; font-weight: 600; color: #1b2740; }

.action-row { margin-bottom: 1rem; }
.section-title { font-size: 1.05rem; font-weight: 600; color: #1b2740; margin: 1.6rem 0 0.7rem; }
.section-hint { color: #425a79; font-size: 0.9rem; margin-bottom: 1rem; }

.item-form { background: rgba(255,255,255,0.55); border: 1px solid #d4d9df; padding: 1.2rem; margin-bottom: 1.2rem; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin-bottom: 0.8rem; }
.form-grid label { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.84rem; color: #324867; }
.form-grid input, .form-grid select { background: transparent; border: 1px solid #bcc5d1; color: #1b2740;
  font-size: 0.9rem; padding: 0.36rem 0.5rem; }
.span2 { grid-column: span 2; }
.cost-preview { font-size: 0.85rem; color: #3a4f6f; margin: 0 0 0.6rem; }

.table-wrap { overflow-x: auto; margin-bottom: 1.6rem; }
.ledger-table { border-collapse: collapse; font-size: 0.85rem; min-width: 640px; width: 100%; }
.ledger-table th { background: rgba(43,62,88,0.07); color: #1b2740; font-weight: 600;
  padding: 0.5rem 0.7rem; text-align: left; border-bottom: 2px solid #d4d9df; }
.ledger-table td { border-bottom: 1px solid #e8ecf0; color: #324867; padding: 0.48rem 0.7rem; }
.ledger-table tr:hover td { background: rgba(255,255,255,0.3); }
.action-cell { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.empty-row { color: #7e8ca0; font-style: italic; text-align: center; }

.profit { color: #2f7d4b; }
.loss { color: #bc3c2a; }

.btn-primary { background: #2b3e58; border: none; color: #fff; cursor: pointer;
  font-size: 0.85rem; letter-spacing: 0.04em; padding: 0.5rem 1.2rem; }
.btn-primary:hover { background: #1b2d45; }
.btn-sm { background: transparent; border: 1px solid #bcc5d1; color: #2b3e58;
  cursor: pointer; font-size: 0.78rem; padding: 0.3rem 0.6rem; }
.btn-sm:hover { background: rgba(43,62,88,0.06); }
.btn-dist { border-color: #7a9cbf; color: #1a4a6e; }
.btn-del { border-color: #d4a0a0; color: #9b3030; }

/* Investor cards */
.inv-summary { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.4rem; }
.inv-card { background: rgba(255,255,255,0.5); border: 1px solid #d4d9df; padding: 1rem; }
.inv-name { font-weight: 600; font-size: 1rem; color: #1b2740; margin: 0 0 0.4rem; }
.inv-stat { font-size: 0.82rem; color: #324867; margin: 0.15rem 0; }

.inv-detail-card { background: rgba(255,255,255,0.4); border: 1px solid #d4d9df; margin-bottom: 1rem; padding: 1rem; }
.inv-detail-head { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.8rem; }
.inv-detail-head strong { font-size: 1rem; color: #1b2740; }
.inv-detail-head span { color: #425a79; font-size: 0.85rem; }

/* Overlay */
.overlay { align-items: center; background: rgba(0,0,0,0.35); bottom: 0; display: flex;
  justify-content: center; left: 0; position: fixed; right: 0; top: 0; z-index: 100; }
.overlay-card { background: #f5f4f0; max-width: 480px; padding: 1.6rem; width: 90%; }
.overlay-title { font-size: 1.1rem; font-weight: 600; color: #1b2740; margin: 0 0 0.8rem; }
.overlay-sub { font-size: 0.88rem; color: #425a79; margin: 0 0 0.8rem; }
.overlay-card label { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.9rem; margin-bottom: 0.8rem; }
.overlay-card input { background: transparent; border: 1px solid #bcc5d1; color: #1b2740;
  font-size: 0.95rem; padding: 0.4rem 0.5rem; width: 100%; }
.overlay-actions { display: flex; gap: 0.8rem; margin-top: 1rem; }

.dist-row { display: grid; grid-template-columns: 1fr 1fr auto; gap: 0.5rem; margin-bottom: 0.5rem; }
.dist-row input { background: transparent; border: 1px solid #bcc5d1; color: #1b2740;
  font-size: 0.88rem; padding: 0.3rem 0.4rem; }

@media (max-width: 768px) {
  .summary-row { grid-template-columns: 1fr 1fr; }
  .form-grid { grid-template-columns: 1fr; }
  .span2 { grid-column: span 1; }
  .tab-btn { font-size: 0.82rem; padding: 0.5rem 0.8rem; }
}
</style>
