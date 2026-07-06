<template>
  <span class="tag" :style="{ color: c[0], background: c[1] }">{{ value || 'Task' }}</span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: String, default: '' } })
const MAP = {
  Epic: ['#b491ff', 'rgba(180,145,255,0.14)'],
  Story: ['#34d399', 'rgba(52,211,153,0.14)'],
  Bug: ['#f2726d', 'rgba(242,114,109,0.14)'],
  Feature: ['#6aa9ff', 'rgba(106,169,255,0.14)'],
  Improvement: ['#4fa3a3', 'rgba(79,163,163,0.14)'],
  Incident: ['#f5b45a', 'rgba(245,180,90,0.14)'],
  'Sub-task': ['var(--muted)', 'var(--surface-2)'],
  Task: ['var(--muted)', 'var(--surface-2)'],
}
const c = computed(() => MAP[props.value] || MAP.Task)
</script>

<style scoped>
.tag { font-size: 10.5px; font-weight: 600; padding: 1.5px 7px; border-radius: 5px; white-space: nowrap; }
</style>
