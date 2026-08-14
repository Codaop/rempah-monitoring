<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import AppShell from "../components/AppShell.vue";
import { supabase } from "../lib/supabase";
import { fmtNum, fmtDateTime, fmtTime, offlineSince } from "../lib/format";

const search = ref("");
const filter = ref("semua");
const rows = ref([]);
const loading = ref(true);
const snapshot = ref(null);
const batchOptions = ref([]);
const selectedBatchId = ref(null);
const report = ref(null);

const filters = [
  { value: "semua", label: "Semua" },
  { value: "sensor", label: "Sensor" },
  { value: "perintah", label: "Perintah" },
  { value: "batch", label: "Batch" },
  { value: "sistem", label: "Sistem" },
];

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rows.value.filter((r) => {
    const okFilter = filter.value === "semua" || r.category === filter.value;
    const okSearch =
      !q ||
      [r.event, r.value, r.status, r.time].join(" ").toLowerCase().includes(q);
    return okFilter && okSearch;
  });
});

function toRow({ time, category, event, value, status }) {
  return { time, category, event, value, status };
}

function statusBadge(s) {
  if (s === "OK" || s === "Sukses") return "badge-ok";
  if (s === "WARNING" || s === "Peringatan") return "badge-warn";
  if (s === "DANGER") return "badge-danger";
  return "badge-info";
}

function statusLabel(s) {
  if (s === "OK") return "Sukses";
  if (s === "WARNING") return "Peringatan";
  if (s === "DANGER") return "Bahaya";
  if (s === "INFO") return "Info";
  return s;
}

async function loadLog() {
  const [sensorRes, cmdRes, logRes] = await Promise.all([
    supabase
      .from("sensor_logs")
      .select("*")
      .order("ts", { ascending: false })
      .limit(80),
    supabase
      .from("commands")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(30),
    supabase.from("batch_logs").select("*").limit(5),
  ]);

  const out = [];
  for (const s of sensorRes.data || []) {
    const temp = Number(s.boiler_temp_c);
    const warn = temp > 98 ? "DANGER" : temp > 92 ? "WARNING" : "OK";
    out.push(
      toRow({
        time: s.ts,
        category: "sensor",
        event: `Lonjakan Suhu Boiler`,
        value: `${fmtNum(s.boiler_temp_c)} °C`,
        status: warn,
      })
    );
    out.push(
      toRow({
        time: s.ts,
        category: "sensor",
        event: `Massa Gas`,
        value: `${fmtNum(s.gas_mass_kg)} kg`,
        // Sensor beban: massa tabung menurun saat gas terpakai. Ambang default
        // untuk tabung LPG 15 kg (tare ~14 kg) — sesuaikan dengan alat.
        status: Number(s.gas_mass_kg) < 15 ? "DANGER" : "OK",
      })
    );
  }
  for (const c of cmdRes.data || []) {
    out.push(
      toRow({
        time: c.created_at,
        category: "perintah",
        event: `Perintah ${c.action}`,
        value: c.expected_state || "—",
        status: c.status === "pending" ? "INFO" : "OK",
      })
    );
  }
  for (const b of logRes.data || []) {
    out.push(
      toRow({
        time: b.created_at,
        category: "batch",
        event: `Batch Dimulai`,
        value: `${fmtNum(b.estimated_yield)} L`,
        status: "INFO",
      })
    );
  }

  out.sort((a, b) => new Date(b.time) - new Date(a.time));
  rows.value = out.slice(0, 200);
  loading.value = false;
}

async function loadSnapshot() {
  const [devRes, stateRes, sensorRes, batchRes, batchLogRes] =
    await Promise.all([
      supabase.from("devices").select("*"),
      supabase.from("device_state").select("device_id, mode"),
      supabase
        .from("sensor_logs")
        .select("*")
        .order("ts", { ascending: false })
        .limit(1),
      supabase
        .from("batches")
        .select("*")
        .order("started_at", { ascending: false })
        .limit(1),
      supabase.from("batch_logs").select("*").limit(1),
    ]);
  const states = stateRes.data || [];
  snapshot.value = {
    generatedAt: new Date(),
    devices: (devRes.data || []).map((d) => ({
      ...d,
      mode: (states.find((s) => s.device_id === d.id) || {}).mode || "IDLE",
    })),
    latest: sensorRes.data?.[0] || null,
    batch: batchRes.data?.[0] || null,
    batchLog: batchLogRes.data?.[0] || null,
  };
}

