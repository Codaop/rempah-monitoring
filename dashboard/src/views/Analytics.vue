<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import AppShell from "../components/AppShell.vue";
import AppModal from "../components/AppModal.vue";
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

// ── Modal rendemen (ticket 55) ──────────────────────────────────────────────
// Wajib diisi saat batch selesai: volume minyak atsiri hasil distilasi (ml).
const showYieldModal = ref(false);
const yieldVolume = ref("");
const yieldBusy = ref(false);
const yieldError = ref("");

// ── Pratinjau/unduh laporan in-app ──────────────────────────────────────────
// Fallback saat popup diblokir browser: tampilkan HTML laporan di iframe
// dalam modal, cetak/unduh lewat tombol aksi (tidak bergantung window.open).
const showReportModal = ref(false);
const reportHtml = ref("");
const reportFrame = ref(null);

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
    const warn = temp > 105 ? "DANGER" : "OK";
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
        // Sensor beban: massa tabung menurun saat gas terpakai. Ambang danger
        // ketika massa < 4 kg — hasil kalibrasi terbaca ±7 kg mendekati berat
        // asli tabung (bukan massa LPG 15 kg penuh).
        status: Number(s.gas_mass_kg) < 4 ? "DANGER" : "OK",
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

// ── Batch-scoped report (ticket 13) ────────────────────────────────────────

const selectedBatch = computed(
  () => batchOptions.value.find((b) => b.id === selectedBatchId.value) || null
);

// Label akhir batch untuk preview laporan — interrupted memakai interrupted_at
// dengan penanda "(terputus)" agar tidak terlihat selesai normal (ticket 61).
function previewEndLabel(b) {
  if (!b) return "";
  if (b.status === "interrupted") {
    return b.interrupted_at
      ? ` → ${fmtDateTime(b.interrupted_at).slice(0, 16)} (terputus)`
      : " (terputus)";
  }
  return b.ended_at
    ? ` → ${fmtDateTime(b.ended_at).slice(0, 16)}`
    : b.status === "active"
      ? " → Masih berjalan"
      : "";
}

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
      "id, producer_id, device_id, charge_mass_kg, target_yield_l, estimated_finish_at, started_at, ended_at, interrupted_at, status"
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
  const [batchLogRes, cmdRes, sensorRes] = await Promise.all([
    supabase.from("batch_logs").select("*").eq("batch_id", b.id).maybeSingle(),
    supabase
      .from("commands")
      .select("*")
      .eq("device_id", b.device_id)
      .order("created_at", { ascending: false })
      .limit(20),
    supabase
      .from("sensor_logs")
      .select("ts, boiler_temp_c, gas_mass_kg")
      .eq("batch_id", b.id)
      .order("ts", { ascending: false })
      .limit(5000),
  ]);
  const sensorRows = sensorRes.data || [];
  // Suhu puncak dihitung dari data sensor aktual batch (bukan hanya nilai
  // yang disimpan batch_logs) — jaminan angka tertinggi yang benar (ticket 53).
  const temps = sensorRows
    .map((r) => Number(r.boiler_temp_c))
    .filter((v) => Number.isFinite(v) && v > 0);
  const peakTemp = temps.length ? Math.max(...temps) : null;
  report.value = {
    batch: b,
    log: batchLogRes.data,
    peakTemp,
    sensorRows,
    commands: (cmdRes.data || []).filter((c) =>
      windowWithin(c.created_at, b.started_at, b.ended_at)
    ),
  };
  // Ticket 55: batch selesai & volume hasil belum tercatat → modal wajib.
  maybeOpenYieldModal(report.value);
}

// ── Modal rendemen (ticket 55) ──────────────────────────────────────────────
function maybeOpenYieldModal(r) {
  if (!r || !r.batch) return;
  const completed = r.batch.status === "completed";
  const recorded = r.log?.oil_volume_ml != null;
  if (completed && !recorded && !yieldBusy.value) {
    yieldVolume.value = "";
    yieldError.value = "";
    showYieldModal.value = true;
  }
}

function closeYieldModal() {
  if (yieldBusy.value) return;
  showYieldModal.value = false;
}

