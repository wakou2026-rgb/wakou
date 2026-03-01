import { defineStore } from "pinia";
import { loginRequest, registerRequest } from "./api";

function getStorage() {
  if (typeof window === "undefined") {
    return {
      getItem() {
        return "";
      },
      setItem() {},
      removeItem() {}
    };
  }
  return window.localStorage;
}

const storage = getStorage();

function roleFallbackDisplayName(role) {
  const roleMap = {
    admin: "管理員",
    super_admin: "總管理員",
    sales: "銷售",
    maintenance: "維護",
    buyer: "會員"
  };
  return roleMap[role] || "會員";
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: storage.getItem("wakou_access_token") || "",
    refreshToken: storage.getItem("wakou_refresh_token") || "",
    email: storage.getItem("wakou_email") || "",
    displayName: storage.getItem("wakou_display_name") || "",
    role: storage.getItem("wakou_role") || "buyer"
  }),
  getters: {
    isLoggedIn(state) {
      return Boolean(state.accessToken);
    }
  },
  actions: {
    async register(payload) {
      await registerRequest(payload);
    },
    async login(credentials, router) {
      const result = await loginRequest(credentials);
      this.accessToken = result.access_token;
      this.refreshToken = result.refresh_token;
      this.email = result.email;
      this.role = result.role;
      this.displayName = result.display_name || roleFallbackDisplayName(this.role);
      storage.setItem("wakou_access_token", this.accessToken);
      storage.setItem("wakou_refresh_token", this.refreshToken);
      storage.setItem("wakou_email", this.email);
      storage.setItem("wakou_display_name", this.displayName);
      storage.setItem("wakou_role", this.role);
      if (router && typeof router.push === "function") {
        await router.push("/");
      }
    },
    logout() {
      this.accessToken = "";
      this.refreshToken = "";
      this.email = "";
      this.displayName = "";
      this.role = "buyer";
      storage.removeItem("wakou_access_token");
      storage.removeItem("wakou_refresh_token");
      storage.removeItem("wakou_email");
      storage.removeItem("wakou_display_name");
      storage.removeItem("wakou_role");
    },
    setDisplayName(nextName) {
      this.displayName = nextName;
      storage.setItem("wakou_display_name", this.displayName);
    },
    async refreshTokens() {
      const rt = this.refreshToken;
      if (!rt) return false;
      try {
        const response = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt })
        });
        if (!response.ok) {
          this.logout();
          return false;
        }
        const data = await response.json();
        this.accessToken = data.access_token;
        storage.setItem("wakou_access_token", this.accessToken);
        return true;
      } catch {
        return false;
      }
    }
  }
});
