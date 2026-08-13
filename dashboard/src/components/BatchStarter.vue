<script setup>
import { ref, computed, onMounted } from "vue";
import { supabase } from "../lib/supabase";
import { fmtDateTime } from "../lib/format";

const props = defineProps({
  devices: { type: Array, default: () => [] },
});
const emit = defineEmits(["command", "log"]);

const session = ref(null);
const sessionDeviceIds = ref(new Set());
const showPicker = ref(false);
const picked = ref(new Set());
const batchDeviceId = ref("");
const massKg = ref("");
const busy = ref(false);
const note = ref("");

const sessionDevices = computed(() =>
  props.devices.filter((d) => sessionDeviceIds.value.has(d.id))
);
const sessionDeviceNames = computed(() =>
  sessionDevices.value.map((d) => d.name)
);
const canStart = computed(() => {
  if (!session.value || !batchDeviceId.value || busy.value) return false;
  const mass = Number(massKg.value);
  return Number.isFinite(mass) && mass > 0;
});

function togglePick(id) {
  const next = new Set(picked.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  picked.value = next;
}

function openStart() {
  picked.value = new Set(sessionDeviceIds.value);
  showPicker.value = true;
}

function closePicker() {
  if (busy.value) return;
  showPicker.value = false;
}

async function loadSession() {
  const { data: sess, error } = await supabase
    .from("sessions")
    .select("*")
    .is("closed_at", null)
    .order("opened_at", { ascending: false })
    .limit(1);
  if (error || !sess?.[0]) return;
  const { data: devRows } = await supabase
    .from("session_devices")
    .select("device_id")
    .eq("session_id", sess[0].id);
  session.value = sess[0];
  sessionDeviceIds.value = new Set((devRows || []).map((r) => r.device_id));
  const first = props.devices.find((d) => sessionDeviceIds.value.has(d.id));
  if (first) batchDeviceId.value = first.id;
}

onMounted(loadSession);

async function openSession() {
  if (picked.value.size === 0 || busy.value) return;
  busy.value = true;
  note.value = "";
  try {
    const devices = props.devices.filter((d) => picked.value.has(d.id));
    const { data: authData } = await supabase.auth.getUser();
    const userId = authData.user?.id;
    if (!userId) throw new Error("sesi pengguna tidak ditemukan.");
    const { data: sess, error: sErr } = await supabase
      .from("sessions")
      .insert({
        producer_id: devices[0].producer_id,
        opened_by: userId,
        opened_at: new Date().toISOString(),
      })
      .select("id, producer_id, opened_at")
      .single();
    if (sErr) throw sErr;
    const { error: sdErr } = await supabase
      .from("session_devices")
      .insert(
        devices.map((d) => ({
          session_id: sess.id,
          device_id: d.id,
          producer_id: d.producer_id,
        }))
      );
    if (sdErr) throw sdErr;

    session.value = sess;
    sessionDeviceIds.value = new Set(devices.map((d) => d.id));
    batchDeviceId.value = devices[0].id;
    showPicker.value = false;
    emit("log", {
      level: "info",
      tag: "SESI",
      message: `Sesi dibuka untuk ${devices.length} perangkat.`,
    });
    note.value = `Sesi dibuka untuk ${devices.map((d) => d.name).join(", ")}.`;
  } catch (e) {
    note.value = `Gagal membuka sesi: ${e.message}`;
  } finally {
    busy.value = false;
  }
}

async function startBatch() {
  if (!session.value || !batchDeviceId.value || busy.value) return;
  busy.value = true;
  note.value = "";
  try {
    const d = props.devices.find((x) => x.id === batchDeviceId.value);
    if (!d) throw new Error("perangkat tidak ditemukan.");
    const mass = Number(massKg.value);
    if (!Number.isFinite(mass) || mass <= 0)
      throw new Error("massa muatan tidak valid.");
    const { error: bErr } = await supabase.from("batches").insert({
      producer_id: d.producer_id,
      session_id: session.value.id,
      device_id: d.id,
      charge_mass_kg: mass,
      target_yield_l: null,
      status: "pending",
    });
    if (bErr) throw bErr;

    const { error: cErr } = await supabase
      .from("commands")
      .insert({
        producer_id: d.producer_id,
        device_id: d.id,
        action: "POWER_ON",
        expected_state: "IDLE",
      });
    if (cErr) throw cErr;

    const mismatch = "IDLE" && d.mode && d.mode !== "IDLE";
    emit("command", {
      device: d,
      action: "POWER_ON",
      expectedState: "IDLE",
      mismatch: Boolean(mismatch),
      at: new Date().toISOString(),
    });
    emit("log", {
      level: "info",
      tag: "BATCH",
      message: `Batch pending: ${mass} kg untuk ${d.name}.`,
    });
    note.value = mismatch
      ? `${d.name}: status belum sesuai — tekan Refresh untuk sinkronisasi.`
      : `Batch ${mass} kg dibuat; perintah POWER_ON terkirim ke ${d.name}.`;
    massKg.value = "";
  } catch (e) {
    note.value = `Gagal: ${e.message}`;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="card">
    <div class="panel-head">
      <h2>Mulai Batch Baru</h2>
      <span v-if="session" class="session-tag">Sesi aktif</span>
    </div>

    <template v-if="session">
      <div class="info-boxes">
        <div class="info-box">
          <div class="info-label">SESI DIBUKA</div>
          <div class="info-val">{{ fmtDateTime(session.opened_at) }}</div>
        </div>
        <div class="info-box">
          <div class="info-label">PERANGKAT SESI</div>
          <div class="info-val">{{ sessionDeviceNames.join(", ") || "—" }}</div>
        </div>
      </div>

      <div class="form-row">
        <select class="input" v-model="batchDeviceId">
          <option value="" disabled>Pilih Perangkat</option>
          <option v-for="d in devices" :key="d.id" :value="d.id">
            {{ d.name }} <template v-if="d.mode">({{ d.mode }})</template>
          </option>
        </select>
      </div>

      <div class="form-row">
        <input
          class="input"
          type="number"
          min="0"
          step="0.1"
          v-model="massKg"
          placeholder="Massa Muatan (kg)"
        />
      </div>

      <button
        class="btn btn-primary start-btn"
        :disabled="busy || !canStart"
        @click="startBatch"
      >
        {{ busy ? "Memulai…" : "Mulai Pemanasan" }}
      </button>
    </template>

    <p v-else class="muted">
      Belum ada sesi terbuka. Buka sesi untuk mencatat batch baru.
    </p>

    <button
      class="btn open-btn"
      :class="session ? 'btn-ghost' : 'btn-primary'"
      @click="openStart"
    >
      Buka Sesi
    </button>

    <div
      v-if="note"
      class="note"
      :class="note.includes('Gagal') ? 'note-err' : ''"
    >
      {{ note }}
    </div>
  </div>

  <div v-if="showPicker" class="overlay" @click.self="closePicker">
    <div class="modal">
      <h2 class="modal-title">Buka Sesi Baru</h2>
      <p class="muted modal-sub">
        Pilih perangkat yang tercakup dalam sesi ini.
      </p>

      <div class="pick-list">
        <label
          v-for="d in devices"
          :key="d.id"
          class="pick-item"
          :class="{ checked: picked.has(d.id) }"
        >
          <input
            type="checkbox"
            :checked="picked.has(d.id)"
            @change="togglePick(d.id)"
          />
          <span class="pick-name">{{ d.name }}</span>
          <small class="muted">{{ d.mode || "IDLE" }}</small>
        </label>
      </div>

      <div class="modal-actions">
        <button
          class="btn btn-ghost btn-sm"
          :disabled="busy"
          @click="closePicker"
        >
          Batal
        </button>
        <button
          class="btn btn-primary btn-sm"
          :disabled="busy || picked.size === 0"
          @click="openSession"
        >
          {{ busy ? "Membuka…" : "Buka Sesi" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  margin-bottom: 16px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.panel-head h2 {
  margin-bottom: 0;
}

.session-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--ok);
  color: #fff;
  letter-spacing: 0.05em;
}

.info-boxes {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 10px;
  margin-bottom: 14px;
}

.info-box {
  background: #f1f5f9;
  border-radius: 10px;
  padding: 12px 14px;
  min-width: 0;
}

.info-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.info-val {
  font-size: 14px;
  font-weight: 600;
  color: var(--navy);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.form-row {
  margin-bottom: 10px;
}

.start-btn {
  width: 100%;
  margin-bottom: 12px;
}

.open-btn {
  width: 100%;
}

.note {
  margin-top: 10px;
  font-size: 12.5px;
  color: var(--warn);
  background: #fdf7e0;
  border-radius: var(--radius-sm);
  padding: 8px 10px;
}
.note-err {
  color: var(--danger);
  background: var(--danger-soft);
}

.overlay {
  position: fixed;
  inset: 0;
  background: rgba(28, 43, 58, 0.45);
  display: grid;
  place-items: center;
  z-index: 100;
  padding: 16px;
}

.modal {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
  width: 100%;
  max-width: 420px;
}

.modal-title {
  margin-bottom: 4px;
}
.modal-sub {
  margin: 0 0 14px;
}

.pick-list {
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-bottom: 16px;
}

.pick-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
  font-size: 13.5px;
  transition: background 0.12s;
}
.pick-item:last-child {
  border-bottom: none;
}
.pick-item:hover,
.pick-item.checked {
  background: var(--teal-soft);
}
.pick-item input {
  accent-color: var(--teal);
}
.pick-name {
  font-weight: 500;
  color: var(--navy);
  flex: 1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
