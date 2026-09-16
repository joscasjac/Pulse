<template>
  <div class="task-modules" aria-label="Task modules">
    <span class="modules-label">Modules</span>
    <span v-for="module in memberships" :key="module.name" class="module-chip">
      <span class="module-symbol" aria-hidden="true">◇</span>{{ module.module_name || module.name }}
      <button v-if="module.can_write !== false && module.can_write !== 0" :disabled="busy" :aria-label="`Remove from ${module.module_name || module.name}`" @click="change(module.name, true)">×</button>
    </span>
    <span v-if="loading" class="modules-hint" role="status">Loading…</span>
    <select v-else-if="available.length" aria-label="Add task to module" :disabled="busy" @change="add($event)"><option value="">Add to module</option><option v-for="module in available" :key="module.name" :value="module.name">{{ module.module_name || module.name }}</option></select>
    <span v-else-if="!memberships.length && !error" class="modules-hint">None</span>
    <p v-if="error" role="alert" class="modules-error">{{ error }} <button :disabled="busy" @click="load">Retry</button></p>
  </div>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ task: { type: String, required: true } })
const emit = defineEmits(['changed'])
const memberships = ref([]), choices = ref([]), loading = ref(false), busy = ref(false), error = ref('')
let generation = 0
const available = computed(() => choices.value.filter(module => !memberships.value.some(item => item.name === module.name) && module.can_write !== false && module.can_write !== 0))
async function load() {
  const request = ++generation, task = props.task
  loading.value = true; error.value = ''
  try {
    const result = await call('pulse.api.modules.task_modules', { task })
    if (request !== generation || task !== props.task) return
    memberships.value = result.modules || []; choices.value = result.available || []
  } catch (e) { if (request === generation) error.value = e?.messages?.[0] || 'Could not load modules.' }
  finally { if (request === generation) loading.value = false }
}
function add(event) { const name = event.target.value; event.target.value = ''; if (name) change(name, false) }
async function change(name, remove) {
  const task = props.task
  busy.value = true; error.value = ''
  try {
    await call('pulse.api.modules.set_tasks', { name, tasks: [task], remove: remove ? 1 : 0 })
    if (props.task === task) { await load(); emit('changed') }
  } catch (e) { if (props.task === task) error.value = e?.messages?.[0] || 'Could not update module membership. Please retry.' }
  finally { busy.value = false }
}
watch(() => props.task, () => { memberships.value = []; choices.value = []; load() }, { immediate: true })
</script>
<style scoped>
.task-modules { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 12px; margin: 8px 0 12px; }
.modules-label { color: var(--muted); margin-right: 5px; }.module-chip { display: inline-flex; align-items: center; gap: 5px; border: 1px solid var(--border); border-radius: 5px; padding: 3px 7px; font-size: 11px; background: var(--surface); }.module-symbol { color: var(--muted); }.module-chip button { color: var(--muted); min-width: 16px; font-size: 14px; line-height: 16px; }
select { max-width: 200px; font-size: 11px; padding: 3px 5px; color: var(--muted); border: 1px solid transparent; border-radius: 4px; background: transparent; }select:hover { border-color: var(--border); }.modules-hint { color: var(--muted); font-size: 11px; }.modules-error { width: 100%; font-size: 11px; margin-top: 3px; }.modules-error button { text-decoration: underline; }
button:disabled,select:disabled { opacity: .5; }button:focus-visible,select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
