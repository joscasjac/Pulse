<template>
  <Teleport to="body">
    <div v-if="open" class="calendar-picker-overlay" @click.self="requestClose">
      <section ref="dialog" class="calendar-picker" role="dialog" aria-modal="true" aria-labelledby="calendar-picker-title" aria-describedby="calendar-picker-description" tabindex="-1" @keydown="onKeydown">
        <header>
          <div><h2 id="calendar-picker-title">Add tasks to {{ displayDate }}</h2><p id="calendar-picker-description">Choose existing tasks to schedule on this day.</p></div>
          <button class="close-button" aria-label="Close task picker" :disabled="pending" @click="requestClose">×</button>
        </header>
        <div class="search-wrap"><Search aria-hidden="true" class="search-icon" /><input ref="searchInput" v-model="query" type="search" placeholder="Search tasks by title or ID" aria-label="Search tasks" :disabled="pending" /></div>
        <div class="selection-summary"><span aria-live="polite">{{ selected.length }} selected</span><button :disabled="pending || !visibleTasks.length" @click="toggleAll">{{ allVisibleSelected ? 'Clear visible selection' : 'Select all' }}</button></div>
        <p v-if="error" class="picker-error" role="alert">{{ error }}</p>
        <div class="task-list" :aria-busy="loading || pending">
          <p v-if="loading" class="empty" role="status">Loading tasks…</p>
          <template v-else>
            <label v-for="task in visibleTasks" :key="task.name" class="task-option" :class="{ selected: selected.includes(task.name) }">
              <input type="checkbox" v-model="selected" :value="task.name" :disabled="pending" :aria-label="`Select ${task.issue_key || task.name}: ${task.subject}`" />
              <span class="task-key">{{ task.issue_key || task.name }}</span>
              <span class="status-dot" :style="{ background: task.status_color || statusColor(task.workflow_state || task.status) }" :title="task.workflow_state || task.status" aria-hidden="true" />
              <span class="task-subject">{{ task.subject }}</span>
              <span class="task-state">{{ task.workflow_state || task.status }}</span>
            </label>
            <p v-if="!visibleTasks.length" class="empty">{{ query.trim() ? 'No tasks match your search.' : 'No editable tasks are available.' }}</p>
          </template>
        </div>
        <footer><button class="button" :disabled="pending" @click="requestClose">Cancel</button><button class="button primary" :disabled="pending || loading || !selected.length" @click="$emit('confirm', [...selected])">{{ pending ? 'Adding tasks…' : `Add selected tasks${selected.length ? ` (${selected.length})` : ''}` }}</button></footer>
      </section>
    </div>
  </Teleport>
