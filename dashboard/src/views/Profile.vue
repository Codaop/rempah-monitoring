<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import { supabase } from '../lib/supabase'
import { fmtDateTime } from '../lib/format'

const router = useRouter()
const profile = ref(null)
const producer = ref(null)
const devices = ref([])
const saving = ref(false)
const saved = ref('')
const error = ref('')

onMounted(async () => {
  const { data: user } = await supabase.auth.getUser()
  profile.value = user.user || null

  if (profile.value) {
    const { data: op } = await supabase.from('operators').select('*').eq('id', profile.value.id).maybeSingle()
    if (op) {
      producer.value = op.producer_id
    }
    const { data: devs } = await supabase.from('devices').select('id, name, producer_id, last_seen_at')
    devices.value = devs || []
  }
})

async function save() {
  saving.value = true
  saved.value = ''
  error.value = ''
  const { error: err } = await supabase.auth.updateUser({ data: {} })
  saving.value = false
  if (err) error.value = err.message
  else saved.value = 'Profil diperbarui.'
}

async function signOutAll() {
  const { error: err } = await supabase.auth.signOut({ scope: 'global' })
  if (!err) router.push({ name: 'login' })
}
</script>

<template>
  <AppShell>
    <div class="page-head">
      <h1 class="page-title">Profil</h1>
    </div>

    <div class="grid">
      <form class="card" @submit.prevent="save">
        <h2>Form Profil</h2>
        <label class="field">
          <span>Email</span>
          <input class="input" :value="profile?.email || ''" disabled />
        </label>
        <label class="field">
          <span>Peran</span>
          <input class="input" value="Operator" disabled />
        </label>
        <label class="field">
          <span>ID Produsen</span>
          <input class="input" :value="producer || '—'" disabled />
        </label>
        <label class="field">
          <span>Terdaftar sejak</span>
          <input class="input" :value="profile?.created_at ? fmtDateTime(profile.created_at) : '—'" disabled />
        </label>

        <p v-if="saved" class="ok">{{ saved }}</p>
        <p v-if="error" class="error">{{ error }}</p>

        <button class="btn btn-primary" type="submit" :disabled="saving">Simpan Perubahan</button>
      </form>

      <div class="card">
        <h2>Manajemen Sesi</h2>
        <div class="sess-row">
          <div>
            <div class="sess-title">Sesi saat ini</div>
            <div class="muted">Aktif di peramban ini.</div>
          </div>
          <span class="badge badge-ok">AKTIF</span>
        </div>
        <div class="sess-row">
          <div>
            <div class="sess-title">Keluar dari semua perangkat</div>
            <div class="muted">Mencabut semua sesi login REM-PAH.</div>
          </div>
          <button class="btn btn-danger btn-sm" @click="signOutAll">Keluar Semua</button>
        </div>

        <h2 class="spaced">Perangkat</h2>
        <table>
          <thead><tr><th>Nama</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="d in devices" :key="d.id">
              <td>{{ d.name }}</td>
              <td>
                <span class="badge" :class="d.last_seen_at ? 'badge-ok' : 'badge-warn'">
                  {{ d.last_seen_at ? 'Terkoneksi' : 'Belum terlihat' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.page-head { margin-bottom: 16px; }
.page-title { font-size: 22px; color: var(--navy); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
.field { display: flex; flex-direction: column; gap: 6px; font-size: 13.5px; font-weight: 500; margin-bottom: 14px; }
.ok { color: var(--ok); font-size: 13px; }
.error { color: var(--danger); font-size: 13px; }
.sess-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--line); }
.sess-title { font-weight: 600; }
.spaced { margin-top: 18px; }
</style>