const estimatedYield = computed(
  () => snapshot.value?.batchLog?.estimated_yield || null
);
const targetYield = computed(
  () => snapshot.value?.batch?.target_yield_l || null
);

// Status online/offline jujur dari last_seen_at per perangkat (threshold 60s,
// konsisten dengan OFFLINE_AFTER_S bridge dan dashboard).
const OFFLINE_MS = 60000;
const anyDeviceOnline = computed(() =>
  (snapshot.value?.devices || []).some(
    (d) =>
      offlineSince(d.last_seen_at) >= 0 &&
      offlineSince(d.last_seen_at) < OFFLINE_MS
  )
);
const latestSensorAge = computed(() => {
  const ts = snapshot.value?.latest?.ts;
  if (!ts) return null;
  return Date.now() - new Date(ts).getTime();
});
const dataFlowing = computed(() => {
  const age = latestSensorAge.value;
  return age !== null && age >= 0 && age < OFFLINE_MS;
});
const yieldProgress = computed(() => {
  if (!estimatedYield.value || !targetYield.value) return 0;
  return Math.min(
    100,
    Math.round((Number(estimatedYield.value) / Number(targetYield.value)) * 100)
  );
});

// ── Batch-scoped report (ticket 13) ────────────────────────────────────────

const selectedBatch = computed(
  () => batchOptions.value.find((b) => b.id === selectedBatchId.value) || null
);

const reportProgress = computed(() => {
  const r = report.value;
  if (!r) return 0;
  const target = Number(r.batch.target_yield_l) || 0;
  const est = Number(r.log?.estimated_yield) || 0;
  return target ? Math.min(100, Math.round((est / target) * 100)) : 0;
});

function deviceNameOf(id) {
  const d = snapshot.value?.devices.find((x) => x.id === id);
  return d ? d.name : id ? `Perangkat ${id.slice(0, 8)}` : "—";
}

function windowWithin(iso, startIso, endIso) {
  const t = new Date(iso).getTime();
  const s = startIso ? new Date(startIso).getTime() : -Infinity;
  const e = endIso ? new Date(endIso).getTime() : Infinity;
  return t >= s && t <= e;
}

async function loadBatches() {
  const { data } = await supabase
    .from("batches")
    .select(
      "id, device_id, charge_mass_kg, target_yield_l, started_at, ended_at, status"
    )
    .order("started_at", { ascending: false })
    .limit(20);
  batchOptions.value = data || [];
  if (batchOptions.value.length)
    selectedBatchId.value = batchOptions.value[0].id;
}

async function loadBatchReport() {
  const b = selectedBatch.value;
  if (!b) {
    report.value = null;
    return;
  }
  const [batchLogRes, cmdRes, alertRes] = await Promise.all([
    supabase.from("batch_logs").select("*").eq("batch_id", b.id).maybeSingle(),
    supabase
      .from("commands")
      .select("*")
      .eq("device_id", b.device_id)
      .order("created_at", { ascending: false })
      .limit(20),
    supabase
      .from("alerts")
      .select("*")
      .eq("device_id", b.device_id)
      .order("ts", { ascending: false })
      .limit(20),
  ]);
  report.value = {
    batch: b,
    log: batchLogRes.data,
    commands: (cmdRes.data || []).filter((c) =>
      windowWithin(c.created_at, b.started_at, b.ended_at)
    ),
    alerts: (alertRes.data || []).filter((a) =>
      windowWithin(a.ts, b.started_at, b.ended_at)
    ),
  };
}

watch(selectedBatchId, loadBatchReport);

function fmtDuration(sec) {
  const mins = Math.max(1, Math.round(Number(sec) / 60));
  if (mins < 60) return `${mins} menit`;
  const h = Math.floor(mins / 60);
  return `${h} jam ${mins % 60} menit`;
}

function batchEventsHtml(r) {
  const rowsHtml = [
    ...r.commands.map(
      (c) =>
        `<tr><td>${fmtDateTime(c.created_at)}</td><td>Perintah ${c.action}</td><td>${c.expected_state || "—"}</td><td>${c.status}</td></tr>`
    ),
    ...r.alerts.map(
      (a) =>
        `<tr><td>${fmtDateTime(a.ts)}</td><td>Alert ${a.kind}</td><td>${fmtNum(a.value)}</td><td>DANGER</td></tr>`
    ),
  ].join("");
  return (
    rowsHtml ||
    `<tr><td colspan="4">Tidak ada kejadian tercatat untuk batch ini.</td></tr>`
  );
}

