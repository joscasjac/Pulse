<template>
  <span class="ava" :style="{ background: bg, width: size + 'px', height: size + 'px', fontSize: size * 0.4 + 'px' }" :title="name">
    {{ initials }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  size: { type: Number, default: 20 },
})

// deterministic, muted hue per user — legible on dark, never neon
const PALETTE = ['#6d7cff', '#3aa675', '#c88a3a', '#b06fc9', '#4f97c4', '#c96a6a', '#8a86d6', '#4fa3a3']
const initials = computed(() => (props.name || '?').replace(/@.*/, '').replace(/[._-]/g, ' ').split(' ').filter(Boolean).slice(0, 2).map((s) => s[0]).join('').toUpperCase() || '?')
const bg = computed(() => {
  let h = 0
  for (const c of props.name || '') h = (h * 31 + c.charCodeAt(0)) & 0xffff
  return PALETTE[h % PALETTE.length]
})
</script>

<style scoped>
.ava {
  display: inline-grid; place-items: center; border-radius: 50%;
  color: #0c1018; font-weight: 700; border: 2px solid var(--surface);
  letter-spacing: -0.02em; flex-shrink: 0;
}
</style>
