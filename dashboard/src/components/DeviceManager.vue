<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { supabase } from "../lib/supabase";
import { fmtDateTime, offlineSince } from "../lib/format";
import AppModal from "./AppModal.vue";

// Root topic MQTT — ditetapkan "rempah" (keputusan tim, ticket 39); bukan
// env configurable lagi. Semua komponen (bridge, fake_esp32, probe) memakai
// root yang sama.
const TOPIC_ROOT = "rempah";
const OFFLINE_MS = 60000;

// Kredensial MQTT bersama (shared credential) — satu username/password untuk
// semua device, di-set di env dashboard (VITE_MQTT_DEVICE_*). Kalau kosong,
// kartu flash menampilkan pesan "hubungi admin" (fallback).
const SHARED_USERNAME = import.meta.env.VITE_MQTT_DEVICE_USERNAME || "";
const SHARED_PASSWORD = import.meta.env.VITE_MQTT_DEVICE_PASSWORD || "";
const hasSharedCredential = Boolean(SHARED_USERNAME && SHARED_PASSWORD);

const devices = ref([]);
const loading = ref(true);
const loadError = ref("");

// ── Form registrasi (ticket 36, diadaptasi ticket 39) ───────────────────────
const newName = ref("");
const regBusy = ref(false);
const regError = ref("");
const flash = ref(null); // device baru → kartu flash provisioning

// ── Kartu flash yang dibuka ulang (ticket 38) ───────────────────────────────
const reflash = ref(null); // device dari daftar → kartu flash

const sortedDevices = computed(() =>
  [...devices.value].sort((a, b) =>
    String(a.name).localeCompare(String(b.name))
  )
);

function mqttTopics(deviceId) {
  return {
    telemetry: `${TOPIC_ROOT}/${deviceId}/telemetry`,
    state: `${TOPIC_ROOT}/${deviceId}/state`,
    command: `${TOPIC_ROOT}/${deviceId}/command`,
  };
}

function deviceOnline(d) {
  const ms = offlineSince(d.last_seen_at);
  return ms >= 0 && ms < OFFLINE_MS;
}

function shortId(id) {
  return id ? id.slice(0, 8).toUpperCase() : "—";
}

async function loadDevices() {
  loading.value = true;
  loadError.value = "";
  const { data, error } = await supabase
    .from("devices")
    .select(
      "id, producer_id, name, mqtt_username, mqtt_password, last_seen_at, created_at"
    )
    .order("created_at", { ascending: true });
  if (error) {
    loadError.value = error.message;
    devices.value = [];
  } else {
    devices.value = data || [];
  }
  loading.value = false;
}

async function registerDevice() {
  const name = newName.value.trim();
  if (!name) {
    regError.value = "Nama perangkat wajib diisi.";
    return;
  }
  regBusy.value = true;
  regError.value = "";
  try {
    const { data: authData } = await supabase.auth.getUser();
    const userId = authData.user?.id;
    if (!userId) throw new Error("sesi pengguna tidak ditemukan.");

    const { data: op } = await supabase
      .from("operators")
      .select("producer_id")
      .eq("id", userId)
      .maybeSingle();
    if (!op?.producer_id)
      throw new Error("operator belum terhubung ke producer.");

    // Model kredensial bersama (ticket 39): tidak ada mqtt_username/password
    // per-device — semua device memakai satu credential yang sama (env
    // dashboard). Baris cukup berisi nama + producer.
    const { data: row, error } = await supabase
      .from("devices")
      .insert({ producer_id: op.producer_id, name })
      .select("id, producer_id, name, mqtt_username, mqtt_password, created_at")
      .single();
    if (error) throw error;

    devices.value.push(row);
    flash.value = row;
    newName.value = "";
    await loadDevices();
  } catch (e) {
    regError.value = `Gagal mendaftarkan perangkat: ${e.message}`;
  } finally {
    regBusy.value = false;
  }
}

// ── Salin ke clipboard ───────────────────────────────────────────────────────
const copied = ref("");
let copyTimer = null;

