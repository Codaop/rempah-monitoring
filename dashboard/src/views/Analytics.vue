<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import AppShell from '../components/AppShell.vue'
import { supabase } from '../lib/supabase'
import { fmtNum, fmtDateTime, fmtTime } from '../lib/format'

const search = ref('')
const filter = ref('semua')
const rows = ref([])
const loading = ref(true)
const snapshot = ref(null)

const filters = [
  { value: 'semua', label: 'Semua' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'perintah', label: 'Perintah' },
  { value: 'batch', label: 'Batch' },
  { value: 'sistem', label: 'Sistem' },
]

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return rows.value.filter((r) => {
    const okFilter = filter.value === 'semua' || r.category === filter.value
    const okSearch = !q || [r.event, r.value, r.status, r.time].join(' ').toLowerCase().includes(q)
    return okFilter && okSearch
  })
})

function toRow({ time, category, event, value, status }) {
  return { time, category, event, value, status }
}

function statusBadge(s) {
  return s === 'OK' ? 'badge-ok' : s === 'WARNING' ? 'badge-warn' : s === 'DANGER' ? 'badge-danger' : 'badge-info'
}

async function loadLog() {
  const [sensorRes, cmdRes, logRes] = await Promise.all([
    supabase.from('sensor_logs').select('*').order('ts', { ascending: false }).limit(80),
    supabase.from('commands').select('*').order('created_at', { ascending: false }).limit(30),
    supabase.from('batch_logs').select('*').limit(5),
  ])

  const out = []
  for (const s of sensorRes.data || []) {
    const temp = Number(s.boiler_temp_c)
    const warn = temp > 98 ? 'DANGER' : temp > 92 ? 'WARNING' : 'OK'
    out.push(toRow({
      time: s.ts,
      category: 'sensor',
      event: `Sensor Suhu Boiler · ${s.device_id.slice(0, 8)}`,
      value: `${fmtNum(s.boiler_temp_c)}°C`,
      status: warn,
    }))
    out.push(toRow({
      time: s.ts,
      category: 'sensor',
      event: `Tekanan Gas · ${s.device_id.slice(0, 8)}`,
      value: `${fmtNum(s.gas_pressure_kpa)} kPa`,
      status: Number(s.gas_pressure_kpa) > 4 ? 'DANGER' : 'OK',
    }))
  }
  for (const c of cmdRes.data || []) {
    out.push(toRow({
      time: c.created_at,
      category: 'perintah',
      event: `Perintah ${c.action} · ${c.device_id.slice(0, 8)}`,
      value: c.expected_state || '—',
      status: c.status === 'pending' ? 'INFO' : 'OK',
    }))
  }
  for (const b of logRes.data || []) {
    out.push(toRow({
      time: b.created_at,
      category: 'batch',
      event: `Perkiraan hasil batch ${b.batch_id.slice(0, 8)}`,
      value: `${fmtNum(b.estimated_yield)} L`,
      status: 'INFO',
    }))
  }

  out.sort((a, b) => new Date(b.time) - new Date(a.time))
  rows.value = out.slice(0, 200)
  loading.value = false
}

async function loadSnapshot() {
  const [devRes, stateRes, sensorRes, batchRes, batchLogRes] = await Promise.all([
    supabase.from('devices').select('*'),
    supabase.from('device_state').select('device_id, mode'),
    supabase.from('sensor_logs').select('*').order('ts', { ascending: false }).limit(1),
    supabase.from('batches').select('*').order('started_at', { ascending: false }).limit(1),
    supabase.from('batch_logs').select('*').limit(1),
  ])
  const states = stateRes.data || []
  snapshot.value = {
    generatedAt: new Date(),
    devices: (devRes.data || []).map((d) => ({
      ...d,
      mode: (states.find((s) => s.device_id === d.id) || {}).mode || 'IDLE',
    })),
    latest: sensorRes.data?.[0] || null,
    batch: batchRes.data?.[0] || null,
    batchLog: batchLogRes.data?.[0] || null,
  }
}

