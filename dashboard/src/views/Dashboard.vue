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
import { fmtNum, fmtTime, fmtDateTime } from "../lib/format";

const REFRESH_MS = 30000;
const route = useRoute();
const batchPanel = ref(null);

const devices = ref([]);
const batch = ref(null);
const batchLog = ref(null);
const history = ref([]);
const alerts = ref([]);
const refreshPrompt = ref("");
const loading = ref(true);
const lastSync = ref(null);

const activeDeviceId = computed(() => devices.value[0]?.id || null);
const latest = computed(() => history.value[history.value.length - 1] || {});
const sparkTemp = computed(() => history.value.map((r) => r.boiler_temp_c));
const sparkGas = computed(() => history.value.map((r) => r.gas_pressure_kpa));
const sparkWater = computed(() => history.value.map((r) => r.water_level));
const sparkYield = computed(() =>
  batchLog.value ? [batchLog.value.estimated_yield || 0] : [0]
);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 11) return "Selamat Pagi";
  if (h < 15) return "Selamat Siang";
  if (h < 18) return "Selamat Sore";
  return "Selamat Malam";
});

const statusSubtitle = computed(() => {
  if (batch.value) return `Status sistem optimal. Batch aktif sedang berjalan.`;
  return "Tidak ada batch aktif saat ini.";
});

const sensorOnline = computed(() => {
  if (!lastSync.value) return false;
  return Date.now() - lastSync.value.getTime() < 120000;
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

async function loadAll() {
  const [devRes, stateRes, batchRes, logRes, histRes] = await Promise.all([
    supabase
      .from("devices")
      .select("id, producer_id, name, mqtt_username, last_seen_at"),
    supabase
      .from("device_state")
      .select("device_id, producer_id, mode, updated_at"),
    supabase
      .from("batches")
      .select("*")
      .eq("status", "active")
      .order("started_at", { ascending: false })
      .limit(1),
    supabase.from("batch_logs").select("*").limit(1),
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

  batch.value = batchRes.data?.[0] || null;
  batchLog.value = logRes.data?.[0] || null;
  history.value = (histRes.data || []).reverse();
  lastSync.value = new Date();
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
  const { data } = await supabase
    .from("sensor_logs")
    .select("*")
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
          Sensor {{ sensorOnline ? "Online" : "Offline" }}
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
          Terhubung
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
          label="TEKANAN GAS"
          :value="fmtNum(latest.gas_pressure_kpa)"
          unit="bar"
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
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </template>
        </MetricCard>

        <MetricCard
          label="SUHU PENDINGIN AIR"
          :value="fmtNum(latest.boiler_temp_c)"
          unit="°C"
          :data="sparkTemp"
          color="#3a7ca5"
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
              <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
            </svg>
          </template>
        </MetricCard>

        <MetricCard
          label="PERKIRAAN HASIL"
          :value="fmtNum(batchLog?.estimated_yield)"
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
