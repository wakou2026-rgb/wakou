<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "./store";

const router = useRouter();
const store = useAuthStore();

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
    statusText.value = "Welcome back.";
  } catch (error) {
    isError.value = true;
    statusText.value = error instanceof Error ? error.message : "Authentication failed";
  }
}
</script>

<template>
  <div class="auth-page container">
    <div class="auth-container">
      <header class="auth-header">
        <p class="eyebrow">Members Only</p>
        <h2 class="page-title">登入鑑賞</h2>
      </header>
      
      <form class="auth-form panel" @submit.prevent="submitLogin">
        <div class="form-group">
          <label for="email">Email Address</label>
          <input 
            id="email"
            v-model="form.email" 
            class="field" 
            type="text" 
            placeholder="admin 或 client@example.com" 
            required
          />
        </div>
        
        <div class="form-group">
          <label for="password">Password</label>
          <input 
            id="password"
            v-model="form.password" 
            class="field" 
            type="password" 
            placeholder="••••••••" 
            required
          />
        </div>
        
        <button class="btn btn-primary submit-btn" type="submit">Sign In</button>
        
        <div class="auth-footer">
          <p v-if="statusText" :class="isError ? 'status-err' : 'status-ok'">
            {{ statusText }}
          </p>
          <p v-else class="register-prompt">
            尚未擁有鑑賞帳號？ <RouterLink to="/register">申請入會</RouterLink>
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
