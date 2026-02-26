<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const collections = ref([]);
const isLoading = ref(true);
const fallbackImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='1000' viewBox='0 0 800 1000'%3E%3Crect width='800' height='1000' fill='%23ebe9e4'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' fill='%238c7b6c' font-family='serif' font-size='34' letter-spacing='2'%3EIMAGE UNAVAILABLE%3C/text%3E%3C/svg%3E";

async function loadCategories() {
  // We fetch real dynamic categories from backend instead of hardcoding
  try {
    const res = await fetch("/api/v1/categories");
    if (res.ok) {
      const data = await res.json();
      collections.value = data.items || [];
    }
  } catch (err) {
    console.error(err);
  } finally {
    isLoading.value = false;
  }
}

function goTo(categoryId) {
  router.push(`/catalog?cat=${categoryId}`);
}

function onImageError(event) {
  const img = event?.target;
  if (!img || img.dataset.fallbackApplied === "1") {
    return;
  }
  img.dataset.fallbackApplied = "1";
  img.src = fallbackImage;
}

onMounted(loadCategories);
</script>

<template>
  <div class="collection-page container">
    <div v-if="isLoading" class="loading-state">載入中...</div>
    
    <div v-else class="collection-grid">
      <section v-for="col in collections" :key="col.id" class="collection-block" @click="goTo(col.id)">
        <div class="col-visual">
          <img :src="col.image" :alt="col.title" class="col-img" loading="lazy" @error="onImageError" />
          <div class="overlay">
            <div class="overlay-content">
              <span class="hover-text">{{ col.title }}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.collection-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 4rem 1rem 8rem;
}

.loading-state {
  text-align: center;
  color: var(--ink-500);
  padding: 4rem;
}

.collection-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2.5rem 1.5rem;
}

.collection-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.col-visual {
  width: 100%;
  position: relative;
  overflow: hidden;
  background: var(--paper-100);
}

.col-img {
  width: 100%;
  height: auto;
  aspect-ratio: 4 / 5;
  object-fit: cover;
  display: block;
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.col-visual:hover .overlay {
  opacity: 1;
}

.overlay-content {
  color: white;
}

.hover-text {
  font-family: var(--font-serif);
  font-size: 1.6rem;
  letter-spacing: 0.15em;
}

@media (max-width: 900px) {
  .collection-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .collection-grid {
    grid-template-columns: 1fr;
  }
}
</style>
