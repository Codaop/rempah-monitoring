<script setup>
import {
  ref,
  computed,
  onMounted,
  onBeforeUnmount,
  watch,
  nextTick,
} from "vue";
import { useRoute } from "vue-router";
import AppShell from "../components/AppShell.vue";
import MetricCard from "../components/MetricCard.vue";
import PowerPanel from "../components/PowerPanel.vue";
import BatchPanel from "../components/BatchPanel.vue";
import NotificationLog from "../components/NotificationLog.vue";
import { supabase } from "../lib/supabase";
import { fmtNum, fmtTime, fmtDateTime, offlineSince } from "../lib/format";

const REFRESH_MS = 30000;
const OFFLINE_MS = 60000; // konsisten dengan OFFLINE_AFTER_S bridge (ticket 31)
const route = useRoute();
const batchPanel = ref(null);

const devices = ref([]);
const batch = ref(null);
const batchLog = ref(null);
const history = ref([]); // semua telemetry (multi-device)
const alerts = ref([]);
const refreshPrompt = ref("");
const loading = ref(true);
const selectedIdx = ref(0);
const commandFeedback = ref("");
const commandStatusCache = new Map(); // command_id → status terakhir (dedupe)

const selectedDevice = computed(() => devices.value[selectedIdx.value] || null);
const activeDeviceId = computed(() => selectedDevice.value?.id || null);

// Riwayat & metrik mengikuti perangkat terpilih (ticket 37) — setiap still
// menampilkan datanya sendiri tanpa tercampur device lain.
const deviceHistory = computed(() =>
  activeDeviceId.value
    ? history.value.filter((r) => r.device_id === activeDeviceId.value)
    : []
);
const latest = computed(
  () => deviceHistory.value[deviceHistory.value.length - 1] || {}
);
// Sparkline hanya menampilkan jendela pendek (60 titik terakhir, ~2 menit @2s
// atau ~5 menit @5s) — jendela penuh 240 titik membuat pergerakan tiap tick
// hanya ~1px sehingga chart terlihat beku walau re-render tepat waktu.
const SPARK_POINTS = 60;
const sparkTemp = computed(() =>
  deviceHistory.value.slice(-SPARK_POINTS).map((r) => r.boiler_temp_c)
);
const sparkGas = computed(() =>
  deviceHistory.value.slice(-SPARK_POINTS).map((r) => r.gas_mass_kg)
);
const sparkCooling = computed(() =>
  deviceHistory.value.slice(-SPARK_POINTS).map((r) => r.cooling_temp_c)
);
const sparkYield = computed(() =>
  batchLog.value && batch.value ? [batchLog.value.estimated_yield || 0] : [0]
);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 11) return "Selamat Pagi";
  if (h < 15) return "Selamat Siang";
  if (h < 18) return "Selamat Sore";
  return "Selamat Malam";
});

// Status online/offline jujur dari devices.last_seen_at (bukan lastSync).
const sensorOnline = computed(() => {
  const d = selectedDevice.value;
  if (!d) return false;
  const ms = offlineSince(d.last_seen_at);
  return ms >= 0 && ms < OFFLINE_MS;
});

// "Terhubung" benar-benar berarti data mengalir: telemetry terakhir perangkat
// terpilih masih segar (< OFFLINE_MS).
const dataFlowing = computed(() => {
  const ts = latest.value?.ts;
  if (!ts) return false;
  const age = Date.now() - new Date(ts).getTime();
  return age >= 0 && age < OFFLINE_MS;
});

const statusSubtitle = computed(() => {
  if (batch.value) return `Status sistem optimal. Batch aktif sedang berjalan.`;
  if (dataFlowing.value)
    return "Tidak ada batch aktif. Nilai di bawah real-time dari perangkat.";
  return "Tidak ada batch aktif saat ini.";
});

function pushAlert(level, tag, message, at) {
  alerts.value.push({
    level,
    tag,
    message,
    at: at || new Date().toISOString(),
  });
  if (alerts.value.length > 200)
    alerts.value.splice(0, alerts.value.length - 200);
}

function checkThresholds(row) {
  if (Number(row.boiler_temp_c) > 98)
    pushAlert(
      "danger",
      "SUHU",
      `Suhu boiler tinggi: ${fmtNum(row.boiler_temp_c)}°C (Perangkat ${row.device_id?.slice(0, 8)})`,
      row.ts
    );
  if (Number(row.water_level) < 50)
    pushAlert(
      "warn",
      "AIR",
      `Level air rendah: ${fmtNum(row.water_level)}%`,
      row.ts
    );
}

