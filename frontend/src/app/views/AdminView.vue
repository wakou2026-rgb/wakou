<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import CommRoomInline from "../components/CommRoomInline.vue";
import {
  addBuyerNote,
  createAdminCost,
  createAdminMagazineArticle,
  createProductApi,
  deleteAdminMagazineArticle,
  deleteAdminProduct,
  exportOrdersCsv,
  fetchAdminCosts,
  fetchAdminEvents,
  fetchAdminMagazineArticles,
  fetchAdminOverview,
  fetchAdminOrders,
  fetchAdminPointsPolicy,
  fetchAdminProducts,
  fetchAdminReportSummary,
  fetchAdminReviews,
  fetchAdminUsers,
  fetchAdminWorkflowQueues,
  fetchBuyerHistory,
  markAdminEventsRead,
  patchAdminOrderStatus,
  rewardBuyerPoints,
  updateAdminProduct,
  updateAdminMagazineArticle,
  updateAdminPointsPolicy,
  updateAdminReview,
} from "../../modules/admin/service";
import { useAuthStore } from "../../modules/auth/store";

const router = useRouter();
const authStore = useAuthStore();

const loading = ref(true);
const isError = ref(false);
const statusText = ref("");
const activeTab = ref("command");
const selectedRoomId = ref(null);

const overview = ref({ metrics: { total_orders: 0, pending_orders: 0, active_rooms: 0 }, recent_orders: [] });
const orders = ref([]);
const users = ref([]);
const queue = ref({ summary: {}, queues: {}, recent_events: [] });
const events = ref([]);
const crm = ref(null);
const products = ref([]);
const costs = ref([]);
const reviews = ref([]);
const magazines = ref([]);
const report = ref({ totals: { revenue_twd: 0, cost_twd: 0, profit_twd: 0 }, series: [] });
const csvOutput = ref("");

const editingProductId = ref(0);
const productForm = reactive({
  sku: "",
  category: "watch",
  grade: "A",
  price_twd: 0,
  nameZh: "",
  nameJa: "",
  nameEn: "",
  descZh: "",
  descJa: "",
  descEn: "",
});
const productImageUrls = ref([""]);
const magazineForm = reactive({
  articleId: 0,
  brand: "Rolex",
  titleZh: "",
  titleJa: "",
  titleEn: "",
  descZh: "",
  descJa: "",
  descEn: "",
  bodyZh: "",
  bodyJa: "",
  bodyEn: "",
  imageUrl: "",
});
const magazineGalleryUrls = ref([""]);
const pointsPolicyForm = reactive({ point_value_twd: 1, base_rate: 0.01, diamond_rate: 0.02, expiry_months: 12 });
const costForm = reactive({ title: "", amount_twd: 0, recorded_at: "" });

const selectedBuyerEmail = ref("");
const statusForm = reactive({ orderId: "", status: "inquiring", note: "" });
const noteForm = reactive({ note: "" });
const rewardForm = reactive({ points: 50, reason: "VIP 手動獎勵" });

const hasAdminAccess = computed(() => ["admin", "super_admin", "sales", "maintenance"].includes(authStore.role));
const tabs = [
  { key: "command", title: "交易指揮" },
  { key: "queue", title: "審核工作流" },
  { key: "products", title: "商品管理" },
  { key: "magazine", title: "雜誌管理" },
  { key: "finance", title: "財務與點數" },
  { key: "crm", title: "客戶價值" },
  { key: "reviews", title: "評價審核" },
  { key: "events", title: "操作紀錄" },
];

