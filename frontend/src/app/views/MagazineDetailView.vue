<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { fetchPublicMagazines } from "../../modules/catalog/service";

const route = useRoute();
const article = ref(null);
const related = ref([]);
const isLoading = ref(true);
const errorText = ref("");

const articleParagraphs = computed(() => {
  if (!article.value) {
    return [];
  }
  const body = article.value.body?.["zh-Hant"] || article.value.body?.en || "";
  return body
    .split(/\n\s*\n/g)
    .map((item) => item.trim())
    .filter(Boolean);
});

const articleGallery = computed(() => {
  if (!article.value) {
    return [];
  }
  const rows = Array.isArray(article.value.gallery_urls) ? article.value.gallery_urls : [];
  if (rows.length > 0) {
    return rows;
  }
  return article.value.image_url ? [article.value.image_url] : [];
});

function parseArticleId() {
  const rawId = String(route.params.id || "");
  const match = rawId.match(/^(\d+)/);
  if (!match) {
    return null;
  }
  return Number(match[1]);
}

onMounted(async () => {
  isLoading.value = true;
  errorText.value = "";
  try {
    const data = await fetchPublicMagazines();
    const rows = data.articles || [];
    const articleId = parseArticleId();
    if (!articleId) {
      errorText.value = "找不到該文章";
      return;
    }
    article.value = rows.find((item) => Number(item.article_id) === articleId) || null;
    if (!article.value) {
      errorText.value = "找不到該文章";
      return;
    }

    related.value = rows
      .filter((item) => item.brand === article.value.brand && item.article_id !== article.value.article_id)
      .slice(0, 3);
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "load article failed";
  } finally {
    isLoading.value = false;
  }
});
</script>

<template>
  <div class="detail-page container">
    <div v-if="isLoading" class="state-msg">載入中...</div>
    <div v-else-if="errorText" class="state-msg error">{{ errorText }}</div>

    <article v-else-if="article" class="article-shell">
      <header class="article-head">
        <p class="article-kicker">Journal / {{ article.brand }}</p>
        <h1>{{ article.title["zh-Hant"] || article.title.en }}</h1>
        <p class="article-lead">{{ article.description["zh-Hant"] || article.description.en }}</p>
      </header>

      <figure class="hero img-frame">
        <img :src="article.image_url" :alt="article.title['zh-Hant'] || article.title.en" />
      </figure>

      <section v-if="articleGallery.length > 1" class="gallery-grid">
        <figure v-for="(image, index) in articleGallery" :key="`${article.article_id}-${index}`" class="gallery-item img-frame">
          <img :src="image" :alt="`${article.title['zh-Hant'] || article.title.en} ${index + 1}`" loading="lazy" />
        </figure>
      </section>

      <div class="article-layout">
        <div class="article-body">
          <p v-for="(paragraph, index) in articleParagraphs" :key="index">{{ paragraph }}</p>
          <p v-if="articleParagraphs.length === 0">內容編輯中，敬請期待完整企劃。</p>
        </div>

        <aside class="related" v-if="related.length > 0">
          <h3>Related</h3>
          <RouterLink
            v-for="item in related"
            :key="item.article_id"
            class="related-item"
            :to="`/magazine/${item.article_id}-${item.slug}`"
          >
            <img :src="item.image_url" :alt="item.title['zh-Hant'] || item.title.en" />
            <span>{{ item.title["zh-Hant"] || item.title.en }}</span>
          </RouterLink>
        </aside>
      </div>
    </article>
  </div>
</template>

<style scoped>
.detail-page {
  max-width: 1200px;
}

.article-shell {
  display: grid;
  gap: 2rem;
}

.article-head {
  display: grid;
  gap: 0.9rem;
  max-width: 760px;
}

.article-kicker {
  color: var(--ink-500);
  font-size: 0.74rem;
  letter-spacing: 0.16em;
  margin: 0;
  text-transform: uppercase;
}

.article-head h1 {
  font-size: clamp(1.8rem, 4vw, 3rem);
  letter-spacing: 0.06em;
}

.article-lead {
  color: var(--ink-700);
  font-size: 1.04rem;
  margin: 0;
}

.hero {
  aspect-ratio: 16 / 8;
}

.gallery-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.gallery-item {
  aspect-ratio: 4 / 3;
}

.article-layout {
  display: grid;
  gap: 2.2rem;
  grid-template-columns: minmax(0, 1fr) 300px;
}

.article-body {
  display: grid;
  gap: 1.2rem;
  max-width: 760px;
}

.article-body p {
  color: var(--ink-800);
  font-family: var(--font-serif);
  font-size: 1.08rem;
  line-height: 1.95;
  margin: 0;
}

.related {
  border-left: 1px solid var(--paper-300);
  display: grid;
  gap: 1rem;
  padding-left: 1.25rem;
}

.related h3 {
  font-size: 0.9rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.related-item {
  display: grid;
  gap: 0.5rem;
}

.related-item img {
  aspect-ratio: 4 / 3;
  object-fit: cover;
  width: 100%;
}

.related-item span {
  color: var(--ink-700);
  font-size: 0.9rem;
  line-height: 1.5;
}

@media (max-width: 920px) {
  .gallery-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .article-layout {
    grid-template-columns: 1fr;
  }

  .related {
    border-left: none;
    border-top: 1px solid var(--paper-300);
    padding-left: 0;
    padding-top: 1rem;
  }
}

@media (max-width: 640px) {
  .gallery-grid {
    grid-template-columns: 1fr;
  }
}
</style>
