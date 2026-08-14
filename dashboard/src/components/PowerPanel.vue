<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { supabase } from "../lib/supabase";
import { offlineSince } from "../lib/format";
import AppModal from "./AppModal.vue";

const props = defineProps({
  devices: { type: Array, default: () => [] },
  batchActive: { type: Boolean, default: false },
  selectedIndex: { type: Number, default: 0 },
  commandFeedback: { type: String, default: "" },
});
const emit = defineEmits(["command", "update:selectedIndex"]);

// State perangkat terpilih diangkat ke Dashboard (v-model) agar kartu metrik,
// sparkline, dan filter realtime memakai device yang sama (ticket 37).
const selectedIdx = computed({
  get: () => {
    const max = Math.max(0, props.devices.length - 1);
    return Math.min(props.selectedIndex, max);
  },
  set: (v) => emit("update:selectedIndex", v),
});

const OFFLINE_MS = 60000; // konsisten dengan OFFLINE_AFTER_S bridge (ticket 31)
const showPicker = ref(false);
const busy = ref(false);
const note = ref("");
const confirm = ref(null); // "power_off" | "estop" | null

// ── Drag toggle ────────────────────────────────────────────────────────────
const trackEl = ref(null);
const trackW = ref(0);
const dragging = ref(false);
const dragPx = ref(0);
const dragStartX = ref(0);
const dragStartPx = ref(0);
const moved = ref(false);

const CIRCLE = 44; // diameter lingkaran toggle
const PAD = 5; // padding track kiri/kanan

const selectedDevice = computed(() => props.devices[selectedIdx.value] || null);

const isPoweredOn = computed(() => {
  const mode = selectedDevice.value?.mode;
  return mode && mode !== "IDLE" && mode !== "ESTOP";
});

const maxTravel = computed(() => Math.max(0, trackW.value - CIRCLE - PAD * 2));

// Posisi lingkaran: kanan saat ON, kiri saat OFF; bebas selama drag.
const circleOffset = computed(() => {
  if (dragging.value) return dragPx.value;
  return isPoweredOn.value ? maxTravel.value : 0;
});

const toggleLabel = computed(() =>
  isPoweredOn.value ? "Tarik untuk mematikan" : "Tarik untuk nyalakan"
);

function measureTrack() {
  if (trackEl.value) trackW.value = trackEl.value.getBoundingClientRect().width;
}

let ro = null;
onMounted(() => {
  measureTrack();
  ro = new ResizeObserver(measureTrack);
  if (trackEl.value) ro.observe(trackEl.value);
});
onBeforeUnmount(() => ro && ro.disconnect());

function onDragStart(e) {
  if (busy.value || !selectedDevice.value) return;
  dragging.value = true;
  moved.value = false;
  dragStartX.value = e.clientX;
  dragStartPx.value = circleOffset.value;
  trackEl.value?.setPointerCapture?.(e.pointerId);
}

function onDragMove(e) {
  if (!dragging.value) return;
  const dx = e.clientX - dragStartX.value;
  if (Math.abs(dx) > 5) moved.value = true;
  const next = Math.min(maxTravel.value, Math.max(0, dragStartPx.value + dx));
  dragPx.value = next;
}

function onDragEnd() {
  if (!dragging.value) return;
  dragging.value = false;
  // Tap tanpa geser → fallback toggle klik.
  if (!moved.value) {
    togglePower();
    return;
  }
  const wantOn = dragPx.value > maxTravel.value / 2;
  dragPx.value = 0;
  if (wantOn !== isPoweredOn.value) {
    if (wantOn) {
      sendCommand("POWER_ON", "IDLE");
    } else {
      requestPowerOff();
    }
  }
}

// ── Perintah daya ───────────────────────────────────────────────────────────
async function sendCommand(action, expectedState) {
  if (!selectedDevice.value) return;
  busy.value = true;
  note.value = "";
  try {
    const d = selectedDevice.value;
    const { error } = await supabase.from("commands").insert({
      producer_id: d.producer_id,
      device_id: d.id,
      action,
      expected_state: expectedState || null,
    });
    if (error) throw error;
    const mismatch = expectedState && d.mode && d.mode !== expectedState;
    emit("command", {
      device: d,
      action,
      expectedState,
      mismatch: Boolean(mismatch),
      at: new Date().toISOString(),
    });
    note.value = mismatch
      ? `${d.name}: status belum sesuai — tekan Refresh untuk sinkronisasi.`
      : `Perintah ${action} terkirim ke ${d.name}.`;
  } catch (e) {
    note.value = `Gagal: ${e.message}`;
  } finally {
    busy.value = false;
  }
}

// Matikan daya: butuh konfirmasi hanya bila batch sedang berjalan.
function requestPowerOff() {
  if (props.batchActive) confirm.value = "power_off";
  else sendCommand("POWER_OFF", selectedDevice.value?.mode);
}

function togglePower() {
  if (isPoweredOn.value) requestPowerOff();
  else sendCommand("POWER_ON", "IDLE");
}

function askEstop() {
  if (!selectedDevice.value || busy.value) return;
  confirm.value = "estop";
}

function confirmAction() {
  if (confirm.value === "power_off") {
    sendCommand("POWER_OFF", selectedDevice.value?.mode);
  } else if (confirm.value === "estop") {
    sendCommand("EMERGENCY_STOP", null);
  }
  confirm.value = null;
}

function selectDevice(idx) {
  selectedIdx.value = idx;
  showPicker.value = false;
}
</script>

