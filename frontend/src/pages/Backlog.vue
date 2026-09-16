<template>
  <div class="backlog-page">
    <header class="planning-page-header">
      <div><h1 class="page-title">Backlog</h1><p class="text-sm text-muted">Unplanned work, ready for your next sprint.</p></div>
      <button class="btn-primary" @click="openEntity('Pulse Sprint', null, project ? { project } : {})"><Plus class="w-3.5 h-3.5" /> New sprint</button>
    </header>
    <nav class="planning-tabs" aria-label="Planning views"><RouterLink :to="{ name: 'Sprints', query: route.query }">Sprints</RouterLink><RouterLink :to="{ name: 'Backlog', query: route.query }" aria-current="page">Backlog</RouterLink></nav>
    <div class="backlog-toolbar">
      <label for="backlog-sprint" class="text-sm text-muted">Plan into</label>
      <select id="backlog-sprint" v-model="selected" class="planning-select">
        <option value="">{{ project ? 'Project backlog' : 'All projects’ backlog' }}</option><option v-for="s in sprints" :key="s.name" :value="s.name">{{ s.sprint_name }}{{ project ? '' : ` · ${s.project}` }}</option>
      </select>
    </div>
    <div class="backlog-content">
      <p v-if="error" role="alert" class="mb-4 text-sm">{{ error }} <button class="btn-ghost" @click="load">Retry</button></p>
      <SprintPlanner :project="current?.project || project" :sprint="selected" />
    </div>
  </div>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { call } from 'frappe-ui'
import { openEntity, entityState } from '@/ui/entity'
import Plus from '~icons/lucide/plus'
import SprintPlanner from '@/components/sprints/SprintPlanner.vue'
const route = useRoute()
const project = computed(() => typeof route.query.project === 'string' ? route.query.project : '')
const sprints = ref([]), selected = ref(''), error = ref('')
const current = computed(() => sprints.value.find(s => s.name === selected.value))
let loadVersion = 0
async function load() {
  const version = ++loadVersion
  error.value = ''
  try {
    const rows = await call('frappe.client.get_list', { doctype: 'Pulse Sprint', fields: ['name', 'sprint_name', 'project'], filters: { status: ['!=', 'Completed'], ...(project.value ? { project: project.value } : {}) }, limit_page_length: 0 })
    if (version !== loadVersion) return
    sprints.value = rows
    if (!rows.some(s => s.name === selected.value)) selected.value = ''
  } catch (e) { if (version === loadVersion) error.value = e.message || 'Sprints could not be loaded.' }
}
watch(project, () => { selected.value = ''; sprints.value = []; load() }, { immediate: true })
watch(() => entityState.saved, load)
</script>
<style scoped>
.planning-page-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 24px 28px 20px; }
.planning-page-header h1 { font-size: 22px; font-weight: 600; margin-bottom: 4px; }
.planning-tabs { display: flex; gap: 24px; padding-inline: 28px; border-bottom: 1px solid var(--border); }
.planning-tabs a { display: block; padding: 12px 0; color: var(--muted); font-size: 13px; border-bottom: 2px solid transparent; }
.planning-tabs a[aria-current=page] { color: var(--text); border-bottom-color: var(--accent); }
.backlog-toolbar { display: flex; align-items: center; gap: 12px; padding: 12px 28px; border-bottom: 1px solid var(--border); }
.planning-select { min-height: 32px; max-width: 100%; padding: 4px 28px 4px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); font-size: 13px; }
.backlog-content { padding: 24px 28px; }
a:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 640px) { .planning-page-header { padding: 20px 16px 16px; flex-wrap: wrap; } .planning-tabs { padding-inline: 16px; } .backlog-toolbar { padding: 12px 16px; flex-wrap: wrap; } .backlog-content { padding: 20px 16px; } }
</style>