</template>
<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import Search from '~icons/lucide/search'
const props = defineProps({ tasks: { type: Array, default: () => [] }, open: Boolean, date: { type: String, default: '' }, pending: Boolean, loading: Boolean, error: { type: String, default: '' } })
const emit = defineEmits(['close', 'confirm'])
const query = ref(''), selected = ref([]), dialog = ref(null), searchInput = ref(null)
let returnFocus = null
const editableTasks = computed(() => props.tasks.filter(task => task.can_write !== false && task.can_write !== 0))
const visibleTasks = computed(() => {
  const search = query.value.trim().toLocaleLowerCase()
  return editableTasks.value.filter(task => !search || `${task.issue_key || task.name} ${task.subject}`.toLocaleLowerCase().includes(search))
})
const allVisibleSelected = computed(() => visibleTasks.value.length > 0 && visibleTasks.value.every(task => selected.value.includes(task.name)))
const displayDate = computed(() => {
  if (!props.date) return 'calendar'
  const date = new Date(`${props.date.slice(0, 10)}T12:00:00`)
  return Number.isNaN(date.getTime()) ? props.date : date.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })
})
function statusColor(status) { return ({ Backlog: '#64748b', 'To Do': '#3b82f6', 'In Progress': '#f59e0b', 'In Review': '#8b5cf6', Blocked: '#ef4444', Done: '#22c55e', Completed: '#22c55e', Cancelled: '#94a3b8' })[status] || 'var(--muted)' }
function toggleAll() {
  const visible = new Set(visibleTasks.value.map(task => task.name))
  selected.value = allVisibleSelected.value ? selected.value.filter(name => !visible.has(name)) : [...new Set([...selected.value, ...visible])]
}
function restoreFocus() { if (returnFocus?.isConnected) returnFocus.focus(); returnFocus = null }
watch(() => props.open, async open => {
  if (!open) { restoreFocus(); return }
  returnFocus = document.activeElement
  query.value = ''; selected.value = []
  await nextTick()
  searchInput.value?.focus()
}, { immediate: true })
watch(editableTasks, tasks => { const available = new Set(tasks.map(task => task.name)); selected.value = selected.value.filter(name => available.has(name)) })
onBeforeUnmount(restoreFocus)
function requestClose() { if (!props.pending) emit('close') }
function onKeydown(event) {
  if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); requestClose(); return }
  if (event.key !== 'Tab') return
  const elements = [...dialog.value.querySelectorAll('button, input, [tabindex]')].filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length)
  if (!elements.length) { event.preventDefault(); dialog.value.focus(); return }
  const first = elements[0], last = elements[elements.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.value)) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialog.value)) { event.preventDefault(); first.focus() }
}
</script>
<style scoped>
.calendar-picker-overlay { position: fixed; inset: 0; z-index: 100; background: rgb(0 0 0 / 30%); display: grid; align-items: start; justify-items: center; padding: min(12vh, 100px) 16px 24px; }
.calendar-picker { width: min(680px, 100%); max-height: 80vh; display: flex; flex-direction: column; background: var(--surface); color: var(--text); border-radius: 8px; box-shadow: 0 16px 48px rgb(0 0 0 / 16%); overflow: hidden; }
header { display: flex; justify-content: space-between; align-items: start; padding: 20px 20px 16px; gap: 16px; }
h2 { font-size: 16px; line-height: 1.4; font-weight: 600; } header p { margin-top: 4px; color: var(--muted); font-size: 12px; }
.close-button { font-size: 22px; line-height: 24px; width: 28px; color: var(--muted); }
.search-wrap { position: relative; margin: 0 20px; }.search-icon { position: absolute; width: 15px; height: 15px; left: 10px; top: 10px; color: var(--muted); }
.search-wrap input { width: 100%; height: 36px; padding: 7px 12px 7px 34px; border: 1px solid var(--border); background: var(--surface); color: var(--text); border-radius: 5px; font-size: 13px; }
.selection-summary { display: flex; justify-content: space-between; padding: 14px 20px 10px; font-size: 12px; color: var(--muted); }.selection-summary button { color: var(--accent); }
.task-list { overflow: auto; min-height: 140px; border-top: 1px solid var(--border); }
.task-option { display: flex; align-items: center; gap: 10px; padding: 12px 20px; cursor: pointer; border-bottom: 1px solid var(--border); font-size: 13px; }.task-option:hover, .task-option.selected { background: var(--surface-2); }
.task-key { color: var(--muted); font-size: 11px; flex: 0 0 78px; }.task-subject { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.task-state { color: var(--muted); font-size: 11px; }.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.empty { padding: 40px 20px; text-align: center; font-size: 13px; color: var(--muted); }.picker-error { padding: 10px 20px; font-size: 12px; color: var(--text); background: var(--surface-2); }
footer { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 20px; border-top: 1px solid var(--border); }.button { border: 1px solid var(--border); border-radius: 5px; min-height: 32px; padding: 6px 12px; font-size: 12px; background: var(--surface); }.button.primary { color: var(--on-accent); background: var(--accent); border-color: var(--accent); }button:disabled { opacity: .5; cursor: default; }
button:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media(max-width: 480px) { .task-state { display: none; }.task-option { padding: 12px; gap: 8px; }.task-key { flex-basis: 60px; }.calendar-picker-overlay { padding: 8vh 12px 20px; } }
</style>
