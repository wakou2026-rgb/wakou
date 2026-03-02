<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { forgotPasswordRequest } from "./api";

const router = useRouter();
const { t } = useI18n();

const form = reactive({
  email: ""
});

const statusText = ref("");
const isError = ref(false);

async function submitForgot() {
  isError.value = false;
  statusText.value = "";
  try {
    await forgotPasswordRequest({ email: form.email });
    isError.value = false;
    statusText.value = t('auth.forgot_success');
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : t('auth.auth_failed');
  }
}
</script>

<template>
  <div class="auth-page container">
    <div class="auth-container">
      <header class="auth-header">
        <p class="eyebrow">{{ $t('auth.forgot_eyebrow') }}</p>
        <h2 class="page-title">{{ $t('auth.forgot_title') }}</h2>
      </header>
      
      <form class="auth-form panel" @submit.prevent="submitForgot">
        <div class="form-group">
          <label for="email">{{ $t('auth.email_label') }}</label>
          <input 
            id="email"
            v-model="form.email" 
            class="field" 
            type="email" 
            :placeholder="$t('auth.email_placeholder')" 
            :aria-label="$t('auth.email_label')"
            required
          />
        </div>
        
        <button class="btn btn-primary submit-btn" type="submit" :aria-label="$t('auth.forgot_submit')">{{ $t('auth.forgot_submit') }}</button>
        
        <div class="auth-footer">
          <p v-if="statusText" :class="isError ? 'status-err' : 'status-ok'">
            {{ statusText }}
          </p>
          <p class="register-prompt" :style="statusText ? 'margin-top: 1rem;' : ''">
            <RouterLink to="/login">{{ $t('auth.forgot_back_login') }}</RouterLink>
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

.submit-btn {
  margin-top: 1rem;
  width: 100%;
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
