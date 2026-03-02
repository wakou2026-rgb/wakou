<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { browseCatalog } from "../../modules/catalog/service";
const route = useRoute();
const router = useRouter();

const { locale, t } = useI18n();

const currentCategory = ref(route.query.cat || "all");
const items = ref([]);
const isLoading = ref(true);
const errorText = ref("");
const categoryTitle = ref("COLLECTION");
const searchText = ref("");
const sortValue = ref("");
const page = ref(1);
const totalPages = ref(0);
const pageSize = 20;

const swatchPalette = ["#1d1d1d", "#3a3f52", "#754f34", "#5f6a58"];
let searchDebounceTimer;

async function loadCatalog() {
  isLoading.value = true;
  errorText.value = "";
  try {
    const payload = {
      lang: locale.value,
      page: page.value,
      pageSize,
      q: searchText.value.trim(),
      sort: sortValue.value
    };
    if (currentCategory.value !== "all") {
      payload.category = currentCategory.value;
    }
    const rows = await browseCatalog(payload);
    items.value = rows.items;
    totalPages.value = rows.totalPages;

    const catRes = await fetch("/api/v1/categories");
    if (catRes.ok) {
      const data = await catRes.json();
      const cat = data.items.find((entry) => entry.id === currentCategory.value);
      categoryTitle.value = cat ? localizeField(cat.title, locale.value) : "COLLECTION";
    }
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "load catalog failed";
  } finally {
    isLoading.value = false;
  }
}

watch(
  () => route.query.cat,
  (newCat) => {
    currentCategory.value = newCat || "all";
    page.value = 1;
    loadCatalog();
  }
);

watch(locale, () => {
  page.value = 1;
  loadCatalog();
});

watch(sortValue, () => {
  page.value = 1;
  loadCatalog();
});

watch(searchText, () => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer);
  }
  searchDebounceTimer = setTimeout(() => {
    page.value = 1;
    loadCatalog();
  }, 300);
});

onBeforeUnmount(() => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer);
  }
});

function goDetail(id) {
  router.push(`/catalog/${id}`);
}

function goPrevPage() {
  if (page.value <= 1) {
    return;
  }
  page.value -= 1;
  loadCatalog();
}

function goNextPage() {
  if (page.value >= totalPages.value) {
    return;
  }
  page.value += 1;
  loadCatalog();
}

onMounted(loadCatalog);
function localizeField(val, lang) {
  const l = lang || locale.value || "zh-Hant";
  if (!val) return "";
  if (typeof val === "string") {
    try {
      const obj = JSON.parse(val);
      if (typeof obj === "object" && obj !== null) {
        return obj[l] || obj["zh-Hant"] || obj["en"] || Object.values(obj)[0] || val;
      }
    } catch {}
    return val;
  }
  if (typeof val === "object") {
    return val[l] || val["zh-Hant"] || val["en"] || Object.values(val)[0] || "";
  }
  return String(val);
}
</script>

<template>
  <div class="catalog-page container">
    <header class="page-header">
      <p class="eyebrow">Curated Selection</p>
      <h1 class="page-title">{{ categoryTitle }}</h1>
    </header>

    <section class="catalog-controls" aria-label="catalog controls">
      <label class="search-wrap" for="catalog-search">
        <span class="search-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="1.8" />
            <path d="M20 20L16.6 16.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          </svg>
        </span>
        <input
          id="catalog-search"
          v-model="searchText"
          class="search-input"
          type="search"
          :placeholder="t('catalog.search_placeholder')"
        />
      </label>

      <label class="sort-wrap" for="catalog-sort">
        <span>{{ t('catalog.sort_label') }}</span>
        <select id="catalog-sort" v-model="sortValue" class="sort-select">
          <option value="">{{ t('catalog.sort_recommended') }}</option>
          <option value="price_asc">{{ t('catalog.sort_price_low_high') }}</option>
          <option value="price_desc">{{ t('catalog.sort_price_high_low') }}</option>
          <option value="newest">{{ t('catalog.sort_newest') }}</option>
          <option value="name_asc">{{ t('catalog.sort_name_asc') }}</option>
        </select>
      </label>
    </section>

    <div v-if="isLoading" class="state-msg">{{ t('collection.loading') }}</div>
    <div v-else-if="errorText" class="state-msg error">{{ errorText }}</div>
    <div v-else-if="items.length === 0" class="empty-state">{{ $t('catalog.empty_category') }}</div>

    <section v-else class="product-grid" aria-label="product listing">
      <article v-for="item in items" :key="item.id" class="product-card" @click="goDetail(item.id)">
        <div class="card-visual img-frame">
          <img :src="item.imageUrls?.[0] || '/logo-transparent.png'" :alt="item.name" loading="lazy" />
        </div>

        <div class="card-copy">
          <p class="card-kicker">{{ localizeField(item.category) || localizeField(currentCategory) }}</p>
          <h2>{{ item.name }}</h2>
          <p class="price">NT$ {{ Number(item.priceTwd).toLocaleString() }}</p>

          <div class="swatches" aria-label="color swatches">
            <span v-for="(swatch, swatchIndex) in swatchPalette" :key="`${item.id}-${swatchIndex}`" class="swatch" :style="{ backgroundColor: swatch }"></span>
          </div>
        </div>
      </article>
    </section>

    <nav v-if="!isLoading && !errorText && totalPages > 0" class="pagination" :aria-label="t('catalog.pagination_label')">
      <button class="page-btn" type="button" :disabled="page <= 1" @click="goPrevPage">
        {{ t('catalog.prev_page') }}
      </button>
      <p class="page-indicator">{{ t('catalog.page_indicator', { page, totalPages }) }}</p>
      <button class="page-btn" type="button" :disabled="page >= totalPages" @click="goNextPage">
        {{ t('catalog.next_page') }}
      </button>
    </nav>
  </div>
