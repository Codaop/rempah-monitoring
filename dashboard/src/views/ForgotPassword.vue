<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { supabase } from "../lib/supabase";

const router = useRouter();
const email = ref("");
const sent = ref(false);
const error = ref("");
const loading = ref(false);

async function submit() {
  error.value = "";
  sent.value = false;
  loading.value = true;
  const { error: err } = await supabase.auth.resetPasswordForEmail(
    email.value.trim(),
    {
      redirectTo: window.location.origin + "/dashboard",
    }
  );
  loading.value = false;
  if (err) {
    error.value = err.message;
    return;
  }
  sent.value = true;
}
</script>

<template>
  <div class="auth-wrap">
    <div class="auth-card card">
      <button
        class="back-btn"
        type="button"
        @click="router.push({ name: 'login' })"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="m12 19-7-7 7-7" />
          <path d="M19 12H5" />
        </svg>
        Kembali
      </button>

      <form @submit.prevent="submit" class="fp-form">
        <div class="auth-logo">
          <div class="logo-circle">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              width="32"
              height="32"
            >
              <path
                d="M12 21C12 21 5 15 5 9a7 7 0 0 1 14 0c0 6-7 12-7 12z"
                stroke="white"
                stroke-width="1.4"
                stroke-linejoin="round"
              />
              <path
                d="M12 7v12"
                stroke="white"
                stroke-width="1.4"
                stroke-linecap="round"
              />
              <path
                d="M9 10c0-1.5 1.2-3 3-3s3 1.5 3 3"
                stroke="white"
                stroke-width="1.4"
                stroke-linecap="round"
                fill="none"
              />
              <circle cx="12" cy="15" r="1.4" fill="white" opacity="0.85" />
              <circle cx="10" cy="12" r="0.9" fill="white" opacity="0.65" />
              <circle cx="14" cy="12" r="0.9" fill="white" opacity="0.65" />
            </svg>
          </div>
          <h1 class="brand-title">REM-PAH</h1>
          <p class="brand-sub">Sistem Kontrol Distilasi</p>
        </div>

        <div class="field">
          <label class="field-label">ALAMAT EMAIL</label>
          <p class="field-hint">
            Link pemulihan akan dikirimkan ke email yang terdaftar.
          </p>
          <div class="input-wrap">
            <span class="input-icon-left">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <rect width="20" height="16" x="2" y="4" rx="2" />
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
              </svg>
            </span>
            <input
              v-model.trim="email"
              class="input input-pl"
              type="email"
              autocomplete="email"
              placeholder="email@gmail.com"
              required
            />
          </div>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>
        <p v-if="sent" class="ok-msg">
          Link reset telah dikirim. Periksa kotak masuk email Anda.
        </p>

        <button
          class="btn btn-submit"
          type="submit"
          :disabled="loading || sent"
        >
          <span>{{ loading ? "Mengirim…" : "Kirim Link" }}</span>
          <span v-if="!loading">🔗</span>
        </button>

        <div class="divider"></div>

        <p class="auth-footer">
          Mengalami kesulitan?
          <a href="mailto:support@rempah.id">Dapatkan dukungan</a>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.auth-wrap {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 16px;
  background: var(--bg);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 28px 32px 32px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: var(--navy);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  padding: 0;
  margin-bottom: 20px;
}
.back-btn:hover {
  color: var(--teal);
}

.fp-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-logo {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.logo-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--navy);
  display: grid;
  place-items: center;
  margin-bottom: 4px;
}

.brand-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--teal);
  letter-spacing: 0.04em;
}

.brand-sub {
  font-size: 13px;
  color: var(--muted);
  margin: 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-label {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--navy);
  letter-spacing: 0.06em;
}

.field-hint {
  font-size: 12.5px;
  color: var(--muted);
  margin: 0;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
  margin-top: 2px;
}

.input-icon-left {
  position: absolute;
  left: 13px;
  display: flex;
  align-items: center;
  color: var(--muted);
  pointer-events: none;
  z-index: 1;
}

.input-pl {
  padding-left: 42px;
}

.error-msg {
  color: var(--danger);
  font-size: 13px;
  margin: 0;
  padding: 8px 12px;
  background: var(--danger-soft);
  border-radius: var(--radius-sm);
}

.ok-msg {
  color: var(--ok);
  font-size: 13px;
  margin: 0;
  padding: 8px 12px;
  background: #e3f5ec;
  border-radius: var(--radius-sm);
}

.btn-submit {
  width: 100%;
  padding: 14px 20px;
  background: var(--navy);
  color: #fff;
  border: none;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition:
    filter 0.15s,
    transform 0.05s;
}
.btn-submit:hover:not(:disabled) {
  filter: brightness(1.15);
}
.btn-submit:active {
  transform: scale(0.98);
}
.btn-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.divider {
  height: 1px;
  background: var(--line);
}

.auth-footer {
  font-size: 13px;
  color: var(--muted);
  text-align: center;
  margin: 0;
}
.auth-footer a {
  color: var(--teal);
  font-weight: 500;
}
</style>
