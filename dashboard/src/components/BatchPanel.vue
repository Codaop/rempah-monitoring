<script setup>
import { ref, computed, onMounted } from "vue";
import { fmtDateTime, fmtNum, offlineSince } from "../lib/format";
import { supabase } from "../lib/supabase";
import AppModal from "./AppModal.vue";

const props = defineProps({
  batch: { type: Object, default: null },
  log: { type: Object, default: null },
  devices: { type: Array, default: () => [] },
});
const emit = defineEmits(["command", "log", "created"]);

// ── Status batch ────────────────────────────────────────────────────────────

const statusLabel = computed(() => {
  if (!props.batch) return null;
  const mode = props.batch.status?.toUpperCase();
  if (mode === "ACTIVE") return "DISTILASI";
  if (mode === "COMPLETED") return "SELESAI";
  if (mode === "IDLE") return "IDLE";
  return mode || "AKTIF";
});

const batchId = computed(() => {
  if (!props.batch?.id) return null;
  return "#" + props.batch.id.slice(0, 4).toUpperCase();
});

// Check if current batch was synced from device (charge_source === "device")
const isBatchFromDevice = computed(() => {
  return props.batch?.charge_source === "device";
});

function fmtMass(kg) {
  if (!kg) return "—";
  const g = Number(kg) * 1000;
  return g >= 1000 ? `${fmtNum(kg)} kg` : `${Math.round(g)} g`;
}

function fmtShortTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Mulai batch baru ────────────────────────────────────────────────────────
const showForm = ref(false);
const pickedId = ref("");
const massKg = ref("");
const finishAt = ref("");
const busy = ref(false);
const note = ref("");
const session = ref(null);
const pendingBatches = ref({}); // device_id -> { charge_mass_kg, charge_source }

// Perangkat tersedia = online (< 60 dtk, konsisten OFFLINE_AFTER_S) DAN mode IDLE.
const OFFLINE_MS = 60000;

function isAvailable(d) {
  if (!d || !d.mode || d.mode !== "IDLE") return false;
  const ms = offlineSince(d.last_seen_at);
  return ms >= 0 && ms < OFFLINE_MS;
}

function statusLabelOf(d) {
  if (!d) return "—";
  if (d.mode && d.mode !== "IDLE") return d.mode;
  const ms = offlineSince(d.last_seen_at);
  if (ms < 0 || ms >= OFFLINE_MS) return "Offline";
  return "Tersedia";
}

const canStart = computed(() => props.devices.some(isAvailable));
const canSubmit = computed(() => {
  const mass = Number(massKg.value);
  // Allow submit if mass is from device (pre-filled and read-only) or manually entered valid mass
  const hasValidMass =
    isMassFromDevice.value || (Number.isFinite(mass) && mass > 0);
  return pickedId.value && hasValidMass && !busy.value;
});

// Check if selected device has pending batch from device
const selectedDevicePendingBatch = computed(() => {
  return pendingBatches.value[pickedId.value];
});

const isMassFromDevice = computed(() => {
  const pb = selectedDevicePendingBatch.value;
  return pb?.charge_source === "device";
});

async function loadPendingBatches() {
  try {
    const { data, error } = await supabase
      .from("batches")
      .select("device_id, charge_mass_kg, charge_source")
      .eq("status", "pending");
    if (error) throw error;
    const map = {};
    for (const b of data || []) {
      map[b.device_id] = {
        charge_mass_kg: b.charge_mass_kg,
        charge_source: b.charge_source,
      };
    }
    pendingBatches.value = map;
  } catch (e) {
    console.warn("Failed to load pending batches:", e);
  }
}

async function openModal() {
  if (!canStart.value || busy.value) return;
  await loadPendingBatches();
  note.value = "";
  pickedId.value = props.devices.find(isAvailable)?.id || "";

  // Pre-fill mass if device has pending batch from device
  const pb = pendingBatches.value[pickedId.value];
  if (pb?.charge_source === "device" && pb.charge_mass_kg) {
    massKg.value = String(pb.charge_mass_kg);
  }
  showForm.value = true;
}

function closeForm() {
  if (busy.value) return;
  showForm.value = false;
  note.value = "";
  massKg.value = "";
  finishAt.value = "";
  pickedId.value = "";
}

async function loadSession() {
  const { data: sess, error } = await supabase
    .from("sessions")
    .select("*")
    .is("closed_at", null)
    .order("opened_at", { ascending: false })
    .limit(1);
  if (error || !sess?.[0]) return;
  session.value = sess[0];
}

onMounted(loadSession);

