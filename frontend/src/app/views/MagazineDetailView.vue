<script setup>
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import { fetchPublicMagazines } from "../../modules/catalog/service";

const route = useRoute();
const { t, locale } = useI18n();
const article = ref(null);
const related = ref([]);
const isLoading = ref(true);
const errorText = ref("");

// ── i18n helpers ──────────────────────────────────────────
function localeText(obj) {
  if (!obj) return "";
  const lang = locale.value;
  // Try exact match, then fallback chain
  if (lang === "zh-Hant" || lang === "zh") return obj["zh-Hant"] || obj["zh_hant"] || obj.en || "";
  if (lang === "ja") return obj.ja || obj["zh-Hant"] || obj["zh_hant"] || obj.en || "";
  return obj.en || obj["zh-Hant"] || obj["zh_hant"] || "";
}

// ── Layout blocks ──────────────────────────────────────────
const layoutBlocks = computed(() => {
  if (!article.value) return [];
  const blocks = article.value.layout_blocks;
  return Array.isArray(blocks) && blocks.length > 0 ? blocks : [];
});

const hasLayoutBlocks = computed(() => layoutBlocks.value.length > 0);

// ── Legacy fallback ────────────────────────────────────────
const articleParagraphs = computed(() => {
  if (!article.value || hasLayoutBlocks.value) return [];
  const body = article.value.body?.["zh-Hant"] || article.value.body?.zh_hant || article.value.body?.en || "";
  return body.split(/\n\s*\n/g).map(item => item.trim()).filter(Boolean);
});

const articleGallery = computed(() => {
  if (!article.value) return [];
  const rows = Array.isArray(article.value.gallery_urls) ? article.value.gallery_urls : [];
  if (rows.length > 0) return rows;
  return article.value.image_url ? [article.value.image_url] : [];
});

// ── Block size class ───────────────────────────────────────
function imageSizeClass(size) {
  if (size === "full") return "block-image--full";
  if (size === "medium") return "block-image--medium";
  return "block-image--wide";
}

// ── ID parsing ─────────────────────────────────────────────
function parseArticleId() {
  const rawId = String(route.params.id || "");
  const match = rawId.match(/^(\d+)/);
  if (!match) return null;
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
      errorText.value = t("magazine.not_found");
      return;
    }
    article.value = rows.find(item => Number(item.article_id) === articleId) || null;
    if (!article.value) {
      errorText.value = t("magazine.not_found");
      return;
    }
    related.value = rows
      .filter(item => item.brand === article.value.brand && item.article_id !== article.value.article_id)
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
    <div v-if="isLoading" class="state-msg">{{ $t('magazine.loading') }}</div>
    <div v-else-if="errorText" class="state-msg error">{{ errorText }}</div>

    <article v-else-if="article" class="article-shell">
      <!-- ── Header ──────────────────────────────────────────── -->
      <header class="article-head">
        <p class="article-kicker">Journal / {{ article.brand }}</p>
        <h1>{{ article.title["zh-Hant"] || article.title.zh_hant || article.title.en }}</h1>
        <p class="article-lead">{{ article.description["zh-Hant"] || article.description.zh_hant || article.description.en }}</p>
      </header>

      <!-- ── Layout blocks (rich mode) ──────────────────────── -->
      <div v-if="hasLayoutBlocks" class="article-blocks">
        <template v-for="(block, idx) in layoutBlocks" :key="idx">

          <!-- hero: full-bleed image with title overlay -->
          <section v-if="block.type === 'hero'" class="block block-hero">
            <figure class="block-hero__img img-frame">
              <img :src="block.image_url" :alt="localeText(block.title)" />
            </figure>
            <div class="block-hero__overlay" v-if="localeText(block.title) || localeText(block.subtitle)">
              <h2 v-if="localeText(block.title)">{{ localeText(block.title) }}</h2>
              <p v-if="localeText(block.subtitle)">{{ localeText(block.subtitle) }}</p>
            </div>
          </section>

          <!-- text: paragraph -->
          <section
            v-else-if="block.type === 'text'"
            class="block block-text"
            :class="`block-text--${block.align || 'left'}`"
          >
            <p>{{ localeText(block.content) }}</p>
          </section>

          <!-- image: standalone figure -->
          <section
            v-else-if="block.type === 'image'"
            class="block block-image"
            :class="imageSizeClass(block.size)"
          >
            <figure class="img-frame">
              <img :src="block.image_url" :alt="localeText(block.caption)" loading="lazy" />
            </figure>
            <figcaption v-if="localeText(block.caption)" class="block-image__caption">
              {{ localeText(block.caption) }}
            </figcaption>
          </section>

          <!-- quote: pull quote -->
          <section v-else-if="block.type === 'quote'" class="block block-quote">
            <blockquote>
              <p>{{ localeText(block.content) }}</p>
              <cite v-if="block.author">— {{ block.author }}</cite>
            </blockquote>
          </section>

          <!-- image_text: side by side -->
          <section
            v-else-if="block.type === 'image_text'"
            class="block block-image-text"
            :class="block.layout === 'image_right' ? 'block-image-text--reverse' : ''"
          >
            <figure class="block-image-text__img img-frame">
              <img :src="block.image_url" :alt="localeText(block.content)" loading="lazy" />
            </figure>
            <div class="block-image-text__body">
              <p>{{ localeText(block.content) }}</p>
            </div>
          </section>

        </template>
      </div>

      <!-- ── Legacy mode (no blocks) ────────────────────────── -->
      <template v-else>
        <figure class="hero img-frame">
          <img :src="article.image_url" :alt="article.title['zh-Hant'] || article.title.en" />
        </figure>

        <section v-if="articleGallery.length > 1" class="gallery-grid">
          <figure
            v-for="(image, index) in articleGallery"
            :key="`${article.article_id}-${index}`"
            class="gallery-item img-frame"
          >
            <img :src="image" :alt="`${article.title['zh-Hant'] || article.title.en} ${index + 1}`" loading="lazy" />
          </figure>
        </section>

        <div class="article-layout">
          <div class="article-body">
            <p v-for="(paragraph, index) in articleParagraphs" :key="index">{{ paragraph }}</p>
            <p v-if="articleParagraphs.length === 0">{{ $t('magazine.wip') }}</p>
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
      </template>

      <!-- ── Related (shown below blocks mode too) ─────────── -->
      <aside class="related related--bottom" v-if="hasLayoutBlocks && related.length > 0">
        <h3>Related</h3>
        <div class="related-grid">
          <RouterLink
            v-for="item in related"
            :key="item.article_id"
            class="related-item"
            :to="`/magazine/${item.article_id}-${item.slug}`"
          >
            <img :src="item.image_url" :alt="item.title['zh-Hant'] || item.title.en" />
            <span>{{ item.title["zh-Hant"] || item.title.en }}</span>
          </RouterLink>
        </div>
      </aside>

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