function commandStatusLabel(status) {
  if (status === "succeeded") return "Sukses";
  if (status === "failed") return "Gagal";
  if (status === "rejected") return "Ditolak";
  if (status === "dispatched") return "Dikirim ke perangkat";
  return null; // pending / lain-lain — tidak perlu notifikasi
}

async function loadAll() {
  const [devRes, stateRes, batchRes, logRes, histRes] = await Promise.all([
    supabase
      .from("devices")
      .select(
        "id, producer_id, name, mqtt_username, last_seen_at, first_seen_at"
      ),
    supabase
      .from("device_state")
      .select("device_id, producer_id, mode, updated_at"),
    supabase
      .from("batches")
      .select("*")
      .eq("status", "active")
      .order("started_at", { ascending: false })
      .limit(1),
    supabase
      .from("batch_logs")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(1),
    supabase
      .from("sensor_logs")
      .select("*")
      .order("ts", { ascending: false })
      .limit(240),
  ]);

  const states = stateRes.data || [];
  devices.value = (devRes.data || []).map((d) => ({
    ...d,
    mode: (states.find((s) => s.device_id === d.id) || {}).mode || "IDLE",
  }));

  // Landaskan grafik ke perangkat yang paling hidup: yang punya batch aktif,
  // atau yang telemetry-nya paling segar. Tanpa ini operator bisa mendarat di
  // unit idle (mis. index 0) dan sparkline tampak beku meski unit lain
  // mengalir realtime.
  const activeBatchDeviceId = batchRes.data?.[0]?.device_id;
  const liveIdx = devices.value.findIndex((d) => d.id === activeBatchDeviceId);
  if (liveIdx >= 0) {
    selectedIdx.value = liveIdx;
  } else {
    const freshest = devices.value.reduce(
      (best, d, i) => {
        const t = d.last_seen_at ? new Date(d.last_seen_at).getTime() : 0;
        return t > best.t ? { t, i } : best;
      },
      { t: 0, i: 0 }
    );
    selectedIdx.value = freshest.i;
  }

  batch.value = batchRes.data?.[0] || null;
  // batch_logs hanya relevan saat batch aktif (ticket 35: metrik idle datang
  // langsung dari telemetry, bukan dari batch).
  if (batch.value) {
    const { data: bl } = await supabase
      .from("batch_logs")
      .select("*")
      .eq("batch_id", batch.value.id)
      .maybeSingle();
    batchLog.value = bl || null;
  } else {
    batchLog.value = null;
  }
  history.value = (histRes.data || []).reverse();
  loading.value = false;

  const hasState = alerts.value.length === 0;
  if (hasState) {
    history.value
      .filter((r) => r.flame_lit)
      .slice(-30)
      .forEach((r) => checkThresholds(r));
    if (batch.value) {
      pushAlert(
        "info",
        "BATCH",
        `Batch aktif dimulai ${fmtDateTime(batch.value.started_at)}`
      );
    }
  }
}

async function refreshQuiet() {
  if (!activeDeviceId.value) return;
  const { data } = await supabase
    .from("sensor_logs")
    .select("*")
    .eq("device_id", activeDeviceId.value)
    .order("ts", { ascending: false })
    .limit(1);
  if (data?.[0]) {
    const seen = history.value.some((r) => r.id === data[0].id);
    if (!seen) {
      history.value.push(data[0]);
      if (history.value.length > 240) history.value.shift();
      checkThresholds(data[0]);
    }
  }
}

let realtime = null;
let pollTimer = null;

