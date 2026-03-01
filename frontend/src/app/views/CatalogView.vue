<script setup>
import { onMounted, ref, watch } from "vue";
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

const swatchPalette = ["#1d1d1d", "#3a3f52", "#754f34", "#5f6a58"];

async function loadCatalog() {
  isLoading.value = true;
  errorText.value = "";
  try {
    const payload = { lang: locale.value };
    if (currentCategory.value !== "all") {
      payload.category = currentCategory.value;
    }
    const rows = await browseCatalog(payload);
    items.value = rows.items || rows;

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
    loadCatalog();
  }
);

watch(locale, () => {
  loadCatalog();
});

function goDetail(id) {
  router.push(`/catalog/${id}`);
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

    <div v-if="isLoading" class="state-msg">Loading...</div>
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
  </div>
</template>

<style scoped>
.catalog-page {
  max-width: 1320px;
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
  .product-grid {
    gap: 2rem 0.8rem;
  }

  .card-copy h2 {
    font-size: 0.82rem;
  }
}
</style>
