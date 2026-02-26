<template>
  <div class="layout" :class="isLoggedIn ? 'state-member' : 'state-guest'">
    <header class="masthead">
      <div class="container masthead-inner">
        <!-- Brand -->
        <RouterLink to="/" class="brand">
          <img src="/logo-transparent.png" alt="Wakou Vintage Select" class="brand-logo" />
          <span class="brand-en">WAKOU VINTAGE SELECT</span>
        </RouterLink>

        <!-- Navigation Desktop -->
        <nav class="nav-main">
          <RouterLink to="/collections">{{ $t("nav.catalog") }}</RouterLink>
          <RouterLink to="/magazine">專欄企劃</RouterLink>
          <RouterLink to="/about">{{ $t("nav.about") }}</RouterLink>
          <RouterLink :to="isLoggedIn ? '/dashboard' : '/login'">{{ $t("nav.dashboard") }}</RouterLink>
          <RouterLink v-if="isAdminRole" to="/admin">管理控制台</RouterLink>
          <RouterLink v-if="!isLoggedIn" to="/login">{{ $t("nav.login") }}</RouterLink>
          <button v-else class="logout-btn" @click="handleLogout">{{ $t("nav.logout") || "Logout" }}</button>
        </nav>

        <!-- Tools -->
        <div class="nav-tools">
          <RouterLink v-if="isLoggedIn" to="/dashboard" class="user-chip user-chip-member" aria-label="會員後台">
            <span class="chip-dot" aria-hidden="true"></span>
            <span>{{ accountLabel }}</span>
            <span v-if="roleBadgeText" class="role-badge">{{ roleBadgeText }}</span>
          </RouterLink>
          <RouterLink v-else to="/login" class="user-chip user-chip-guest">會員登入</RouterLink>
          <RouterLink to="/cart" class="cart-icon-link" :aria-label="$t('nav.cart')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M7 18c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2Zm10 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2ZM7.2 14h9.8c.75 0 1.4-.42 1.72-1.04L22 6.5H6.17L5.27 4H2v2h1.93l2.39 8.01L5.42 16c-.08.2-.12.41-.12.63 0 .76.61 1.37 1.37 1.37H21v-2H7.04l.16-.36Z" />
            </svg>
            <span v-if="cartCount > 0" class="cart-badge">{{ cartCount }}</span>
          </RouterLink>
          <button v-if="isLoggedIn" class="bell-icon-link" type="button" aria-label="通知" @click="clearNotifAndGo">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2Zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2Z" />
            </svg>
            <span v-if="notificationCount > 0" class="bell-badge">{{ notificationCount }}</span>
          </button>
          <button class="lang-toggle" :class="{ active: locale === 'zh-Hant' }" @click="setLocale('zh-Hant')">繁</button>
          <span class="lang-sep">/</span>
          <button class="lang-toggle" :class="{ active: locale === 'ja' }" @click="setLocale('ja')">日</button>
          <span class="lang-sep">/</span>
          <button class="lang-toggle" :class="{ active: locale === 'en' }" @click="setLocale('en')">EN</button>
        </div>
      </div>
    </header>

    <!-- Navigation Mobile -->
    <nav class="nav-mobile container">
      <RouterLink to="/collections">{{ $t("nav.catalog") }}</RouterLink>
      <RouterLink to="/magazine">專欄企劃</RouterLink>
      <RouterLink to="/about">{{ $t("nav.about") }}</RouterLink>
      <RouterLink :to="isLoggedIn ? '/dashboard' : '/login'">{{ $t("nav.dashboard") }}</RouterLink>
      <RouterLink v-if="isAdminRole" to="/admin">管理</RouterLink>
    </nav>

    <main class="main-content">
      <RouterView />
    </main>
    
    <footer class="footer">
      <div class="container footer-inner">
        <div class="footer-links">
          <p class="copyright">&copy; 2026 Wakou Vintage Select. Digital Artisan Blueprint.</p>
          <div class="social-row">
            <a
              class="social-link"
              href="https://www.instagram.com/"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Instagram"
              title="Instagram"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M7.5 2h9A5.5 5.5 0 0 1 22 7.5v9a5.5 5.5 0 0 1-5.5 5.5h-9A5.5 5.5 0 0 1 2 16.5v-9A5.5 5.5 0 0 1 7.5 2Zm0 2A3.5 3.5 0 0 0 4 7.5v9A3.5 3.5 0 0 0 7.5 20h9a3.5 3.5 0 0 0 3.5-3.5v-9A3.5 3.5 0 0 0 16.5 4h-9Zm10.75 1.5a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5ZM12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10Zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" />
              </svg>
            </a>
            <a
              class="social-link"
              href="https://www.youtube.com/"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="YouTube"
              title="YouTube"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M23 12c0 1.96-.2 3.41-.57 4.61-.34 1.11-1.21 1.98-2.32 2.32C18.91 19.8 17.46 20 15.5 20h-7c-1.96 0-3.41-.2-4.61-.57-1.11-.34-1.98-1.21-2.32-2.32C1.2 15.41 1 13.96 1 12s.2-3.41.57-4.61c.34-1.11 1.21-1.98 2.32-2.32C5.09 4.2 6.54 4 8.5 4h7c1.96 0 3.41.2 4.61.57 1.11.34 1.98 1.21 2.32 2.32.37 1.2.57 2.65.57 4.61Zm-13-3.22v6.44L15.5 12 10 8.78Z" />
              </svg>
            </a>
          </div>
          <RouterLink to="/contact" class="contact-link">聯絡我們</RouterLink>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "./modules/auth/store";
