<template>
  <svg viewBox="0 0 120 70" class="w-full" style="max-height: 130px">
    <path :d="arc(0, 180)" fill="none" stroke="var(--surface-2)" stroke-width="12" stroke-linecap="round" />
    <path :d="arc(0, pct * 1.8)" fill="none" :stroke="color" stroke-width="12" stroke-linecap="round" />
    <text x="60" y="52" text-anchor="middle" font-size="20" font-weight="700" fill="currentColor">{{ Math.round(pct) }}%</text>
    <text x="60" y="64" text-anchor="middle" font-size="7" fill="var(--muted)">{{ label }}</text>
  </svg>
</template>

<script setup>
const props = defineProps({
  value: { type: Number, default: 0 },
  label: { type: String, default: '' },
  color: { type: String, default: '#22c55e' },
})
const pct = Math.max(0, Math.min(100, props.value))

// semicircle arc from angle a1 to a2 (degrees), radius 48, center (60,54)
function polar(cx, cy, r, deg) {
  const rad = (deg - 180) * (Math.PI / 180)
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}
function arc(a1, a2) {
  const [x1, y1] = polar(60, 54, 48, a1)
  const [x2, y2] = polar(60, 54, 48, a2)
  const large = a2 - a1 > 180 ? 1 : 0
  return `M ${x1} ${y1} A 48 48 0 ${large} 1 ${x2} ${y2}`
}
</script>
