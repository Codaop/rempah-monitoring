<script setup>
import { computed } from "vue";
import { fmtTime } from "../lib/format";

const props = defineProps({
  alerts: { type: Array, default: () => [] },
});

const sorted = computed(() =>
  [...props.alerts].sort((a, b) => new Date(b.at) - new Date(a.at)).slice(0, 30)
);

function dotColor(level) {
  if (level === "danger") return "#e53e3e";
  if (level === "warn") return "#d69e2e";
  if (level === "ok" || level === "success") return "#2f9e63";
  return "#3a7ca5";
}
</script>

<template>
  <div class="card">
    <h2>Log Notifikasi</h2>
    <div class="log" v-if="sorted.length">
      <div v-for="(a, i) in sorted" :key="i" class="entry">
        <span class="dot" :style="{ background: dotColor(a.level) }"></span>
        <div class="entry-body">
          <div class="entry-msg">{{ a.message }}</div>
          <div class="entry-meta">
            {{ fmtTime(a.at) }}<template v-if="a.tag"> · {{ a.tag }}</template>
          </div>
        </div>
      </div>
    </div>
    <p v-else class="muted">Belum ada notifikasi.</p>
  </div>
</template>

<style scoped>
.log {
  display: flex;
  flex-direction: column;
}

.entry {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
  align-items: flex-start;
}
.entry:last-child {
  border-bottom: 0;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: 0 0 9px;
  margin-top: 4px;
}

.entry-body {
  flex: 1;
  min-width: 0;
}

.entry-msg {
  font-size: 13.5px;
  color: var(--text);
  font-weight: 500;
}

.entry-meta {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}
</style>
