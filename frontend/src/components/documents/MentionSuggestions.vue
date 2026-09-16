<template>
  <div class="mention-options" v-show="items.length" role="listbox" aria-label="People to mention">
    <button v-for="(item, index) in items" :key="item.id || item.value || index"
      type="button" role="option" :aria-selected="selected === index"
      :class="{ selected: selected === index }" @mousedown.prevent
      @click="choose(index)" @mouseenter="selected = index">
      {{ item.display || item.label || item.name }}
    </button>
  </div>
</template>
<script setup>
import { ref, watch, nextTick } from 'vue'
const props = defineProps({ items: { type: Array, default: () => [] }, command: { type: Function, required: true } })
const selected = ref(0)
watch(() => props.items, () => { selected.value = 0 })
function choose(index) { if (props.items[index]) props.command(props.items[index]) }
function onKeyDown({ event }) {
  if (!props.items.length) return false
  if (event.key === 'Enter') { choose(selected.value); return true }
  if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return false
  selected.value = (selected.value + (event.key === 'ArrowUp' ? -1 : 1) + props.items.length) % props.items.length
  nextTick(() => document.querySelector('.mention-options [aria-selected="true"]')?.scrollIntoView({ block: 'nearest' }))
  return true
}
defineExpose({ onKeyDown })
</script>
<style scoped>
.mention-options { min-width: 180px; max-height: 280px; overflow-y: auto; padding: 4px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface, white); box-shadow: 0 8px 24px #0002; }
.mention-options button { display: block; width: 100%; padding: 8px 12px; text-align: left; border-radius: 4px; color: var(--text); font-size: 13px; }
.mention-options button.selected { background: var(--surface-2, #f4f4f5); }
</style>
