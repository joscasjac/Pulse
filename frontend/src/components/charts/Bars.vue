<template>
  <svg :viewBox="`0 0 ${w} ${h}`" class="w-full" :style="{ height: h + 'px' }">
    <g v-for="(b, i) in bars" :key="i">
      <rect :x="b.x" :y="b.y" :width="barW" :height="b.h" rx="3" :fill="b.color" />
      <text :x="b.x + barW / 2" :y="b.y - 3" text-anchor="middle" font-size="8" fill="currentColor">{{ b.value }}</text>
      <text :x="b.x + barW / 2" :y="h - 3" text-anchor="middle" font-size="7" fill="var(--muted)">{{ b.short }}</text>
    </g>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  height: { type: Number, default: 160 },
  color: { type: String, default: '#4f8cff' },
})

const w = 320
const h = computed(() => props.height)
const pad = 16
const gap = 8

const barW = computed(() => {
  const n = Math.max(props.data.length, 1)
  return (w - pad * 2 - gap * (n - 1)) / n
})

const bars = computed(() => {
  const max = Math.max(...props.data.map((d) => d.value || 0), 1)
  const chartH = h.value - 26
  return props.data.map((d, i) => {
    const bh = ((d.value || 0) / max) * chartH
    return {
      x: pad + i * (barW.value + gap),
      y: chartH - bh + 6,
      h: bh,
      value: d.value,
      short: String(d.label).slice(0, 6),
      color: d.color || props.color,
    }
  })
})
</script>
