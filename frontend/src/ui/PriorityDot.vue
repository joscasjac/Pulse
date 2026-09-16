<template>
  <span class="prio" :style="{ color: color }" :title="`Priority: ${value || 'None'}`">
    <svg viewBox="0 0 16 16" class="priority-icon" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" aria-hidden="true">
      <template v-if="urgent"><rect x="1.5" y="1.5" width="13" height="13" rx="3"/><path d="M8 4.5v4M8 11.5h.01"/></template>
      <template v-else-if="!level"><circle cx="8" cy="8" r="6"/><path d="m4 4 8 8"/></template>
      <template v-else><path v-for="n in 4" :key="n" :d="`M${2 + (n - 1) * 4} 13v-${n * 3 - 2}`" :opacity="n <= level + 1 ? 1 : .18"/></template>
    </svg>
    <span v-if="showLabel">{{ value || 'None' }}</span>
  </span>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: String, default: '' }, showLabel: { type: Boolean, default: false } })
const level = computed(() => ({ Low: 1, Medium: 2, High: 3 }[props.value] || 0))
const urgent = computed(() => ['Urgent', 'Critical'].includes(props.value))
const color = computed(() => ({ Low: '#6172f3', Medium: '#e69b24', High: '#f97316', Urgent: '#ef4444', Critical: '#ef4444' }[props.value] || 'var(--muted)'))
</script>
<style scoped>
.prio { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; }
.priority-icon { width: 14px; height: 14px; flex-shrink: 0; }
</style>