async function startBatch() {
  if (busy.value) return;
  const d = props.devices.find((x) => x.id === pickedId.value);
  if (!d || !isAvailable(d)) return;

  // If mass is from device, use that value (read-only)
  let mass = Number(massKg.value);
  if (
    isMassFromDevice.value &&
    selectedDevicePendingBatch.value?.charge_mass_kg
  ) {
    mass = Number(selectedDevicePendingBatch.value.charge_mass_kg);
  }

  if (!Number.isFinite(mass) || mass <= 0) {
    note.value = "Massa muatan tidak valid.";
    return;
  }
  busy.value = true;
  note.value = "";
  try {
    const { data: authData } = await supabase.auth.getUser();
    const userId = authData.user?.id;
    if (!userId) throw new Error("sesi pengguna tidak ditemukan.");

    let sess = session.value;
    if (!sess) {
      const { data: s, error: sErr } = await supabase
        .from("sessions")
        .insert({
          producer_id: d.producer_id,
          opened_by: userId,
          opened_at: new Date().toISOString(),
        })
        .select("id, producer_id, opened_at")
        .single();
      if (sErr) throw sErr;
      const { error: sdErr } = await supabase.from("session_devices").insert({
        session_id: s.id,
        device_id: d.id,
        producer_id: d.producer_id,
      });
      if (sdErr) throw sdErr;
      sess = s;
      session.value = s;
      emit("log", {
        level: "info",
        tag: "SESI",
        message: `Sesi dibuka untuk ${d.name}.`,
      });
    }

    // If there's a pending batch from device, update it instead of creating new
    let batchId;
    const pb = selectedDevicePendingBatch.value;
    if (pb?.charge_source === "device" && pb.charge_mass_kg) {
      // Update existing pending batch from device
      const { data: updatedBatch, error: uErr } = await supabase
        .from("batches")
        .update({
          producer_id: d.producer_id,
          session_id: sess.id,
          charge_mass_kg: mass,
          estimated_finish_at: finishAt.value
            ? new Date(finishAt.value).toISOString()
            : null,
          status: "pending",
          charge_source: "device",
        })
        .eq("device_id", d.id)
        .eq("status", "pending")
        .select("id")
        .single();
      if (uErr) throw uErr;
      batchId = updatedBatch.id;
    } else {
      // Create new batch (dashboard-initiated)
      const { data: newBatch, error: bErr } = await supabase
        .from("batches")
        .insert({
          producer_id: d.producer_id,
          session_id: sess.id,
          device_id: d.id,
          charge_mass_kg: mass,
          estimated_finish_at: finishAt.value
            ? new Date(finishAt.value).toISOString()
            : null,
          status: "pending",
          charge_source: "dashboard",
        })
        .select("id")
        .single();
      if (bErr) throw bErr;
      batchId = newBatch.id;
    }

    const { error: cErr } = await supabase.from("commands").insert({
      producer_id: d.producer_id,
      device_id: d.id,
      action: "POWER_ON",
      expected_state: "IDLE",
    });
    if (cErr) throw cErr;

    const mismatch = d.mode && d.mode !== "IDLE";
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
    emit("created");
    closeForm();
  } catch (e) {
    // User-friendly error messages following UX laws:
    // 1. Visibility of system status - clear what happened
    // 2. Match between system and real world - user language, not technical
    // 3. User control and freedom - clear way to recover
    // 4. Consistency and standards - consistent error format
    // 5. Error prevention - prevent errors where possible
    // 6. Recognition rather than recall - don't make user remember error codes
    // 7. Flexibility and efficiency - shortcuts for experts
    // 8. Aesthetic and minimalist design - concise messages
    // 9. Help users recognize, diagnose, recover - actionable guidance
    // 10. Help and documentation - link to help if needed
    let userMessage = "Gagal memulai batch.";
    const errMsg = e.message || String(e);

    if (
      errMsg.includes("duplicate") ||
      errMsg.includes("conflict") ||
      errMsg.includes("unique")
    ) {
      userMessage =
        "Batch sudah ada untuk perangkat ini. Silakan tunggu atau batalkan batch yang berjalan.";
    } else if (
      errMsg.includes("network") ||
      errMsg.includes("fetch") ||
      errMsg.includes("ECONNREFUSED")
    ) {
      userMessage =
        "Tidak dapat terhubung ke server. Periksa koneksi internet dan coba lagi.";
    } else if (
      errMsg.includes("auth") ||
      errMsg.includes("sesi") ||
      errMsg.includes("JWT")
    ) {
      userMessage = "Sesi Anda telah berakhir. Silakan login ulang.";
    } else if (
      errMsg.includes("permission") ||
      errMsg.includes("RLS") ||
      errMsg.includes("policy")
    ) {
      userMessage =
        "Anda tidak memiliki izin untuk memulai batch ini. Hubungi administrator.";
    } else if (
      errMsg.includes("invalid") ||
      errMsg.includes("valid") ||
      errMsg.includes("constraint")
    ) {
      userMessage =
        "Data yang dimasukkan tidak valid. Periksa massa muatan dan coba lagi.";
    } else if (errMsg.includes("timeout")) {
      userMessage =
        "Permintaan timeout. Server terlalu lama merespons. Coba lagi.";
    } else {
      // Fallback: show first 100 chars of error for debugging
      userMessage = `Gagal memulai batch: ${errMsg.slice(0, 100)}`;
    }

    note.value = userMessage;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="card">
    <div class="panel-head">
      <h2>Progress Batch {{ batchId || "" }}</h2>
      <span v-if="statusLabel" class="status-tag">{{ statusLabel }}</span>
    </div>

    <template v-if="batch">
      <div class="info-boxes">
        <div class="info-box">
          <div class="info-label">WAKTU MULAI</div>
          <div class="info-val">{{ fmtShortTime(batch.started_at) }}</div>
        </div>
        <div class="info-box">
          <div class="info-label">WAKTU SELESAI (ESTIMASI)</div>
          <div class="info-val">
            {{
              batch.estimated_finish_at
                ? fmtShortTime(batch.estimated_finish_at)
                : log?.estimated_finish_at
                  ? fmtShortTime(log.estimated_finish_at)
                  : "—"
            }}
          </div>
        </div>
        <div class="info-box">
          <div class="info-label">MASSA MUATAN</div>
          <div class="info-val">
            {{ fmtMass(batch.charge_mass_kg) }}
            <span v-if="isBatchFromDevice" class="source-badge"
              >dari perangkat</span
            >
          </div>
        </div>
      </div>
    </template>

    <p v-else class="muted empty-hint">
      Belum ada batch aktif. Mulai batch baru untuk melihat progres.
    </p>

    <!-- Mulai Batch Baru (di tengah panel) -->
    <div class="start-wrap">
      <button
        class="btn btn-primary start-btn"
        :disabled="!canStart || busy"
        @click="openModal"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="16" />
          <line x1="8" y1="12" x2="16" y2="12" />
        </svg>
        Mulai Batch Baru
      </button>
      <p v-if="!canStart" class="muted start-hint">
        Tidak ada perangkat tersedia untuk memulai batch.
      </p>
    </div>
  </div>

  <!-- Modal form batch baru -->
  <AppModal :open="showForm" title="Mulai Batch Baru" @close="closeForm">
    <p class="muted modal-sub">
      Pilih perangkat yang akan digunakan untuk batch distilasi baru.
    </p>

    <div class="pick-list">
      <label
        v-for="d in devices"
        :key="d.id"
        class="pick-item"
        :class="{ checked: pickedId === d.id, disabled: !isAvailable(d) }"
      >
        <input
          type="radio"
          name="batch-device"
          :value="d.id"
          v-model="pickedId"
          :disabled="!isAvailable(d)"
        />
        <span class="pick-name">{{ d.name }}</span>
        <span class="pick-status" :class="isAvailable(d) ? 'ok' : 'off'">
          {{ statusLabelOf(d) }}
        </span>
      </label>
    </div>

    <div class="form-row">
      <label class="field-label" for="batch-mass">Massa Muatan (kg)</label>
      <input
        id="batch-mass"
        v-model="massKg"
        class="input"
        type="number"
        min="0"
        step="0.1"
        placeholder="contoh: 5.5"
        :disabled="isMassFromDevice"
        :readonly="isMassFromDevice"
      />
      <p v-if="isMassFromDevice" class="field-hint">
        Massa muatan diset dari perangkat (ESP32 remote):
        {{ fmtMass(selectedDevicePendingBatch?.charge_mass_kg) }}
      </p>
    </div>

    <div class="form-row">
      <label class="field-label" for="batch-finish"
        >Perkiraan Waktu Selesai (opsional)</label
      >
      <input
        id="batch-finish"
        v-model="finishAt"
        class="input"
        type="datetime-local"
      />
    </div>

    <p
      v-if="note"
      class="note"
      :class="note.includes('Gagal') ? 'note-err' : ''"
    >
      {{ note }}
    </p>

    <template #actions>
      <button class="btn btn-ghost" :disabled="busy" @click="closeForm">
        Batal
      </button>
      <button
        class="btn btn-primary"
        :disabled="busy || !canSubmit"
        @click="startBatch"
      >
        {{ busy ? "Menyimpan…" : "Mulai Batch" }}
      </button>
    </template>
  </AppModal>
</template>

<style scoped>
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.panel-head h2 {
  margin-bottom: 0;
}

.status-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--navy);
  color: #fff;
  letter-spacing: 0.05em;
}

