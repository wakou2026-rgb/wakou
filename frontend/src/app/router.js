import { createRouter, createWebHistory } from "vue-router";

import HomeView from "./views/HomeView.vue";
import LoginView from "../modules/auth/LoginView.vue";
import RegisterView from "../modules/auth/RegisterView.vue";
import ForgotPasswordView from "../modules/auth/ForgotPasswordView.vue";
import ResetPasswordView from "../modules/auth/ResetPasswordView.vue";
import ChangePasswordView from "../modules/auth/ChangePasswordView.vue";
import CatalogView from "./views/CatalogView.vue";
import CartView from "./views/CartView.vue";
import CheckoutView from "./views/CheckoutView.vue";
import CommRoomView from "./views/CommRoomView.vue";
import DashboardView from "./views/DashboardView.vue";
import AccountSectionView from "./views/AccountSectionView.vue";
import ProductDetailView from "./views/ProductDetailView.vue";
import AboutView from "./views/AboutView.vue";
import ContactView from "./views/ContactView.vue";
import CollectionView from "./views/CollectionView.vue";
import MagazineView from "./views/MagazineView.vue";
import MagazineDetailView from "./views/MagazineDetailView.vue";
import LedgerView from "../modules/admin/LedgerView.vue";


export const routes = [
  { path: "/", component: HomeView },
  { path: "/login", component: LoginView },
  { path: "/register", component: RegisterView },
  { path: "/forgot-password", component: ForgotPasswordView },
  { path: "/reset-password", component: ResetPasswordView },
  { path: "/change-password", component: ChangePasswordView },
  { path: "/catalog", component: CatalogView },
  { path: "/collections", component: CollectionView, meta: { title: "Collections" } },
  { path: "/catalog/:id", component: ProductDetailView },
  { path: "/cart", component: CartView },
  { path: "/checkout", component: CheckoutView },
  { path: "/comm-room/:id", component: CommRoomView },
  { path: "/dashboard", component: DashboardView, meta: { title: "Account Center" } },
  { path: "/dashboard/:section(timeline|rooms|orders|messages|points|coupons|gacha|wishlist)", component: AccountSectionView, meta: { title: "Account Detail" } },
  { path: "/magazine", component: MagazineView, meta: { title: "Magazine" } },
  { path: "/magazine/:id(.*)", component: MagazineDetailView },
  { path: "/about", component: AboutView },
  { path: "/contact", component: ContactView, meta: { title: "Contact" } },
  { path: "/warehouse", redirect: "/dashboard/timeline" },
  { path: "/admin/ledger", component: LedgerView, meta: { requiresAdmin: true, title: "商品帳本" } },
  
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to) => {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("wakou_access_token") || "" : "";
  const role = typeof window !== "undefined" ? window.localStorage.getItem("wakou_role") || "buyer" : "buyer";
  const cartRaw = typeof window !== "undefined" ? window.localStorage.getItem("wakou_cart_lines") || "[]" : "[]";
  let cartLines = [];
  try {
    const parsed = JSON.parse(cartRaw);
    cartLines = Array.isArray(parsed) ? parsed : [];
  } catch {
    cartLines = [];
  }
  if (to.meta?.requiresAdmin && !token) {
    return { path: "/login" };
  }
  if (to.meta?.requiresAdmin && !["admin", "super_admin", "sales", "maintenance"].includes(role)) {
    return { path: "/dashboard" };
  }
  if (to.path.startsWith("/comm-room/") && to.query.from !== "dashboard" && to.query.from !== "admin") {
    return { path: "/dashboard", query: { focus: "conversations" } };
  }
  if (to.path === "/checkout" && cartLines.length === 0) {
    return { path: "/cart" };
  }
  return true;
});

export default router;