async function copyText(label, text) {
  try {
    await navigator.clipboard.writeText(text);
    copied.value = label;
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => (copied.value = ""), 2000);
  } catch {
    copied.value = "";
  }
}

onMounted(loadDevices);
onBeforeUnmount(() => clearTimeout(copyTimer));
</script>

<template>
  <div class="device-manager">
    <div v-if="loadError" class="note note-err">{{ loadError }}</div>

    <!-- Form registrasi -->
    <div class="reg-card">
      <h3 class="reg-title">Daftarkan Perangkat Baru</h3>
      <p class="muted reg-sub">
        Buat baris device milik producer Anda. Semua perangkat memakai satu
        kredensial MQTT bersama — kartu flash berisi nilai untuk konfigurasi
        awal firmware (UUID, topic, kredensial).
      </p>
      <div class="reg-row">
        <input
          v-model="newName"
          class="input reg-input"
          type="text"
          placeholder="Nama perangkat, mis. Boiler Utama"
          @keyup.enter="registerDevice"
        />
        <button
          class="btn btn-primary"
          :disabled="regBusy || !newName.trim()"
          @click="registerDevice"
        >
          {{ regBusy ? "Mendaftar…" : "Daftarkan" }}
        </button>
      </div>
      <p v-if="regError" class="note note-err">{{ regError }}</p>
    </div>

    <!-- Daftar perangkat (ticket 38) -->
    <div class="list-card">
      <h3 class="reg-title">Perangkat Terdaftar</h3>
      <p v-if="loading" class="muted">Memuat perangkat…</p>
      <p v-else-if="devices.length === 0" class="muted">
        Belum ada perangkat terdaftar.
      </p>
      <div v-else class="dev-table-wrap">
        <table class="dev-table">
          <thead>
            <tr>
              <th>NAMA</th>
              <th>UUID</th>
              <th>DIDAFTARKAN</th>
              <th>STATUS</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in sortedDevices" :key="d.id">
              <td class="td-name">{{ d.name }}</td>
              <td class="td-mono">{{ d.id }}</td>
              <td class="td-muted">{{ fmtDateTime(d.created_at) }}</td>
              <td>
                <span
                  class="status-chip"
                  :class="deviceOnline(d) ? 'ok' : 'off'"
                >
                  <span class="chip-dot"></span>
                  {{ deviceOnline(d) ? "Online" : "Offline" }}
                </span>
              </td>
              <td>
                <button
                  class="btn btn-ghost btn-sm flash-btn"
                  @click="reflash = d"
                >
                  Kartu Flash
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Kartu flash provisioning — device baru (ticket 39) -->
    <AppModal
      :open="!!flash"
      title="Kartu Flash Perangkat"
      max-width="520px"
      @close="flash = null"
    >
      <template v-if="flash">
        <p class="muted modal-sub">
          Nilai referensi untuk konfigurasi awal firmware ESP32 (flash via
          USB/serial) — bukan mekanisme self-provisioning.
        </p>

        <div class="flash-block">
          <div class="flash-label">NAMA PERANGKAT</div>
          <div class="flash-value">{{ flash.name }}</div>
        </div>
        <div class="flash-block">
          <div class="flash-label">DEVICE ID (UUID)</div>
          <div class="flash-row">
            <code class="flash-code">{{ flash.id }}</code>
            <button class="copy-btn" @click="copyText('id', flash.id)">
              {{ copied === "id" ? "✓" : "Salin" }}
            </button>
          </div>
        </div>

        <div class="flash-block">
          <div class="flash-label">TOPIC MQTT</div>
          <div class="topic-row">
            <code class="flash-code">{{ mqttTopics(flash.id).telemetry }}</code>
            <button
              class="copy-btn"
              @click="copyText('telemetry', mqttTopics(flash.id).telemetry)"
            >
              {{ copied === "telemetry" ? "✓" : "Salin" }}
            </button>
          </div>
          <div class="topic-row">
            <code class="flash-code">{{ mqttTopics(flash.id).state }}</code>
            <button
              class="copy-btn"
              @click="copyText('state', mqttTopics(flash.id).state)"
            >
              {{ copied === "state" ? "✓" : "Salin" }}
            </button>
          </div>
          <div class="topic-row">
            <code class="flash-code">{{ mqttTopics(flash.id).command }}</code>
            <button
              class="copy-btn"
              @click="copyText('command', mqttTopics(flash.id).command)"
            >
              {{ copied === "command" ? "✓" : "Salin" }}
            </button>
          </div>
        </div>

        <template v-if="hasSharedCredential">
          <div class="flash-block">
            <div class="flash-label">MQTT USERNAME (BERSAMA)</div>
            <div class="flash-row">
              <code class="flash-code">{{ SHARED_USERNAME }}</code>
              <button
                class="copy-btn"
                @click="copyText('user', SHARED_USERNAME)"
              >
                {{ copied === "user" ? "✓" : "Salin" }}
              </button>
            </div>
          </div>
          <div class="flash-block">
            <div class="flash-label">MQTT PASSWORD (BERSAMA)</div>
            <div class="flash-row">
              <code class="flash-code">{{ SHARED_PASSWORD }}</code>
              <button
                class="copy-btn"
                @click="copyText('pass', SHARED_PASSWORD)"
              >
                {{ copied === "pass" ? "✓" : "Salin" }}
              </button>
            </div>
          </div>
        </template>
        <p v-else class="note note-warn">
          Kredensial MQTT bersama belum dikonfigurasi di env dashboard
          (VITE_MQTT_DEVICE_USERNAME / VITE_MQTT_DEVICE_PASSWORD) — hubungi
          admin sistem.
        </p>

        <p class="muted flash-foot">
          Root topic: <code>rempah/</code>. Gunakan client_id unik per perangkat
          di firmware (mis. <code>client-&lt;device_id&gt;</code>) — bukan di
          web HiveMQ.
        </p>
      </template>

      <template #actions>
        <button class="btn btn-ghost" @click="flash = null">Tutup</button>
      </template>
    </AppModal>

    <!-- Kartu flash provisioning — dibuka ulang dari daftar (ticket 38) -->
    <AppModal
      :open="!!reflash"
      title="Kartu Flash Perangkat"
      max-width="520px"
      @close="reflash = null"
    >
      <template v-if="reflash">
        <p class="muted modal-sub">
          Nilai referensi provisioning — UUID, topic, dan kredensial MQTT
          bersama untuk konfigurasi awal firmware.
        </p>

        <div class="flash-block">
          <div class="flash-label">NAMA PERANGKAT</div>
          <div class="flash-value">{{ reflash.name }}</div>
        </div>
        <div class="flash-block">
          <div class="flash-label">DEVICE ID (UUID)</div>
          <div class="flash-row">
            <code class="flash-code">{{ reflash.id }}</code>
            <button class="copy-btn" @click="copyText('id', reflash.id)">
              {{ copied === "id" ? "✓" : "Salin" }}
            </button>
          </div>
        </div>
        <div class="flash-block">
          <div class="flash-label">DIDAFTARKAN</div>
          <div class="flash-value">{{ fmtDateTime(reflash.created_at) }}</div>
        </div>

        <div class="flash-block">
          <div class="flash-label">TOPIC MQTT</div>
          <div class="topic-row">
            <code class="flash-code">{{
              mqttTopics(reflash.id).telemetry
            }}</code>
            <button
              class="copy-btn"
              @click="copyText('telemetry', mqttTopics(reflash.id).telemetry)"
            >
              {{ copied === "telemetry" ? "✓" : "Salin" }}
            </button>
          </div>
          <div class="topic-row">
            <code class="flash-code">{{ mqttTopics(reflash.id).state }}</code>
            <button
              class="copy-btn"
              @click="copyText('state', mqttTopics(reflash.id).state)"
            >
              {{ copied === "state" ? "✓" : "Salin" }}
            </button>
          </div>
          <div class="topic-row">
            <code class="flash-code">{{ mqttTopics(reflash.id).command }}</code>
            <button
              class="copy-btn"
              @click="copyText('command', mqttTopics(reflash.id).command)"
            >
              {{ copied === "command" ? "✓" : "Salin" }}
            </button>
          </div>
        </div>

        <template v-if="hasSharedCredential">
          <div class="flash-block">
            <div class="flash-label">MQTT USERNAME (BERSAMA)</div>
            <div class="flash-row">
              <code class="flash-code">{{ SHARED_USERNAME }}</code>
              <button
                class="copy-btn"
                @click="copyText('user', SHARED_USERNAME)"
              >
                {{ copied === "user" ? "✓" : "Salin" }}
              </button>
            </div>
          </div>
          <div class="flash-block">
            <div class="flash-label">MQTT PASSWORD (BERSAMA)</div>
            <div class="flash-row">
              <code class="flash-code">{{ SHARED_PASSWORD }}</code>
              <button
                class="copy-btn"
                @click="copyText('pass', SHARED_PASSWORD)"
              >
                {{ copied === "pass" ? "✓" : "Salin" }}
              </button>
            </div>
          </div>
        </template>
        <p v-else class="note note-warn">
          Kredensial MQTT bersama belum dikonfigurasi di env dashboard
          (VITE_MQTT_DEVICE_USERNAME / VITE_MQTT_DEVICE_PASSWORD) — hubungi
          admin sistem.
        </p>

        <p class="muted flash-foot">
          Root topic: <code>rempah/</code>. Gunakan client_id unik per perangkat
          di firmware (mis. <code>client-&lt;device_id&gt;</code>) — bukan di
          web HiveMQ.
        </p>
      </template>

      <template #actions>
        <button class="btn btn-ghost" @click="reflash = null">Tutup</button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.reg-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
  margin-bottom: 16px;
}