</template>

<style scoped>
.catalog-page {
  max-width: 1320px;
}

.catalog-controls {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.search-wrap {
  align-items: center;
  background: var(--paper-100);
  border: 1px solid var(--ink-200);
  border-radius: 999px;
  display: flex;
  flex: 1;
  gap: 0.45rem;
  max-width: 460px;
  min-width: 240px;
  padding: 0.55rem 0.95rem;
}

.search-icon {
  color: var(--ink-500);
  display: inline-flex;
}

.search-icon svg {
  display: block;
  height: 1rem;
  width: 1rem;
}

.search-input {
  background: transparent;
  border: 0;
  color: var(--ink-900);
  flex: 1;
  font-size: 0.9rem;
  min-width: 0;
  outline: none;
}

.sort-wrap {
  align-items: center;
  color: var(--ink-500);
  display: inline-flex;
  font-size: 0.75rem;
  gap: 0.55rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.sort-select {
  background: var(--paper-100);
  border: 1px solid var(--ink-200);
  border-radius: 999px;
  color: var(--ink-900);
  font-size: 0.83rem;
  padding: 0.46rem 0.85rem;
}

.product-grid {
  display: grid;
  gap: 3rem 1.4rem;
  grid-template-columns: repeat(4, minmax(170px, 220px));
  justify-content: start;
}

.product-card {
  cursor: pointer;
  display: grid;
  gap: 0.85rem;
  transition: transform 220ms ease;
}

.product-card:hover {
  transform: translateY(-4px);
}

.card-visual {
  aspect-ratio: 1 / 1;
}

.card-copy {
  display: grid;
  gap: 0.35rem;
}

.card-kicker {
  color: var(--ink-500);
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  margin: 0;
  text-transform: uppercase;
}

.card-copy h2 {
  font-size: 0.88rem;
  letter-spacing: 0.03em;
  line-height: 1.45;
  margin: 0;
  min-height: 2.6em;
}

.price {
  color: var(--ink-900);
  font-size: 0.94rem;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  margin: 0;
}

.swatches {
  display: flex;
  gap: 0.3rem;
  margin-top: 0.35rem;
}

.swatch {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  display: inline-block;
  height: 0.8rem;
  width: 0.8rem;
}

.empty-state {
  color: var(--ink-500);
  text-align: center;
}

.pagination {
  align-items: center;
  display: flex;
  gap: 0.95rem;
  justify-content: center;
  margin-top: 2.2rem;
}

.page-btn {
  background: var(--paper-100);
  border: 1px solid var(--ink-200);
  border-radius: 999px;
  color: var(--ink-900);
  cursor: pointer;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  min-width: 88px;
  padding: 0.48rem 0.9rem;
  text-transform: uppercase;
}

.page-btn:disabled {
  color: var(--ink-400);
  cursor: not-allowed;
}

.page-indicator {
  color: var(--ink-600);
  font-size: 0.82rem;
  margin: 0;
}

@media (max-width: 1180px) {
  .product-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .catalog-controls {
    align-items: stretch;
  }

  .search-wrap {
    max-width: 100%;
    min-width: 0;
    width: 100%;
  }

  .sort-wrap {
    justify-content: space-between;
    width: 100%;
  }

  .product-grid {
    gap: 2rem 0.8rem;
  }

  .card-copy h2 {
    font-size: 0.82rem;
  }
}
</style>
