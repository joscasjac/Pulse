<template>
  <span class="prio" :style="{ color: c }" :title="`Priority: ${value || 'None'}`">
    <span class="bars">
      <i v-for="n in 3" :key="n" :style="{ background: n <= level ? c : 'var(--border)' }" />
    </span>
    <span v-if="showLabel" class="lbl">{{ value }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: String, default: '' }, showLabel: { type: Boolean, default: false } })
const LEVEL = { Low: 1, Medium: 2, High: 3, Critical: 3, Urgent: 3 }
const COLOR = { Low: 'var(--muted)', Medium: '#f5b45a', High: '#f59e0b', Critical: '#f2726d', Urgent: '#f2726d' }
const level = computed(() => LEVEL[props.value] || 0)
const c = computed(() => COLOR[props.value] || 'var(--muted)')
</script>

<style scoped>
.prio { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; }
.bars { display: inline-flex; align-items: flex-end; gap: 1.5px; height: 10px; }
.bars i { width: 3px; border-radius: 1px; }
.bars i:nth-child(1) { height: 5px; }
.bars i:nth-child(2) { height: 8px; }
.bars i:nth-child(3) { height: 10px; }
</style>
