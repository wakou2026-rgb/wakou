<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { fetchProductDetail } from "../../modules/catalog/service";
import { useAuthStore } from "../../modules/auth/store";
import { addCartItem } from "../../modules/cart/service";
import { createOrder } from "../../modules/checkout/service";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { t, locale } = useI18n();

const item = ref(null);
const loading = ref(true);
const isError = ref(false);
const statusText = ref("");
const selectedPhoto = ref(0);
const showConfirmModal = ref(false);
const isProcessing = ref(false);

const photos = computed(() => {
  if (!item.value) {
    return [];
  }
  const urls = item.value.imageUrls || [];
  if (urls.length === 0) {
    return ["/logo-transparent.png"];
  }
  return urls;
});

async function loadDetail() {
  loading.value = true;
  isError.value = false;
  statusText.value = "";
  try {
    const productId = route.params.id;
    item.value = await fetchProductDetail(productId, { lang: locale.value });
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "load detail failed";
  } finally {
    loading.value = false;
  }
}

onMounted(loadDetail);

watch(locale, () => {
  loadDetail();
});

function localizeField(val) {
  const l = locale.value || "zh-Hant";
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

function addToCart() {
  if (!item.value) {
    return;
  }
  addCartItem(item.value);
  statusText.value = t("product.added_cart");
}

function promptInquiryOrder() {
  if (!authStore.isLoggedIn) {
    router.push("/login");
    return;
  }
  showConfirmModal.value = true;
}

async function confirmOrder() {
  if (!item.value || isProcessing.value) {
    return;
  }
  isProcessing.value = true;
  isError.value = false;
  try {
    const created = await createOrder({ product_id: item.value.id, mode: "inquiry" });
    const commRoomId = Number(created?.comm_room_id ?? created?.commRoomId ?? 0);
    if (!Number.isInteger(commRoomId) || commRoomId <= 0) {
      throw new Error("create order succeeded but missing comm room id");
    }
    // Don't hide modal until after successful creation to prevent flashes, 
    // but the router push will unmount us anyway.
    await router.push(`/comm-room/${commRoomId}?from=dashboard`);
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "create order failed";
    isProcessing.value = false;
    showConfirmModal.value = false;
  }
}
</script>

<template>
  <div class="detail container">
    <div v-if="loading" class="state-msg">Loading detail...</div>
    <div v-else-if="isError && !item" class="state-msg error">{{ statusText }}</div>

    <div v-else-if="item" class="detail-grid">
      <section class="gallery">
        <div class="hero img-frame">
          <img :src="photos[selectedPhoto]" :alt="item.name" />
        </div>
        <div class="thumbs">
          <button
            v-for="(photo, index) in photos"
            :key="photo"
            class="thumb"
            :class="{ active: selectedPhoto === index }"
            @click="selectedPhoto = index"
          >
            <img :src="photo" :alt="`${item.name} ${index + 1}`" />
          </button>
        </div>
      </section>

      <section class="summary panel">
        <p class="eyebrow">Product Detail</p>
        <h1>{{ item.name }}</h1>
        <p class="meta">{{ item.sku }} ・ {{ localizeField(item.category) }} ・ Grade {{ item.grade }}</p>
        <p class="price">NT$ {{ item.priceTwd.toLocaleString() }}</p>
        <p class="desc">{{ item.description || $t('product.desc_fallback') }}</p>

        <div class="actions">
          <button class="btn btn-primary" @click="promptInquiryOrder">{{ $t('product.inquiry_btn') }}</button>
          <button class="btn btn-muted" @click="addToCart">{{ $t('product.add_cart') }}</button>
        </div>

        <p v-if="statusText" class="status-msg" :class="isError ? 'status-err' : 'status-ok'">{{ statusText }}</p>
      </section>
    </div>

    <!-- Confirm Modal -->
    <div v-if="showConfirmModal" class="modal-overlay" @click="showConfirmModal = false">
      <div class="modal-content" @click.stop>
        <h3 style="margin-top:0;">{{ $t('product.modal_title') }}</h3>
        <p>{{ $t('product.modal_body') }}</p>
        <div class="modal-actions" style="margin-top: 1.5rem; display: flex; gap: 0.8rem; justify-content: flex-end;">
          <button class="btn btn-muted" @click="showConfirmModal = false" :disabled="isProcessing">{{ $t('product.cancel') }}</button>
          <button class="btn btn-primary" @click="confirmOrder" :disabled="isProcessing">{{ isProcessing ? $t('product.processing') : $t('product.confirm') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-grid {
  display: grid;
  gap: 2rem;
  grid-template-columns: 3fr 2fr;
}

.hero {
  aspect-ratio: 11/8;
}

.thumbs {
  display: grid;
  gap: 0.8rem;
  grid-template-columns: repeat(4, 1fr);
  margin-top: 0.8rem;
}

.thumb {
  background: transparent;
  border: 1px solid var(--paper-300);
  cursor: pointer;
  padding: 0;
}

.thumb.active {
  border-color: var(--ink-900);
}

.thumb img {
  display: block;
  width: 100%;
}

.summary h1 {
  margin-bottom: 0.8rem;
}

.meta {
  color: var(--ink-500);
  margin-bottom: 0.6rem;
}

.price {
  font-size: 1.6rem;
  margin-bottom: 1.2rem;
}

.actions {
  display: flex;
  gap: 0.8rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-content {
  background: #fff;
  padding: 2rem;
  max-width: 480px;
  width: 90%;
  border: 1px solid var(--paper-300);
  box-shadow: 0 16px 34px -28px rgba(44, 42, 38, 0.35);
}

@media (max-width: 900px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .actions {
    flex-direction: column;
  }
}
</style>