.info-boxes {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.info-box {
  background: #f1f5f9;
  border-radius: 10px;
  padding: 12px 14px;
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
  font-size: 15px;
  font-weight: 600;
  color: var(--navy);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.source-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--teal-soft);
  color: var(--teal);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.empty-hint {
  margin: 0 0 16px;
}

.start-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.start-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 26px;
  font-size: 14px;
}

.start-hint {
  margin: 0;
  font-size: 12.5px;
}

.modal-sub {
  margin: 0 0 14px;
}

.pick-list {
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-bottom: 14px;
  max-height: 240px;
  overflow-y: auto;
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
.pick-item:hover:not(.disabled),
.pick-item.checked {
  background: var(--teal-soft);
}
.pick-item.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.pick-item input {
  accent-color: var(--teal);
}
.pick-name {
  font-weight: 500;
  color: var(--navy);
  flex: 1;
}
.pick-status {
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 999px;
  white-space: nowrap;
}
.pick-status.ok {
  background: #e3f5ec;
  color: var(--ok);
}
.pick-status.off {
  background: var(--danger-soft);
  color: var(--danger);
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

.field-hint {
  margin: 4px 0 0;
  font-size: 11.5px;
  color: var(--muted);
  font-style: italic;
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

@media (max-width: 600px) {
  .info-boxes {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
