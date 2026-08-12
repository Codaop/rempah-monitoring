<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import AppShell from '../components/AppShell.vue'
import MetricCard from '../components/MetricCard.vue'
import PowerPanel from '../components/PowerPanel.vue'
import BatchPanel from '../components/BatchPanel.vue'
import NotificationLog from '../components/NotificationLog.vue'
import { supabase } from '../lib/supabase'
import { fmtNum, fmtTime, fmtDateTime } from '../lib/format'

const REFRESH_MS = 30000

const devices = ref([])
const batch = ref(null)
const batchLog = ref(null)
const history = ref([])
const alerts = ref([])
const refreshPrompt = ref('')
const loading = ref(true)
const lastSync = ref(null)

const activeDeviceId = computed(() => devices.value[0]?.id || null)
const latest = computed(() => history.value[history.value.length - 1] || {})
const sparkTemp = computed(() => history.value.map((r) => r.boiler_temp_c))
const sparkGas = computed(() => history.value.map((r) => r.gas_pressure_kpa))
const sparkWater = computed(() => history.value.map((r) => r.water_level))

function pushAlert(level, tag, message, at) {
  alerts.value.push({ level, tag, message, at: at || new Date().toISOString() })
  if (alerts.value.length > 200) alerts.value.splice(0, alerts.value.length - 200)
}

function checkThresholds(row) {
  if (Number(row.boiler_temp_c) > 98) pushAlert('danger', 'SUHU', `Suhu boiler tinggi: ${fmtNum(row.boiler_temp_c)}°C (Perangkat ${row.device_id.slice(0, 8)})`, row.ts)
  if (Number(row.water_level) < 50) pushAlert('warn', 'AIR', `Level air rendah: ${fmtNum(row.water_level)}%`, row.ts)
}

async function loadAll() {
  const [devRes, stateRes, batchRes, logRes, histRes] = await Promise.all([
    supabase.from('devices').select('id, producer_id, name, mqtt_username, last_seen_at'),
    supabase.from('device_state').select('device_id, producer_id, mode, updated_at'),
    supabase.from('batches').select('*').eq('status', 'active').order('started_at', { ascending: false }).limit(1),
    supabase.from('batch_logs').select('*').limit(1),
    supabase.from('sensor_logs').select('*').order('ts', { ascending: false }).limit(240),
  ])

  if (devRes.error || stateRes.error) console.error('load error', devRes.error, stateRes.error)

  const states = stateRes.data || []
  devices.value = (devRes.data || []).map((d) => ({
    ...d,
    mode: (states.find((s) => s.device_id === d.id) || {}).mode || 'IDLE',
  }))

  batch.value = batchRes.data?.[0] || null
  batchLog.value = logRes.data?.[0] || null
  history.value = (histRes.data || []).reverse()
  lastSync.value = new Date()
  loading.value = false

  // Rebuild alert baseline from recent history
  const hasState = alerts.value.length === 0
  if (hasState) {
    history.value.filter((r) => r.flame_lit).slice(-30).forEach((r) => checkThresholds(r))
    if (batch.value) {
      pushAlert('info', 'BATCH', `Batch aktif dimulai ${fmtDateTime(batch.value.started_at)}`)
    }
    devices.value.forEach((d) => {
      if (!d.last_seen_at) return
      const age = Date.now() - new Date(d.last_seen_at).getTime()
      if (age > 45000) pushAlert('warn', 'STATUS', `${d.name} tampak offline (${fmtTime(d.last_seen_at)})`)
    })
  }
}

async function refreshQuiet() {
  const { data } = await supabase.from('sensor_logs').select('*').order('ts', { ascending: false }).limit(1)
  if (data?.[0]) {
    const seen = history.value.some((r) => r.id === data[0].id)
    if (!seen) {
      history.value.push(data[0])
      if (history.value.length > 240) history.value.shift()
      checkThresholds(data[0])
    }
  }
}

let realtime = null
let pollTimer = null

