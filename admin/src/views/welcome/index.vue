<script setup lang="ts">
defineOptions({
  name: "Welcome"
});
</script>

<template>
  <div class="welcome-page">
    <div class="welcome-hero">
      <p class="kicker">WAKOU VINTAGE SELECT</p>
      <h1>後台管理系統</h1>
      <p class="subtitle">管理商品、訂單、雜誌與財務報表</p>
      <a href="http://localhost/" target="_blank" rel="noopener" class="front-link">
        前往前台網站 →
      </a>
    </div>

    <div class="quick-links">
      <a href="/admin#/product" class="quick-card">
        <span class="quick-icon">🏷️</span>
        <span class="quick-label">商品管理</span>
      </a>
      <a href="/admin#/order" class="quick-card">
        <span class="quick-icon">📦</span>
        <span class="quick-label">訂單管理</span>
      </a>
      <a href="/admin#/magazine" class="quick-card">
        <span class="quick-icon">📖</span>
        <span class="quick-label">雜誌管理</span>
      </a>
      <a href="/admin#/finance" class="quick-card">
        <span class="quick-icon">📊</span>
        <span class="quick-label">財務報表</span>
      </a>
    </div>
  </div>
</template>

<style scoped>
.welcome-page {
  padding: 32px 24px;
  max-width: 800px;
}

.welcome-hero {
  margin-bottom: 36px;
}

.kicker {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.18em;
  color: #8c8c8c;
  font-weight: 500;
}

h1 {
  margin: 0 0 6px;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1.25;
}

.subtitle {
  margin: 0 0 20px;
  font-size: 14px;
  color: #595959;
}

.front-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  background: #409eff;
  color: #fff;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.18s, box-shadow 0.18s;
}

.front-link:hover {
  background: #337ecc;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35);
}

.quick-links {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.quick-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 12px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  text-decoration: none;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
  cursor: pointer;
}

.quick-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.15);
  transform: translateY(-2px);
}

.quick-icon {
  font-size: 28px;
}

.quick-label {
  font-size: 13px;
  font-weight: 500;
  color: #262626;
}

@media (max-width: 600px) {
  .quick-links {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