.reg-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--navy);
  margin: 0 0 2px;
}

.reg-sub {
  margin: 0 0 12px;
  font-size: 12.5px;
}

.reg-row {
  display: flex;
  gap: 10px;
}

.reg-input {
  flex: 1;
  min-width: 0;
}

.list-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
}

.list-card .reg-title {
  margin-bottom: 12px;
}

.dev-table-wrap {
  overflow-x: auto;
}

.dev-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.dev-table th {
  text-align: left;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--muted);
  text-transform: uppercase;
  padding: 6px 10px;
  border-bottom: 1px solid var(--line);
}

.dev-table td {
  padding: 10px;
  border-bottom: 1px solid var(--line);
  color: var(--text);
  vertical-align: middle;
}

.dev-table tr:last-child td {
  border-bottom: none;
}

.td-name {
  font-weight: 600;
  color: var(--navy);
  white-space: nowrap;
}

.td-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
  color: var(--muted);
}

.td-muted {
  color: var(--muted);
  white-space: nowrap;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

.status-chip.ok {
  background: #e3f5ec;
  color: var(--ok);
}

.status-chip.off {
  background: var(--danger-soft);
  color: var(--danger);
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.flash-btn {
  white-space: nowrap;
}

/* Kartu flash */
.modal-sub {
  margin: 0 0 14px;
}

.flash-block {
  margin-bottom: 12px;
}

.flash-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--muted);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.flash-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--navy);
}

.flash-row,
.topic-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.flash-code {
  flex: 1;
  min-width: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 7px 10px;
  color: var(--navy);
  overflow-x: auto;
  white-space: nowrap;
}

.copy-btn {
  flex: 0 0 auto;
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: white;
  color: var(--teal);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.12s;
}

.copy-btn:hover {
  background: var(--teal-soft);
}

.topic-row {
  margin-top: 6px;
}

.flash-foot {
  margin: 14px 0 0;
  font-size: 12px;
}

.note {
  font-size: 12.5px;
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  margin: 4px 0 0;
}

.note-err {
  color: var(--danger);
  background: var(--danger-soft);
  margin-bottom: 12px;
}

.note-warn {
  color: var(--warn);
  background: #fdf7e0;
  margin: 0 0 12px;
}

@media (max-width: 520px) {
  .reg-row {
    flex-direction: column;
  }
}
</style>
