<script setup>
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { browseCatalog, fetchPublicMagazines } from "../../modules/catalog/service";

const { locale } = useI18n();
const magazines = ref([]);
const newArrivals = ref([]);
const currentSlide = ref(0);
const latestMagazine = computed(() => magazines.value[0] || null);

function normalizeMagazines(payload) {
  const rows = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.articles)
      ? payload.articles
      : Array.isArray(payload?.items)
        ? payload.items
        : [];

  return rows
    .map((item) => {
      const articleId = Number(item?.article_id ?? item?.id ?? 0);
      const title = typeof item?.title === "string"
        ? item.title
        : item?.title?.["zh-Hant"] || item?.title?.en || "";

      return {
        articleId,
        slug: item?.slug || "",
        title,
        coverUrl: item?.cover_url || item?.image_url || "",
        publishedAt: item?.published_at || ""
      };
    })
    .filter((item) => Number.isFinite(item.articleId) && item.articleId > 0);
}

function toMagazinePath(article) {
  if (!article) {
    return "/magazine";
  }
  return article.slug ? `/magazine/${article.articleId}-${article.slug}` : `/magazine/${article.articleId}`;
}

function nextSlide() {
  if (newArrivals.value.length === 0) return;
  currentSlide.value = (currentSlide.value + 1) % newArrivals.value.length;
}

function prevSlide() {
  if (newArrivals.value.length === 0) return;
  currentSlide.value = (currentSlide.value - 1 + newArrivals.value.length) % newArrivals.value.length;
}

onMounted(async () => {
  try {
    const [magResult, catalogResult] = await Promise.allSettled([
      fetchPublicMagazines(),
      browseCatalog(),
    ]);
    if (magResult.status === "fulfilled") {
      magazines.value = normalizeMagazines(magResult.value).slice(0, 1);
    }
    if (catalogResult.status === "fulfilled") {
      newArrivals.value = (Array.isArray(catalogResult.value) ? catalogResult.value : []).slice(0, 4);
    }
  } catch {
    magazines.value = [];
    newArrivals.value = [];
  }
});

function formatPrice(val) {
  return `NT$ ${Number(val || 0).toLocaleString()}`;
}
</script>