function openReport(print) {
  const s = snapshot.value
  if (!s) return
  const w = window.open('', '_blank', 'width=820,height=900')
  if (!w) return
  const rowsHtml = rows.value.slice(0, 60).map((r) =>
    `<tr><td>${fmtDateTime(r.time)}</td><td>${r.event}</td><td>${r.value}</td><td>${r.status}</td></tr>`
  ).join('')
  const deviceRows = s.devices.map((d) =>
    `<tr><td>${d.name}</td><td>${d.mode || 'IDLE'}</td><td>${d.last_seen_at ? fmtDateTime(d.last_seen_at) : '—'}</td></tr>`
  ).join('')
  w.document.write(`<!DOCTYPE html><html lang="id"><head><meta charset="utf-8"><title>Laporan REM-PAH</title>
<style>
  body{font-family:system-ui,Segoe UI,sans-serif;color:#1c2b3a;padding:32px;}
  h1{font-size:22px;margin:0 0 4px;} .sub{color:#64748b;margin-bottom:20px;font-size:13px;}
  h2{font-size:15px;margin:22px 0 8px;border-bottom:2px solid #3a7ca5;padding-bottom:4px;}
  table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px;}
  th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #dbe2e8;}
  th{background:#e4eef4;font-size:11px;text-transform:uppercase;letter-spacing:.03em;}
  .cards{display:flex;gap:14px;flex-wrap:wrap;}
  .card{flex:1;min-width:150px;border:1px solid #dbe2e8;border-radius:8px;padding:10px 12px;}
  .card .l{font-size:11px;color:#64748b;text-transform:uppercase;} .card .v{font-size:18px;font-weight:700;margin-top:2px;}
  footer{margin-top:30px;font-size:11px;color:#94a3b8;}
  @media print{body{padding:16px;}}
</style></head><body>
  <h1>REM-PAH — Laporan Monitoring Kapulaga</h1>
  <div class="sub">Dibuat: ${fmtDateTime(s.generatedAt)}</div>
  <h2>Ringkasan Real-time</h2>
  <div class="cards">
    <div class="card"><div class="l">Suhu Boiler</div><div class="v">${s.latest ? fmtNum(s.latest.boiler_temp_c) : '—'}°C</div></div>
    <div class="card"><div class="l">Tekanan Gas</div><div class="v">${s.latest ? fmtNum(s.latest.gas_pressure_kpa) : '—'} kPa</div></div>
    <div class="card"><div class="l">Level Air</div><div class="v">${s.latest ? fmtNum(s.latest.water_level) : '—'}%</div></div>
    <div class="card"><div class="l">Perkiraan Hasil</div><div class="v">${s.batchLog ? fmtNum(s.batchLog.estimated_yield) : '—'} L</div></div>
  </div>
  <h2>Status Perangkat</h2>
  <table><thead><tr><th>Perangkat</th><th>Mode</th><th>Terakhir Terlihat</th></tr></thead><tbody>${deviceRows}</tbody></table>
  <h2>Log Sistem (60 entri terakhir)</h2>
  <table><thead><tr><th>CAPTIME</th><th>KEJADIAN &amp; SENSOR</th><th>NILAI</th><th>STATUS</th></tr></thead><tbody>${rowsHtml}</tbody></table>
  <footer>Dokumen ini dihasilkan otomatis oleh dashboard REM-PAH. Data tunduk pada kebijakan RLS Supabase.</footer>
  <script>${print ? 'window.onload=function(){setTimeout(function(){window.print()},400)}' : ''}<\/script>
</body></html>`)
  w.document.close()
}

onMounted(async () => {
  await Promise.all([loadLog(), loadSnapshot()])
})

const POLL = 30000
let timer = null
onMounted(() => {
  timer = setInterval(() => {
    loadLog()
    loadSnapshot()
  }, POLL)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <AppShell>
    <div class="page-head">
      <div>
        <h1 class="page-title">Analitik &amp; Log</h1>
        <p class="muted">Laporan PDF dan log sistem.</p>
      </div>
      <div class="actions">
        <button class="btn btn-ghost" @click="openReport(false)">Pratinjau Laporan</button>
        <button class="btn btn-primary" @click="openReport(true)">Unduh Laporan PDF</button>
      </div>
    </div>

    <div class="card">
      <h2>Laporan PDF</h2>
      <p class="muted">
        Membuka laporan berisi ringkasan real-time, status perangkat, dan 60 entri log terakhir.
        Pilih "Simpan sebagai PDF" pada dialog cetak browser untuk mengunduh.
      </p>
    </div>

    <div class="card">
      <div class="log-head">
        <h2>Log Sistem</h2>
        <div class="controls">
          <input v-model="search" class="input" placeholder="Cari…" />
          <select v-model="filter" class="input">
            <option v-for="f in filters" :key="f.value" :value="f.value">{{ f.label }}</option>
          </select>
        </div>
      </div>

      <div class="table-wrap">
        <table v-if="!loading">
          <thead>
            <tr><th>CAPTIME</th><th>KEJADIAN &amp; SENSOR</th><th>NILAI</th><th>STATUS</th></tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in filtered.slice(0, 100)" :key="i">
              <td>{{ fmtDateTime(r.time) }}</td>
              <td>{{ r.event }}</td>
              <td>{{ r.value }}</td>
              <td><span class="badge" :class="statusBadge(r.status)">{{ r.status }}</span></td>
            </tr>
            <tr v-if="filtered.length === 0">
              <td colspan="4" class="muted">Tidak ada data yang cocok.</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">Memuat log…</p>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.page-head { margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
.page-title { font-size: 22px; color: var(--navy); }
.actions { display: flex; gap: 8px; }
.card + .card { margin-top: 16px; }
.log-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }
.controls { display: flex; gap: 8px; }
.controls .input { width: 190px; }
.table-wrap { overflow-x: auto; }
</style>
