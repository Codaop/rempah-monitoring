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
import AppModal from "../components/AppModal.vue";
import { supabase } from "../lib/supabase";
import {
  mqttStatus,
  mqttError,
  liveByDevice,
  connectMqtt,
  disconnectMqtt,
  setAllowedDevices,
  seedDrips,
  publishCommand,
} from "../lib/mqtt";
import { fmtNum, fmtTime, fmtDateTime, offlineSince } from "../lib/format";

// Auto-refresh ringan tiap 10 detik — HANYA menyegarkan data metric cards
// (riwayat telemetry + seed tetesan). Perubahan device/batch dilayani
// subscription Realtime; reload penuh hanya saat mount/refresh manual.
const REFRESH_MS = 10000;
const OFFLINE_MS = 60000; // konsisten dengan OFFLINE_AFTER_S bridge (ticket 31)
const route = useRoute();
const batchPanel = ref(null);

const devices = ref([]);
const batch = ref(null);
const batchLog = ref(null);
const history = ref([]); // semua telemetry (multi-device)
const alerts = ref([]);
const refreshPrompt = ref("");
const lastMessageAt = ref(null); // terakhir kali terima pesan MQTT dari broker

// ── Resume batch terputus (ticket 60) ───────────────────────────────────────
// Saat device kembali online & ada batch interrupted, modal konfirmasi muncul:
// lanjutkan batch yang sama (RESUME_BATCH + POWER_ON) atau mulai batch baru.
const interruptedBatch = ref(null); // batch interrupted terbaru
const handledInterruptIds = ref(new Set()); // nasib sudah diputuskan (dismiss/resume/baru)
const resumeBusy = ref(false);
const resumeError = ref("");
const loading = ref(true);
const lastSyncAt = ref(null); // terakhir kali auto-refresh penuh selesai
const selectedIdx = ref(0);
const commandFeedback = ref("");
const commandStatusCache = new Map(); // command_id → status terakhir (dedupe)

const selectedDevice = computed(() => devices.value[selectedIdx.value] || null);
const activeDeviceId = computed(() => selectedDevice.value?.id || null);

// ── Penghitung tetesan (card TOTAL TETESAN) ────────────────────────────────
// drip_count dari broker sudah merupakan jumlah total tetesan yang dideteksi
// hardware — ditampilkan apa adanya (tidak diakumulasi). Sesuai tiket 65,
// card HANYA menampilkan data yang benar-benar datang dari broker: tanpa data
// live segar, card menampilkan 0 (tidak ada fallback ke riwayat DB).
const batchDeviceId = computed(() => batch.value?.device_id || null);
// Device yang datanya ditampilkan card tetesan: batch aktif jika ada, selain
// itu perangkat terpilih. Kebasahan dicek pada entri live device yang sama.
const dripDeviceId = computed(
  () => batchDeviceId.value || activeDeviceId.value || null
);
const dripLiveEntry = computed(() =>
  dripDeviceId.value ? liveByDevice[dripDeviceId.value] : null
);
const dripFresh = computed(() => {
  const e = dripLiveEntry.value;
  return !!(e && e.received_at && Date.now() - e.received_at < OFFLINE_MS);
});
const dripValue = computed(() => {
  if (
    mqttStatus.value === "connected" &&
    dripFresh.value &&
    dripLiveEntry.value?.total_drips != null
  ) {
    return fmtNum(dripLiveEntry.value.total_drips, 0);
  }
  return "0";
});
const sparkDrips = computed(() => {
  if (mqttStatus.value === "connected" && dripFresh.value) {
    return dripLiveEntry.value?.sparks?.drip_count || [];
  }
  return [];
});