async function submitYield() {
  const r = report.value;
  if (!r || !r.batch || yieldBusy.value) return;
  const vol = Number(yieldVolume.value);
  if (!Number.isFinite(vol) || vol <= 0) {
    yieldError.value = "Volume minyak harus diisi dan lebih dari 0.";
    return;
  }
  const chargeKg = Number(r.batch.charge_mass_kg);
  if (!Number.isFinite(chargeKg) || chargeKg <= 0) {
    yieldError.value = "Berat bahan baku batch tidak valid (0/kosong).";
    return;
  }
  yieldBusy.value = true;
  yieldError.value = "";
  try {
    // Rendemen (%) = berat minyak atsiri / berat bahan baku × 100%
    // Berat minyak atsiri = nilai ml yang diisi operator (1 ml = 1 g),
    // berat bahan baku dari charge batch (kg → g).
    const rendemenPct = (vol / (chargeKg * 1000)) * 100;
    const { error } = await supabase.from("batch_logs").upsert(
      {
        batch_id: r.batch.id,
        producer_id: r.batch.producer_id,
        oil_volume_ml: vol,
        yield_rendemen_pct: rendemenPct,
        yield_recorded_at: new Date().toISOString(),
      },
      { onConflict: "batch_id" }
    );
    if (error) throw error;
    showYieldModal.value = false;
    await loadBatchReport();
  } catch (e) {
    yieldError.value = `Gagal menyimpan: ${e.message}`;
  } finally {
    yieldBusy.value = false;
  }
}

watch(selectedBatchId, loadBatchReport);

function batchStatusLabel(status) {
  if (status === "completed") return "Selesai";
  if (status === "active") return "Aktif";
  if (status === "pending") return "Menunggu";
  if (status === "interrupted") return "Terputus";
  return status ? status.toUpperCase() : "—";
}

function fmtDuration(sec) {
  const s = Math.max(1, Math.round(Number(sec)));
  const mins = Math.round(s / 60);
  if (mins < 60) return `${mins} menit`;
  const h = Math.floor(mins / 60);
  return `${h} jam ${mins % 60} menit`;
}

// Durasi batch dalam detik, dihitung langsung dari selesai − mulai.
// Fallback ke interval ISO ("PT{n}S") dari batch_logs bila timestamp tidak lengkap.
// Batch interrupted: durasi jujur dari started_at sampai interrupted_at — bukan
// seolah selesai normal (ticket 61).
function batchDurationSec(b, log) {
  const endIso = b.status === "interrupted" ? b.interrupted_at : b.ended_at;
  if (b.started_at && endIso) {
    const ms = new Date(endIso).getTime() - new Date(b.started_at).getTime();
    if (Number.isFinite(ms) && ms > 0) return ms / 1000;
  }
  const iso = log?.duration;
  if (typeof iso === "string" && iso.startsWith("PT")) {
    const sec = Number(iso.slice(2, -1));
    if (Number.isFinite(sec) && sec > 0) return sec;
  }
  return null;
}

function batchEventsHtml(r) {
  const rowsHtml = [];
  // Log sensor — konsisten dengan tabel "Log Sistem" di halaman.
  const sensorSample = (r.sensorRows || []).slice(0, 100);
  for (const s of sensorSample) {
    const temp = Number(s.boiler_temp_c);
    if (Number.isFinite(temp)) {
      const warn = temp > 105 ? "DANGER" : "OK";
      rowsHtml.push(
        `<tr><td>${fmtDateTime(s.ts)}</td><td>Lonjakan Suhu Boiler</td><td>${fmtNum(temp)} °C</td><td>${warn}</td></tr>`
      );
    }
    const gas = Number(s.gas_mass_kg);
    if (Number.isFinite(gas)) {
      rowsHtml.push(
        `<tr><td>${fmtDateTime(s.ts)}</td><td>Massa Gas</td><td>${fmtNum(gas)} kg</td><td>${gas < 4 ? "DANGER" : "OK"}</td></tr>`
      );
    }
  }
  // Log perintah — dalam jendela batch (ticket 54).
  for (const c of r.commands || []) {
    rowsHtml.push(
      `<tr><td>${fmtDateTime(c.created_at)}</td><td>Perintah ${c.action}</td><td>${c.expected_state || "—"}</td><td>${c.status}</td></tr>`
    );
  }
  return (
    rowsHtml.join("") ||
    `<tr><td colspan="4">Tidak ada log sistem untuk batch ini.</td></tr>`
  );
}