<template>
  <div class="home container">
    <!-- Hero Editorial -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">{{ $t('home.welcome') }}</h1>
        <p class="hero-desc">
          {{ $t('home.hero_desc') }}
        </p>
        <div class="hero-actions">
          <RouterLink class="btn btn-primary" to="/catalog">{{ $t('home.explore_cta') }}</RouterLink>
        </div>
      </div>
      <div class="hero-visual">
        <div class="img-frame aspect-tall">
          <img src="/main.png" alt="Wakou Vintage Select" />
        </div>
      </div>
    </section>

    <hr class="divider" />

    <!-- Magazine + New Arrivals (nanamica style) -->
    <section class="discover">
      <div class="discover-magazine">
        <template v-if="latestMagazine">
          <RouterLink :to="toMagazinePath(latestMagazine)" class="mag-link">
            <div class="mag-cover img-frame">
            <img
                :src="latestMagazine.coverUrl || `https://picsum.photos/seed/wakou-mag/900/1200`"
                :alt="latestMagazine.title || 'Latest Magazine'"
            />
            </div>
            <div class="mag-info">
              <p class="eyebrow">{{ $t('home.latest_journal') }}</p>
              <h3>{{ latestMagazine.title || $t('home.latest_journal_title') }}</h3>
              <p class="mag-date" v-if="latestMagazine.publishedAt">{{ latestMagazine.publishedAt }}</p>
              <p class="mag-category">JOURNAL / Wakou</p>
            </div>
          </RouterLink>
        </template>
        <template v-else>
          <div class="mag-cover img-frame">
            <img src="https://picsum.photos/seed/wakou-mag/900/1200" alt="Journal" />
          </div>
          <div class="mag-info">
            <p class="eyebrow">{{ $t('home.latest_journal') }}</p>
            <h3>{{ $t('home.latest_journal_title') }}</h3>
            <p class="mag-category">JOURNAL / Wakou</p>
          </div>
        </template>
      </div>

      <div class="discover-arrivals">
        <div class="arrivals-header">
          <p class="arrivals-label">{{ $t('home.new_arrivals') }}</p>
        </div>
        <div class="arrivals-carousel" v-if="newArrivals.length > 0">
          <button class="carousel-arrow carousel-prev" @click="prevSlide" aria-label="Previous">&lsaquo;</button>
          <RouterLink
            :to="`/catalog/${newArrivals[currentSlide].id}`"
            class="carousel-slide"
          >
            <div class="carousel-img img-frame">
              <img
                :src="newArrivals[currentSlide].imageUrls?.[0] || `https://picsum.photos/seed/wakou-arr-${newArrivals[currentSlide].id}/600/750`"
                :alt="newArrivals[currentSlide].name"
                :key="newArrivals[currentSlide].id"
              />
            </div>
            <div class="carousel-info">
              <p class="carousel-name">{{ newArrivals[currentSlide].name }}</p>
              <p class="carousel-price">{{ formatPrice(newArrivals[currentSlide].priceTwd) }}</p>
            </div>
          </RouterLink>
          <button class="carousel-arrow carousel-next" @click="nextSlide" aria-label="Next">&rsaquo;</button>
        </div>
        <div v-else class="arrivals-empty">
          <p>{{ $t('home.new_arrivals_empty') }}</p>
        </div>
        <div class="arrivals-cta">
          <RouterLink class="btn-cta" to="/collections">
            <span>{{ $t('home.shop_now') }}</span>
            <span class="cta-arrow">›</span>
          </RouterLink>
        </div>
      </div>
    </section>

    <hr class="divider" />

    <!-- Selection Flow -->
    <section class="selection-flow">
      <div class="section-intro">
        <p class="eyebrow">{{ $t('home.selection_eyebrow') }}</p>
        <h2 class="page-title">{{ $t('home.selection_title') }}</h2>
        <p class="page-meta">{{ $t('home.selection_desc') }}</p>
      </div>

      <div class="flow-list">
        <article class="flow-step">
          <div class="step-watermark">01</div>
          <div class="step-grid">
            <div class="step-info">
              <h3 class="step-title">{{ $t('home.step1_title') }}</h3>
              <p class="step-desc">{{ $t('home.step1_desc') }}</p>
            </div>
            <div class="step-media img-frame">
              <img src="/Exclusive Acquisition.png" alt="Exclusive Acquisition" />
            </div>
          </div>
        </article>

        <article class="flow-step">
          <div class="step-watermark">02</div>
          <div class="step-grid">
            <div class="step-info">
              <h3 class="step-title">{{ $t('home.step2_title') }}</h3>
              <p class="step-desc">{{ $t('home.step2_desc') }}</p>
            </div>
            <div class="step-media img-frame">
              <img src="/Restoration & Packaging.png" alt="Restoration & Packaging" />
            </div>
          </div>
        </article>

        <article class="flow-step">
          <div class="step-watermark">03</div>
          <div class="step-grid">
            <div class="step-info">
              <h3 class="step-title">{{ $t('home.step3_title') }}</h3>
              <p class="step-desc">{{ $t('home.step3_desc') }}</p>
            </div>
            <div class="step-media img-frame">
              <img src="/Premium Showcase.png" alt="Premium Showcase" />
            </div>
          </div>
        </article>
      </div>
    </section>

    <hr class="divider" />

    <!-- Pillars (moved to bottom) -->
    <section class="pillars">
      <div class="section-intro">
        <p class="eyebrow">{{ $t('ui.philosophy') }}</p>
        <h2 class="page-title">{{ $t('ui.pillars_title') }}</h2>
      </div>
      
      <div class="pillar-grid">
        <article class="pillar-card">
          <div class="pillar-header">
            <span class="pillar-num">01</span>
          </div>
          <div class="pillar-content">
            <h3>{{ $t('ui.source_transparency') }}</h3>
            <p class="meta">Source Transparency</p>
            <p class="pillar-desc">{{ $t('ui.source_desc') }}</p>
          </div>
        </article>
        
        <article class="pillar-card">
          <div class="pillar-header">
            <span class="pillar-num">02</span>
          </div>
          <div class="pillar-content">
            <h3>{{ $t('ui.artisan_check') }}</h3>
            <p class="meta">Artisan Check</p>
            <p class="pillar-desc">{{ $t('ui.artisan_desc') }}</p>
          </div>
        </article>
        
        <article class="pillar-card">
          <div class="pillar-header">
            <span class="pillar-num">03</span>
          </div>
          <div class="pillar-content">
            <h3>{{ $t('ui.exclusive_protocol') }}</h3>
            <p class="meta">Exclusive Protocol</p>
            <p class="pillar-desc">{{ $t('ui.exclusive_desc') }}</p>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
}

/* Hero */
.hero {
  align-items: center;
  display: grid;
  gap: clamp(2rem, 4vw, 4.5rem);
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  min-height: clamp(520px, 68vh, 760px);
}

.hero-title {
  font-size: clamp(3.5rem, 6vw, 5.5rem);
  letter-spacing: 0.1em;
  line-height: 1.1;
  margin-bottom: 2rem;
}

.hero-desc {
  font-size: 1.15rem;
  line-height: 1.9;
  margin-bottom: 3.5rem;
  max-width: 480px;
}

.aspect-tall {
  aspect-ratio: 4/5;
  background: var(--paper-200);
}

