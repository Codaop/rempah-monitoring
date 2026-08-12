<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase'

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  const { error: err } = await supabase.auth.signInWithPassword({
    email: email.value.trim(),
    password: password.value,
  })
  loading.value = false
  if (err) {
    error.value = err.message === 'Invalid login credentials' ? 'Email atau kata sandi salah.' : err.message
    return
  }
  router.push({ name: 'dashboard' })
}
</script>

<template>
  <div class="auth-wrap">
    <form class="auth-card card" @submit.prevent="submit">
      <div class="auth-logo">
        <div class="logo">R</div>
        <h1>REM-PAH</h1>
        <p class="muted">Dashboard Monitoring Kapulaga</p>
      </div>

      <label class="field">
        <span>Email</span>
        <input v-model.trim="email" class="input" type="email" autocomplete="email" placeholder="operator@perusahaan.com" required />
      </label>

      <label class="field">
        <span>Kata sandi</span>
        <input v-model="password" class="input" type="password" autocomplete="current-password" placeholder="••••••••" required />
      </label>

      <div class="auth-row">
        <router-link :to="{ name: 'forgot' }">Lupa kata sandi?</router-link>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <button class="btn btn-primary full" type="submit" :disabled="loading">
        {{ loading ? 'Memuat…' : 'Masuk' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.auth-wrap { min-height: 100vh; display: grid; place-items: center; padding: 16px; }
.auth-card { width: 100%; max-width: 380px; display: flex; flex-direction: column; gap: 14px; }
.auth-logo { text-align: center; margin-bottom: 6px; }
.logo {
  width: 52px; height: 52px; border-radius: 14px; margin: 0 auto 8px;
  background: var(--teal); color: #fff; display: grid; place-items: center;
  font-weight: 800; font-size: 26px;
}
h1 { font-size: 22px; color: var(--navy); }
.field { display: flex; flex-direction: column; gap: 6px; font-size: 13.5px; font-weight: 500; }
.auth-row { text-align: right; font-size: 13px; }
.error { color: var(--danger); font-size: 13px; margin: 0; }
.full { width: 100%; }
</style>
