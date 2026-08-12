<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: '—' },
  unit: { type: String, default: '' },
  hint: { type: String, default: '' },
  data: { type: Array, default: () => [] },
  color: { type: String, default: '#3a7ca5' },
})

const el = ref(null)
let chart = null

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  const values = props.data.map((d) => Number(d) || 0)
  const n = values.length
  chart.setOption({
    grid: { top: 4, bottom: 4, left: 4, right: 4 },
    xAxis: { type: 'category', show: false, data: values.map((_, i) => i) },
    yAxis: { type: 'value', show: false, min: (v) => Math.max(0, v.min - 1), max: (v) => v.max + 1 },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color: props.color },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: props.color + '55' },
            { offset: 1, color: props.color + '00' },
          ],
        },
      },
    }],
    animation: n > 50 ? false : undefined,
  })
}

onMounted(() => {
  render()
  const ro = new ResizeObserver(() => chart && chart.resize())
  ro.observe(el.value)
  return () => ro.disconnect()
})

watch(() => props.data, () => nextTick(render), { deep: true })

onBeforeUnmount(() => {
  chart && chart.dispose()
  chart = null
})
</script>

<template>
  <div class="card metric">
    <div class="metric-label">{{ label }}</div>
    <div class="metric-value">{{ value }}<span class="metric-unit">{{ unit }}</span></div>
    <div class="metric-hint">{{ hint }}</div>
    <div ref="el" class="spark"></div>
  </div>
</template>

<style scoped>
.metric { min-width: 0; }
.metric-label { font-size: 13px; color: var(--muted); font-weight: 500; }
.metric-value { font-size: 26px; font-weight: 700; color: var(--navy); margin-top: 2px; }
.metric-unit { font-size: 13px; font-weight: 500; color: var(--muted); margin-left: 3px; }
.metric-hint { font-size: 12px; color: var(--muted); }
.spark { height: 44px; margin-top: 8px; }
</style>
