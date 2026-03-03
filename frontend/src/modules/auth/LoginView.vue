<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "./store";
import { useI18n } from "vue-i18n";

const router = useRouter();
const store = useAuthStore();
const { t } = useI18n();

const form = reactive({
  email: "",
  password: ""
});

const statusText = ref("");
const isError = ref(false);

async function submitLogin() {
  isError.value = false;
  statusText.value = "";
  try {
    await store.login({ email: form.email, password: form.password }, router);
    statusText.value = t('auth.welcome_back');
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
        <p class="eyebrow">{{ $t('auth.eyebrow') }}</p>
        <h2 class="page-title">{{ $t('auth.login_title') }}</h2>
      </header>
      
      <form class="auth-form panel" @submit.prevent="submitLogin">
        <div class="form-group">
          <label for="email">{{ $t('auth.email_label') }}</label>
          <input 
            id="email"
            v-model="form.email" 
            class="field" 
            type="text" 
            placeholder="admin 或 client@example.com" 
            :aria-label="$t('auth.email_label')"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="password">{{ $t('auth.password_label') }}</label>
          <input 
            id="password"
            v-model="form.password" 
            class="field" 
            type="password" 
            placeholder="••••••••" 
            :aria-label="$t('auth.password_label')"
            required
          />
        </div>
        
        <button class="btn btn-primary submit-btn" type="submit" :aria-label="$t('auth.sign_in')">{{ $t('auth.sign_in') }}</button>
        <RouterLink to="/forgot-password" class="forgot-link">{{ $t('auth.forgot_password') }}</RouterLink>
        
        <div class="auth-footer">
          <p v-if="statusText" :class="isError ? 'status-err' : 'status-ok'">
            {{ statusText }}
          </p>
          <p class="register-prompt">
            {{ $t('auth.no_account') }} <RouterLink to="/register">{{ $t('auth.register_link') }}</RouterLink>
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

.forgot-link {
  color: var(--ink-500);
  display: block;
  font-size: 0.85rem;
  margin-top: 1rem;
  text-align: center;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.forgot-link:hover {
  color: var(--ink-900);
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
