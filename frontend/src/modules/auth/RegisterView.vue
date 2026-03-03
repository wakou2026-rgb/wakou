<script setup>
import { computed, onUnmounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "./store";
import { useI18n } from "vue-i18n";

const router = useRouter();
const store = useAuthStore();
const { t } = useI18n();

const form = reactive({
  email: "",
  password: "",
  role: "buyer",
  verification_code: ""
});

const statusText = ref("");
const isError = ref(false);
const codeCooldown = ref(0);
const canSubmit = computed(() => /^\d{6}$/.test(form.verification_code));

let cooldownTimer = null;

function normalizeVerificationCode() {
  form.verification_code = form.verification_code
    .normalize("NFKC")
    .replace(/\D/g, "")
    .slice(0, 6);
}

function onVerificationCodePaste(event) {
  const raw = event.clipboardData?.getData("text") || "";
  const normalized = raw.normalize("NFKC").replace(/\D/g, "").slice(0, 6);
  if (!normalized) {
    return;
  }
  event.preventDefault();
  form.verification_code = normalized;
}

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer);
    cooldownTimer = null;
  }
});

function startCooldown(seconds) {
  codeCooldown.value = Number(seconds) || 60;
  if (cooldownTimer) {
    clearInterval(cooldownTimer);
  }
  cooldownTimer = setInterval(() => {
    codeCooldown.value -= 1;
    if (codeCooldown.value <= 0) {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
      codeCooldown.value = 0;
    }
  }, 1000);
}

async function requestCode() {
  isError.value = false;
  statusText.value = "";
  if (!form.email) {
    isError.value = true;
    statusText.value = t('auth.email_required');
    return;
  }
  try {
    const result = await store.requestRegisterCode({ email: form.email });
    startCooldown(result.cooldown_seconds || 60);
    statusText.value = t('auth.code_sent');
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : t('auth.request_code_failed');
  }
}

async function submitRegister() {
  isError.value = false;
  statusText.value = "";
  normalizeVerificationCode();
  if (!/^\d{6}$/.test(form.verification_code)) {
    isError.value = true;
    statusText.value = t("auth.code_format_invalid");
    return;
  }
  try {
    await store.register(form);
    statusText.value = t('auth.register_success');
    setTimeout(() => {
      router.push("/login");
    }, 1500);
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : t('auth.register_failed');
  }
}
</script>

<template>
  <div class="auth-page container">
    <div class="auth-container">
      <header class="auth-header">
        <p class="eyebrow">{{ $t('auth.register_eyebrow') }}</p>
        <h2 class="page-title">{{ $t('auth.register_title') }}</h2>
      </header>
      
      <form class="auth-form panel" @submit.prevent="submitRegister">
        <div class="form-group">
          <label for="reg-email">{{ $t('auth.email_label') }}</label>
          <input 
            id="reg-email"
            v-model="form.email" 
            class="field" 
            type="email" 
            :placeholder="$t('auth.email_placeholder')"
            :aria-label="$t('auth.email_label')"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="reg-password">{{ $t('auth.password_label') }}</label>
          <input 
            id="reg-password"
            v-model="form.password" 
            class="field" 
            type="password" 
            :placeholder="$t('auth.password_placeholder')"
            :aria-label="$t('auth.password_label')"
            required
          />
        </div>

        <div class="form-group">
          <label for="verification-code">{{ $t('auth.verify_code_label') }}</label>
          <div class="code-row">
            <input
              id="verification-code"
              v-model="form.verification_code"
              class="field"
              type="text"
              inputmode="numeric"
              maxlength="6"
              :placeholder="$t('auth.code_placeholder')"
              :aria-label="$t('auth.verify_code_label')"
              @input="normalizeVerificationCode"
              @paste="onVerificationCodePaste"
              required
            />
            <button
              class="btn btn-secondary code-btn"
              type="button"
              :disabled="codeCooldown > 0"
              :aria-label="$t('auth.request_code')"
              @click="requestCode"
            >
              {{ codeCooldown > 0 ? $t('auth.resend_countdown', { seconds: codeCooldown }) : $t('auth.request_code') }}
            </button>
          </div>
        </div>

        <button class="btn btn-primary submit-btn" type="submit" :disabled="!canSubmit" :aria-label="$t('auth.register_btn')">{{ $t('auth.register_btn') }}</button>
        
        <div class="auth-footer">
          <p v-if="statusText" :class="isError ? 'status-err' : 'status-ok'">
            {{ statusText }}
          </p>
          <p v-else class="register-prompt">
            {{ $t('auth.already_account') }} <RouterLink to="/login">{{ $t('auth.login_title') }}</RouterLink>
          </p>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  align-items: center;
  display: flex;
  justify-content: center;
  min-height: 60vh;
}

.auth-container {
  width: 100%;
  max-width: 500px;
}

.auth-header {
  margin-bottom: 3rem;
  text-align: center;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
  padding: 3rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  color: var(--ink-500);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.select-styled {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%233E3B36' stroke-width='1.5' stroke-linecap='square' stroke-linejoin='miter'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-position: right 0 center;
  background-repeat: no-repeat;
  cursor: pointer;
  padding-right: 1.5rem;
}

.submit-btn {
  margin-top: 1rem;
  width: 100%;
}

.submit-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.code-row {
  display: grid;
  gap: 0.6rem;
  grid-template-columns: 1fr auto;
}

.code-btn {
  min-width: 124px;
  white-space: nowrap;
}

.auth-footer {
  margin-top: 0.5rem;
  text-align: center;
}

.register-prompt {
  color: var(--ink-500);
  font-size: 0.9rem;
  margin: 0;
}

.register-prompt a {
  color: var(--ink-900);
  font-weight: 500;
  text-decoration: underline;
  text-underline-offset: 4px;
}

.register-prompt a:hover {
  color: var(--accent-700);
}

@media (max-width: 760px) {
  .auth-form {
    padding: 2.5rem 1.5rem;
  }
}
</style>
