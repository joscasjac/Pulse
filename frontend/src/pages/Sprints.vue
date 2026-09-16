<template>
  <div class="sprints-page">
    <header class="planning-page-header">
      <div><h1 class="page-title">Sprints</h1><p class="text-sm text-muted">Plan a cycle and track its progress.</p></div>
      <button @click="openEntity('Pulse Sprint', null, project ? { project } : {})" class="btn-primary"><Plus class="w-3.5 h-3.5" /> New sprint</button>
    </header>
    <nav class="planning-tabs" aria-label="Planning views"><RouterLink :to="{ name: 'Sprints', query: route.query }" aria-current="page">Sprints</RouterLink><RouterLink :to="{ name: 'Backlog', query: route.query }">Backlog</RouterLink></nav>
    <p v-if="error" role="alert" class="px-7 py-4 text-sm">{{ error }} <button class="btn-ghost" @click="reload">Retry</button></p>
    <p v-if="loading" role="status" class="text-muted px-7 py-6">Loading sprints…</p>
    <div v-else class="sprint-layout">
      <nav aria-label="Sprints" class="sprint-list">
        <div class="sprint-list-heading"><span>All sprints</span><span>{{ sprints.length }}</span></div>
        <button v-for="s in sprints" :key="s.name" @click="selected = s.name" :aria-current="selected === s.name ? 'true' : undefined" class="sprint-choice">
          <span class="font-medium break-words">{{ s.sprint_name || s.name }}</span><StatusPill :value="s.status" />
          <span class="text-xs text-muted block mt-2">{{ s.project }} · {{ s.start_date || 'No start date' }} → {{ s.end_date || 'No end date' }}</span>
        </button>
        <p v-if="!sprints.length" class="text-muted py-8">No sprints yet. Create a sprint to plan your first cycle.</p>
      </nav>
      <section v-if="current" class="sprint-detail min-w-0 space-y-6" :aria-label="current.sprint_name">
        <div class="flex flex-wrap justify-between items-center gap-3"><h2 class="text-lg font-semibold break-words">{{ current.sprint_name }}</h2><button v-if="current.status !== 'Completed'" class="btn-ghost" @click="openEntity('Pulse Sprint', current.name)">Edit dates and details</button></div>
        <p v-if="detailError" role="alert">{{ detailError }} <button class="btn-ghost" @click="loadDetails">Retry details</button></p>
        <form v-if="current.status !== 'Completed'" class="sprint-settings space-y-3" @submit.prevent="save(false)">
          <label class="block text-sm">Sprint goal<textarea v-model="goal" rows="2" class="sprint-input" placeholder="What should this sprint accomplish?" /></label>
          <div class="flex flex-wrap items-end gap-3">
            <label class="text-sm">Measure progress by<select v-model="measure" class="sprint-input"><option>Tasks</option><option>Hours</option><option>Points</option></select></label>
            <button class="btn-ghost" :disabled="busy" type="submit">Save planning settings</button>
            <button v-if="current.status === 'Planned'" class="btn-primary" :disabled="busy" type="button" @click="save(true)">Start sprint</button>
            <button v-if="current.status === 'Active'" class="btn-ghost" :disabled="busy" type="button" @click="openClose">Close sprint</button>
          </div>
        </form>
        <div v-if="progress" class="space-y-2">
          <p v-if="current.status === 'Completed' && progress.goal" class="text-sm">{{ progress.goal }}</p>
          <p class="text-sm">{{ progress.completed }} of {{ progress.planned }} {{ progress.measure?.toLowerCase() }} completed · {{ progress.percent }}%</p>
          <progress class="sprint-progress" :max="Math.max(progress.planned, 1)" :value="progress.completed" :aria-label="`${progress.percent}% completed`" />
          <p class="text-sm text-muted">Estimated workload: {{ progress.estimated_hours }} hours · {{ progress.estimated_points }} points · {{ progress.tasks }} tasks</p>
        </div>
        <SprintPlanner v-if="current.status !== 'Completed'" :project="current.project" :sprint="current.name" @changed="loadDetails" />
        <section v-if="current.status !== 'Planned'" class="space-y-3">
          <h3 class="font-semibold">Burndown</h3>
          <p v-if="chartError" class="text-sm text-muted">{{ chartError }}</p>
          <template v-if="chart.length">
            <p class="text-xs text-muted">{{ progress?.measure || measure }} remaining · solid: recorded work · dashed: ideal</p>
            <svg viewBox="0 0 640 190" role="img" aria-label="Sprint burndown: recorded remaining work and ideal remaining work" class="burndown-chart">
              <line x1="35" y1="160" x2="625" y2="160" stroke="currentColor" opacity=".25" />
              <polyline :points="chartPoints('ideal_remaining')" fill="none" stroke="currentColor" stroke-dasharray="6 5" stroke-width="2" />
              <polyline :points="chartPoints('actual_remaining')" fill="none" stroke="var(--accent)" stroke-width="3" />
              <text x="5" y="20" fill="currentColor" font-size="12">{{ chartMax }}</text><text x="15" y="160" fill="currentColor" font-size="12">0</text>
              <text x="35" y="185" fill="currentColor" font-size="12">{{ chart[0].date }}</text><text x="625" y="185" text-anchor="end" fill="currentColor" font-size="12">{{ chart.at(-1).date }}</text>
            </svg>
            <details><summary class="cursor-pointer text-sm">View daily values</summary><div class="overflow-x-auto"><table class="w-full text-sm mt-3"><thead><tr><th>Date</th><th>Scope</th><th>Completed</th><th>Remaining</th><th>Ideal</th></tr></thead><tbody><tr v-for="row in chart" :key="row.date"><td>{{ row.date }}</td><td>{{ row.scope ?? '—' }}</td><td>{{ row.completed ?? '—' }}</td><td>{{ row.actual_remaining ?? '—' }}</td><td>{{ row.ideal_remaining }}</td></tr></tbody></table></div></details>
          </template>
        </section>
        <section v-if="current.status === 'Completed' && progress" class="space-y-3">
          <h3 class="font-semibold">Sprint summary</h3>
          <p class="text-sm">{{ progress.completed_tasks }} tasks completed. Unfinished work: {{ dispositionLabel(progress.unfinished_disposition) }}.</p>
          <div v-for="[key, label] in summarySections" :key="key"><h4 class="text-sm font-medium">{{ label }}</h4><p class="text-sm text-muted break-words">{{ progress[key]?.join(', ') || 'None' }}</p></div>
        </section>
        <p role="status" class="text-sm text-muted">{{ notice }}</p>
      </section>
    </div>
    <dialog ref="closeDialog" class="close-dialog" @cancel="cancelClose">
      <form @submit.prevent="finish" class="space-y-4">
        <h2 class="text-xl font-semibold">Close {{ current?.sprint_name }}</h2>
        <p class="text-sm text-muted">{{ progress?.unfinished_task_ids?.length || 0 }} unfinished tasks remain. Choose where this work belongs before freezing the sprint summary.</p>
        <label class="block text-sm">Unfinished work<select v-model="disposition" class="sprint-input"><option value="backlog">Return to backlog</option><option value="next">Move to another sprint</option><option value="retain">Keep in this completed sprint</option></select></label>
        <label v-if="disposition === 'next'" class="block text-sm">Destination sprint<select v-model="destination" required class="sprint-input"><option value="" disabled>Select a sprint</option><option v-for="s in destinations" :key="s.name" :value="s.name">{{ s.sprint_name }}</option></select></label>
        <p v-if="closeError" role="alert" class="text-sm">{{ closeError }}</p>
        <div class="flex flex-wrap justify-end gap-3"><button type="button" class="btn-ghost" :disabled="busy" @click="closeDialog.close()">Cancel</button><button class="btn-primary" :disabled="busy || (disposition === 'next' && !destination)">{{ busy ? 'Closing…' : 'Close sprint' }}</button></div>
      </form>
    </dialog>
  </div>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { call } from 'frappe-ui'
