<script setup>
import { computed } from 'vue'
import { fmtTime } from '../lib/format'

const props = defineProps({
  alerts: { type: Array, default: () => [] },
})

const sorted = computed(() => [...props.alerts].sort((a, b) => new Date(b.at) - new Date(a.at)).slice(0, 30))
</script>

<template>
  <div class="card">
    <h2>Log Notifikasi</h2>
    <div class="log" v-if="sorted.length">
      <div v-for="(a, i) in sorted" :key="i" class="entry">
        <span class="badge" :class="`badge-${a.level}`">{{ a.tag }}</span>
        <div class="entry-body">
          <div class="entry-msg">{{ a.message }}</div>
          <div class="muted">{{ fmtTime(a.at) }}</div>
        </div>
      </div>
    </div>
    <p v-else class="muted">Belum ada notifikasi.</p>
  </div>
</template>

<style scoped>
.log { display: flex; flex-direction: column; }
.entry { display: flex; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--line); align-items: flex-start; }
.entry:last-child { border-bottom: 0; }
.entry-body { flex: 1; min-width: 0; }
.entry-msg { font-size: 13.5px; }
</style>
