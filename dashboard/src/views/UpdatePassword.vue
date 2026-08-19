<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { supabase } from "../lib/supabase";

const router = useRouter();

const checking = ref(true);
const ready = ref(false);
const password = ref("");
const confirm = ref("");
const busy = ref(false);
const error = ref("");
const done = ref(false);

let authSub = null;

onMounted(async () => {
  const { data: subData } = supabase.auth.onAuthStateChange((event) => {
    if (event === "PASSWORD_RECOVERY") ready.value = true;
    if (event === "SIGNED_OUT") ready.value = false;
  });
  authSub = subData.subscription;

  const { data } = await supabase.auth.getSession();
  ready.value = Boolean(data.session);
  checking.value = false;
});

onUnmounted(() => {
  authSub?.unsubscribe();
});

async function submit() {
  error.value = "";
  const pw = password.value;
  if (pw.length < 8) {
    error.value = "Kata sandi minimal 8 karakter.";
    return;
  }
  if (pw !== confirm.value) {
    error.value = "Konfirmasi kata sandi tidak cocok.";
    return;
  }
  busy.value = true;
  const { error: err } = await supabase.auth.updateUser({ password: pw });
  busy.value = false;
  if (err) {
    error.value = err.message;
    return;
  }
  done.value = true;
  setTimeout(() => router.push({ name: "login" }), 1600);
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

      <div class="auth-logo">
        <div class="logo-circle">
          <img src="/logo.svg" alt="REMPAH" class="logo-img" />
        </div>
        <h1 class="brand-title">REMPAH</h1>
        <p class="brand-sub">Sistem Kontrol Distilasi</p>
      </div>

      <p v-if="checking" class="muted center">Memeriksa link…</p>

      <template v-else-if="!ready">
        <p class="state-msg">
          Link tidak valid atau sudah kedaluwarsa. Silakan minta link baru.
        </p>
        <button
          class="btn btn-submit"
          type="button"
          @click="router.push({ name: 'forgot' })"
        >
          Kirim Ulang Link
        </button>
      </template>

      <template v-else-if="done">
        <p class="ok-msg">
          Kata sandi berhasil diubah. Mengalihkan ke halaman masuk…
        </p>
      </template>

      <form v-else class="up-form" @submit.prevent="submit">
        <p class="state-msg">Buat kata sandi baru untuk akun Anda.</p>

        <div class="field">
          <label class="field-label" for="new-password">KATA SANDI BARU</label>
          <input
            id="new-password"
            v-model="password"
            class="input"
            type="password"
            autocomplete="new-password"
            placeholder="Minimal 8 karakter"
            required
          />
        </div>

        <div class="field">
          <label class="field-label" for="confirm-password"
            >KONFIRMASI KATA SANDI</label
          >
          <input
            id="confirm-password"
            v-model="confirm"
            class="input"
            type="password"
            autocomplete="new-password"
            placeholder="Ulangi kata sandi baru"
            required
          />
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button class="btn btn-submit" type="submit" :disabled="busy">
          {{ busy ? "Menyimpan…" : "Simpan Kata Sandi" }}
        </button>
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

.auth-logo {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
}

.logo-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--navy);
  display: grid;
  place-items: center;
  margin-bottom: 4px;
  overflow: hidden;
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
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

.center {
  text-align: center;
  margin: 12px 0;
}

.state-msg {
  font-size: 13.5px;
  color: var(--muted);
  margin: 0 0 14px;
  text-align: center;
}

.up-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--navy);
  letter-spacing: 0.06em;
}

.input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--navy);
  background: #fff;
  outline: none;
  transition: border-color 0.12s;
}
.input:focus {
  border-color: var(--teal);
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
  padding: 10px 12px;
  background: #e3f5ec;
  border-radius: var(--radius-sm);
  text-align: center;
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

@media (max-width: 400px) {
  .auth-wrap {
    padding: 10px;
  }
  .auth-card {
    padding: 20px;
  }
}
</style>