function buildReportHtml(r, print) {
  const b = r.batch;
  const log = r.log || {};
  const durationSec = batchDurationSec(b, log);
  const peakTemp = r.peakTemp ?? log.peak_temp;
  const batchId = `#${b.id.slice(0, 8).toUpperCase()}`;
  const gasUsed =
    log.gas_used_kg != null ? fmtNum(log.gas_used_kg) + " kg" : "—";
  const gasDetail =
    log.gas_start_kg != null && log.gas_end_kg != null
      ? `(awal ${fmtNum(log.gas_start_kg)} kg → akhir ${fmtNum(log.gas_end_kg)} kg)`
      : "";
  // Tanggal "Dibuat" = waktu batch berakhir tercatat (laporan akhir), bukan
  // waktu preview/download. batch_logs.created_at tidak dipakai karena bisa
  // terbentuk sejak batch dibuka (upsert awal saat batch berjalan).
  // Batch interrupted: gunakan interrupted_at — waktu batch benar-benar berhenti.
  const createdLabel = b.ended_at
    ? fmtDateTime(b.ended_at)
    : b.status === "interrupted" && b.interrupted_at
      ? fmtDateTime(b.interrupted_at)
      : log.created_at
        ? fmtDateTime(log.created_at)
        : fmtDateTime(new Date());
  const oilVolume =
    log.oil_volume_ml != null ? fmtNum(log.oil_volume_ml) + " ml" : "—";
  const rendemen =
    log.yield_rendemen_pct != null
      ? fmtNum(log.yield_rendemen_pct) + " %"
      : "—";
  // Batch terputus: baris "Selesai" jujur — pakai interrupted_at + label.
  const endLabel =
    b.status === "interrupted"
      ? b.interrupted_at
        ? `${fmtDateTime(b.interrupted_at)} (terputus)`
        : "Terputus"
      : b.ended_at
        ? fmtDateTime(b.ended_at)
        : b.status === "active"
          ? "Masih berjalan"
          : "—";
  return `<!DOCTYPE html><html lang="id"><head><meta charset="utf-8"><title>Laporan Batch REMPAH</title>
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
  <h1>REMPAH — Laporan Batch</h1>
  <div class="sub">${batchId} — ${deviceNameOf(b.device_id)} · Dibuat: ${createdLabel} · Status: ${batchStatusLabel(b.status)}</div>
  <h2>Identitas &amp; Ringkasan</h2>
  <table>
    <tr><th>Mulai</th><td>${b.started_at ? fmtDateTime(b.started_at) : "—"}</td></tr>
    <tr><th>Selesai</th><td>${endLabel}</td></tr>
    <tr><th>Durasi</th><td>${durationSec != null ? fmtDuration(durationSec) : "—"}</td></tr>
    <tr><th>Perkiraan Selesai (Input Operator)</th><td>${b.estimated_finish_at ? fmtDateTime(b.estimated_finish_at) : "—"}</td></tr>
    <tr><th>Massa Muatan</th><td>${b.charge_mass_kg ? fmtNum(b.charge_mass_kg) + " kg" : "—"}</td></tr>
    <tr><th>Penggunaan Gas</th><td>${gasUsed} ${gasDetail}</td></tr>
    <tr><th>Suhu Puncak</th><td>${peakTemp != null ? fmtNum(peakTemp) + " °C" : "—"}</td></tr>
    <tr><th>Volume Hasil Minyak</th><td>${oilVolume}</td></tr>
    <tr><th>Rendemen</th><td>${rendemen}</td></tr>
  </table>
  <h2>Log Sistem</h2>
  <table><thead><tr><th>CAPTIME</th><th>LOG</th><th>NILAI</th><th>STATUS</th></tr></thead><tbody>${batchEventsHtml(r)}</tbody></table>
  <script>${print ? "window.onload=function(){setTimeout(function(){window.print()},400)}" : ""}<\/script>
</body></html>`;
}

function openReport(print) {
  const r = report.value;
  if (!r) return;
  const html = buildReportHtml(r, print);
  // Prefer popup (perilaku lama); jika diblokir popup blocker → fallback
  // pratinjau in-app lewat iframe di modal agar tombol selalu berfungsi.
  const w = window.open("", "_blank", "width=820,height=900");
  if (w) {
    w.document.write(html);
    w.document.close();
    return;
  }
  reportHtml.value = html;
  showReportModal.value = true;
}