function formatCurrency(value) {
  return `NT$ ${Number(value || 0).toLocaleString()}`;
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function statusLabel(status) {
  const map = {
    inquiring: "待回覆",
    waiting_quote: "待回覆",
    quoted: "待確認",
    buyer_accepted: "待匯款",
    proof_uploaded: "待核款",
    paid: "待出貨",
    completed: "已完成",
    cancelled: "已取消",
  };
  return map[String(status || "")] || String(status || "-");
}

function queueColumns() {
  return ["待回覆", "待買家確認", "待匯款證明", "待核款", "待出貨", "已完成"];
}

function openRoom(roomId) {
  const id = Number(roomId);
  if (!Number.isInteger(id) || id <= 0) return;
  selectedRoomId.value = id;
}

function closeRoom() {
  selectedRoomId.value = null;
  loadAdmin();
}

async function loadAdmin() {
  if (!hasAdminAccess.value) return;
  loading.value = true;
  isError.value = false;
  statusText.value = "";
  try {
    const [overviewResp, ordersResp, usersResp, queueResp, eventsResp] = await Promise.all([
      fetchAdminOverview(),
      fetchAdminOrders(),
      fetchAdminUsers().catch(() => ({ items: [] })),
      fetchAdminWorkflowQueues(),
      fetchAdminEvents(),
    ]);
    overview.value = overviewResp;
    orders.value = ordersResp.items || [];
    users.value = usersResp.items || [];
    queue.value = queueResp;
    events.value = eventsResp.items || [];
    const [productsResp, costsResp, reportResp, reviewsResp, pointsResp] = await Promise.all([
      fetchAdminProducts().catch(() => ({ items: [] })),
      fetchAdminCosts().catch(() => ({ items: [] })),
      fetchAdminReportSummary().catch(() => ({ totals: { revenue_twd: 0, cost_twd: 0, profit_twd: 0 }, series: [] })),
      fetchAdminReviews().catch(() => ({ items: [] })),
      fetchAdminPointsPolicy().catch(() => ({ point_value_twd: 1, base_rate: 0.01, diamond_rate: 0.02, expiry_months: 12 })),
    ]);
    const magazinesResp = await fetchAdminMagazineArticles().catch(() => ({ items: [] }));
    products.value = productsResp.items || [];
    magazines.value = magazinesResp.items || [];
    costs.value = costsResp.items || [];
    report.value = reportResp;
    reviews.value = reviewsResp.items || [];
    Object.assign(pointsPolicyForm, pointsResp || {});
    if (events.value.length > 0) {
      await markAdminEventsRead(events.value[0].id);
    }
    if (!selectedBuyerEmail.value && users.value.length > 0) {
      selectedBuyerEmail.value = users.value[0].email;
      await loadCrm(selectedBuyerEmail.value);
    }
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "載入後台失敗";
    if (statusText.value.includes("401")) {
      authStore.logout();
      router.push("/login");
    }
  } finally {
    loading.value = false;
  }
}

function startEditMagazine(article) {
  magazineForm.articleId = Number(article.article_id || 0);
  magazineForm.brand = article.brand || "Rolex";
  magazineForm.titleZh = article.title?.["zh-Hant"] || "";
  magazineForm.titleJa = article.title?.ja || "";
  magazineForm.titleEn = article.title?.en || "";
  magazineForm.descZh = article.description?.["zh-Hant"] || "";
  magazineForm.descJa = article.description?.ja || "";
  magazineForm.descEn = article.description?.en || "";
  magazineForm.bodyZh = article.body?.["zh-Hant"] || "";
  magazineForm.bodyJa = article.body?.ja || "";
  magazineForm.bodyEn = article.body?.en || "";
  magazineForm.imageUrl = article.image_url || "";
  magazineGalleryUrls.value = Array.isArray(article.gallery_urls) && article.gallery_urls.length > 0 ? [...article.gallery_urls] : [article.image_url || ""];
}

function resetMagazineForm() {
  magazineForm.articleId = 0;
  magazineForm.brand = "Rolex";
  magazineForm.titleZh = "";
  magazineForm.titleJa = "";
  magazineForm.titleEn = "";
  magazineForm.descZh = "";
  magazineForm.descJa = "";
  magazineForm.descEn = "";
  magazineForm.bodyZh = "";
  magazineForm.bodyJa = "";
  magazineForm.bodyEn = "";
  magazineForm.imageUrl = "";
  magazineGalleryUrls.value = [""];
}

function addMagazineImageField() {
  magazineGalleryUrls.value.push("");
}

function removeMagazineImageField(index) {
  if (magazineGalleryUrls.value.length <= 1) {
    magazineGalleryUrls.value = [""];
    return;
  }
  magazineGalleryUrls.value.splice(index, 1);
}

async function submitMagazine() {
  if (!magazineForm.titleZh.trim() || !magazineForm.imageUrl.trim()) {
    isError.value = true;
    statusText.value = "請填寫雜誌標題與圖片網址";
    return;
  }
  const payload = {
    brand: magazineForm.brand,
    title: {
      "zh-Hant": magazineForm.titleZh,
      ja: magazineForm.titleJa || magazineForm.titleZh,
      en: magazineForm.titleEn || magazineForm.titleZh,
    },
    description: {
      "zh-Hant": magazineForm.descZh || magazineForm.titleZh,
      ja: magazineForm.descJa || magazineForm.descZh || magazineForm.titleZh,
      en: magazineForm.descEn || magazineForm.descZh || magazineForm.titleZh,
    },
    body: {
      "zh-Hant": magazineForm.bodyZh || magazineForm.descZh || magazineForm.titleZh,
      ja: magazineForm.bodyJa || magazineForm.descJa || magazineForm.descZh || magazineForm.titleZh,
      en: magazineForm.bodyEn || magazineForm.descEn || magazineForm.descZh || magazineForm.titleZh,
    },
    image_url: magazineForm.imageUrl,
    gallery_urls: magazineGalleryUrls.value.map((item) => item.trim()).filter(Boolean),
  };
  try {
    if (magazineForm.articleId > 0) {
      await updateAdminMagazineArticle(magazineForm.articleId, payload);
      statusText.value = "雜誌文章已更新";
    } else {
      await createAdminMagazineArticle(payload);
      statusText.value = "雜誌文章已新增";
    }
    resetMagazineForm();
    await loadAdmin();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "雜誌儲存失敗";
  }
}

async function removeMagazine(articleId) {
  try {
    await deleteAdminMagazineArticle(articleId);
    await loadAdmin();
    statusText.value = `雜誌文章 #${articleId} 已刪除`;
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "刪除雜誌文章失敗";
  }
}

async function createProduct() {
  if (!productForm.sku.trim() || !productForm.nameZh.trim()) return;
  const payload = {
    sku: productForm.sku,
    category: productForm.category,
    grade: productForm.grade,
    price_twd: Number(productForm.price_twd || 0),
    name: {
      "zh-Hant": productForm.nameZh,
      ja: productForm.nameJa || productForm.nameZh,
      en: productForm.nameEn || productForm.nameZh,
    },
    description: {
      "zh-Hant": productForm.descZh || productForm.nameZh,
      ja: productForm.descJa || productForm.descZh || productForm.nameZh,
      en: productForm.descEn || productForm.descZh || productForm.nameZh,
    },
    image_urls: productImageUrls.value.map((item) => item.trim()).filter(Boolean),
  };
  try {
    if (editingProductId.value > 0) {
      await updateAdminProduct(editingProductId.value, payload);
      statusText.value = "商品已更新";
    } else {
      await createProductApi(payload);
      statusText.value = "商品已新增";
    }
    resetProductForm();
    await loadAdmin();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "新增商品失敗";
  }
}

function resetProductForm() {
  editingProductId.value = 0;
  productForm.sku = "";
  productForm.category = "watch";
  productForm.grade = "A";
  productForm.price_twd = 0;
  productForm.nameZh = "";
  productForm.nameJa = "";
  productForm.nameEn = "";
  productForm.descZh = "";
  productForm.descJa = "";
  productForm.descEn = "";
  productImageUrls.value = [""];
}

function startEditProduct(item) {
  editingProductId.value = Number(item.id || 0);
  productForm.sku = item.sku || "";
  productForm.category = item.category || "watch";
  productForm.grade = item.grade || "A";
  productForm.price_twd = Number(item.price_twd || 0);
  productForm.nameZh = item.name?.["zh-Hant"] || "";
  productForm.nameJa = item.name?.ja || "";
  productForm.nameEn = item.name?.en || "";
  productForm.descZh = item.description?.["zh-Hant"] || "";
  productForm.descJa = item.description?.ja || "";
  productForm.descEn = item.description?.en || "";
  productImageUrls.value = Array.isArray(item.image_urls) && item.image_urls.length > 0 ? [...item.image_urls] : [""];
}

function addProductImageField() {
  productImageUrls.value.push("");
}

function removeProductImageField(index) {
  if (productImageUrls.value.length <= 1) {
    productImageUrls.value = [""];
    return;
  }
  productImageUrls.value.splice(index, 1);
}

async function removeProduct(productId) {
  try {
    await deleteAdminProduct(productId);
    await loadAdmin();
    statusText.value = `商品 #${productId} 已刪除`;
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "刪除商品失敗";
  }
}

async function createCost() {
  try {
    await createAdminCost({ title: costForm.title, amount_twd: Number(costForm.amount_twd), recorded_at: costForm.recorded_at });
    costForm.title = "";
    costForm.amount_twd = 0;
    costForm.recorded_at = "";
    await loadAdmin();
    statusText.value = "成本項目已新增";
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "新增成本失敗";
  }
}

async function savePointsPolicy() {
  try {
    await updateAdminPointsPolicy({
      point_value_twd: Number(pointsPolicyForm.point_value_twd),
      base_rate: Number(pointsPolicyForm.base_rate),
      diamond_rate: Number(pointsPolicyForm.diamond_rate),
      expiry_months: Number(pointsPolicyForm.expiry_months),
    });
    statusText.value = "點數規則已更新";
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "點數規則更新失敗";
  }
}

async function toggleReviewHidden(review) {
  try {
    await updateAdminReview(review.id, { hidden: !review.hidden });
    await loadAdmin();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "更新評價失敗";
  }
}

async function downloadCsv() {
  try {
    csvOutput.value = await exportOrdersCsv();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "CSV 匯出失敗";
  }
}

async function loadCrm(email) {
  if (!email) return;
  selectedBuyerEmail.value = email;
  try {
    crm.value = await fetchBuyerHistory(email);
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "載入 CRM 失敗";
  }
}

async function submitOrderStatus() {
  const orderId = Number(statusForm.orderId);
  if (!Number.isInteger(orderId) || orderId <= 0) {
    isError.value = true;
    statusText.value = "請輸入有效訂單 ID";
    return;
  }
  try {
    await patchAdminOrderStatus(orderId, { status: statusForm.status, note: statusForm.note });
    statusForm.note = "";
    statusText.value = `訂單 #${orderId} 狀態已更新`;
    await loadAdmin();
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "更新狀態失敗";
  }
}

async function submitBuyerNote() {
  if (!selectedBuyerEmail.value || !noteForm.note.trim()) return;
  try {
    await addBuyerNote(selectedBuyerEmail.value, { note: noteForm.note });
    noteForm.note = "";
    await loadCrm(selectedBuyerEmail.value);
    statusText.value = "CRM 備註已新增";
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "新增備註失敗";
  }
}

async function submitReward() {
  if (!selectedBuyerEmail.value) return;
  try {
    await rewardBuyerPoints(selectedBuyerEmail.value, { points: Number(rewardForm.points), reason: rewardForm.reason });
    await loadCrm(selectedBuyerEmail.value);
    statusText.value = "已調整買家點數";
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "點數調整失敗";
  }
}

function logout() {
  authStore.logout();
  router.push("/");
}

onMounted(loadAdmin);
</script>

<template>
  <div class="console-wrap">
    <p v-if="!hasAdminAccess" class="state">目前帳號無後台權限。</p>
    <template v-else>
      <header class="console-header">
        <div>
          <p class="eyebrow">TRADE COMMAND CENTER</p>
          <h1>交易指揮中心</h1>
          <p class="muted">人工議價、核款、CRM、稽核事件一站完成。</p>
        </div>
        <div class="header-actions">
          <span class="badge">{{ authStore.role }}</span>
          <button class="btn btn-muted" type="button" @click="logout">登出</button>
        </div>
      </header>

      <nav class="tab-nav">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          type="button"
          @click="activeTab = tab.key"
        >
          {{ tab.title }}
        </button>
      </nav>

      <p v-if="statusText" class="status" :class="isError ? 'error' : 'ok'">{{ statusText }}</p>

      <section v-if="activeTab === 'command'" class="block-grid">
        <article class="panel metric"><p class="label">訂單總數</p><p class="value">{{ overview.metrics.total_orders }}</p></article>
        <article class="panel metric"><p class="label">待處理</p><p class="value">{{ overview.metrics.pending_orders }}</p></article>
        <article class="panel metric"><p class="label">活躍溝通室</p><p class="value">{{ overview.metrics.active_rooms }}</p></article>
        <article class="panel metric"><p class="label">今日事件</p><p class="value">{{ (events || []).length }}</p></article>

        <article class="panel wide">
          <div class="panel-head"><h2>議價 / 狀態控制台</h2></div>
          <div class="inline-form">
            <input v-model="statusForm.orderId" class="field" type="number" min="1" placeholder="Order ID" />
            <select v-model="statusForm.status" class="field">
              <option value="inquiring">待回覆</option>
              <option value="quoted">已報價</option>
              <option value="buyer_accepted">買家同意</option>
              <option value="proof_uploaded">已上傳存證</option>
              <option value="paid">已收款</option>
              <option value="completed">已完成</option>
              <option value="cancelled">已取消</option>
            </select>
            <input v-model="statusForm.note" class="field" type="text" placeholder="管理備註（可選）" />
            <button class="btn btn-primary" type="button" @click="submitOrderStatus">更新</button>
          </div>
          <p class="muted">點擊訂單列可直接進入該訂單諮詢室。</p>
        </article>

        <article class="panel wide">
          <div class="panel-head"><h2>訂單即時列表</h2></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>ID</th><th>買家</th><th>商品</th><th>狀態</th><th>金額</th><th></th></tr></thead>
              <tbody>
                <tr v-for="order in orders.slice(0, 12)" :key="order.id">
                  <td>#{{ order.id }}</td>
                  <td>{{ order.buyer_email }}</td>
                  <td>{{ order.product_name }}</td>
                  <td>{{ statusLabel(order.status) }}</td>
                  <td>{{ formatCurrency(order.final_amount_twd || order.amount_twd) }}</td>
                  <td><button class="btn btn-muted" type="button" @click="openRoom(order.comm_room_id)">開啟溝通室</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-if="activeTab === 'queue'" class="kanban">
        <article v-for="column in queueColumns()" :key="column" class="panel queue-col">
          <div class="panel-head">
            <h2>{{ column }}</h2>
            <span class="badge quiet">{{ queue.summary?.[column] || 0 }}</span>
          </div>
          <div class="queue-list">
            <button
              v-for="item in (queue.queues?.[column] || []).slice(0, 6)"
              :key="`${column}-${item.order_id}`"
              class="queue-item"
              type="button"
              @click="openRoom(item.room_id)"
            >
              <p>#{{ item.order_id }} ・ {{ item.product_name }}</p>
              <p class="muted">{{ item.buyer_email }} ・ {{ formatCurrency(item.amount_twd) }}</p>
            </button>
            <p v-if="(queue.queues?.[column] || []).length === 0" class="muted">目前無項目</p>
          </div>
        </article>
      </section>

      <section v-if="activeTab === 'products'" class="panel">
        <div class="panel-head"><h2>商品管理</h2><button class="btn btn-muted" type="button" @click="resetProductForm">清空表單</button></div>
        <div class="inline-form">
          <input v-model="productForm.sku" class="field" type="text" placeholder="SKU" />
          <select v-model="productForm.category" class="field">
            <option value="watch">鐘錶</option>
            <option value="accessory">飾品</option>
            <option value="vintage">古著</option>
            <option value="small_goods">小物</option>
            <option value="apparel">服飾</option>
            <option value="furniture">家具</option>
          </select>
          <select v-model="productForm.grade" class="field">
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
          </select>
          <input v-model.number="productForm.price_twd" class="field" type="number" min="1" placeholder="售價" />
          <button class="btn btn-primary" type="button" @click="createProduct">{{ editingProductId > 0 ? '更新商品' : '新增商品' }}</button>
        </div>
        <div class="inline-form">
          <input v-model="productForm.nameZh" class="field" type="text" placeholder="名稱（繁中）" />
          <input v-model="productForm.nameJa" class="field" type="text" placeholder="名稱（日文）" />
          <input v-model="productForm.nameEn" class="field" type="text" placeholder="名稱（英文）" />
        </div>
        <div class="inline-form">
          <textarea v-model="productForm.descZh" class="field field-textarea" rows="3" placeholder="描述（繁中）"></textarea>
          <textarea v-model="productForm.descJa" class="field field-textarea" rows="3" placeholder="描述（日文）"></textarea>
          <textarea v-model="productForm.descEn" class="field field-textarea" rows="3" placeholder="描述（英文）"></textarea>
        </div>
        <div class="field-stack">
          <p class="muted">商品插圖（多張）</p>
          <div v-for="(_url, index) in productImageUrls" :key="`product-image-${index}`" class="inline-form">
            <input v-model="productImageUrls[index]" class="field" type="text" placeholder="https://image-url" />
            <button class="btn btn-muted" type="button" @click="removeProductImageField(index)">移除</button>
          </div>
          <button class="btn btn-muted" type="button" @click="addProductImageField">新增圖片欄位</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>SKU</th><th>名稱</th><th>分類</th><th>售價</th><th></th></tr></thead>
            <tbody>
              <tr v-for="item in products.slice(0, 40)" :key="item.id">
                <td>{{ item.id }}</td>
                <td>{{ item.sku }}</td>
                <td>{{ item.name?.['zh-Hant'] || item.sku }}</td>
                <td>{{ item.category }}</td>
                <td>{{ formatCurrency(item.price_twd) }}</td>
                <td>
                  <div class="row-actions">
                    <button class="btn btn-muted" type="button" @click="startEditProduct(item)">編輯</button>
                    <button class="btn btn-muted" type="button" @click="removeProduct(item.id)">刪除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="activeTab === 'magazine'" class="panel">
        <div class="panel-head"><h2>雜誌管理（前台連動）</h2></div>
        <div class="inline-form">
          <input v-model="magazineForm.brand" class="field" type="text" placeholder="品牌" />
          <input v-model="magazineForm.titleZh" class="field" type="text" placeholder="標題（繁中）" />
          <input v-model="magazineForm.titleJa" class="field" type="text" placeholder="標題（日文）" />
          <input v-model="magazineForm.titleEn" class="field" type="text" placeholder="標題（英文）" />
        </div>
        <div class="inline-form">
          <input v-model="magazineForm.descZh" class="field" type="text" placeholder="摘要（繁中）" />
          <input v-model="magazineForm.descJa" class="field" type="text" placeholder="摘要（日文）" />
          <input v-model="magazineForm.descEn" class="field" type="text" placeholder="摘要（英文）" />
        </div>
        <div class="inline-form">
          <textarea v-model="magazineForm.bodyZh" class="field field-textarea" rows="4" placeholder="內文（繁中）"></textarea>
          <textarea v-model="magazineForm.bodyJa" class="field field-textarea" rows="4" placeholder="內文（日文）"></textarea>
          <textarea v-model="magazineForm.bodyEn" class="field field-textarea" rows="4" placeholder="內文（英文）"></textarea>
        </div>
        <div class="inline-form">
          <input v-model="magazineForm.imageUrl" class="field" type="text" placeholder="圖片網址" />
          <button class="btn btn-primary" type="button" @click="submitMagazine">{{ magazineForm.articleId > 0 ? '更新文章' : '新增文章' }}</button>
        </div>
        <div class="field-stack">
          <p class="muted">插圖圖組（可排序輸入）</p>
          <div v-for="(_url, index) in magazineGalleryUrls" :key="`mag-image-${index}`" class="inline-form">
            <input v-model="magazineGalleryUrls[index]" class="field" type="text" placeholder="https://gallery-image-url" />
            <button class="btn btn-muted" type="button" @click="removeMagazineImageField(index)">移除</button>
          </div>
          <div class="row-actions">
            <button class="btn btn-muted" type="button" @click="addMagazineImageField">新增插圖欄位</button>
            <button class="btn btn-muted" type="button" @click="resetMagazineForm">清空表單</button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>品牌</th><th>標題</th><th>摘要</th><th></th></tr></thead>
            <tbody>
              <tr v-for="item in magazines.slice(0, 40)" :key="item.article_id">
                <td>#{{ item.article_id }}</td>
                <td>{{ item.brand }}</td>
                <td>{{ item.title?.['zh-Hant'] || item.title?.en }}</td>
                <td>{{ item.description?.['zh-Hant'] || item.description?.en }}</td>
                <td>
                  <div class="row-actions">
                    <button class="btn btn-muted" type="button" @click="startEditMagazine(item)">編輯</button>
                    <button class="btn btn-muted" type="button" @click="removeMagazine(item.article_id)">刪除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="activeTab === 'finance'" class="crm-grid">
        <article class="panel">
          <div class="panel-head"><h2>財務摘要</h2><button class="btn btn-muted" type="button" @click="downloadCsv">匯出 CSV</button></div>
          <p>收入：{{ formatCurrency(report.totals?.revenue_twd) }}</p>
          <p>成本：{{ formatCurrency(report.totals?.cost_twd) }}</p>
          <p>利潤：{{ formatCurrency(report.totals?.profit_twd) }}</p>
          <pre v-if="csvOutput" class="csv">{{ csvOutput }}</pre>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>新增成本與點數規則</h2></div>
          <div class="inline-form">
            <input v-model="costForm.title" class="field" type="text" placeholder="成本項目" />
            <input v-model.number="costForm.amount_twd" class="field" type="number" min="1" placeholder="金額" />
            <input v-model="costForm.recorded_at" class="field" type="date" />
            <button class="btn btn-primary" type="button" @click="createCost">新增成本</button>
          </div>
          <div class="inline-form">
            <input v-model.number="pointsPolicyForm.point_value_twd" class="field" type="number" min="1" placeholder="1點幣值" />
            <input v-model.number="pointsPolicyForm.base_rate" class="field" type="number" step="0.001" placeholder="一般回饋率" />
            <input v-model.number="pointsPolicyForm.diamond_rate" class="field" type="number" step="0.001" placeholder="高階回饋率" />
            <input v-model.number="pointsPolicyForm.expiry_months" class="field" type="number" min="1" placeholder="有效(月)" />
          </div>
          <button class="btn btn-muted" type="button" @click="savePointsPolicy">儲存點數規則</button>
        </article>
      </section>

      <section v-if="activeTab === 'crm'" class="crm-grid">
        <article class="panel">
          <div class="panel-head"><h2>買家名單</h2></div>
          <div class="user-list">
            <button
              v-for="user in users"
              :key="user.email"
              class="user-item"
              :class="{ active: user.email === selectedBuyerEmail }"
              type="button"
              @click="loadCrm(user.email)"
            >
              <p>{{ user.display_name || user.email }}</p>
              <p class="muted">{{ user.email }}</p>
            </button>
          </div>
        </article>

        <article class="panel">
          <div class="panel-head"><h2>客戶價值卡</h2></div>
          <p v-if="!crm" class="muted">請選擇買家。</p>
          <template v-else>
            <p>累積交易：{{ crm.total_orders }} 筆</p>
            <p>總消費：{{ formatCurrency(crm.total_spent_twd) }}</p>
            <p>轉化率：{{ crm.conversion_rate_pct }}%</p>
            <p>點數餘額：{{ crm.points_balance }}</p>
            <div class="inline-form">
              <input v-model.number="rewardForm.points" class="field" type="number" />
              <input v-model="rewardForm.reason" class="field" type="text" placeholder="調整原因" />
              <button class="btn btn-primary" type="button" @click="submitReward">發放 / 扣回</button>
            </div>
            <div class="inline-form">
              <input v-model="noteForm.note" class="field" type="text" placeholder="新增客戶備註" />
              <button class="btn btn-muted" type="button" @click="submitBuyerNote">新增備註</button>
            </div>
            <ul class="notes">
              <li v-for="note in crm.notes || []" :key="note.id">{{ note.note }}<span class="muted"> ・ {{ note.author }}</span></li>
            </ul>
          </template>
        </article>
      </section>

      <section v-if="activeTab === 'reviews'" class="panel">
        <div class="panel-head"><h2>評價審核</h2></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>訂單</th><th>評分</th><th>內容</th><th>狀態</th><th></th></tr></thead>
            <tbody>
              <tr v-for="review in reviews" :key="review.id">
                <td>#{{ review.order_id }}</td>
                <td>{{ review.rating }}/5</td>
                <td>{{ review.comment }}</td>
                <td>{{ review.hidden ? '隱藏' : '公開' }}</td>
                <td><button class="btn btn-muted" type="button" @click="toggleReviewHidden(review)">{{ review.hidden ? '改公開' : '隱藏' }}</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="activeTab === 'events'" class="panel">
        <div class="panel-head"><h2>不可竄改事件紀錄</h2></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>#</th><th>事件</th><th>描述</th><th>角色</th><th>時間</th></tr></thead>
            <tbody>
              <tr v-for="event in events.slice(0, 60)" :key="event.id">
                <td>{{ event.id }}</td>
                <td>{{ event.title }}</td>
                <td>{{ event.detail }}</td>
                <td>{{ event.actor_role }}</td>
                <td>{{ formatDate(event.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <Teleport defer to="body">
      <div v-if="selectedRoomId" class="overlay">
        <CommRoomInline :roomId="selectedRoomId" @close="closeRoom" />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.console-wrap { min-height: 100vh; background: radial-gradient(circle at 8% 0%, #f5f0e6 0, #ece6da 42%, #e7e2d7 100%); padding: 1.2rem; color: #1f2836; }
.console-header { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; margin-bottom: 0.8rem; }
.eyebrow { margin: 0; font-size: 0.73rem; letter-spacing: 0.15em; color: #7d6742; }
h1 { margin: 0.35rem 0; font-size: clamp(1.8rem, 3vw, 2.8rem); }
.header-actions { display: flex; align-items: center; gap: 0.5rem; }
.badge { border: 1px solid rgba(109, 90, 61, 0.25); padding: 0.2rem 0.48rem; color: #6f5b3a; text-transform: uppercase; font-size: 0.72rem; }
.badge.quiet { background: rgba(255,255,255,0.7); }
.tab-nav { display: flex; gap: 0.5rem; margin-bottom: 0.8rem; flex-wrap: wrap; }
.tab-btn { border: 1px solid rgba(108,90,63,0.3); background: rgba(255,255,255,0.56); color: #2e3540; padding: 0.4rem 0.7rem; cursor: pointer; }
.tab-btn.active { background: #2b3646; color: #fff; }
.status { margin: 0 0 0.7rem; }
.status.ok { color: #2f7d4b; }
.status.error, .state { color: #b33232; }
.block-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.7rem; }
.panel { border: 1px solid rgba(130, 108, 72, 0.26); background: rgba(255,255,255,0.7); padding: 0.85rem; }
.panel-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem; }
.panel-head h2 { margin: 0; font-size: 1rem; }
.metric .label { margin: 0; color: #6f675b; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }
.metric .value { margin: 0.25rem 0 0; font-size: 2rem; }
.wide { grid-column: span 2; }
.inline-form { display: grid; gap: 0.5rem; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 0.5rem; }
.field { border: 1px solid rgba(117,99,70,0.34); background: #fff; padding: 0.5rem; }
.field-textarea { min-height: 96px; resize: vertical; }
.field-stack { display: grid; gap: 0.45rem; margin-bottom: 0.6rem; }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; border-bottom: 1px solid rgba(132,109,73,0.16); padding: 0.48rem 0.4rem; font-size: 0.88rem; }
.kanban { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.7rem; }
.queue-list { display: grid; gap: 0.4rem; }
.queue-item { border: 1px solid rgba(117,99,70,0.24); background: rgba(255,255,255,0.56); text-align: left; padding: 0.45rem; cursor: pointer; }
.queue-item p { margin: 0; }
.crm-grid { display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 0.7rem; }
.user-list { display: grid; gap: 0.4rem; max-height: 60vh; overflow: auto; }
.user-item { border: 1px solid rgba(110,94,68,0.25); background: rgba(255,255,255,0.55); text-align: left; padding: 0.45rem; cursor: pointer; }
.user-item.active { border-color: #2c3a4b; background: rgba(44,58,75,0.08); }
.user-item p, .notes { margin: 0; }
.notes { margin-top: 0.5rem; padding-left: 1rem; display: grid; gap: 0.3rem; }
.muted { color: #6d685e; }
.btn { border: 1px solid rgba(117,99,70,0.36); padding: 0.5rem 0.66rem; cursor: pointer; }
.btn-primary { background: #2d394a; color: #fff; }
.btn-muted { background: rgba(255,255,255,0.72); color: #2c3642; }
.row-actions { display: flex; gap: 0.4rem; }
.overlay { position: fixed; inset: 0; background: var(--paper-50); z-index: 9999; }
@media (max-width: 1100px) {
  .block-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kanban { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .crm-grid { grid-template-columns: 1fr; }
  .wide { grid-column: span 2; }
  .inline-form { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .block-grid, .kanban { grid-template-columns: 1fr; }
  .wide { grid-column: span 1; }
}
</style>
