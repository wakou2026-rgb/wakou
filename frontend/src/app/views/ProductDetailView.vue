<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchProductDetail } from "../../modules/catalog/service";
import { useAuthStore } from "../../modules/auth/store";
import { addCartItem } from "../../modules/cart/service";
import { createOrder } from "../../modules/checkout/service";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

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
    item.value = await fetchProductDetail(productId);
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "load detail failed";
  } finally {
    loading.value = false;
  }
}

onMounted(loadDetail);

function addToCart() {
  if (!item.value) {
    return;
  }
  addCartItem(item.value);
  statusText.value = "已加入購物車";
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
        <p class="meta">{{ item.sku }} ・ {{ item.category }} ・ Grade {{ item.grade }}</p>
        <p class="price">NT$ {{ item.priceTwd.toLocaleString() }}</p>
        <p class="desc">{{ item.description || "此件藏品提供多角度細節照，實際成交前可於專屬諮詢室進一步確認品況、運費與出貨時程。" }}</p>

        <div class="actions">
          <button class="btn btn-primary" @click="promptInquiryOrder">發起諮詢並下單</button>
          <button class="btn btn-muted" @click="addToCart">加入購物車</button>
        </div>

        <p v-if="statusText" class="status-msg" :class="isError ? 'status-err' : 'status-ok'">{{ statusText }}</p>
      </section>
    </div>

    <!-- Confirm Modal -->
    <div v-if="showConfirmModal" class="modal-overlay" @click="showConfirmModal = false">
      <div class="modal-content" @click.stop>
        <h3 style="margin-top:0;">確認發起諮詢</h3>
        <p>此商品為手工/高價物件，將為您開啟專屬諮詢室確認細節（如運費、實物照）。<br><br>確認後即會建立專屬諮詢訂單。</p>
        <div class="modal-actions" style="margin-top: 1.5rem; display: flex; gap: 0.8rem; justify-content: flex-end;">
          <button class="btn btn-muted" @click="showConfirmModal = false" :disabled="isProcessing">取消</button>
          <button class="btn btn-primary" @click="confirmOrder" :disabled="isProcessing">{{ isProcessing ? '處理中...' : '確認發起' }}</button>
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
