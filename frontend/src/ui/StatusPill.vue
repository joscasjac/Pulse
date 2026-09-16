<template>
  <span class="pill" :style="{ color: c.fg, background: c.bg }">
    <span class="dot" :style="{ background: c.fg }" />{{ label || value }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: String, default: '' }, label: { type: String, default: '' } })

// semantic tones — meaning, not decoration
const TONES = {
  // task statuses
  Open: 'muted', 'To Do': 'violet', Working: 'amber', 'In Progress': 'amber',
  'Pending Review': 'blue', 'In Review': 'blue', Completed: 'green', Done: 'green',
  Overdue: 'red', Cancelled: 'muted',
  // project / sprint / generic
  Active: 'green', Planned: 'blue', Backlog: 'muted',
  Approved: 'green', Rejected: 'red', Draft: 'muted', Submitted: 'blue',
  'On Track': 'green', 'At Risk': 'amber', 'Off Track': 'red',
  High: 'amber', Critical: 'red', Urgent: 'red', Medium: 'amber', Low: 'muted',
}
const COLORS = {
  green: ['var(--status-green)', 'color-mix(in srgb, var(--status-green) 9%, var(--surface))'],
  amber: ['var(--status-amber)', 'color-mix(in srgb, var(--status-amber) 9%, var(--surface))'],
  blue: ['var(--status-blue)', 'color-mix(in srgb, var(--status-blue) 9%, var(--surface))'],
  violet: ['var(--status-violet)', 'color-mix(in srgb, var(--status-violet) 9%, var(--surface))'],
  red: ['var(--status-red)', 'color-mix(in srgb, var(--status-red) 9%, var(--surface))'],
  muted: ['var(--muted)', 'var(--surface-2)'],
}
const c = computed(() => {
  const [fg, bg] = COLORS[TONES[props.value] || 'muted']
  return { fg, bg }
})
</script>

<style scoped>
.pill {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 6px; white-space: nowrap;
}
.dot { width: 5px; height: 5px; border-radius: 50%; }
</style>
