import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./app/router";
import i18n from "./i18n";
import "./styles.css";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

if (apiBaseUrl && typeof window !== "undefined" && typeof window.fetch === "function") {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    if (typeof input === "string" && input.startsWith("/api/")) {
      return nativeFetch(`${apiBaseUrl}${input}`, init);
    }

    if (input instanceof Request && input.url.startsWith("/api/")) {
      const proxiedRequest = new Request(`${apiBaseUrl}${input.url}`, input);
      return nativeFetch(proxiedRequest, init);
    }

    return nativeFetch(input, init);
  };
}

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(i18n);

app.mount("#app");
