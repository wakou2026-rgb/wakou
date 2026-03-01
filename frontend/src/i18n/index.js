import { createI18n } from "vue-i18n";
import { messages } from "./messages";

const _stored = typeof window !== "undefined" ? window.localStorage.getItem("wakou_locale") : null;
const _validLocales = ["zh-Hant", "ja", "en"];
const _initLocale = _validLocales.includes(_stored) ? _stored : "zh-Hant";

const i18n = createI18n({
  legacy: false,
  locale: _initLocale,
  fallbackLocale: "en",
  messages
});

export default i18n;
