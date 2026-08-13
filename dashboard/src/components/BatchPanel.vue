<script setup>
import { computed } from "vue";
import { fmtDateTime, fmtNum } from "../lib/format";

const props = defineProps({
  batch: { type: Object, default: null },
  log: { type: Object, default: null },
});

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

    <p v-else class="muted">
      Belum ada batch aktif. Mulai batch baru untuk melihat progres.
    </p>
  </div>
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

@media (max-width: 600px) {
  .info-boxes {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
