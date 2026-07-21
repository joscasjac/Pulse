<template>
  <div class="mt-1 h-[calc(100%-1.25rem)]">
    <!-- KPI number card -->
    <div v-if="widget.widget_type === 'Number Card'" class="flex flex-col justify-center h-full">
      <div class="text-3xl font-bold" :style="{ color: widget.color || '#111827' }">{{ metricValue }}</div>
      <div class="text-xs text-muted mt-1">{{ widget.metric }}</div>
    </div>

    <!-- List-style widgets -->
    <ul v-else-if="listLike" class="text-sm space-y-1 overflow-auto h-full pr-1">
      <li v-for="(item, n) in listItems" :key="n" class="flex items-center gap-2 text-muted">
        <span class="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
        <span class="truncate">{{ item }}</span>
      </li>
      <li v-if="!listItems.length" class="text-muted text-xs">No items</li>
    </ul>

    <!-- Bar chart -->
    <svg v-else-if="bars.length" :viewBox="`0 0 ${vw} ${vh}`" class="w-full h-full" preserveAspectRatio="none">
      <g v-for="(b, i) in bars" :key="i">
        <rect
          :x="i * (barW + gap) + gap" :y="vh - 16 - b.h" :width="barW" :height="b.h"
          rx="2" :fill="widget.color || '#3b82f6'" opacity="0.85"
        />
        <text :x="i * (barW + gap) + gap + barW / 2" :y="vh - 4" font-size="7"
              text-anchor="middle" fill="#9ca3af">{{ b.short }}</text>
      </g>
    </svg>

    <div v-else class="h-full grid place-items-center text-muted text-xs">No data</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  widget: { type: Object, required: true },
  stats: { type: Object, default: () => ({}) },
  series: { type: Object, default: () => ({}) },
})

const vw = 100
const vh = 60
const gap = 3

const listLike = computed(() =>
  ['My Tasks', 'Task List', 'Activity Feed'].includes(props.widget.widget_type)
)

const metricValue = computed(() => {
  const v = props.stats?.[props.widget.metric]
  return v === undefined || v === null ? '-' : v
})

const listItems = computed(() => {
  const src =
    props.widget.widget_type === 'Activity Feed'
      ? props.series?.workload
      : props.series?.tasks_by_state
  return (src || []).map((x) => `${x.label} - ${x.value}`)
})

const seriesData = computed(() => {
  const m = props.widget.metric
  const map = {
    velocity: props.series?.velocity,
    workload: props.series?.workload,
    tasks_by_state: props.series?.tasks_by_state,
    tasks_by_type: props.series?.tasks_by_type,
  }
  // Never fabricate data: with no real series for this metric, render "No data"
  // (the burndown widget used to synthesise a fake descending line here).
  return map[m] || []
})

const barW = computed(() => {
  const n = Math.max(seriesData.value.length, 1)
  return (vw - gap * (n + 1)) / n
})

const bars = computed(() => {
  const data = seriesData.value
  const max = Math.max(...data.map((d) => d.value), 1)
  return data.map((d) => ({
    h: ((d.value / max) * (vh - 22)) || 0,
    short: String(d.label).slice(0, 4),
  }))
})
</script>
