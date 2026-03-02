<script setup>
import { reactive, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { resetPasswordRequest } from "./api";

const router = useRouter();
const route = useRoute();
const { t } = useI18n();

const form = reactive({
  new_password: "",
  confirm_password: ""
});

const statusText = ref("");
const isError = ref(false);

async function submitReset() {
  isError.value = false;
  statusText.value = "";
  
  if (form.new_password.length < 8) {
    isError.value = true;
    statusText.value = t('auth.reset_password_too_short');
    return;
  }
  
  if (form.new_password !== form.confirm_password) {
    isError.value = true;
    statusText.value = t('auth.reset_password_mismatch');
    return;
  }
  
  try {
    const token = route.query.token || "";
    await resetPasswordRequest({ token, new_password: form.new_password });
    isError.value = false;
    statusText.value = t('auth.reset_success');
    
    setTimeout(() => {
      router.push("/login");
    }, 2000);
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
        <p class="eyebrow">{{ $t('auth.reset_eyebrow') }}</p>
        <h2 class="page-title">{{ $t('auth.reset_title') }}</h2>
      </header>
      
      <form class="auth-form panel" @submit.prevent="submitReset">
        <div class="form-group">
          <label for="new_password">{{ $t('auth.reset_new_password') }}</label>
          <input 
            id="new_password"
            v-model="form.new_password" 
            class="field" 
            type="password" 
            :placeholder="$t('auth.password_placeholder')" 
            :aria-label="$t('auth.reset_new_password')"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="confirm_password">{{ $t('auth.reset_confirm_password') }}</label>
          <input 
            id="confirm_password"
            v-model="form.confirm_password" 
            class="field" 
            type="password" 
            :placeholder="$t('auth.password_placeholder')" 
            :aria-label="$t('auth.reset_confirm_password')"
            required
          />
        </div>
        
        <button class="btn btn-primary submit-btn" type="submit" :aria-label="$t('auth.reset_submit')">{{ $t('auth.reset_submit') }}</button>
        
        <div class="auth-footer">
          <p v-if="statusText" :class="isError ? 'status-err' : 'status-ok'">
            {{ statusText }}
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

@media (max-width: 760px) {
  .auth-form {
    padding: 2.5rem 1.5rem;
  }
}
</style>
