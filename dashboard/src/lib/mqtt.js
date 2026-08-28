// Wrapper MQTT WebSocket untuk dashboard (ticket 01–03).
//
// Browser terhubung LANGSUNG ke broker HiveMQ Cloud via WSS, terpisah dari
// jalur bridge → Supabase. Store live (`liveByDevice`) menjadi sumber nilai
// metric cards & sparkline saat koneksi aktif; bila terputus, Dashboard.vue
// otomatis fallback ke riwayat Supabase.
import { reactive, ref } from "vue";
import mqtt from "mqtt";

const url = import.meta.env.VITE_MQTT_URL;
const username = import.meta.env.VITE_MQTT_USERNAME;
const password = import.meta.env.VITE_MQTT_PASSWORD;

// Status koneksi: idle | connecting | connected | reconnecting | offline
export const mqttStatus = ref("idle");
export const mqttError = ref("");

// Live store per device_id:
// {
//   device_id, received_at (Date.now browser), mode (dari state),
//   telemetry: { boiler_temp_c, cooling_temp_c, gas_mass_kg, water_level, drip_count, flame_lit },
//   sparks: { boiler_temp_c: [], cooling_temp_c: [], gas_mass_kg: [] }  // ring buffer
// }
export const liveByDevice = reactive({});

export const SPARK_POINTS = 60;

let client = null;
const allowedDeviceIds = new Set(); // hanya device milik operator

const NUMERIC_FIELDS = ["boiler_temp_c", "cooling_temp_c", "gas_mass_kg"];

function pushSpark(arr, value) {
  arr.push(value);
  if (arr.length > SPARK_POINTS) arr.shift();
}

function ensureEntry(deviceId) {
  if (!liveByDevice[deviceId]) {
    liveByDevice[deviceId] = {
      device_id: deviceId,
      received_at: 0,
      mode: null,
      cause: null,
      telemetry: {},
      sparks: {
        boiler_temp_c: [],
        cooling_temp_c: [],
        gas_mass_kg: [],
      },
    };
  }
  return liveByDevice[deviceId];
}

function applyTelemetry(entry, msg) {
  const t = entry.telemetry;
  for (const key of NUMERIC_FIELDS) {
    const v = Number(msg[key]);
    if (Number.isFinite(v)) {
      t[key] = v;
      pushSpark(entry.sparks[key], v);
    }
  }
  if (msg.water_level !== undefined) t.water_level = Number(msg.water_level);
  if (msg.drip_count !== undefined) t.drip_count = Number(msg.drip_count);
  if (msg.flame_lit !== undefined) t.flame_lit = Boolean(msg.flame_lit);
  entry.received_at = Date.now();
}

function applyState(entry, msg) {
  if (typeof msg.mode === "string" && msg.mode) entry.mode = msg.mode;
  if (msg.cause) entry.cause = msg.cause;
  entry.received_at = Date.now();
}

// Telemetry payload TIDAK membawa device_id (asal dari segmen topik); state
// membawa device_id di payload. Timestamp `ts` dari firmware masih millis()
// (bukan ISO), jadi kesegaran memakai waktu terima browser, bukan `ts`.
function handleMessage(topic, buf) {
  const parts = topic.split("/");
  if (parts.length !== 3) return;
  const deviceId = parts[1];
  const kind = parts[2];
  if (!allowedDeviceIds.has(deviceId)) return;

  let msg;
  try {
    msg = JSON.parse(buf.toString());
  } catch {
    return;
  }
  if (!msg || typeof msg !== "object") return;

  const entry = ensureEntry(deviceId);
  if (kind === "telemetry") applyTelemetry(entry, msg);
  else if (kind === "state") applyState(entry, msg);
}

export function setAllowedDevices(deviceIds = []) {
  allowedDeviceIds.clear();
  for (const id of deviceIds) {
    if (id) allowedDeviceIds.add(id);
  }
}

export function connectMqtt(deviceIds = []) {
  setAllowedDevices(deviceIds);

  if (!url || !username || !password) {
    console.warn(
      "[REMPAH] ⚠ Konfigurasi MQTT WebSocket tidak ditemukan — dashboard " +
        "memakai jalur Supabase Realtime.\n" +
        "Tambah di dashboard/.env:\n" +
        "  VITE_MQTT_URL=wss://<host>:8884/mqtt\n" +
        "  VITE_MQTT_USERNAME=rempah_hivemq\n" +
        "  VITE_MQTT_PASSWORD=<password>\n" +
        "Lihat docs/ops.md."
    );
    mqttStatus.value = "offline";
    return null;
  }

  if (client) return client;

  mqttStatus.value = "connecting";
  client = mqtt.connect(url, {
    username,
    password,
    clientId: `rempah-dashboard-${Math.random().toString(16).slice(2, 10)}`,
    reconnectPeriod: 5000,
    connectTimeout: 10000,
    keepalive: 30,
    clean: true,
  });

  client.on("connect", () => {
    mqttStatus.value = "connected";
    mqttError.value = "";
    client.subscribe("rempah/+/telemetry", { qos: 1 });
    client.subscribe("rempah/+/state", { qos: 1 });
  });

  client.on("reconnect", () => {
    mqttStatus.value = "reconnecting";
  });

  client.on("close", () => {
    mqttStatus.value = "offline";
  });

  client.on("offline", () => {
    mqttStatus.value = "offline";
  });

  client.on("error", (err) => {
    mqttError.value = String((err && err.message) || err);
  });

  client.on("message", handleMessage);

  return client;
}

export function disconnectMqtt() {
  if (client) {
    try {
      client.end(true);
    } catch {
      // abaikan — client sudah dalam keadaan tertutup
    }
    client = null;
  }
  mqttStatus.value = "idle";
}
