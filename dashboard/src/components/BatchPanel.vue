<script setup>
import { computed } from 'vue'
import { fmtDateTime, fmtNum } from '../lib/format'

const props = defineProps({
  batch: { type: Object, default: null },
  log: { type: Object, default: null },
})

const progress = computed(() => {
  if (!props.batch || !props.log) return 0
  const target = Number(props.batch.target_yield_l)
  const est = Number(props.log.estimated_yield)
  if (!target) return 0
  return Math.min(100, Math.max(0, (est / target) * 100))
})
</script>

<template>
  <div class="card">
    <h2>Progres Batch</h2>

    <template v-if="batch">
      <div class="rows">
        <div class="row"><span class="muted">Waktu Mulai</span><strong>{{ fmtDateTime(batch.started_at) }}</strong></div>
        <div class="row"><span class="muted">Perkiraan Selesai</span><strong>{{ log?.estimated_finish_at ? fmtDateTime(log.estimated_finish_at) : '—' }}</strong></div>
        <div class="row"><span class="muted">Charge Mass</span><strong>{{ fmtNum(batch.charge_mass_kg) }} kg</strong></div>
        <div class="row"><span class="muted">Target Hasil</span><strong>{{ fmtNum(batch.target_yield_l) }} L</strong></div>
      </div>

      <div class="bar-wrap">
        <div class="bar">
          <div class="bar-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <div class="bar-meta">
          <span class="muted">Perkiraan Hasil</span>
          <strong>{{ fmtNum(log?.estimated_yield) }} / {{ fmtNum(batch.target_yield_l) }} L · {{ Math.round(progress) }}%</strong>
        </div>
      </div>

      <span class="badge" :class="batch.status === 'active' ? 'badge-ok' : 'badge-info'">{{ batch.status }}</span>
    </template>

    <p v-else class="muted">Belum ada batch aktif. Mulai batch baru untuk melihat progres.</p>
  </div>
</template>

<style scoped>
.rows { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
.row { display: flex; justify-content: space-between; align-items: baseline; }
.bar-wrap { margin: 4px 0 12px; }
.bar { height: 10px; background: var(--line); border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; background: linear-gradient(90deg, var(--teal), var(--ok)); border-radius: 999px; transition: width 0.6s ease; }
.bar-meta { display: flex; justify-content: space-between; margin-top: 6px; font-size: 13px; }
</style>