/* Discover: Magazine + New Arrivals */
.discover {
  display: grid;
  gap: clamp(1.6rem, 2.6vw, 3rem);
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  padding: clamp(3.2rem, 7vh, 6rem) 0;
  align-items: stretch;
  min-height: clamp(560px, 76vh, 860px);
}

.discover-magazine,
.discover-arrivals {
  background: var(--paper-200);
  display: flex;
  flex-direction: column;
  min-height: clamp(520px, 74vh, 760px);
  padding: 1.6rem;
}

.mag-link {
  color: inherit;
  display: flex;
  flex: 1;
  flex-direction: column;
  text-decoration: none;
}

.mag-cover {
  flex: 1;
  overflow: hidden;
  min-height: 0;
  position: relative;
  aspect-ratio: 4 / 5;
}

.mag-cover img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mag-info {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding-top: 1.5rem;
}

.mag-info .eyebrow {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  letter-spacing: 0.15em;
  color: var(--ink-500);
  margin: 0;
}

.mag-info h3 {
  font-family: var(--font-serif);
  font-size: 1.4rem;
  color: var(--ink-900);
  margin: 0;
  text-decoration: underline;
  text-underline-offset: 0.3em;
  text-decoration-thickness: 1px;
}

.mag-date {
  color: var(--ink-500);
  font-family: var(--font-sans);
  font-size: 0.8rem;
  margin: 0;
}

.mag-category {
  color: var(--ink-500);
  font-family: var(--font-sans);
  font-size: 0.8rem;
  letter-spacing: 0.05em;
  margin: 0;
}

/* Right panel: New Arrivals carousel */
.discover-arrivals {
  padding-inline: 2rem;
}

.arrivals-header {
  text-align: center;
  margin-bottom: 0.4rem;
}

.arrivals-label {
  color: var(--ink-900);
  font-family: var(--font-sans);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  margin: 0;
  text-transform: uppercase;
}

.arrivals-carousel {
  flex: 1;
  position: relative;
  display: grid;
  place-items: center;
  min-height: 0;
}

.carousel-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--ink-800);
  background: var(--paper-100);
  color: var(--ink-800);
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  padding: 0;
}

.carousel-prev {
  left: -20px;
}

.carousel-next {
  right: -20px;
}

.carousel-arrow:hover {
  background: var(--ink-800);
  color: var(--paper-50);
}

.carousel-slide {
  display: grid;
  grid-template-rows: auto auto;
  justify-items: center;
  align-content: center;
  gap: 1rem;
  padding-inline: clamp(1.25rem, 2.8vw, 2.5rem);
  text-decoration: none;
  color: var(--ink-900);
  min-height: 0;
  width: 100%;
}

.carousel-img {
  width: min(100%, 430px);
  aspect-ratio: 3 / 4;
  overflow: hidden;
  background: var(--paper-100);
  position: relative;
  min-height: 320px;
}

.carousel-img img {
  position: relative;
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition: transform 0.5s cubic-bezier(0.25, 1, 0.5, 1);
}

.carousel-slide:hover .carousel-img img {
  transform: scale(1.03);
}

.carousel-info {
  text-align: center;
  padding-top: 0.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.carousel-name {
  font-family: var(--font-sans);
  font-size: 0.95rem;
  letter-spacing: 0.03em;
  margin: 0;
  text-decoration: underline;
  text-underline-offset: 0.3em;
  text-decoration-thickness: 1px;
}

.carousel-price {
  color: var(--ink-700);
  font-size: 0.85rem;
  margin: 0;
}

.arrivals-empty {
  color: var(--ink-500);
  font-size: 0.95rem;
  padding: 3rem 0;
  text-align: center;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.arrivals-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  padding-top: 2rem;
  margin-top: auto;
}

.btn-cta {
  display: inline-flex;
  align-items: center;
  gap: 0.8rem;
  text-decoration: none;
  color: var(--ink-900);
  font-family: var(--font-sans);
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  transition: opacity 0.3s ease;
}

.btn-cta:hover {
  opacity: 0.7;
}

.cta-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--ink-800);
  color: var(--paper-50);
  font-size: 1.3rem;
  line-height: 1;
  transition: background 0.3s ease;
}

.btn-cta:hover .cta-arrow {
  background: var(--ink-900);
}

/* Selection Flow */
.selection-flow {
  padding: 7rem 0;
  display: flex;
  flex-direction: column;
  gap: 4rem;
}

.selection-flow .section-intro {
  text-align: left;
  max-width: 600px;
}