function openReport(print) {
  const r = report.value;
  if (!r) return;
  const b = r.batch;
  const log = r.log || {};
  const target = Number(b.target_yield_l) || 0;
  const est = Number(log.estimated_yield) || 0;
  const pct = target ? Math.min(100, Math.round((est / target) * 100)) : 0;
  const durationMin =
    log.duration != null
      ? Math.round(Number(log.duration) / 60)
      : b.started_at && b.ended_at
        ? Math.round((new Date(b.ended_at) - new Date(b.started_at)) / 60000)
        : null;
  const w = window.open("", "_blank", "width=820,height=900");
  if (!w) return;
  const batchId = `#${b.id.slice(0, 8).toUpperCase()}`;
  w.document
    .write(`<!DOCTYPE html><html lang="id"><head><meta charset="utf-8"><title>Laporan Batch REM-PAH</title>
<style>
  body{font-family:system-ui,Segoe UI,sans-serif;color:#1c2b3a;padding:32px;}
  h1{font-size:22px;margin:0 0 4px;} .sub{color:#64748b;margin-bottom:20px;font-size:13px;}
  h2{font-size:15px;margin:22px 0 8px;border-bottom:2px solid #3a7ca5;padding-bottom:4px;}
  table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px;}
  th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #dbe2e8;}
  th{background:#e4eef4;font-size:11px;text-transform:uppercase;letter-spacing:.03em;}
  .tag{display:inline-block;font-size:11px;font-weight:700;padding:3px 10px;border-radius:6px;background:#1c2b3a;color:#fff;}
  @media print{body{padding:16px;}}
</style></head><body>
  <h1>REM-PAH — Laporan Batch</h1>
  <div class="sub">${batchId} — ${deviceNameOf(b.device_id)} · Dibuat: ${fmtDateTime(new Date())} · Status: ${b.status.toUpperCase()}</div>
  <h2>Identitas &amp; Ringkasan</h2>
  <table>
    <tr><th>Mulai</th><td>${b.started_at ? fmtDateTime(b.started_at) : "—"}</td></tr>
    <tr><th>Selesai</th><td>${b.ended_at ? fmtDateTime(b.ended_at) : "—"}</td></tr>
    <tr><th>Durasi</th><td>${durationMin != null ? fmtDuration(durationMin * 60) : "—"}</td></tr>
    <tr><th>Massa Muatan</th><td>${b.charge_mass_kg ? fmtNum(b.charge_mass_kg) + " kg" : "—"}</td></tr>
    <tr><th>Suhu Puncak</th><td>${log.peak_temp != null ? fmtNum(log.peak_temp) + " °C" : "—"}</td></tr>
    <tr><th>Hasil Estimasi vs Target</th><td>${fmtNum(est)} L / ${target ? fmtNum(target) + " L" : "—"} (${pct}%)</td></tr>
    <tr><th>Hasil Akhir</th><td>${log.yield_l != null ? fmtNum(log.yield_l) + " L" : "—"}</td></tr>
  </table>
  <h2>Kejadian Penting</h2>
  <table><thead><tr><th>CAPTIME</th><th>KEJADIAN &amp; SENSOR</th><th>NILAI</th><th>STATUS</th></tr></thead><tbody>${batchEventsHtml(r)}</tbody></table>
  <script>${print ? "window.onload=function(){setTimeout(function(){window.print()},400)}" : ""}<\/script>
</body></html>`);
  w.document.close();
}

onMounted(async () => {
  await Promise.all([loadLog(), loadSnapshot()]);
  await loadBatches();
  await loadBatchReport();
});