import StatusPill from '@/ui/StatusPill.vue'
import { openEntity, entityState } from '@/ui/entity'
import SprintPlanner from '@/components/sprints/SprintPlanner.vue'
import Plus from '~icons/lucide/plus'
const route = useRoute()
const project = computed(() => typeof route.query.project === 'string' ? route.query.project : '')
const sprints = ref([]), selected = ref(''), loading = ref(true), error = ref(''), busy = ref(false), notice = ref('')
const goal = ref(''), measure = ref('Tasks'), progress = ref(null), chart = ref([]), detailError = ref(''), chartError = ref('')
const closeDialog = ref(null), disposition = ref('backlog'), destination = ref(''), closeError = ref('')
const current = computed(() => sprints.value.find(s => s.name === selected.value))
const destinations = computed(() => sprints.value.filter(s => s.project === current.value?.project && s.name !== selected.value && s.status !== 'Completed'))
const summarySections = [['completed_task_ids', 'Completed work'], ['unfinished_task_ids', 'Unfinished work at close'], ['scope_added', 'Added during sprint'], ['scope_removed', 'Removed during sprint']]
const chartMax = computed(() => Math.max(1, ...chart.value.flatMap(r => [r.actual_remaining || 0, r.ideal_remaining || 0])))
function chartPoints(key) { return chart.value.map((r, i) => r[key] == null ? null : `${35 + i / Math.max(chart.value.length - 1, 1) * 590},${160 - r[key] / chartMax.value * 140}`).filter(Boolean).join(' ') }
function dispositionLabel(value) { return { backlog: 'returned to backlog', next: 'moved to another sprint', retain: 'kept in this sprint' }[value] || value }
let reloadVersion = 0
async function reload() {
  const version = ++reloadVersion
  loading.value = true; error.value = ''
  try {
    const rows = await call('frappe.client.get_list', { doctype: 'Pulse Sprint', fields: ['name', 'sprint_name', 'status', 'start_date', 'end_date', 'project', 'goal', 'progress_measure'], filters: project.value ? { project: project.value } : {}, order_by: 'start_date desc', limit_page_length: 0 })
    if (version !== reloadVersion) return
    sprints.value = rows
    if (!rows.some(s => s.name === selected.value)) selected.value = rows[0]?.name || ''
  }
  catch (e) { if (version === reloadVersion) error.value = e.message || 'Sprints could not be loaded.' }
  finally { if (version === reloadVersion) loading.value = false }
}
let detailVersion = 0
async function loadDetails() {
  const name = selected.value, version = ++detailVersion
  progress.value = null; chart.value = []; detailError.value = ''; chartError.value = ''
  if (!name) return
  const results = await Promise.allSettled([call('pulse.api.planning.sprint_progress', { sprint: name }), current.value?.status === 'Planned' ? Promise.resolve(null) : call('pulse.api.reports.run_report', { report: 'burndown', sprint: name })])
  if (version !== detailVersion) return
  if (results[0].status === 'fulfilled') progress.value = results[0].value
  else detailError.value = results[0].reason.message || 'Sprint progress could not be loaded.'
  if (results[1].status === 'fulfilled') chart.value = results[1].value?.data || []
  else chartError.value = results[1].reason.message || 'Recorded history is unavailable for this sprint.'
}
async function save(start) {
  if (busy.value) return
  busy.value = true; detailError.value = ''; notice.value = ''
  try { await call('pulse.api.planning.configure_sprint', { sprint: selected.value, goal: goal.value, progress_measure: measure.value, start: start ? 1 : 0 }); await reload(); await loadDetails(); notice.value = start ? 'Sprint started.' : 'Planning settings saved.' }
  catch (e) { detailError.value = e.message || 'Sprint settings could not be saved.' }
  finally { busy.value = false }
}
function cancelClose(event) { if (busy.value) event.preventDefault() }
function openClose() { disposition.value = 'backlog'; destination.value = ''; closeError.value = ''; closeDialog.value.showModal() }
async function finish() {
  if (busy.value) return
  busy.value = true; closeError.value = ''
  try { await call('pulse.api.planning.close_sprint', { sprint: selected.value, unfinished: disposition.value, next_sprint: destination.value || null }); closeDialog.value.close(); await reload(); await loadDetails(); notice.value = 'Sprint closed. The summary is now frozen.' }
  catch (e) { closeError.value = e.message || 'The sprint could not be closed. Review the destination and retry.' }
  finally { busy.value = false }
}
watch(current, s => { goal.value = s?.goal || ''; measure.value = s?.progress_measure || 'Tasks'; loadDetails() })
watch(() => entityState.saved, reload)
watch(project, () => { selected.value = ''; sprints.value = []; reload() }, { immediate: true })
</script>
<style scoped>
.sprints-page { flex: 1; height: 100%; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.sprints-page > :not(.sprint-layout) { flex-shrink: 0; }

.planning-page-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 24px 28px 20px; }
.planning-page-header h1 { font-size: 22px; font-weight: 600; margin-bottom: 4px; }
.planning-tabs { display: flex; gap: 24px; padding-inline: 28px; border-bottom: 1px solid var(--border); }
.planning-tabs a { display: block; padding: 12px 0; color: var(--muted); font-size: 13px; border-bottom: 2px solid transparent; }
.planning-tabs a[aria-current=page] { color: var(--text); border-bottom-color: var(--accent); }
.sprint-layout { display: grid; grid-template-columns: 260px minmax(0, 1fr); flex: 1; min-height: 0; overflow: hidden; grid-template-rows: minmax(0, 1fr); }
.sprint-list { min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 16px 12px; border-inline-end: 1px solid var(--border); }
.sprint-list-heading { position: sticky; top: -16px; z-index: 1; background: var(--surface); display: flex; align-items: center; justify-content: space-between; padding: 4px 10px 12px; font-size: 12px; color: var(--muted); }
.sprint-detail { min-height: 0; overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable; padding: 24px 28px; }
.sprint-settings { padding-bottom: 20px; border-bottom: 1px solid var(--border); }
.sprint-choice { text-align: start; display: block; width: 100%; padding: 12px 10px; border: 0; border-radius: 6px; background: transparent; margin-bottom: 4px; }
.sprint-choice:hover { background: var(--hover); }
.sprint-choice[aria-current=true] { background: var(--hover); box-shadow: inset 0 0 0 1px var(--border); }
.sprint-choice .pill { margin-inline-start: 8px; }
.sprint-input { display: block; width: 100%; margin-top: 6px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); padding: 8px 10px; }
.sprint-progress { width: 100%; height: 8px; accent-color: var(--accent); }
.burndown-chart { width: 100%; max-height: 260px; }
.close-dialog { width: min(520px, calc(100vw - 32px)); padding: 24px; border: 1px solid var(--border); border-radius: 8px; color: var(--text); background: var(--surface); }
.close-dialog::backdrop { background: rgb(0 0 0 / .5); }
th, td { padding: 8px; text-align: start; border-bottom: 1px solid var(--border); }
button:disabled { opacity: .55; cursor: wait; }
a:focus-visible, button:focus-visible, select:focus-visible, textarea:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 800px) { .sprint-layout { grid-template-columns: 1fr; grid-template-rows: minmax(80px, 28%) minmax(0, 1fr); } .sprint-list { border-inline-end: 0; border-bottom: 1px solid var(--border); max-height: none; overflow-y: auto; } }
@media (max-width: 640px) { .planning-page-header { padding: 20px 16px 16px; flex-wrap: wrap; } .planning-tabs { padding-inline: 16px; } .sprint-detail { padding: 20px 16px; } }
</style>
