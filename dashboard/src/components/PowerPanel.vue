<script setup>
import { ref } from 'vue'
import { supabase } from '../lib/supabase'
import { fmtTime, offlineSince } from '../lib/format'

const props = defineProps({
  devices: { type: Array, default: () => [] },
})
const emit = defineEmits(['command'])

const busy = ref({})
const note = ref('')

async function sendCommand(device, action, expectedState) {
  const key = device.id
  busy.value = { ...busy.value, [key]: action }
  note.value = ''
  try {
    const { error } = await supabase
      .from('commands')
      .insert({ producer_id: device.producer_id, device_id: device.id, action, expected_state: expectedState })
    if (error) throw error
    const mismatch = expectedState && device.mode && device.mode !== expectedState
    emit('command', {
      device,
      action,
      expectedState,
      mismatch: Boolean(mismatch),
      at: new Date().toISOString(),
    })
    if (mismatch) {
      note.value = `${device.name}: status belum sesuai — kirim perintah "refresh" untuk sinkronisasi.`
    } else {
      note.value = `Perintah ${action} terkirim ke ${device.name}.`
    }
  } catch (e) {
    note.value = `Gagal mengirim perintah: ${e.message}`
  } finally {
    busy.value = { ...busy.value, [key]: null }
  }
}

function online(device) {
  const ms = offlineSince(device.last_seen_at)
  return ms >= 0 && ms < 45000
}
</script>

<template>
  <div class="card">
    <h2>Daya & Darurat</h2>

    <div class="devices">
      <div v-for="d in devices" :key="d.id" class="device">
        <div class="dev-head">
          <span class="dot" :class="online(d) ? 'on' : 'off'"></span>
          <div>
            <div class="dev-name">{{ d.name }}</div>
            <div class="muted">
              {{ online(d) ? `Online · terakhir ${fmtTime(d.last_seen_at)}` : 'Offline' }}
            </div>
          </div>
          <span class="badge" :class="d.mode === 'IDLE' || d.mode === 'STOPPED' ? 'badge-warn' : 'badge-ok'">{{ d.mode }}</span>
        </div>
        <div class="dev-actions">
          <button
            class="btn btn-primary btn-sm"
            :disabled="busy[d.id] === 'POWER_ON'"
            @click="sendCommand(d, 'POWER_ON', 'RUNNING')"
          >
            Nyalakan
          </button>
          <button
            class="btn btn-ghost btn-sm"
            :disabled="busy[d.id] === 'POWER_OFF'"
            @click="sendCommand(d, 'POWER_OFF', 'IDLE')"
          >
            Matikan
          </button>
          <button
            class="btn btn-danger btn-sm"
            :disabled="busy[d.id] === 'EMERGENCY_STOP'"
            @click="sendCommand(d, 'EMERGENCY_STOP', 'STOPPED')"
          >
            ⏻ Emergency Stop
          </button>
        </div>
      </div>
    </div>

    <div v-if="note" class="note">{{ note }}</div>
  </div>
</template>

<style scoped>
.devices { display: flex; flex-direction: column; gap: 12px; }
.device { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; }
.dev-head { display: flex; gap: 10px; align-items: center; }
.dev-name { font-weight: 600; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex: 0 0 10px; }
.dot.on { background: var(--ok); box-shadow: 0 0 0 3px rgba(47, 158, 99, 0.18); }
.dot.off { background: var(--muted); }
.badge { margin-left: auto; }
.dev-actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.note { margin-top: 10px; font-size: 13px; color: var(--warn); background: #fdf0dc; border-radius: var(--radius-sm); padding: 8px 10px; }
</style>
