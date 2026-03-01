<script setup>
import { computed, ref } from "vue";
import { getCartItems, removeCartItem, updateCartQty } from "../../modules/cart/service";
import { useI18n } from "vue-i18n";

const lines = ref(getCartItems());
const { t } = useI18n();

const total = computed(() =>
  lines.value.reduce((sum, item) => sum + Number(item.priceTwd || 0) * Number(item.qty || 1), 0)
);

function changeQty(itemId, nextQty) {
  lines.value = updateCartQty(itemId, Number(nextQty));
}

function removeLine(itemId) {
  lines.value = removeCartItem(itemId);
}
</script>

<template>
  <div class="cart-page container">
    <header class="page-header">
      <p class="eyebrow">Your Selection</p>
      <h1 class="page-title">{{ $t("nav.cart") }}</h1>
    </header>

    <div class="divider"></div>

    <div v-if="lines.length === 0" class="empty-state">
      <p>{{ $t('cart.empty') }}</p>
      <RouterLink class="btn btn-primary" to="/collections">{{ $t('cart.return_gallery') }}</RouterLink>
    </div>

    <div v-else class="cart-layout">
      <!-- List -->
      <div class="cart-list">
        <article v-for="item in lines" :key="item.id" class="cart-item">
          <div class="item-visual img-frame">
             <img :src="item.imageUrls?.[0] || '/logo-transparent.png'" :alt="item.name" />
          </div>
          
          <div class="item-details">
            <div class="item-meta">
              <span class="sku">{{ item.sku }}</span>
              <h3 class="name">{{ item.name }}</h3>
              <p class="price">NT$ {{ Number(item.priceTwd).toLocaleString() }}</p>
            </div>
            
            <div class="item-actions">
              <div class="qty-control">
                <label class="sr-only">Quantity</label>
                <input
                  class="field qty-input"
                  type="number"
                  min="1"
                  :value="item.qty"
                  @input="changeQty(item.id, $event.target.value)"
                />
              </div>
              <button class="remove-btn" @click="removeLine(item.id)">
                {{ $t('cart.remove') }}
              </button>
            </div>
          </div>
        </article>
      </div>

      <!-- Summary Panel -->
      <aside class="cart-summary panel">
        <h3 class="summary-title">{{ $t('cart.summary_title') }}</h3>
        <div class="summary-row">
          <span>{{ $t('cart.subtotal') }}</span>
          <span>NT$ {{ total.toLocaleString() }}</span>
        </div>
        <div class="summary-row">
          <span>Shipping</span>
          <span>{{ $t('cart.shipping_tbd') }}</span>
        </div>
        <div class="summary-total">
          <span>{{ $t('cart.total') }}</span>
          <span>NT$ {{ total.toLocaleString() }}</span>
        </div>
        <RouterLink class="btn btn-primary w-full" to="/checkout">{{ $t('cart.proceed_checkout') }}</RouterLink>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 2rem;
}

.empty-state {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 3rem;
  padding: 6rem 0;
}

.empty-state p {
  color: var(--ink-700);
  font-family: var(--font-serif);
  font-size: 1.3rem;
  letter-spacing: 0.05em;
  margin: 0;
}

.cart-layout {
  align-items: flex-start;
  display: grid;
  gap: 6rem;
  grid-template-columns: 1fr 400px;
  padding-bottom: 4rem;
}

.cart-list,
.cart-summary {
  background: rgba(255, 255, 255, 0.58);
  border: 1px solid var(--paper-200);
  box-shadow: 0 14px 34px -28px rgba(44, 42, 38, 0.45);
}

/* List */
.cart-list {
  display: flex;
  flex-direction: column;
  padding: 1.2rem 2rem;
}

.cart-item {
  border-bottom: 1px solid var(--paper-200);
  display: flex;
  gap: 3rem;
  padding: 3rem 0;
}

.cart-item:first-child {
  padding-top: 0;
}

.item-visual {
  aspect-ratio: 1;
  width: 140px;
}

.item-details {
  display: flex;
  flex: 1;
  justify-content: space-between;
}

.item-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sku {
  color: var(--ink-500);
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
  letter-spacing: 0.05em;
}

.name {
  font-size: 1.6rem;
  margin: 0 0 0.5rem;
}

.price {
  color: var(--ink-900);
  font-family: var(--font-serif);
  font-size: 1.1rem;
  margin: 0;
}

.item-actions {
  align-items: flex-end;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.qty-input {
  text-align: center;
  width: 60px;
}

.remove-btn {
  background: transparent;
  border: none;
  color: var(--ink-500);
  cursor: pointer;
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  padding: 0;
  text-transform: uppercase;
  transition: color 0.3s;
}

.remove-btn:hover {
  color: var(--danger-500);
}

/* Summary Panel */
.cart-summary {
  padding: 2.1rem;
}

.summary-title {
  border-bottom: 1px solid var(--paper-200);
  font-size: 1.4rem;
  margin: 0 0 2rem;
  padding-bottom: 1rem;
}

.summary-row {
  color: var(--ink-700);
  display: flex;
  font-size: 0.95rem;
  justify-content: space-between;
  margin-bottom: 1.2rem;
}

.calc-later {
  color: var(--ink-500);
  font-style: italic;
}

.summary-total {
  border-top: 1px solid var(--ink-900);
  display: flex;
  font-family: var(--font-serif);
  font-size: 1.3rem;
  justify-content: space-between;
  margin: 2.5rem 0 2.5rem;
  padding-top: 1.5rem;
}

.w-full {
  width: 100%;
}

@media (max-width: 900px) {
  .cart-layout {
    grid-template-columns: 1fr;
    gap: 4rem;
  }
  
  .item-details {
    flex-direction: column;
    gap: 2rem;
  }
  
  .item-actions {
    align-items: flex-start;
    flex-direction: row;
  }
}
</style>