onMounted(async () => {
  await loadAll();

  realtime = supabase
    .channel("dashboard-live")
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "sensor_logs" },
      (payload) => {
        const row = payload.new;
        if (activeDeviceId.value && row.device_id === activeDeviceId.value) {
          const seen = history.value.some((r) => r.id === row.id);
          if (!seen) {
            history.value.push(row);
            if (history.value.length > 240) history.value.shift();
            checkThresholds(row);
          }
        }
      }
    )
    .on(
      "postgres_changes",
      { event: "UPDATE", schema: "public", table: "device_state" },
      (payload) => {
        const d = devices.value.find((x) => x.id === payload.new.device_id);
        if (d) d.mode = payload.new.mode;
        pushAlert(
          "info",
          "STATUS",
          `Perangkat ${payload.new.device_id.slice(0, 8)} → mode ${payload.new.mode}`
        );
      }
    )
    // Handshake koneksi pertama (ticket 41): first_seen_at baru terisi →
    // provisioning berhasil end-to-end, beri tahu operator sekali saja.
    .on(
      "postgres_changes",
      { event: "UPDATE", schema: "public", table: "devices" },
      (payload) => {
        const d = devices.value.find((x) => x.id === payload.new.id);
        if (d) d.first_seen_at = payload.new.first_seen_at || d.first_seen_at;
        if (payload.new.first_seen_at && !payload.old?.first_seen_at) {
          const name = d ? d.name : payload.new.id.slice(0, 8);
          pushAlert(
            "info",
            "PROVISION",
            `Perangkat ${name} terhubung pertama kali — provisioning berhasil.`
          );
        }
      }
    )
    // Pesan dari device tak dikenal (ticket 43): konfigurasi firmware salah
    // atau device liar — tampilkan agar cepat ketahuan, bukan di-drop diam-diam.
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "unknown_messages" },
      (payload) => {
        const u = payload.new;
        pushAlert(
          "warn",
          "UNKNOWN",
          `Pesan dari device tak dikenal ${String(u.device_id).slice(0, 8)} — cek konfigurasi firmware.`
        );
      }
    )
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "commands" },
      (payload) => {
        const c = payload.new;
        const d = devices.value.find((x) => x.id === c.device_id);
        const name = d ? d.name : c.device_id.slice(0, 8);
        pushAlert(
          c.action === "EMERGENCY_STOP" ? "danger" : "info",
          "CMD",
          `Perintah ${c.action} untuk ${name}`
        );
      }
    )
    // Feedback eksekusi command (ticket 32): status berubah → notifikasi +
    // catatan di PowerPanel, tanpa duplikasi.
    .on(
      "postgres_changes",
      { event: "UPDATE", schema: "public", table: "commands" },
      (payload) => {
        const c = payload.new;
        const label = commandStatusLabel(c.status);
        if (!label) return;
        if (commandStatusCache.get(c.id) === c.status) return; // dedupe
        commandStatusCache.set(c.id, c.status);
        const d = devices.value.find((x) => x.id === c.device_id);
        const name = d ? d.name : c.device_id.slice(0, 8);
        const level =
          c.status === "failed" || c.status === "rejected" ? "warn" : "info";
        pushAlert(
          level,
          "CMD",
          `Perintah ${c.action} untuk ${name}: ${label}.`
        );
        if (activeDeviceId.value === c.device_id) {
          commandFeedback.value = `Perintah ${c.action}: ${label}.`;
        }
      }
    )
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "batch_logs" },
      (payload) => {
        batchLog.value = payload.new;
        pushAlert(
          "info",
          "ESTIMASI",
          `Perkiraan hasil diperbarui: ${fmtNum(payload.new.estimated_yield)} L`
        );
      }
    )
    .subscribe();

  pollTimer = setInterval(refreshQuiet, REFRESH_MS);
});

onBeforeUnmount(() => {
  clearInterval(pollTimer);
  realtime && supabase.removeChannel(realtime);
});

// Jaga selectedIdx tetap valid saat daftar device berubah (ticket 37).
watch(devices, (list) => {
  if (selectedIdx.value >= list.length)
    selectedIdx.value = Math.max(0, list.length - 1);
});

function onCommand({ device, action, mismatch }) {
  if (mismatch) {
    refreshPrompt.value = `${device.name}: mode saat ini ${device.mode} ≠ status yang diharapkan. Tekan "Refresh" untuk memuat ulang.`;
  }
  pushAlert("info", "CMD", `Perintah ${action} untuk ${device.name}`);
}

function onBatchLog({ level, tag, message }) {
  pushAlert(level || "info", tag || "BATCH", message);
}

async function onBatchCreated() {
  await loadAll();
}

watch(
  () => route.query.start,
  async (v) => {
    if (!v) return;
    await nextTick();
    batchPanel.value?.openModal();
  },
  { immediate: true }
);

async function refreshState() {
  refreshPrompt.value = "";
  await loadAll();
  pushAlert("info", "SISTEM", "Status perangkat disinkronkan.");
}
</script>

