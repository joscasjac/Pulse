<template>
  <section aria-label="Sprint planning" class="space-y-3">
    <p v-if="sprint" class="text-xs text-muted">Drag work into a sprint, or use each task’s move button.</p>
    <p v-if="error" role="alert" class="text-sm">{{ error }} <button class="btn-ghost" @click="load">Retry</button></p>
    <p v-if="loading" role="status" class="text-muted">Loading planning tasks…</p>
    <div v-else class="planning-columns">
      <section v-for="lane in lanes" :key="lane.key" class="planning-lane" @dragover.prevent @drop.prevent="drop($event, lane.key)">
        <h3 class="planning-lane-heading">{{ lane.label }} <span class="text-muted">({{ lane.tasks.length }})</span></h3>
        <div class="planning-lane-body" tabindex="0" :aria-label="`${lane.label} tasks`">
        <ul>
          <li v-for="task in lane.tasks" :key="task.name" :draggable="!busy && Boolean(sprint)" @dragstart="drag($event, task.name)" class="planning-task">
            <div class="min-w-0"><p class="break-words text-sm">{{ task.subject }}</p><p class="text-xs text-muted mt-1">{{ task.status }} · {{ task.expected_time || 0 }} h · {{ task.pulse_story_points || 0 }} points</p></div>
            <button v-if="sprint" class="btn-ghost" :disabled="busy" @click="move(task.name, lane.key ? null : sprint)">{{ lane.key ? 'To backlog' : 'To sprint' }}</button>
          </li>
        </ul>
        <button v-if="more[lane.key ? 'sprint' : 'backlog']" class="btn-ghost mt-3" :disabled="busy" @click="loadMore(lane)">Load more tasks</button>
        <p v-if="!lane.tasks.length" class="text-sm text-muted py-5">{{ lane.key ? 'Add tasks from the backlog to plan this sprint.' : 'No unplanned tasks in this project.' }}</p>
        </div>
      </section>
    </div>
    <p role="status" class="text-sm text-muted">{{ notice }}</p>
  </section>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ project: { type: String, default: '' }, sprint: { type: String, default: '' } })
const emit = defineEmits(['changed'])
const backlog = ref([]), planned = ref([]), loading = ref(false), busy = ref(false), error = ref(''), notice = ref('')
const more = ref({ backlog: false, sprint: false })
const fields = ['name', 'subject', 'status', 'expected_time', 'pulse_story_points']
const lanes = computed(() => [{ key: '', label: 'Backlog', tasks: backlog.value }, ...(props.sprint ? [{ key: props.sprint, label: 'Sprint work', tasks: planned.value }] : [])])
let loadVersion = 0
async function load() {
  const version = ++loadVersion
  loading.value = true; error.value = ''
  backlog.value = []; planned.value = []; more.value = { backlog: false, sprint: false }
  const filters = { pulse_archived: 0, ...(props.project ? { project: props.project } : {}) }
  try {
    const [left, right] = await Promise.all([
      call('frappe.client.get_list', { doctype: 'Task', fields, filters: { ...filters, pulse_sprint: ['is', 'not set'], status: ['not in', ['Completed', 'Cancelled']] }, limit_page_length: 100, order_by: 'pulse_rank asc, modified desc' }),
      props.sprint ? call('frappe.client.get_list', { doctype: 'Task', fields, filters: { ...filters, pulse_sprint: props.sprint }, limit_page_length: 100, order_by: 'pulse_rank asc, modified desc' }) : Promise.resolve([]),
    ])
    if (version === loadVersion) { backlog.value = left; planned.value = right; more.value = { backlog: left.length === 100, sprint: right.length === 100 } }
  } catch (e) { if (version === loadVersion) error.value = e.message || 'Planning tasks could not be loaded.' }
  finally { if (version === loadVersion) loading.value = false }
}
async function loadMore(lane) {
  if (busy.value) return
  busy.value = true; error.value = ''
  const project = props.project, sprint = props.sprint
  try {
    const filters = { pulse_archived: 0, ...(project ? { project } : {}) }
    filters.pulse_sprint = lane.key || ['is', 'not set']
    if (!lane.key) filters.status = ['not in', ['Completed', 'Cancelled']]
    const rows = await call('frappe.client.get_list', { doctype: 'Task', fields, filters, limit_start: lane.tasks.length, limit_page_length: 100, order_by: 'pulse_rank asc, modified desc' })
    if (project === props.project && sprint === props.sprint) {
      const target = lane.key ? planned : backlog
      target.value.push(...rows)
      more.value[lane.key ? 'sprint' : 'backlog'] = rows.length === 100
    }
  } catch (e) { error.value = e.message || 'More tasks could not be loaded.' }
  finally { busy.value = false }
}
function drag(event, name) { event.dataTransfer.setData('application/x-pulse-task', name); event.dataTransfer.effectAllowed = 'move' }
function drop(event, target) { const name = event.dataTransfer.getData('application/x-pulse-task'); if (name && props.sprint) move(name, target || null) }
async function move(name, target) {
  if (busy.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try { await call('pulse.api.planning.move_to_sprint', { tasks: [name], sprint: target }); notice.value = target ? 'Task added to sprint.' : 'Task returned to backlog.'; await load(); emit('changed') }
  catch (e) { error.value = e.message || 'Task could not be moved. Check your access and retry.' }
  finally { busy.value = false }
}
watch(() => [props.project, props.sprint], load, { immediate: true })
</script>
<style scoped>
.planning-columns { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 24px; }
.planning-lane { display: flex; flex-direction: column; min-height: 0; min-width: 0; border-top: 1px solid var(--border); }
.planning-lane-body { min-height: 100px; max-height: clamp(180px, 42dvh, 480px); overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable; }
.planning-lane-heading { flex-shrink: 0; display: flex; align-items: center; gap: 8px; padding-block: 14px; font-size: 13px; font-weight: 600; }
.planning-task { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 4px; border-bottom: 1px solid var(--border); }
.planning-task:hover { background: var(--hover); }
.planning-task button { flex-shrink: 0; font-size: 12px; }
.planning-task[draggable=true] { cursor: grab; }
.planning-lane-body:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
button:disabled { opacity: .55; cursor: wait; }
</style>