/* ── Block system ─────────────────────────────────────── */
.article-blocks {
  display: grid;
  gap: 2.5rem;
}

.block {
  width: 100%;
}

/* hero */
.block-hero {
  position: relative;
}

.block-hero__img {
  aspect-ratio: 16 / 7;
  margin: 0;
}

.block-hero__overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 2rem;
  background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 100%);
  color: #fff;
}

.block-hero__overlay h2 {
  font-size: clamp(1.4rem, 3vw, 2.4rem);
  letter-spacing: 0.06em;
  margin: 0 0 0.4rem;
}

.block-hero__overlay p {
  font-size: 1rem;
  margin: 0;
  opacity: 0.9;
}

/* text */
.block-text p {
  color: var(--ink-800);
  font-family: var(--font-serif);
  font-size: 1.08rem;
  line-height: 1.95;
  margin: 0;
  max-width: 760px;
}

.block-text--center p {
  text-align: center;
  margin: 0 auto;
}

.block-text--right p {
  text-align: right;
  margin-left: auto;
}

/* image */
.block-image figure {
  margin: 0;
}

.block-image--full figure {
  aspect-ratio: 16 / 6;
}

.block-image--wide figure {
  aspect-ratio: 16 / 8;
  max-width: 900px;
}

.block-image--medium figure {
  aspect-ratio: 4 / 3;
  max-width: 560px;
}

.block-image__caption {
  font-size: 0.82rem;
  color: var(--ink-500);
  text-align: center;
  margin-top: 0.5rem;
  font-style: italic;
}

/* quote */
.block-quote {
  max-width: 700px;
  margin: 0 auto;
}

.block-quote blockquote {
  border-left: 3px solid var(--accent-500, #c9a96e);
  padding: 1rem 1.5rem;
  margin: 0;
  background: var(--paper-50, #fafaf8);
}

.block-quote blockquote p {
  font-family: var(--font-serif);
  font-size: 1.2rem;
  line-height: 1.8;
  color: var(--ink-800);
  margin: 0 0 0.6rem;
  font-style: italic;
}

.block-quote blockquote cite {
  font-size: 0.88rem;
  color: var(--ink-500);
  font-style: normal;
  letter-spacing: 0.06em;
}

/* image_text */
.block-image-text {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  align-items: center;
}

.block-image-text--reverse {
  direction: rtl;
}

.block-image-text--reverse > * {
  direction: ltr;
}

.block-image-text__img {
  aspect-ratio: 4 / 3;
  margin: 0;
}

.block-image-text__body p {
  color: var(--ink-800);
  font-family: var(--font-serif);
  font-size: 1.05rem;
  line-height: 1.9;
  margin: 0;
}

/* ── Legacy mode ─────────────────────────────────────── */
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

/* ── Related ─────────────────────────────────────────── */
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

.related--bottom {
  border-left: none;
  border-top: 1px solid var(--paper-300);
  padding-left: 0;
  padding-top: 1.5rem;
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.2rem;
}

/* ── img-frame shared ────────────────────────────────── */
:deep(.img-frame),
.img-frame {
  overflow: hidden;
  border-radius: 2px;
}

:deep(.img-frame img),
.img-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
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

  .block-image-text {
    grid-template-columns: 1fr;
  }

  .block-image-text--reverse {
    direction: ltr;
  }

  .related-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .gallery-grid {
    grid-template-columns: 1fr;
  }

  .related-grid {
    grid-template-columns: 1fr;
  }
}
</style>