import { getCartItems } from "./modules/cart/service";
import { shouldClearUnreadOnRoute } from "./modules/account/membership";

const { locale } = useI18n();
const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();
const adminRoles = new Set(["admin", "super_admin", "sales", "maintenance"]);

const isLoggedIn = computed(() => authStore.isLoggedIn);
const isAdminRole = computed(() => adminRoles.has(authStore.role));
const roleBadgeText = computed(() => {
  if (!isLoggedIn.value) {
    return "";
  }
  const roleMap = {
    admin: "ADMIN",
    super_admin: "ROOT",
    sales: "SALES",
    maintenance: "MAINT"
  };
  return roleMap[authStore.role] || "";
});
const accountLabel = computed(() => {
  if (!isLoggedIn.value) {
    return "訪客";
  }
  if (authStore.displayName) {
    return authStore.displayName;
  }
  const roleLabel = {
    admin: "管理員",
    super_admin: "總管理員",
    sales: "銷售",
    maintenance: "維護",
    buyer: "會員"
  };
  return roleLabel[authStore.role] || "會員";
});
const cartCount = ref(0);
const notificationCount = ref(0);

function syncCartCount() {
  cartCount.value = getCartItems().reduce((sum, line) => sum + (line.qty || 0), 0);
  const raw = typeof window !== "undefined" ? window.localStorage.getItem("wakou_unread_count") || "0" : "0";
  notificationCount.value = Number(raw) || 0;
}

function clearUnreadBadgeLocal() {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("wakou_unread_count", "0");
  }
  notificationCount.value = 0;
}

function clearNotifAndGo() {
  clearUnreadBadgeLocal();
  router.push("/dashboard/messages");
}

function setLocale(nextLocale) {
  locale.value = nextLocale;
}

function handleLogout() {
  authStore.logout();
  router.push("/");
}

onMounted(() => {
  syncCartCount();
  if (shouldClearUnreadOnRoute(route.fullPath)) {
    clearUnreadBadgeLocal();
  }
  window.addEventListener("storage", syncCartCount);
  window.addEventListener("focus", syncCartCount);
});

onBeforeUnmount(() => {
  window.removeEventListener("storage", syncCartCount);
  window.removeEventListener("focus", syncCartCount);
});

watch(
  () => route.fullPath,
  (path) => {
    syncCartCount();
    if (shouldClearUnreadOnRoute(path)) {
      clearUnreadBadgeLocal();
    }
  }
);
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.masthead {
  border-bottom: 1px solid var(--paper-200);
  padding: 1.2rem 0;
}

.layout.state-member .masthead {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0));
}

.layout.state-guest .masthead {
  background: transparent;
}

