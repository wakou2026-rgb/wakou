<script setup>
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { fetchPublicMagazines } from "../../modules/catalog/service";

const { t } = useI18n();
const isLoading = ref(true);
const errorText = ref("");
const activeBrand = ref("ALL");
const articles = ref([]);
const fallbackImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='900' height='1200' viewBox='0 0 900 1200'%3E%3Crect width='900' height='1200' fill='%23ebe9e4'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' fill='%238c7b6c' font-family='serif' font-size='32' letter-spacing='2'%3EIMAGE UNAVAILABLE%3C/text%3E%3C/svg%3E";

const availableBrands = computed(() => {
  const unique = new Set(articles.value.map((item) => item.brand));
  return ["ALL", ...Array.from(unique)];
});

const filteredArticles = computed(() => {
  if (activeBrand.value === "ALL") {
    return articles.value;
  }
  return articles.value.filter((item) => item.brand === activeBrand.value);
});

const featuredArticle = computed(() => filteredArticles.value[0] || null);
const gridArticles = computed(() => filteredArticles.value.slice(1));

function toArticlePath(article) {
  return `/magazine/${article.article_id}-${article.slug}`;
}

function onImageError(event) {
  const img = event?.target;
  if (!img || img.dataset.fallbackApplied === "1") {
    return;
  }
  img.dataset.fallbackApplied = "1";
  img.src = fallbackImage;
}

async function loadMagazines() {
  isLoading.value = true;
  errorText.value = "";
  try {
    const data = await fetchPublicMagazines();
    const rows = (data.articles || []).map((item) => ({
      article_id: item.article_id,
      slug: item.slug,
      brand: item.brand,
      title: item.title || {},
      description: item.description || {},
      image_url: item.image_url,
      gallery_urls: Array.isArray(item.gallery_urls) ? item.gallery_urls : [],
      published_at: item.published_at,
      status: item.published === false ? "archived" : "published"
    }));
    articles.value = rows.filter((item) => item.status !== "archived");
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "load magazines failed";
  } finally {
    isLoading.value = false;
  }
}

onMounted(loadMagazines);
</script>

<template>
  <div class="magazine-page container">
    <header class="intro">
      <p class="eyebrow">Editorial Journal</p>
      <h1 class="page-title">Magazine</h1>
      <p class="page-meta">{{ $t('magazine.page_meta') }}</p>
    </header>

    <section class="filter-bar" aria-label="brand filters">
      <button
        v-for="brand in availableBrands"
        :key="brand"
        class="filter-btn"
        :class="{ active: activeBrand === brand }"
        @click="activeBrand = brand"
      >
        {{ brand }}
      </button>
    </section>

    <div v-if="isLoading" class="state-msg">{{ $t('magazine.loading_articles') }}</div>
    <div v-else-if="errorText" class="state-msg error">{{ errorText }}</div>

    <template v-else>
      <article v-if="featuredArticle" class="featured-card">
        <RouterLink :to="toArticlePath(featuredArticle)" class="featured-link">
          <div class="featured-visual img-frame">
              <img :src="featuredArticle.image_url" :alt="featuredArticle.title['zh-Hant'] || featuredArticle.title.en" @error="onImageError" />
          </div>
          <div class="featured-copy">
            <p class="featured-brand">{{ featuredArticle.brand }}</p>
            <h2>{{ featuredArticle.title["zh-Hant"] || featuredArticle.title.en }}</h2>
            <p>{{ featuredArticle.description["zh-Hant"] || featuredArticle.description.en }}</p>
          </div>
        </RouterLink>
      </article>

      <section class="article-grid">
        <article v-for="item in gridArticles" :key="item.article_id" class="article-card">
          <RouterLink :to="toArticlePath(item)" class="article-link">
            <div class="article-visual img-frame">
              <img :src="item.image_url" :alt="item.title['zh-Hant'] || item.title.en" loading="lazy" @error="onImageError" />
            </div>
            <div class="article-copy">
              <p class="article-brand">{{ item.brand }}</p>
              <h3>{{ item.title["zh-Hant"] || item.title.en }}</h3>
              <p>{{ item.description["zh-Hant"] || item.description.en }}</p>
            </div>
          </RouterLink>
        </article>
      </section>

      <div v-if="filteredArticles.length === 0" class="empty-state">{{ $t('magazine.brand_empty') }}</div>
    </template>
  </div>
</template>

<style scoped>
.magazine-page {
  display: grid;
  gap: 2.5rem;
  max-width: 1240px;
}

.intro {
  max-width: 640px;
}

.filter-bar {
  border-bottom: 1px solid var(--paper-300);
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding-bottom: 1rem;
}

.filter-btn {
  background: transparent;
  border: 1px solid var(--paper-300);
  color: var(--ink-700);
  cursor: pointer;
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  padding: 0.45rem 0.9rem;
  text-transform: uppercase;
}

.filter-btn.active {
  border-color: var(--ink-900);
  color: var(--ink-900);
}

.featured-card {
  border-bottom: 1px solid var(--paper-300);
  padding-bottom: 2.2rem;
}

.featured-link {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: 3fr 2fr;
}

.featured-visual {
  aspect-ratio: 3 / 2;
}

.featured-copy {
  align-self: center;
  display: grid;
  gap: 0.8rem;
}

.featured-copy h2 {
  font-size: clamp(1.45rem, 2.4vw, 2rem);
  letter-spacing: 0.05em;
}

.featured-copy p {
  color: var(--ink-700);
  margin: 0;
}

.featured-brand,
.article-brand {
  color: var(--ink-500);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  margin: 0;
  text-transform: uppercase;
}

.article-grid {
  display: grid;
  gap: 2.2rem 1.5rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.article-link {
  display: grid;
  gap: 0.9rem;
}

.article-visual {
  aspect-ratio: 3 / 4;
}

.article-copy {
  display: grid;
  gap: 0.45rem;
}

.article-copy h3 {
  font-size: 1.02rem;
  letter-spacing: 0.03em;
  line-height: 1.4;
}

.article-copy p {
  color: var(--ink-600);
  margin: 0;
}

.empty-state {
  color: var(--ink-500);
  text-align: center;
}

@media (max-width: 980px) {
  .featured-link {
    grid-template-columns: 1fr;
  }

  .article-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .article-grid {
    grid-template-columns: 1fr;
  }
}
</style>
