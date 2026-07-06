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
  green: ['#34d399', 'rgba(52,211,153,0.13)'],
  amber: ['#f5b45a', 'rgba(245,180,90,0.13)'],
  blue: ['#6aa9ff', 'rgba(106,169,255,0.13)'],
  violet: ['#b491ff', 'rgba(180,145,255,0.13)'],
  red: ['#f2726d', 'rgba(242,114,109,0.13)'],
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