.masthead-inner {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

/* Brand */
.brand {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.7rem;
  margin-right: auto; /* Push nav to the right */
}

.brand-logo {
  display: block;
  height: 42px;
  width: auto;
}

.brand-en {
  color: var(--ink-500);
  font-size: 0.52rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

/* Nav Main */
.nav-main {
  display: flex;
  gap: 1.4rem;
  margin-right: 1.2rem;
}

.nav-main a, .logout-btn {
  background: transparent;
  border: none;
  color: var(--ink-500);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  padding: 0 0 0.5rem 0;
  position: relative;
  text-transform: uppercase;
  transition: color 0.3s ease;
  white-space: nowrap;
}

.nav-main a::after, .logout-btn::after {
  background: var(--ink-900);
  bottom: 0;
  content: "";
  height: 1px;
  left: 0;
  position: absolute;
  transform: scaleX(0);
  transform-origin: right;
  transition: transform 0.4s cubic-bezier(0.19, 1, 0.22, 1);
  width: 100%;
}

.nav-main a:hover,
.nav-main a.router-link-active,
.logout-btn:hover {
  color: var(--ink-900);
}

.nav-main a:hover::after,
.nav-main a.router-link-active::after,
.logout-btn:hover::after {
  transform: scaleX(1);
  transform-origin: left;
}

.nav-mobile {
  display: none;
}

/* Nav Tools */
.nav-tools {
  align-items: center;
  display: flex;
  gap: 0.55rem;
  padding-bottom: 0.5rem;
}

.user-chip {
  border: 1px solid var(--paper-300);
  color: var(--ink-700);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.7rem;
  min-width: 84px;
  max-width: 130px;
  overflow: hidden;
  padding: 0.2rem 0.55rem;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-chip-member {
  background: rgba(255, 255, 255, 0.56);
}

.user-chip-guest {
  border-color: var(--ink-300);
  color: var(--ink-600);
}

.chip-dot {
  background: var(--ok-500);
  border-radius: 999px;
  display: inline-block;
  flex-shrink: 0;
  height: 0.42rem;
  width: 0.42rem;
}

.role-badge {
  border: 1px solid var(--ink-300);
  font-size: 0.56rem;
  letter-spacing: 0.08em;
  line-height: 1;
  padding: 0.16rem 0.24rem;
}

.cart-icon-link {
  align-items: center;
  color: var(--ink-700);
  display: inline-flex;
  height: 1.8rem;
  justify-content: center;
  margin-right: 0.5rem;
  position: relative;
  width: 1.8rem;
}

.cart-icon-link svg {
  fill: currentColor;
  height: 1.3rem;
  width: 1.3rem;
}

.cart-badge {
  align-items: center;
  background: var(--ink-900);
  border-radius: 999px;
  color: var(--paper-50);
  display: inline-flex;
  font-size: 0.62rem;
  height: 1rem;
  justify-content: center;
  min-width: 1rem;
  padding: 0 0.2rem;
  position: absolute;
  right: -0.35rem;
  top: -0.25rem;
}

.bell-icon-link {
  align-items: center;
  background: transparent;
  border: 0;
  color: var(--ink-700);
  cursor: pointer;
  display: inline-flex;
  height: 1.8rem;
  justify-content: center;
  position: relative;
  width: 1.8rem;
}

.bell-icon-link svg {
  fill: currentColor;
  height: 1.3rem;
  width: 1.3rem;
}

.bell-badge {
  align-items: center;
  background: var(--ink-900);
  border-radius: 999px;
  color: var(--paper-50);
  display: inline-flex;
  font-size: 0.62rem;
  height: 1rem;
  justify-content: center;
  min-width: 1rem;
  padding: 0 0.2rem;
  position: absolute;
  right: -0.35rem;
  top: -0.25rem;
}

.lang-toggle {
  background: transparent;
  border: none;
  color: var(--ink-300);
  cursor: pointer;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  padding: 0;
  transition: color 0.3s;
}

.lang-toggle:hover {
  color: var(--ink-700);
}

.lang-toggle.active {
  color: var(--ink-900);
  font-weight: 600;
}

.lang-sep {
  color: var(--paper-300);
  font-size: 0.8rem;
}

/* Main Content */
.main-content {
  flex: 1;
  padding: 4rem 0 8rem;
  width: 100%;
}

/* Footer */
.footer {
  border-top: 1px solid var(--paper-200);
  padding: 4rem 0;
}

.footer-inner {
  display: flex;
  justify-content: flex-end;
}

.footer-links {
  align-items: flex-end;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.social-row {
  display: flex;
  gap: 0.4rem;
}

.copyright {
  color: var(--ink-500);
  font-size: 0.8rem;
  letter-spacing: 0.05em;
  margin: 0;
}

.contact-link {
  color: var(--ink-300);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.contact-link:hover {
  color: var(--ink-700);
}

.social-link {
  align-items: center;
  color: var(--ink-400);
  display: inline-flex;
  height: 1.7rem;
  justify-content: center;
  transition: color 0.2s ease;
  width: 1.7rem;
}

.social-link:hover {
  color: var(--ink-700);
}

.social-link svg {
  fill: currentColor;
  height: 1.05rem;
  width: 1.05rem;
}

@media (max-width: 900px) {
  .masthead {
    padding: 2rem 0 0;
  }

  .brand-logo {
    height: 36px;
  }
  
  .masthead-inner {
    align-items: center;
    margin-bottom: 1.5rem;
  }
  
  .nav-main {
    display: none;
  }
  
  .nav-mobile {
    border-top: 1px solid var(--paper-200);
    display: flex;
    gap: 1.5rem;
    overflow-x: auto;
    padding-bottom: 1rem;
    padding-top: 1.5rem;
    white-space: nowrap;
  }
  
  .nav-mobile a {
    color: var(--ink-700);
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  
  .nav-mobile a.router-link-active {
    color: var(--ink-900);
    font-weight: 600;
  }
  
  .footer-inner {
    flex-direction: column;
    gap: 2rem;
  }
  
  .footer-links {
    align-items: flex-start;
  }
}
</style>
