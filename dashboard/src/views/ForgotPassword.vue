<script setup>
import { ref } from 'vue'
import { supabase } from '../lib/supabase'

const email = ref('')
const sent = ref(false)
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  sent.value = false
  loading.value = true
  const { error: err } = await supabase.auth.resetPasswordForEmail(email.value.trim(), {
    redirectTo: window.location.origin + '/dashboard',
  })
  loading.value = false
  if (err) {
    error.value = err.message
    return
  }
  sent.value = true
}
</script>

<template>
  <div class="auth-wrap">
    <form class="auth-card card" @submit.prevent="submit">
      <div class="auth-logo">
        <div class="logo">R</div>
        <h1>Lupa kata sandi?</h1>
        <p class="muted">Masukkan email Anda dan kami akan mengirim tautan untuk mengatur ulang kata sandi.</p>
      </div>

      <label class="field">
        <span>Email</span>
        <input v-model.trim="email" class="input" type="email" autocomplete="email" placeholder="operator@perusahaan.com" required />
      </label>

      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="sent" class="ok">Tautan reset telah dikirim. Periksa kotak masuk email Anda.</p>

      <button class="btn btn-primary full" type="submit" :disabled="loading">
        {{ loading ? 'Mengirim…' : 'Kirim tautan reset' }}
      </button>

      <div class="auth-row">
        <router-link :to="{ name: 'login' }">← Kembali ke Masuk</router-link>
      </div>
    </form>
  </div>
</template>

<style scoped>
.auth-wrap { min-height: 100vh; display: grid; place-items: center; padding: 16px; }
.auth-card { width: 100%; max-width: 380px; display: flex; flex-direction: column; gap: 14px; }
.auth-logo { text-align: center; }
.logo {
  width: 52px; height: 52px; border-radius: 14px; margin: 0 auto 8px;
  background: var(--teal); color: #fff; display: grid; place-items: center;
  font-weight: 800; font-size: 26px;
}
h1 { font-size: 20px; color: var(--navy); }
.field { display: flex; flex-direction: column; gap: 6px; font-size: 13.5px; font-weight: 500; }
.error { color: var(--danger); font-size: 13px; margin: 0; }
.ok { color: var(--ok); font-size: 13px; margin: 0; }
.full { width: 100%; }
.auth-row { text-align: center; font-size: 13px; }
</style>
