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

// ── Progress batch ──────────────────────────────────────────────────────────
const progress = computed(() => {
  if (!props.batch || !props.log) return 0;
  const target = Number(props.batch.target_yield_l);
  const est = Number(props.log.estimated_yield);
  if (!target) return 0;
  return Math.min(100, Math.max(0, (est / target) * 100));
});

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
const targetL = ref("");
const busy = ref(false);
const note = ref("");
const session = ref(null);

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
  return pickedId.value && Number.isFinite(mass) && mass > 0 && !busy.value;
});

function openModal() {
  if (!canStart.value || busy.value) return;
  note.value = "";
  pickedId.value = props.devices.find(isAvailable)?.id || "";
  showForm.value = true;
}

function closeForm() {
  if (busy.value) return;
  showForm.value = false;
  note.value = "";
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
  const mass = Number(massKg.value);
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

    const { error: bErr } = await supabase.from("batches").insert({
      producer_id: d.producer_id,
      session_id: sess.id,
      device_id: d.id,
      charge_mass_kg: mass,
      target_yield_l: targetL.value ? Number(targetL.value) : null,
      status: "pending",
    });
    if (bErr) throw bErr;

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
    note.value = `Gagal: ${e.message}`;
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
      <div class="progress-row">
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <span class="progress-pct">{{ Math.round(progress) }}% Selesai</span>
      </div>

      <div class="info-boxes">
        <div class="info-box">
          <div class="info-label">WAKTU MULAI</div>
          <div class="info-val">{{ fmtShortTime(batch.started_at) }}</div>
        </div>
        <div class="info-box">
          <div class="info-label">WAKTU SELESAI (ESTIMASI)</div>
          <div class="info-val">
            {{
              log?.estimated_finish_at
                ? fmtShortTime(log.estimated_finish_at)
                : "—"
            }}
          </div>
        </div>
        <div class="info-box">
          <div class="info-label">MASSA MUATAN</div>
          <div class="info-val">{{ fmtMass(batch.charge_mass_kg) }}</div>
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
      />
    </div>

    <div class="form-row">
      <label class="field-label" for="batch-target"
        >Target Hasil (L, opsional)</label
      >
      <input
        id="batch-target"
        v-model="targetL"
        class="input"
        type="number"
        min="0"
        step="0.01"
        placeholder="kosongkan bila belum tahu"
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

.progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.bar-track {
  flex: 1;
  height: 10px;
  background: var(--line);
  border-radius: 999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--teal);
  border-radius: 999px;
  transition: width 0.6s ease;
}

.progress-pct {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  white-space: nowrap;
  flex: 0 0 auto;
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