function printReportFromModal() {
  reportFrame.value?.contentWindow?.print();
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
            {{ deviceNameOf(b.device_id) }} ({{ batchStatusLabel(b.status)
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
              {{ deviceNameOf(report.batch.device_id) }} ·
              {{ batchStatusLabel(report.batch.status) }}</b
            >
          </div>
          <div class="preview-row">
            <span>Mulai / Selesai</span
            ><b
              >{{
                report.batch.started_at
                  ? fmtDateTime(report.batch.started_at).slice(0, 16)
                  : "—"
              }}{{ previewEndLabel(report.batch) }}</b
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
            <span>Suhu Puncak</span
            ><b>{{
              (report.peakTemp ?? report.log?.peak_temp) != null
                ? fmtNum(report.peakTemp ?? report.log?.peak_temp) + " °C"
                : "—"
            }}</b>
          </div>
          <div class="preview-row">
            <span>Penggunaan Gas</span
            ><b>{{
              report.log?.gas_used_kg != null
                ? fmtNum(report.log.gas_used_kg) + " kg"
                : "—"
            }}</b>
          </div>
          <div class="preview-row">
            <span>Volume Hasil Minyak</span
            ><b>{{
              report.log?.oil_volume_ml != null
                ? fmtNum(report.log.oil_volume_ml) + " ml"
                : "—"
            }}</b>
          </div>
          <div class="preview-row">
            <span>Rendemen</span
            ><b>{{
              report.log?.yield_rendemen_pct != null
                ? fmtNum(report.log.yield_rendemen_pct) + " %"
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

    <!-- Modal rendemen — wajib saat batch selesai (ticket 55) -->
    <AppModal
      :open="showYieldModal"
      title="Catat Volume Hasil Minyak"
      @close="closeYieldModal"
    >
      <p class="muted modal-sub">
        Batch
        {{
          report?.batch ? "#" + report.batch.id.slice(0, 8).toUpperCase() : ""
        }}
        telah selesai. Isi volume minyak atsiri hasil distilasi (diukur dengan
        gelas ukur).
      </p>
      <div class="form-row">
        <label class="field-label" for="yield-volume"
          >Volume Hasil Minyak (ml) — wajib</label
        >
        <input
          id="yield-volume"
          v-model="yieldVolume"
          class="input"
          type="number"
          min="0"
          step="0.1"
          placeholder="contoh: 150"
          autofocus
        />
      </div>
      <p v-if="report?.batch?.charge_mass_kg" class="muted calc-hint">
        Berat bahan baku: {{ fmtNum(report.batch.charge_mass_kg) }} kg —
        rendemen (%) = berat minyak (ml ≈ g) ÷ berat bahan baku (kg × 1000) ×
        100
      </p>
      <p v-if="yieldError" class="note note-err">{{ yieldError }}</p>
      <template #actions>
        <button
          class="btn btn-primary"
          :disabled="yieldBusy"
          @click="submitYield"
        >
          {{ yieldBusy ? "Menyimpan…" : "Simpan" }}
        </button>
      </template>
    </AppModal>

    <!-- Pratinjau laporan in-app — fallback saat popup diblokir browser -->
    <AppModal
      :open="showReportModal"
      title="Pratinjau Laporan Batch"
      maxWidth="860px"
      @close="showReportModal = false"
    >
      <iframe
        ref="reportFrame"
        :srcdoc="reportHtml"
        class="report-frame"
        title="Laporan Batch REMPAH"
      ></iframe>
      <template #actions>
        <button class="btn btn-ghost" @click="showReportModal = false">
          Tutup
        </button>
        <button class="btn btn-primary" @click="printReportFromModal">
          Cetak / Unduh PDF
        </button>
      </template>
    </AppModal>
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
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 16px;
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

/* Frame pratinjau laporan in-app (fallback popup) */
.report-frame {
  width: 100%;
  height: 68vh;
  min-height: 420px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
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

/* Modal rendemen (ticket 55) */
.modal-sub {
  margin: 0 0 14px;
}
.form-row {
  margin-bottom: 12px;
}
.field-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
}
.calc-hint {
  margin: 4px 0 0;
  font-size: 12px;
}
.note {
  font-size: 12.5px;
  color: var(--warn);
  background: #fdf7e0;
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  margin: 4px 0 0;
}
.note-err {
  color: var(--danger);
  background: var(--danger-soft);
}
</style>