const POLL = 30000;
let timer = null;
onMounted(() => {
  timer = setInterval(() => {
    loadLog();
    loadSnapshot();
  }, POLL);
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <AppShell>
    <!-- Header -->
    <div class="page-head">
      <div>
        <h1 class="page-title">Analitik &amp; Log</h1>
        <p class="page-sub">
          Visualisasi data komprehensif tentang kinerja sistem dan log
        </p>
      </div>
      <div class="status-badges">
        <span class="status-pill">
          <span
            class="dot-status"
            :class="anyDeviceOnline ? 'dot-ok' : 'dot-off'"
          ></span>
          Perangkat {{ anyDeviceOnline ? "Online" : "Offline" }}
        </span>
        <span class="status-pill">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <path d="M5 12.55a11 11 0 0 1 14.08 0" />
            <path d="M1.42 9a16 16 0 0 1 21.16 0" />
            <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
            <line x1="12" y1="20" x2="12.01" y2="20" />
          </svg>
          {{ dataFlowing ? "Data Mengalir" : "Menunggu Data" }}
        </span>
      </div>
    </div>

    <!-- Top section: 2 columns -->
    <div class="top-grid">
      <!-- Left: PDF Report card -->
      <div class="card report-card">
        <h2>Laporan Batch</h2>
        <p class="muted">Pilih batch untuk melihat ringkasan &amp; unduh PDF</p>
        <select
          v-if="batchOptions.length"
          v-model="selectedBatchId"
          class="input batch-picker"
        >
          <option v-for="b in batchOptions" :key="b.id" :value="b.id">
            {{ "#" + b.id.slice(0, 8).toUpperCase() }} —
            {{ deviceNameOf(b.device_id) }} ({{ b.status
            }}{{
              b.started_at
                ? " · " + fmtDateTime(b.started_at).slice(0, 16)
                : ""
            }})
          </option>
        </select>
        <p v-else class="muted">Belum ada batch untuk dilaporkan.</p>
        <div v-if="report" class="report-preview">
          <div class="preview-row">
            <span>Batch</span
            ><b
              >{{ "#" + report.batch.id.slice(0, 8).toUpperCase() }} ·
              {{ deviceNameOf(report.batch.device_id) }}</b
            >
          </div>
          <div class="preview-row">
            <span>Mulai / Selesai</span
            ><b
              >{{
                report.batch.started_at
                  ? fmtDateTime(report.batch.started_at).slice(0, 16)
                  : "—"
              }}{{
                report.batch.ended_at
                  ? " → " + fmtDateTime(report.batch.ended_at).slice(0, 16)
                  : ""
              }}</b
            >
          </div>
          <div class="preview-row">
            <span>Massa Muatan</span
            ><b>{{
              report.batch.charge_mass_kg
                ? fmtNum(report.batch.charge_mass_kg) + " kg"
                : "—"
            }}</b>
          </div>
          <div class="preview-row">
            <span>Hasil vs Target</span
            ><b
              >{{ fmtNum(report.log?.estimated_yield) }} /
              {{ fmtNum(report.batch.target_yield_l) }} L ({{
                reportProgress
              }}%)</b
            >
          </div>
          <div class="preview-row">
            <span>Suhu Puncak</span
            ><b>{{
              report.log?.peak_temp != null
                ? fmtNum(report.log.peak_temp) + " °C"
                : "—"
            }}</b>
          </div>
        </div>
        <div class="report-btns">
          <button
            class="btn btn-ghost report-btn"
            :disabled="!report"
            @click="openReport(false)"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            </svg>
            Pratinjau PDF
          </button>
          <button
            class="btn btn-primary report-btn"
            :disabled="!report"
            @click="openReport(true)"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Unduh PDF
          </button>
        </div>
      </div>

      <!-- Right: Hasil -->
      <div class="right-col">
        <div class="card yield-card">
          <div class="yield-header">
            <div class="yield-icon">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#a07840"
                stroke-width="1.8"
                stroke-linecap="round"
              >
                <path d="M6 2v6l-2 4a6 6 0 0 0 6 8h4a6 6 0 0 0 6-8l-2-4V2" />
                <line x1="6" y1="8" x2="18" y2="8" />
              </svg>
            </div>
            <span class="yield-label">HASIL YANG DIPERKIRAKAN</span>
          </div>
          <div class="yield-value">
            {{ estimatedYield !== null ? fmtNum(estimatedYield) : "—" }}
            <span class="yield-unit">Liter</span>
          </div>
          <div class="yield-bar-wrap">
            <div class="yield-bar">
              <div
                class="yield-fill"
                :style="{ width: yieldProgress + '%' }"
              ></div>
            </div>
          </div>
          <div class="yield-pct">{{ yieldProgress }}% dari target</div>
        </div>
      </div>
    </div>

    <!-- System Log -->
    <div class="card log-card">
      <div class="log-head">
        <h2>Log Sistem</h2>
        <div class="log-controls">
          <div class="search-wrap">
            <svg
              class="search-icon"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              v-model="search"
              class="input search-input"
              placeholder="Cari log..."
            />
          </div>
          <div class="filter-wrap">
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
            </svg>
            <select v-model="filter" class="input filter-select">
              <option v-for="f in filters" :key="f.value" :value="f.value">
                {{ f.label }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <div class="table-wrap">
        <table v-if="!loading">
          <thead>
            <tr>
              <th>CAPTIME</th>
              <th>KEJADIAN &amp; SENSOR</th>
              <th>NILAI</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in filtered.slice(0, 100)" :key="i">
              <td class="td-time">
                <div class="td-time-row">
                  <span class="time-bar"></span>
                  <div>
                    <div>{{ fmtDateTime(r.time) }}</div>
                    <div class="muted">{{ r.category }}</div>
                  </div>
                </div>
              </td>
              <td>{{ r.event }}</td>
              <td>{{ r.value }}</td>
              <td>
                <span class="badge" :class="statusBadge(r.status)">{{
                  statusLabel(r.status)
                }}</span>
              </td>
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
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--navy);
}
.page-sub {
  font-size: 13px;
  color: var(--muted);
  margin: 4px 0 0;
}

.status-badges {
  display: flex;
  gap: 8px;
  align-items: center;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 500;
  background: white;
}
.dot-ok {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ok);
}
.dot-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot-off {
  background: var(--muted);
}

