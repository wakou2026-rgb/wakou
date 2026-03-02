<script setup>
import { onUnmounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "./store";

const router = useRouter();
const store = useAuthStore();

const form = reactive({
  email: "",
  password: "",
  role: "buyer",
  verification_code: ""
});

const statusText = ref("");
const isError = ref(false);
const codeCooldown = ref(0);

let cooldownTimer = null;

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
    statusText.value = "Please enter your email first";
    return;
  }
  try {
    const result = await store.requestRegisterCode({ email: form.email });
    startCooldown(result.cooldown_seconds || 60);
    statusText.value = "Verification code sent. Please check your mailbox.";
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Request verification code failed";
  }
}

async function submitRegister() {
  isError.value = false;
  statusText.value = "";
  try {
    await store.register(form);
    statusText.value = "Registration successful. Redirecting...";
    setTimeout(() => {
      router.push("/login");
    }, 1500);
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Registration failed";
  }
}
</script>

<template>
  <div class="auth-page container">
    <div class="auth-container">
      <header class="auth-header">
        <p class="eyebrow">Join Us</p>
        <h2 class="page-title">申請入會</h2>
      </header>
      
      <form class="auth-form panel" @submit.prevent="submitRegister">
        <div class="form-group">
          <label for="reg-email">Email Address</label>
          <input 
            id="reg-email"
            v-model="form.email" 
            class="field" 
            type="email" 
            placeholder="client@example.com" 
            required
          />
        </div>
        
        <div class="form-group">
          <label for="reg-password">Password</label>
          <input 
            id="reg-password"
            v-model="form.password" 
            class="field" 
            type="password" 
            placeholder="••••••••" 
            required
          />
        </div>

        <div class="form-group">
          <label for="verification-code">Verification Code</label>
          <div class="code-row">
            <input
              id="verification-code"
              v-model="form.verification_code"
              class="field"
              type="text"
              inputmode="numeric"
              maxlength="6"
              placeholder="6-digit code"
              required
            />
            <button
              class="btn btn-secondary code-btn"
              type="button"
              :disabled="codeCooldown > 0"
              @click="requestCode"
            >
              {{ codeCooldown > 0 ? `Resend (${codeCooldown}s)` : "Send Code" }}
            </button>
          </div>
        </div>

        <div class="form-group">
          <label for="role">Account Type</label>
          <select id="role" v-model="form.role" class="field select-styled">
            <option value="buyer">Collector (Buyer)</option>
            <option value="admin">Artisan (Admin)</option>
          </select>
        </div>
        
        <button class="btn btn-primary submit-btn" type="submit">Create Account</button>
        
        <div class="auth-footer">
          <p v-if="statusText" :class="isError ? 'status-err' : 'status-ok'">
            {{ statusText }}
          </p>
          <p v-else class="register-prompt">
            已經擁有帳號？ <RouterLink to="/login">登入鑑賞</RouterLink>
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