// Riwayat & metrik mengikuti perangkat terpilih (ticket 37) — setiap still
// menampilkan datanya sendiri tanpa tercampur device lain.
const deviceHistory = computed(() =>
  activeDeviceId.value
    ? history.value.filter((r) => r.device_id === activeDeviceId.value)
    : []
);
// latest: saat live segar → nilai telemetry live; saat basi/putus → 0 (bukan
// fallback riwayat DB). Sesuai tiket 65: card menampilkan 0 ketika tidak ada
// data segar dari broker.
const latest = computed(() => {
  if (useLive.value && liveEntry.value) {
    const e = liveEntry.value;
    return {
      ...(e.telemetry || {}),
      mode: e.mode,
      ts: e.received_at ? new Date(e.received_at).toISOString() : null,
    };
  }
  // Data basi / MQTT terputus → kembalikan 0 untuk semua metric numerik
  return {
    boiler_temp_c: 0,
    gas_mass_kg: 0,
    cooling_temp_c: 0,
    water_level: 0,
    drip_count: 0,
    flame_lit: false,
    mode: null,
    ts: null,
  };
});
// Sparkline hanya menampilkan jendela pendek (60 titik terakhir) — jendela
// penuh 240 titik membuat pergerakan tiap tick hanya ~1px sehingga chart
// terlihat beku walau re-render tepat waktu.
const SPARK_POINTS = 60;
// Jalur live MQTT (ticket 01–03): saat browser terhubung langsung ke broker,
// nilai & sparkline diambil dari store live; TIDAK ADA fallback ke riwayat
// Supabase (tiket 65: card menampilkan 0 & sparkline kosong saat data basi).
const liveEntry = computed(() =>
  activeDeviceId.value ? liveByDevice[activeDeviceId.value] : null
);
const liveFresh = computed(() => {
  const e = liveEntry.value;
  return !!(e && e.received_at && Date.now() - e.received_at < OFFLINE_MS);
});
const useLive = computed(
  () => mqttStatus.value === "connected" && liveFresh.value
);
function pickSpark(deviceId, key) {
  if (!useLive.value) return [];
  const s = liveByDevice[deviceId]?.sparks?.[key];
  return s && s.length ? s : [];
}
const sparkTemp = computed(() =>
  pickSpark(activeDeviceId.value, "boiler_temp_c")
);
const sparkGas = computed(() => pickSpark(activeDeviceId.value, "gas_mass_kg"));
const sparkCooling = computed(() =>
  pickSpark(activeDeviceId.value, "cooling_temp_c")
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

// Indikator jalur data live di header (ticket 01).
const isReconnecting = computed(() => {
  if (!lastMessageAt.value) return false;
  const age = Date.now() - new Date(lastMessageAt.value).getTime();
  const staleData = age > REFRESH_MS; // 10 detik
  // Reconnecting jika: >10s tidak ada data + status MQTT bukan connected (atau connecting)
  return staleData && (mqttStatus.value !== "connected" || mqttStatus.value === "connecting");
});

const mqttLabel = computed(() => {
  if (isReconnecting.value) return "MQTT Menghubungkan…";
  if (mqttStatus.value === "connected")
    return useLive.value ? "MQTT Live" : "MQTT Terhubung";
  if (mqttStatus.value === "connecting") return "MQTT Menghubungkan…";
  if (mqttStatus.value === "reconnecting") return "MQTT Menghubung ulang…";
  return "Realtime";
});
const mqttDotClass = computed(() => {
  if (mqttStatus.value === "connected") return "dot-ok";
  if (mqttStatus.value === "connecting" || mqttStatus.value === "reconnecting")
    return "dot-warn";
  if (isReconnecting.value) return "dot-warn";
  return "dot-off";
});

const hasOnlineDevice = computed(() => 
  devices.value.some(d => sensorOnline.value)
);

const statusSubtitle = computed(() => {
  if (isReconnecting.value) return "Menunggu data dari broker MQTT (10+ detik)";
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
  if (Number(row.boiler_temp_c) > 105)
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
  const [devRes, stateRes, batchRes, logRes, histRes, interruptedRes] =
    await Promise.all([
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
      // Batch terputus terbaru (ticket 58): device mati mendadak → status
      // interrupted. Dipakai modal konfirmasi resume (ticket 60).
      supabase
        .from("batches")
        .select("*")
        .eq("status", "interrupted")
        .order("interrupted_at", { ascending: false })
        .limit(1),
    ]);

  const states = stateRes.data || [];
  devices.value = (devRes.data || []).map((d) => ({
    ...d,
    mode: (states.find((s) => s.device_id === d.id) || {}).mode || "IDLE",
  }));

  // Landaskan grafik ke perangkat yang paling hidup: yang punya batch aktif,
  // atau yang telemetry-nya paling segar. Tanpa ini operator bisa mendarat di
  // unit idle (mis. index 0) dan sparkline tampak beku meski unit lain
  // mengalir realtime. Hanya dilakukan saat load PERTAMA — pada auto-refresh
  // berikutnya pilihan operator di PowerPanel tidak boleh di-reset.
  if (loading.value) {
    const activeBatchDeviceId = batchRes.data?.[0]?.device_id;
    const liveIdx = devices.value.findIndex(
      (d) => d.id === activeBatchDeviceId
    );
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
  }

  batch.value = batchRes.data?.[0] || null;
  interruptedBatch.value = interruptedRes.data?.[0] || null;
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

  // Seed penghitung tetesan: nilai drip_count TERAKHIR batch aktif dari
  // Supabase — bukan SUM, karena tiap baris sudah bernilai kumulatif.
  // (Tiket 65: dripDbTotal dihapus — card tidak pakai fallback riwayat DB)
  if (batch.value) {
    const { data: drips } = await supabase
      .from("sensor_logs")
      .select("drip_count")
      .eq("batch_id", batch.value.id)
      .order("ts", { ascending: false })
      .limit(1);
    const latest = Number(drips?.[0]?.drip_count) || 0;
    seedDrips(batch.value.device_id, latest);
  }
  history.value = (histRes.data || []).reverse();
  loading.value = false;

  // TAMBAHAN: deteksi device mati (>1 menit tidak menerima data)
  const deadDevices = devices.value.filter((d) => {
    if (!d.last_seen_at) return false;
    const ms = offlineSince(d.last_seen_at);
    return ms >= OFFLINE_MS;
  });
  if (deadDevices.length > 0 && alerts.value.length === 0) {
    pushAlert(
      "warn",
      "SISTEM",
      `${deadDevices.length} perangkat mati (>1 menit tidak data dari broker)`
    );
  }

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

// Auto-refresh ringan (REFRESH_MS): HANYA menyegarkan data yang dipakai
// metric cards — riwayat telemetry (sparkline) & nilai tetesan batch aktif.
// Tidak me-reset devices/batch/state sehingga pilihan operator di panel
// tidak terganggu; transisi batch/device dilayani subscription Realtime.
async function refreshCards() {
  try {
    const batchId = batch.value?.id || null;
    const [histRes, seedRes] = await Promise.all([
      supabase
        .from("sensor_logs")
        .select("*")
        .order("ts", { ascending: false })
        .limit(240),
      batchId
        ? supabase
            .from("sensor_logs")
            .select("drip_count")
            .eq("batch_id", batchId)
            .order("ts", { ascending: false })
            .limit(1)
        : Promise.resolve({ data: null }),
    ]);
    if (histRes.data) history.value = histRes.data.reverse();
    if (seedRes.data && batchId) {
      // Nilai terakhir sudah kumulatif — ganti, bukan tambah.
      const latest = Number(seedRes.data?.[0]?.drip_count) || 0;
      seedDrips(batch.value.device_id, latest);
    }
    lastMessageAt.value = new Date().toISOString();
    lastSyncAt.value = new Date().toISOString();
  } catch (err) {
    console.warn("[REMPAH] Refresh card gagal:", err);
  }
}

let realtime = null;
let pollTimer = null;

onMounted(async () => {
  await loadAll();

  // Jalur live: browser terhubung langsung ke broker MQTT (ticket 01).
  connectMqtt(devices.value.map((d) => d.id));

  realtime = supabase
    .channel("dashboard-live")
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "sensor_logs" },
      (payload) => {
        const row = payload.new;
        // Nilai drip_count sudah kumulatif — tampilkan nilai terbaru saja,
        // jangan diakumulasi (revisi logika card tetesan).
        // (Tiket 65: dripDbTotal dihapus — card tidak pakai fallback riwayat DB)
        if (activeDeviceId.value && row.device_id === activeDeviceId.value) {
          const seen = history.value.some((r) => r.id === row.id);
          if (!seen) {
            history.value.push(row);
            if (history.value.length > 240) history.value.shift();
            checkThresholds(row);
          }
        }
        // TAMBAHAN: track terakhir kali terima pesan dari broker MQTT
        lastMessageAt.value = new Date().toISOString();
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
        if (d) {
          d.first_seen_at = payload.new.first_seen_at || d.first_seen_at;
          d.last_seen_at = payload.new.last_seen_at || d.last_seen_at;
        }
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
    // Transisi batch (aktif → terputus/selesai/batal) dilayani Realtime —
    // status panel & modal resume tetap segar tanpa reload penuh.
    .on(
      "postgres_changes",
      { event: "UPDATE", schema: "public", table: "batches" },
      (payload) => {
        const nb = payload.new;
        if (nb.status === "active") {
          const isSame = batch.value?.id === nb.id;
          batch.value = nb;
          if (interruptedBatch.value?.id === nb.id) {
            interruptedBatch.value = null;
          }
          if (!isSame) batchLog.value = null;
        } else if (nb.status === "interrupted") {
          if (batch.value?.id === nb.id) {
            batch.value = null;
            batchLog.value = null;
          }
          interruptedBatch.value = nb;
        } else {
          // completed / cancelled — batch aktif berakhir
          if (batch.value?.id === nb.id) {
            batch.value = null;
            batchLog.value = null;
          }
          if (interruptedBatch.value?.id === nb.id) {
            interruptedBatch.value = null;
          }
        }
      }
    )
    .subscribe();

  pollTimer = setInterval(refreshCards, REFRESH_MS);
});

onBeforeUnmount(() => {
  clearInterval(pollTimer);
  realtime && supabase.removeChannel(realtime);
  disconnectMqtt();
});

// Jaga selectedIdx tetap valid & sinkronkan daftar device ke live store MQTT
// (ticket 37, 01) — device baru ikut difilter/subscribe tanpa reload.
watch(devices, (list) => {
  if (selectedIdx.value >= list.length)
    selectedIdx.value = Math.max(0, list.length - 1);
  setAllowedDevices(list.map((d) => d.id));
});

// Mode device ikut ter-update dari pesan state MQTT yang retained (ticket 02).
watch(liveByDevice, (store) => {
  for (const dev of devices.value) {
    const e = store[dev.id];
    if (e && e.mode && dev.mode !== e.mode) dev.mode = e.mode;
  }
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

function deviceName(id) {
  const d = devices.value.find((x) => x.id === id);
  return d ? d.name : id ? `Perangkat ${id.slice(0, 8)}` : "—";
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

// ── Resume batch terputus (ticket 60) ───────────────────────────────────────
// Modal muncul saat device pemilik batch interrupted kembali online dan nasib
// batch itu belum diputuskan di sesi ini (dismiss/resume/baru).
const resumeDeviceOnline = computed(() => {
  const b = interruptedBatch.value;
  if (!b) return false;
  const d = devices.value.find((x) => x.id === b.device_id);
  if (!d) return false;
  // Gunakan lastMessageAt jika ada (tracking broker MQTT), else fallback ke last_seen_at
  let ms;
  if (lastMessageAt.value) {
    ms = Date.now() - new Date(lastMessageAt.value).getTime();
  } else {
    ms = offlineSince(d.last_seen_at);
  }
  return ms >= 0 && ms < OFFLINE_MS;
});

const showResumeModal = computed(() => {
  const b = interruptedBatch.value;
  if (!b) return false;
  if (handledInterruptIds.value.has(b.id)) return false;
  return resumeDeviceOnline.value;
});

function dismissResumeModal() {
  // Operator menunda keputusan → jangan muncul lagi tiap auto-refresh.
  if (interruptedBatch.value)
    handledInterruptIds.value.add(interruptedBatch.value.id);
}

async function resumeInterruptedBatch() {
  const b = interruptedBatch.value;
  if (!b || resumeBusy.value) return;
  const d = devices.value.find((x) => x.id === b.device_id);
  if (!d) return;
  resumeBusy.value = true;
  resumeError.value = "";
  try {
    // RESUME_BATCH: bridge mengembalikan batch interrupted → active (ticket 59).
    const { error: rErr } = await supabase.from("commands").insert({
      producer_id: d.producer_id,
      device_id: d.id,
      action: "RESUME_BATCH",
      expected_state: null,
    });
    if (rErr) throw rErr;
    // Nyalakan perangkat seketika via broker MQTT — tanpa menunggu poll bridge
    // (2s). Firmware idempoten terhadap "mulai" ganda; bridge tetap meneruskan
    // POWER_ON di bawah sebagai jalur cadangan + lifecycle command.
    publishCommand(d.id, "mulai");
    // POWER_ON: nyalakan ulang pemanasan; telemetry lanjut ke batch yang sama.
    const { error: pErr } = await supabase.from("commands").insert({
      producer_id: d.producer_id,
      device_id: d.id,
      action: "POWER_ON",
      expected_state: "IDLE",
    });
    if (pErr) throw pErr;
    handledInterruptIds.value.add(b.id);
    await loadAll();
    pushAlert(
      "info",
      "BATCH",
      `Batch #${b.id.slice(0, 4).toUpperCase()} dilanjutkan — menunggu perangkat menyala.`
    );
  } catch (e) {
    resumeError.value = `Gagal: ${e.message}`;
  } finally {
    resumeBusy.value = false;
  }
}

function startNewBatchInstead() {
  const b = interruptedBatch.value;
  if (!b) return;
  // Batch lama tetap interrupted (masuk riwayat), form batch baru dibuka.
  handledInterruptIds.value.add(b.id);
  pushAlert(
    "info",
    "BATCH",
    `Batch #${b.id.slice(0, 4).toUpperCase()} dibiarkan terputus — membuat batch baru.`
  );
  batchPanel.value?.openModal();
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
        <span
          class="status-pill"
          :title="
            mqttError || 'Jalur data live: MQTT WebSocket ↔ Supabase Realtime'
          "
        >
          <span class="dot-status" :class="mqttDotClass"></span>
          {{ mqttLabel }}
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
          label="TOTAL TETESAN"
          :value="dripValue"
          unit="tetes"
          :data="sparkDrips"
          color="#3a7ca5"
          :hint="
            mqttStatus === 'connected' && dripFresh
              ? 'Total tetesan perangkat (live)'
              : 'Menunggu data perangkat'
          "
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
              <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
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

    <!-- Modal resume batch terputus (ticket 60) -->
    <AppModal
      :open="showResumeModal"
      title="Batch Terputus Ditemukan"
      @close="dismissResumeModal"
    >
      <p class="muted modal-sub">
        Batch
        {{
          interruptedBatch
            ? "#" + interruptedBatch.id.slice(0, 8).toUpperCase()
            : ""
        }}
        (
        {{ interruptedBatch ? deviceName(interruptedBatch.device_id) : "—" }}
        ) terputus saat mesin mati mendadak. Perangkat sudah kembali online.
        Lanjutkan batch yang sama atau mulai batch baru?
      </p>
      <div class="resume-info" v-if="interruptedBatch">
        <div class="info-row">
          <span>Mulai</span
          ><b>{{
            interruptedBatch.started_at
              ? fmtDateTime(interruptedBatch.started_at).slice(0, 16)
              : "—"
          }}</b>
        </div>
        <div class="info-row">
          <span>Terputus</span
          ><b>{{
            interruptedBatch.interrupted_at
              ? fmtDateTime(interruptedBatch.interrupted_at).slice(0, 16)
              : "—"
          }}</b>
        </div>
        <div class="info-row">
          <span>Massa Muatan</span
          ><b>{{
            interruptedBatch.charge_mass_kg
              ? fmtNum(interruptedBatch.charge_mass_kg) + " kg"
              : "—"
          }}</b>
        </div>
      </div>
      <p v-if="resumeError" class="note note-err">{{ resumeError }}</p>
      <template #actions>
        <button
          class="btn btn-ghost"
          :disabled="resumeBusy"
          @click="dismissResumeModal"
        >
          Nanti
        </button>
        <button
          class="btn btn-ghost"
          :disabled="resumeBusy || !hasOnlineDevice.value"
          @click="startNewBatchInstead"
        >
          Mulai Batch Baru
        </button>
        <button
          class="btn btn-primary"
          :disabled="resumeBusy || !hasOnlineDevice.value"
          @click="resumeInterruptedBatch"
        >
          {{ resumeBusy ? "Mengirim…" : "Lanjutkan Batch" }}
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
.dot-warn {
  background: #d69e2e;
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

/* Modal resume batch (ticket 60) */
.modal-sub {
  margin: 0 0 14px;
}

.resume-info {
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  overflow: hidden;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
}
.info-row:last-child {
  border-bottom: none;
}
.info-row span {
  color: var(--muted);
}
.info-row b {
  color: var(--navy);
  font-weight: 600;
  text-align: right;
}

.note-err {
  color: var(--danger);
  background: var(--danger-soft);
}
</style>