<template>
  <div class="card">
    <h2>Tombol Daya &amp; Emergency</h2>

    <div
      ref="trackEl"
      class="toggle-row"
      :class="{ on: isPoweredOn, disabled: busy || !selectedDevice, dragging }"
      @pointerdown="onDragStart"
      @pointermove="onDragMove"
      @pointerup="onDragEnd"
      @pointercancel="onDragEnd"
    >
      <button
        type="button"
        class="toggle-circle"
        :style="{ transform: `translateX(${circleOffset}px)` }"
        :aria-pressed="isPoweredOn"
        aria-label="Nyalakan atau matikan daya"
        @keydown.enter.prevent="togglePower"
        @keydown.space.prevent="togglePower"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          stroke-width="2.5"
          stroke-linecap="round"
          width="18"
          height="18"
        >
          <polyline points="13 17 18 12 13 7" />
          <polyline points="6 17 11 12 6 7" />
        </svg>
      </button>
      <span class="toggle-label">{{ toggleLabel }}</span>
    </div>

    <div class="device-picker" v-if="showPicker && devices.length > 0">
      <div
        v-for="(d, i) in devices"
        :key="d.id"
        class="picker-item"
        :class="{ active: i === selectedIdx }"
        @click="selectDevice(i)"
      >
        <span
          class="picker-dot"
          :class="offlineSince(d.last_seen_at) < OFFLINE_MS ? 'on' : 'off'"
        ></span>
        {{ d.name }} <small class="muted">{{ d.mode || "IDLE" }}</small>
      </div>
    </div>

    <button class="btn-device" @click="showPicker = !showPicker">
      <svg
        width="15"
        height="15"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
      >
        <rect width="20" height="14" x="2" y="3" rx="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
      {{ selectedDevice ? selectedDevice.name : "Pilih Perangkat" }}
    </button>

    <button
      class="btn-estop"
      :disabled="busy || !selectedDevice"
      @click="askEstop"
    >
      Emergency Stop
    </button>

    <div
      v-if="note"
      class="note"
      :class="note.includes('Gagal') ? 'note-err' : ''"
    >
      {{ note }}
    </div>
    <div v-if="commandFeedback" class="note note-feedback">
      {{ commandFeedback }}
    </div>
  </div>

  <!-- Konfirmasi matikan daya saat batch berjalan -->
  <AppModal
    :open="confirm === 'power_off'"
    title="Matikan Daya?"
    @close="confirm = null"
  >
    <p class="confirm-text">
      Batch sedang berjalan. Mematikan daya akan mengakhiri batch
      {{ selectedDevice ? selectedDevice.name : "" }} dan menutupnya. Lanjutkan?
    </p>
    <template #actions>
      <button class="btn btn-ghost" @click="confirm = null">Batal</button>
      <button class="btn btn-danger" :disabled="busy" @click="confirmAction">
        Ya, Matikan
      </button>
    </template>
  </AppModal>

  <!-- Konfirmasi emergency stop -->
  <AppModal
    :open="confirm === 'estop'"
    title="Emergency Stop?"
    @close="confirm = null"
  >
    <p class="confirm-text">
      Semua proses akan dihentikan segera dan perangkat masuk mode ESTOP.
      Tindakan ini butuh reset manual. Lanjutkan?
    </p>
    <template #actions>
      <button class="btn btn-ghost" @click="confirm = null">Batal</button>
      <button class="btn btn-danger" :disabled="busy" @click="confirmAction">
        Ya, Stop
      </button>
    </template>
  </AppModal>
</template>

<style scoped>
h2 {
  margin-bottom: 16px;
}

.toggle-row {
  position: relative;
  height: 54px;
  background: #f1f5f9;
  border-radius: 999px;
  padding: 0;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 12px;
  user-select: none;
  touch-action: none;
  display: flex;
  align-items: center;
}
.toggle-row:hover:not(.disabled) {
  background: #e2e8f0;
}
.toggle-row.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-circle {
  position: absolute;
  left: 5px;
  top: 5px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: var(--ok);
  display: grid;
  place-items: center;
  cursor: grab;
  touch-action: none;
  padding: 0;
  transition:
    transform 0.25s ease,
    background 0.2s;
}
.toggle-row.on .toggle-circle {
  background: var(--warn);
}
.toggle-row.dragging .toggle-circle {
  transition: none;
  cursor: grabbing;
}
.toggle-row.disabled .toggle-circle {
  cursor: not-allowed;
}
.toggle-circle:focus-visible {
  outline: 2px solid var(--teal);
  outline-offset: 2px;
}

.toggle-label {
  flex: 1;
  text-align: center;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--navy);
  padding: 0 12px;
  pointer-events: none;
}

.confirm-text {
  font-size: 13.5px;
  color: var(--text);
  margin: 0;
  line-height: 1.5;
}

.device-picker {
  background: white;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  overflow: hidden;
  max-height: 220px;
  overflow-y: auto;
}
.picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13.5px;
  border-bottom: 1px solid var(--line);
  transition: background 0.12s;
}
.picker-item:last-child {
  border-bottom: none;
}
.picker-item:hover,
.picker-item.active {
  background: var(--teal-soft);
}
.picker-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: 0 0 8px;
}
.picker-dot.on {
  background: var(--ok);
}
.picker-dot.off {
  background: var(--muted);
}

.btn-device {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--navy);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 10px;
  transition: filter 0.15s;
}
.btn-device:hover {
  filter: brightness(1.15);
}

.btn-estop {
  width: 100%;
  padding: 13px 16px;
  background: var(--danger);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: filter 0.15s;
  letter-spacing: 0.01em;
}
.btn-estop:hover:not(:disabled) {
  filter: brightness(1.1);
}
.btn-estop:disabled {
  opacity: 0.55;
  cursor: not-allowed;
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
.note-feedback {
  color: var(--ok);
  background: #e3f5ec;
}
</style>
