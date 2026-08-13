<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: "—" },
  unit: { type: String, default: "" },
  hint: { type: String, default: "" },
  data: { type: Array, default: () => [] },
  color: { type: String, default: "#3a7ca5" },
});

const el = ref(null);
let chart = null;

function render() {
  if (!el.value) return;
  if (!chart) chart = echarts.init(el.value);
  const values = props.data.map((d) => Number(d) || 0);
  const n = values.length;
  chart.setOption({
    grid: { top: 4, bottom: 4, left: 4, right: 4 },
    xAxis: { type: "category", show: false, data: values.map((_, i) => i) },
    yAxis: {
      type: "value",
      show: false,
      min: (v) => Math.max(0, v.min - 1),
      max: (v) => v.max + 1,
    },
    series: [
      {
        type: "line",
        data: values,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: props.color },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: props.color + "44" },
              { offset: 1, color: props.color + "00" },
            ],
          },
        },
      },
    ],
    animation: n > 50 ? false : undefined,
  });
}

onMounted(() => {
  render();
  const ro = new ResizeObserver(() => chart && chart.resize());
  ro.observe(el.value);
  return () => ro.disconnect();
});

watch(
  () => props.data,
  () => nextTick(render),
  { deep: true }
);

onBeforeUnmount(() => {
  chart && chart.dispose();
  chart = null;
});
</script>

<template>
  <div class="card metric">
    <div class="metric-top">
      <div
        class="metric-icon-box"
        :style="{ background: color + '18', color: color }"
      >
        <slot name="icon">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
          />
        </slot>
      </div>
      <span class="metric-label">{{ label }}</span>
    </div>
    <div class="metric-value">
      {{ value }}<span class="metric-unit"> {{ unit }}</span>
    </div>
    <div ref="el" class="spark"></div>
  </div>
</template>

<style scoped>
.metric {
  min-width: 0;
  padding: 16px;
}

.metric-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.metric-icon-box {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  flex: 0 0 30px;
}

.metric-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.metric-value {
  font-size: 30px;
  font-weight: 700;
  color: var(--navy);
  line-height: 1.1;
  margin-bottom: 2px;
}

.metric-unit {
  font-size: 14px;
  font-weight: 500;
  color: var(--muted);
}

.spark {
  height: 44px;
  margin-top: 6px;
}
</style>