onMounted(async () => {
  await loadAll()

  realtime = supabase
    .channel('dashboard-live')
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'sensor_logs' }, (payload) => {
      const row = payload.new
      if (activeDeviceId.value && row.device_id === activeDeviceId.value) {
        const seen = history.value.some((r) => r.id === row.id)
        if (!seen) {
          history.value.push(row)
          if (history.value.length > 240) history.value.shift()
          checkThresholds(row)
        }
      }
    })
    .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'device_state' }, (payload) => {
      const d = devices.value.find((x) => x.id === payload.new.device_id)
      if (d) d.mode = payload.new.mode
      pushAlert('info', 'STATUS', `Perangkat ${payload.new.device_id.slice(0, 8)} → mode ${payload.new.mode}`)
    })
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'commands' }, (payload) => {
      const c = payload.new
      const d = devices.value.find((x) => x.id === c.device_id)
      const name = d ? d.name : c.device_id.slice(0, 8)
      const level = c.action === 'EMERGENCY_STOP' ? 'danger' : 'info'
      pushAlert(level, 'CMD', `Perintah ${c.action} untuk ${name}`)
    })
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'batch_logs' }, (payload) => {
      batchLog.value = payload.new
      pushAlert('info', 'ESTIMASI', `Perkiraan hasil diperbarui: ${fmtNum(payload.new.estimated_yield)} L`)
    })
    .subscribe()

  pollTimer = setInterval(refreshQuiet, REFRESH_MS)
})

onBeforeUnmount(() => {
  clearInterval(pollTimer)
  realtime && supabase.removeChannel(realtime)
})

function onCommand({ device, action, mismatch }) {
  if (mismatch) {
    refreshPrompt.value = `${device.name}: mode saat ini ${device.mode} ≠ status yang diharapkan. Tekan "Refresh" untuk memuat ulang.`
  }
  pushAlert('info', 'CMD', `Perintah ${action} untuk ${device.name}`)
}

async function refreshState() {
  refreshPrompt.value = ''
  await loadAll()
  pushAlert('info', 'SISTEM', 'Status perangkat disinkronkan.')
}
</script>

<template>
  <AppShell>
    <div class="page-head">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <p class="muted">
          Sinkron terakhir: {{ lastSync ? fmtTime(lastSync) : '…' }} ·
          <a href="#" @click.prevent="refreshState">Refresh</a>
        </p>
      </div>
    </div>

    <div v-if="refreshPrompt" class="refresh-prompt">
      <span>{{ refreshPrompt }}</span>
      <button class="btn btn-primary btn-sm" @click="refreshState">Refresh</button>
    </div>

    <div v-if="loading" class="muted">Memuat data…</div>

    <template v-else>
      <div class="grid-cards">
        <MetricCard label="Suhu Boiler" :value="fmtNum(latest.boiler_temp_c)" unit="°C" :data="sparkTemp" hint="Sumber: sensor boiler" />
        <MetricCard label="Tekanan Gas" :value="fmtNum(latest.gas_pressure_kpa)" unit="kPa" :data="sparkGas" color="#d69e2e" hint="Sumber: sensor gas" />
        <MetricCard label="Suhu Pendingin Air" :value="fmtNum(latest.boiler_temp_c)" unit="°C" :data="sparkTemp" color="#64748b" hint="Baca sensor boiler" />
        <MetricCard label="Level Air" :value="fmtNum(latest.water_level)" unit="%" :data="sparkWater" color="#3a7ca5" hint="Sumber: sensor air" />
        <MetricCard label="Perkiraan Hasil" :value="fmtNum(batchLog?.estimated_yield)" unit="L" :data="[batchLog?.estimated_yield || 0]" color="#2f9e63" hint="Dari kalkulasi bridge" />
      </div>

      <div class="grid-mid">
        <PowerPanel :devices="devices" @command="onCommand" />
        <BatchPanel :batch="batch" :log="batchLog" />
      </div>

      <NotificationLog :alerts="alerts" />
    </template>
  </AppShell>
</template>

<style scoped>
.page-head { margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
.page-title { font-size: 22px; color: var(--navy); }
.refresh-prompt {
  display: flex; gap: 12px; align-items: center; justify-content: space-between;
  background: #fdf0dc; color: #8a5a12; padding: 10px 14px; border-radius: var(--radius-sm);
  margin-bottom: 16px; font-size: 13.5px;
}
.grid-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px; margin-bottom: 16px;
}
.grid-mid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }

@media (max-width: 900px) {
  .grid-mid { grid-template-columns: 1fr; }
}
</style>