.selection-flow .eyebrow {
  font-family: var(--font-sans);
  letter-spacing: 0.15em;
  color: var(--ink-500);
  margin-bottom: 1rem;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.selection-flow .page-title {
  font-family: var(--font-serif);
  font-size: 2.8rem;
  margin-bottom: 1.5rem;
  color: var(--ink-900);
}

.selection-flow .page-meta {
  font-size: 1.1rem;
  line-height: 1.9;
  color: var(--ink-700);
}

.flow-list {
  display: flex;
  flex-direction: column;
}

.flow-step {
  position: relative;
  padding: 5rem 0;
  border-top: 1px solid var(--paper-300);
  isolation: isolate;
}

.flow-step:last-child {
  border-bottom: 1px solid var(--paper-300);
}

.step-watermark {
  position: absolute;
  top: 1.5rem;
  left: 0;
  font-size: 10rem;
  font-family: var(--font-serif);
  color: var(--paper-300);
  line-height: 0.8;
  z-index: -1;
  user-select: none;
}

.step-grid {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 6rem;
  align-items: center;
}

.step-info {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding-right: 2rem;
}

.step-title {
  font-family: var(--font-serif);
  font-size: 2rem;
  color: var(--ink-900);
  margin: 0;
  line-height: 1.3;
}

.step-desc {
  font-size: 1.05rem;
  line-height: 1.9;
  color: var(--ink-700);
  margin: 0;
}

.step-media {
  aspect-ratio: 3/2;
  overflow: hidden;
  background: var(--paper-200);
}

.step-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.7s cubic-bezier(0.25, 1, 0.5, 1);
}

.flow-step:hover .step-media img {
  transform: scale(1.03);
}

/* Pillars */
.pillars {
  padding: 6rem 0 8rem;
  display: flex;
  flex-direction: column;
  gap: 4rem;
}

.pillars .section-intro {
  text-align: center;
}

.pillars .eyebrow {
  font-family: var(--font-sans);
  letter-spacing: 0.15em;
  color: var(--ink-500);
  margin-bottom: 1rem;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.pillars .page-title {
  font-family: var(--font-serif);
  font-size: 2.5rem;
  color: var(--ink-900);
  margin: 0;
}

.pillar-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3rem;
}

.pillar-card {
  border-top: 1px solid var(--ink-900);
  padding-top: 2rem;
  position: relative;
  transition: transform 0.4s cubic-bezier(0.25, 1, 0.5, 1);
  display: flex;
  flex-direction: column;
}

.pillar-card:hover {
  transform: translateY(-8px);
}

.pillar-header {
  margin-bottom: 2.5rem;
}

.pillar-num {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  color: var(--ink-300);
  letter-spacing: 0.1em;
}

.pillar-content h3 {
  font-family: var(--font-serif);
  font-size: 1.8rem;
  margin: 0 0 0.5rem 0;
  color: var(--ink-900);
}

.pillar-content .meta {
  font-family: var(--font-sans);
  font-size: 0.85rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--ink-500);
  margin: 0 0 1.5rem 0;
}

.pillar-desc {
  font-size: 1rem;
  line-height: 1.9;
  color: var(--ink-700);
  margin: 0;
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 3rem;
    padding-top: 2rem;
  }
  
  .hero-visual {
    order: -1;
  }

  .discover {
    grid-template-columns: 1fr;
    gap: 3rem;
    padding: 4rem 0;
    min-height: auto;
  }

  .discover-magazine,
  .discover-arrivals {
    min-height: auto;
    padding: 1.2rem;
  }

  .carousel-img {
    width: min(100%, 420px);
    min-height: 280px;
  }

  .carousel-arrow {
    width: 32px;
    height: 32px;
    font-size: 1.1rem;
  }

  .carousel-prev {
    left: 0.5rem;
  }

  .carousel-next {
    right: 0.5rem;
  }
  
  .selection-flow {
    padding: 4rem 0;
    gap: 3rem;
  }
  
  .step-watermark {
    font-size: 7rem;
    top: 2rem;
  }
  
  .step-grid {
    grid-template-columns: 1fr;
    gap: 3rem;
  }
  
  .step-info {
    padding-right: 0;
  }
  
  .step-media {
    aspect-ratio: 4/3;
  }
  
  .flow-step {
    padding: 4rem 0;
  }

  .pillars {
    padding: 4rem 0 5rem;
  }
  
  .pillar-grid {
    grid-template-columns: 1fr;
    gap: 4rem;
  }
  
  .pillar-card {
    padding-top: 1.5rem;
  }
  
  .pillar-header {
    margin-bottom: 1.5rem;
  }
}

@media (max-width: 1200px) {
  .hero {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    min-height: 0;
  }

  .hero-title {
    font-size: clamp(2.8rem, 5.6vw, 4.2rem);
  }

  .hero-desc {
    font-size: 1.02rem;
    max-width: 42ch;
  }

  .discover-magazine,
  .discover-arrivals {
    min-height: clamp(480px, 65vh, 640px);
  }
}
</style>