/* Top grid */
.top-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

@media (max-width: 900px) {
  .top-grid {
    grid-template-columns: 1fr;
  }
}

/* Report card */
.report-card h2 {
  margin-bottom: 4px;
}
.batch-picker {
  margin-top: 12px;
  width: 100%;
}
.report-preview {
  margin: 16px 0;
  background: #f1f5f9;
  border-radius: 10px;
  padding: 18px;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
}
.preview-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12.5px;
}
.preview-row span {
  color: var(--muted);
}
.preview-row b {
  color: var(--navy);
  text-align: right;
}
.preview-blur {
  display: flex;
  flex-direction: column;
  gap: 8px;
  opacity: 0.4;
}
.preview-line {
  height: 8px;
  background: #94a3b8;
  border-radius: 4px;
}
.w50 {
  width: 50%;
}
.w60 {
  width: 60%;
}
.w70 {
  width: 70%;
}
.w80 {
  width: 80%;
}
.w90 {
  width: 90%;
}
.preview-block {
  height: 40px;
  width: 60%;
  background: #94a3b8;
  border-radius: 6px;
  margin: 4px 0;
}

.report-btns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.report-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 11px;
}

/* Right column */
.right-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Yield card */
.yield-card {
}
.yield-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.yield-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #f5ecd7;
  display: grid;
  place-items: center;
}
.yield-label {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--muted);
  text-transform: uppercase;
}
.yield-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--navy);
  margin-bottom: 10px;
}
.yield-unit {
  font-size: 16px;
  font-weight: 500;
  color: var(--muted);
  margin-left: 4px;
}
.yield-bar-wrap {
  margin-bottom: 6px;
}
.yield-bar {
  height: 8px;
  background: var(--line);
  border-radius: 999px;
  overflow: hidden;
}
.yield-fill {
  height: 100%;
  background: var(--warn);
  border-radius: 999px;
  transition: width 0.5s;
}
.yield-pct {
  font-size: 12px;
  color: var(--muted);
  text-align: right;
}

/* Power status card — dihapus bersama kartu STATUS LISTRIK */

/* Log section */
.log-card {
  margin-top: 0;
}
.log-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 10px;
}
.log-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.search-wrap {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1 1 180px;
  min-width: 0;
}
.search-icon {
  position: absolute;
  left: 10px;
  color: var(--muted);
  pointer-events: none;
}
.search-input {
  padding-left: 32px;
  width: 100%;
}
.filter-wrap svg {
  position: absolute;
  left: 10px;
  color: var(--muted);
  pointer-events: none;
}
.filter-wrap {
  position: relative;
  display: flex;
  align-items: center;
  flex: 0 0 auto;
}
.filter-select {
  padding-left: 30px;
  width: 130px;
}

@media (max-width: 600px) {
  .search-wrap {
    flex-basis: 100%;
  }
}

.table-wrap {
  overflow-x: auto;
}

.td-time-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.time-bar {
  width: 3px;
  height: 36px;
  background: var(--warn);
  border-radius: 2px;
  flex: 0 0 3px;
  margin-top: 2px;
}
</style>