<template>
  <AppShell>
    <!-- Header -->
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ greeting }}, Operator</h1>
        <p class="page-sub">{{ statusSubtitle }}</p>
      </div>
      <div class="status-badges">
        <span class="status-pill">
          <span
            class="dot-status"
            :class="sensorOnline ? 'dot-ok' : 'dot-off'"
          ></span>
          {{ selectedDevice ? selectedDevice.name : "Perangkat" }}
          {{ sensorOnline ? "Online" : "Offline" }}
        </span>
        <span class="status-pill">
          <svg
            width="13"
            height="13"
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
          {{ dataFlowing ? "Terhubung" : "Menunggu Data" }}
        </span>
      </div>
    </div>

    <!-- Refresh prompt -->
    <div v-if="refreshPrompt" class="refresh-prompt">
      <span>{{ refreshPrompt }}</span>
      <button class="btn btn-primary btn-sm" @click="refreshState">
        Refresh
      </button>
    </div>

    <div v-if="loading" class="muted load-msg">Memuat data…</div>

    <template v-else>
      <!-- Indikator nilai real-time saat idle (ticket 35) -->
      <div v-if="!batch && dataFlowing" class="idle-live-hint">
        <span class="dot-status dot-ok"></span>
        Nilai real-time dari perangkat — belum ada batch aktif.
      </div>

      <!-- 4 Metric Cards -->
      <div class="grid-cards">
        <MetricCard
          label="SUHU BOILER"
          :value="fmtNum(latest.boiler_temp_c)"
          unit="°C"
          :data="sparkTemp"
          color="#d69e2e"
        >
          <template #icon>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            >
              <path
                d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"
              />
            </svg>
          </template>
        </MetricCard>

        <MetricCard
          label="MASSA GAS"
          :value="fmtNum(latest.gas_mass_kg)"
          unit="kg"
          :data="sparkGas"
          color="#5a8a5a"
        >
          <template #icon>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 3v12" />
              <path d="M8 7h8" />
              <path d="M9 21h6" />
              <path d="M8 15h8" />
            </svg>
          </template>
        </MetricCard>

        <MetricCard
          label="SUHU PENDINGIN"
          :value="fmtNum(latest.cooling_temp_c)"
          unit="°C"
          :data="sparkCooling"
          color="#2f9e63"
        >
          <template #icon>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            >
              <path
                d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"
              />
            </svg>
          </template>
        </MetricCard>

        <MetricCard
          label="PERKIRAAN HASIL"
          :value="batch ? fmtNum(batchLog?.estimated_yield) : '—'"
          unit="L"
          :data="sparkYield"
          color="#a07840"
        >
          <template #icon>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            >
              <path d="M6 2v6l-2 4a6 6 0 0 0 6 8h4a6 6 0 0 0 6-8l-2-4V2" />
              <line x1="6" y1="8" x2="18" y2="8" />
            </svg>
          </template>
        </MetricCard>
      </div>

      <!-- Power + Batch panels -->
      <div class="grid-mid">
        <PowerPanel
          :devices="devices"
          :batch-active="!!batch"
          :selected-index="selectedIdx"
          :command-feedback="commandFeedback"
          @update:selected-index="selectedIdx = $event"
          @command="onCommand"
        />
        <BatchPanel
          ref="batchPanel"
          :batch="batch"
          :log="batchLog"
          :devices="devices"
          @command="onCommand"
          @log="onBatchLog"
          @created="onBatchCreated"
        />
      </div>

      <!-- Notification log -->
      <NotificationLog :alerts="alerts" />
    </template>
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
  margin: 2px 0 0;
}

.status-badges {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
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
  color: var(--text);
  background: white;
}

.dot-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot-ok {
  background: var(--ok);
}
.dot-off {
  background: var(--muted);
}

.idle-live-hint {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--teal);
  background: var(--teal-soft);
  border-radius: 999px;
  padding: 6px 14px;
  margin-bottom: 14px;
}

.refresh-prompt {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  background: #fdf0dc;
  color: #8a5a12;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  font-size: 13.5px;
}

.load-msg {
  margin-bottom: 16px;
}

.grid-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

@media (max-width: 1000px) {
  .grid-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .grid-cards {
    grid-template-columns: 1fr;
  }
}

.grid-mid {
  display: grid;
  grid-template-columns: 1fr 1.8fr;
  gap: 16px;
  margin-bottom: 16px;
}

@media (max-width: 900px) {
  .grid-mid {
    grid-template-columns: 1fr;
  }
}
</style>
