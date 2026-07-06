<template>
  <div class="flex items-center gap-4">
    <svg :viewBox="`0 0 ${size} ${size}`" :width="size" :height="size" class="shrink-0">
      <circle :cx="c" :cy="c" :r="r" fill="none" :stroke="track" :stroke-width="stroke" />
      <circle v-for="(s, i) in segments" :key="i" :cx="c" :cy="c" :r="r" fill="none"
        :stroke="s.color" :stroke-width="stroke" :stroke-dasharray="`${s.len} ${circ - s.len}`"
        :stroke-dashoffset="-s.offset" :transform="`rotate(-90 ${c} ${c})`" stroke-linecap="butt" />
      <text :x="c" :y="c - 2" text-anchor="middle" font-size="18" font-weight="700" fill="currentColor">{{ total }}</text>
      <text :x="c" :y="c + 14" text-anchor="middle" font-size="8" fill="var(--muted)">{{ centerLabel }}</text>
    </svg>
    <ul class="text-xs space-y-1">
      <li v-for="(s, i) in segments" :key="i" class="flex items-center gap-1.5">
        <span class="w-2.5 h-2.5 rounded-sm" :style="{ background: s.color }" />
        <span class="text-muted">{{ s.label }}</span>
        <span class="ml-1 font-medium">{{ s.value }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  size: { type: Number, default: 120 },
  stroke: { type: Number, default: 18 },
  centerLabel: { type: String, default: 'total' },
})

const PALETTE = ['#4f8cff', '#22c55e', '#f59e0b', '#a78bfa', '#ef4444', '#06b6d4', '#ec4899', '#84cc16']
const track = 'var(--surface-2)'
const c = computed(() => props.size / 2)
const r = computed(() => props.size / 2 - props.stroke / 2)
const circ = computed(() => 2 * Math.PI * r.value)
const total = computed(() => props.data.reduce((a, d) => a + (d.value || 0), 0))

const segments = computed(() => {
  let offset = 0
  return props.data.map((d, i) => {
    const frac = total.value ? (d.value || 0) / total.value : 0
    const len = frac * circ.value
    const seg = { label: d.label, value: d.value, color: d.color || PALETTE[i % PALETTE.length], len, offset }
    offset += len
    return seg
  })
})
</script>
