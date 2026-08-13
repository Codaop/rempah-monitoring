<script setup>
import { ref, computed } from "vue";
import { supabase } from "../lib/supabase";
import { offlineSince } from "../lib/format";

const props = defineProps({
  devices: { type: Array, default: () => [] },
});
const emit = defineEmits(["command"]);

const selectedIdx = ref(0);
const showPicker = ref(false);
const busy = ref(false);
const note = ref("");

const selectedDevice = computed(() => props.devices[selectedIdx.value] || null);
const isOnline = computed(() => {
  if (!selectedDevice.value) return false;
  const ms = offlineSince(selectedDevice.value.last_seen_at);
  return ms >= 0 && ms < 45000;
});

const isPoweredOn = computed(() => {
  const mode = selectedDevice.value?.mode;
  return mode && mode !== "IDLE" && mode !== "ESTOP";
});

async function sendCommand(action, expectedState) {
  if (!selectedDevice.value) return;
  busy.value = true;
  note.value = "";
  try {
    const d = selectedDevice.value;
    const { error } = await supabase
      .from("commands")
      .insert({
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

function togglePower() {
  if (isPoweredOn.value) {
    sendCommand("POWER_OFF", selectedDevice.value?.mode);
  } else {
    sendCommand("POWER_ON", "IDLE");
  }
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
      class="toggle-row"
      @click="togglePower"
      :class="{ on: isPoweredOn, disabled: busy || !selectedDevice }"
    >
      <div class="toggle-circle">
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
      </div>
      <span class="toggle-label">{{
        isPoweredOn ? "Tarik untuk mematikan" : "Tarik untuk nyalakan"
      }}</span>
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
          :class="offlineSince(d.last_seen_at) < 45000 ? 'on' : 'off'"
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
      :disabled="busy"
      @click="sendCommand('EMERGENCY_STOP', null)"
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
  </div>
</template>

<style scoped>
h2 {
  margin-bottom: 16px;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 0;
  background: #f1f5f9;
  border-radius: 999px;
  padding: 5px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 12px;
  user-select: none;
}
.toggle-row:hover:not(.disabled) {
  background: #e2e8f0;
}
.toggle-row.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--ok);
  display: grid;
  place-items: center;
  flex: 0 0 44px;
  transition: background 0.2s;
}
.toggle-row.on .toggle-circle {
  background: var(--warn);
}

.toggle-label {
  flex: 1;
  text-align: center;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--navy);
  padding-right: 12px;
}

.device-picker {
  background: white;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  overflow: hidden;
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
</style>
