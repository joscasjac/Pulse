<template>
  <transition name="fade">
    <div v-if="createState.open" class="ovl" @click.self="close" @keydown.esc="close">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Create task">
        <div class="head">
          <div class="flex items-center gap-2">
            <SquarePen class="w-4 h-4" style="color:var(--accent)" />
            <span class="font-semibold">New task</span>
          </div>
          <button class="p-1 rounded hover-app text-muted" aria-label="Close new task" @click="close"><X class="w-4 h-4" /></button>
        </div>

        <div class="body">
          <p v-if="dataError" class="load-error" role="alert">{{ dataError }} <button class="underline" @click="retryData">Retry</button></p>
          <p v-else-if="!projects.length" class="text-sm text-muted">{{ dataLoading ? 'Loading projects…' : 'No projects are available. Create a project or ask for access first.' }}</p>
          <div v-if="form.module" class="module-context"><span>Module: {{ createState.defaults.module_name || form.module }}</span><button type="button" aria-label="Remove module from new task" @click="form.module = null">×</button></div>
          <!-- project + type -->
          <div class="project-row">
            <label class="fld">
              <span class="lbl">Project</span>
              <select v-model="form.project" @change="changeProject" class="in">
                <option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option>
              </select>
            </label>

          </div>

          <label class="fld">
            <span class="lbl">Summary <b style="color:var(--accent)">*</b></span>
            <input ref="first" v-model="form.subject" placeholder="What needs to be done?" class="in" @keyup.enter="focusDesc" />
          </label>

          <label class="fld">
            <span class="lbl">Description</span>
            <textarea aria-label="Task description" v-model="form.description" rows="3" placeholder="Add detail, acceptance criteria…" class="in" />
          </label>

          <!-- priority + state + points + due -->
          <div class="row">
            <label class="fld">
              <span class="lbl">Priority</span>
              <select v-model="form.priority" class="in"><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select>
            </label>
            <label class="fld">
              <span class="lbl">Status</span>
              <select v-model="form.state" class="in"><option v-for="s in config.statuses" :key="s.label">{{ s.label }}</option></select>
            </label>

          </div>

          <!-- assignees -->
          <div class="fld">
            <span class="lbl">Assignees</span>
            <div class="chips">
              <button v-for="name in form.assignees" :key="name" type="button" class="chip on" :aria-label="`Remove ${name}`" @click="toggle(name)">
                <Avatar :name="name" :size="18" /><span>{{ assignable.find(u => u.name === name)?.full_name || name.split('@')[0] }}</span><X class="w-3 h-3" />
              </button>
              <select class="assignee-select" aria-label="Add assignee" @change="if ($event.target.value) toggle($event.target.value); $event.target.value = ''">
                <option value="">Add assignee</option><option v-for="u in assignable.filter(u => !form.assignees.includes(u.name))" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
              </select>
            </div>
          </div>
          <details class="additional-properties" :open="createState.defaults.repeat || createState.defaults.exp_end_date || createState.defaults.exp_start_date || undefined"><summary>More properties <span>Dates, estimates, labels & repeating tasks</span></summary><div class="additional-content">
          <div class="row">            <label class="fld">
              <span class="lbl">Type</span>
              <select v-model="form.task_type" class="in">
                <option v-for="t in issueTypes" :key="t" :value="t">{{ t }}</option>
              </select>
            </label>            <label class="fld">
              <span class="lbl">Due date</span>
              <input v-model="form.exp_end_date" type="date" class="in" />
            </label></div>
          <div class="row4" v-if="!form.repeat">
            <label class="fld"><span class="lbl">Start date</span><input v-model="form.exp_start_date" type="date" class="in" /></label>
            <label class="fld"><span class="lbl">Estimated hours</span><input v-model.number="form.expected_time" type="number" min="0" step="0.25" class="in" /></label>
            <label class="fld"><span class="lbl">Story points</span><input v-model.number="form.pulse_story_points" type="number" min="0" step="0.5" class="in" /></label>
          </div>
          <fieldset v-if="config.labels.length && !form.repeat"><legend class="lbl mb-2">Labels</legend><div class="chips"><label v-for="l in config.labels" :key="l.name" class="chip"><input v-model="form.pulse_labels" type="checkbox" :value="l.name" /><span :style="{ color: l.color }">●</span>{{ l.label_name }}</label></div></fieldset>
          <!-- repeat / recurring -->
          <div class="row">
            <label class="fld">
              <span class="lbl">Repeat</span>
              <select v-model="form.repeat" class="in" :disabled="!!form.module">
                <option :value="false">Does not repeat (one-off)</option>
                <option :value="true">Repeats on a schedule</option>
              </select>
            </label>
            <label class="fld" v-if="form.repeat">
              <span class="lbl">Every</span>
              <div class="flex gap-2">
                <input v-model.number="form.interval_count" type="number" min="1" class="in" style="width:72px" />
                <select v-model="form.interval_unit" class="in"><option>Day</option><option>Week</option><option>Month</option></select>
              </div>
            </label>
          </div>
          <p v-if="form.module" class="text-xs text-muted">Remove the module selection to create a repeating task.</p>
          <div v-if="form.repeat" class="text-[11px] text-faint -mt-1">
            A new task lands in <b>To Do</b> {{ cadenceLabel }} — it won't get buried in the backlog. Status above is ignored for recurring tasks.
          </div>

          <label class="fld" v-if="sprints.length && !form.repeat">
            <span class="lbl">Sprint</span>
            <select v-model="form.pulse_sprint" class="in">
              <option :value="null">— none —</option>
              <option v-for="s in sprints" :key="s.name" :value="s.name">{{ s.sprint_name || s.name }} ({{ s.status }})</option>
            </select>
          </label>

          </div></details>
        </div>

        <div class="foot">
          <span class="text-xs text-faint">{{ form.assignees.length }} assignee{{ form.assignees.length === 1 ? '' : 's' }}</span>
          <div class="flex gap-2">
            <button class="btn ghost" @click="close">Cancel</button>
            <button class="btn primary" :disabled="!canSubmit || submitting" @click="submit">
              {{ submitting ? 'Creating…' : (form.repeat ? 'Create recurring' : 'Create task') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { call } from 'frappe-ui'
import Avatar from '@/ui/Avatar.vue'
import { createState, closeCreate, markCreated } from '@/ui/create'
import { toast } from '@/ui/toast'
import SquarePen from '~icons/lucide/square-pen'
import X from '~icons/lucide/x'
import Check from '~icons/lucide/check'

const config = ref({ statuses: [], labels: [] })
const configLoading = ref(false)
let projectRequest = 0
const dataError = ref(''), dataLoading = ref(false)
const projects = ref([])
const issueTypes = ref([])
const assignable = ref([])
const sprints = ref([])
const submitting = ref(false)
const first = ref(null)

const form = reactive({
  project: null, module: null, task_type: 'Task', subject: '', description: '',
  priority: 'Medium', state: 'Backlog',
  exp_end_date: '', exp_start_date: '', expected_time: 0, pulse_story_points: 0, pulse_labels: [], pulse_sprint: null, assignees: [],
  repeat: false, interval_count: 1, interval_unit: 'Week',
})

const canSubmit = computed(() => form.project && form.subject.trim() && !configLoading.value && config.value.statuses.length)
const cadenceLabel = computed(() => {
  const n = form.interval_count || 1
  const u = (form.interval_unit || 'Week').toLowerCase()
  return n === 1 ? `every ${u}` : `every ${n} ${u}s`
})

function toggle(u) {
  const i = form.assignees.indexOf(u)
  i >= 0 ? form.assignees.splice(i, 1) : form.assignees.push(u)
}
function focusDesc() { document.querySelector('[aria-label="Task description"]')?.focus() }

async function ensureData() {
  dataError.value = ''; dataLoading.value = true
  try {
    projects.value = await call('frappe.client.get_list', { doctype: 'Project', fields: ['name', 'project_name'], limit_page_length: 0 })
    assignable.value = await call('pulse.api.spa.get_assignable_users')
  } catch (e) { dataError.value = e?.messages?.[0] || 'Could not load project choices. Retry to create your task.' }
  finally { dataLoading.value = false }
}
async function retryData() {
  await ensureData()
  form.project = projects.value.find(p => p.name === form.project)?.name || projects.value[0]?.name || null
  await loadProject()
}

function changeProject() { form.module = null; form.pulse_sprint = null; return loadProject() }
async function loadProject() {
  const request = ++projectRequest
  const project = form.project
  configLoading.value = true
  config.value = { statuses: [], labels: [] }
  try {
    await loadSprints()
    if (!project) return
    const result = await call('pulse.api.task_config.get_config', { project })
    if (request !== projectRequest || form.project !== project) return
    config.value = result
    issueTypes.value = result.task_types
    if (!issueTypes.value.includes(form.task_type)) form.task_type = issueTypes.value[0] || null
    if (!result.statuses.some(s => s.label === form.state)) form.state = result.statuses[0]?.label
    form.pulse_labels = []
  } catch (e) { toast.error('Could not load project task settings. Select the project again to retry.') }
  finally { if (request === projectRequest) configLoading.value = false }
}
async function loadSprints() {
  const project = form.project, request = projectRequest
  sprints.value = []
  if (!project) { form.pulse_sprint = null; return }
  try {
    const rows = await call('frappe.client.get_list', {
      doctype: 'Pulse Sprint', filters: { project, status: ['in', ['Planned', 'Active']] },
      fields: ['name', 'sprint_name', 'status'], limit_page_length: 0,
    })
    if (request !== projectRequest || project !== form.project) return
    sprints.value = rows.filter(sprint => ['Planned', 'Active'].includes(sprint.status))
    if (!sprints.value.some(sprint => sprint.name === form.pulse_sprint)) form.pulse_sprint = null
  } catch (error) {
    if (request === projectRequest && project === form.project) form.pulse_sprint = null
    throw error
  }
}

watch(() => createState.open, async (open) => {
  if (!open) return
  await ensureData()
  Object.assign(form, {
    project: createState.defaults.project || projects.value[0]?.name || null,
    module: createState.defaults.module || null,
    task_type: 'Task', subject: '', description: '', priority: 'Medium',
    state: createState.defaults.state || 'Backlog',
    exp_end_date: String(createState.defaults.exp_end_date || '').slice(0, 10), exp_start_date: String(createState.defaults.exp_start_date || '').slice(0, 10), expected_time: 0, pulse_story_points: 0, pulse_labels: [], pulse_sprint: createState.defaults.pulse_sprint || null, assignees: [],
    repeat: createState.defaults.module ? false : createState.defaults.repeat || false, interval_count: 1, interval_unit: 'Week',
  })
  await loadProject()
  nextTick(() => first.value?.focus())
})

function close() { closeCreate() }

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    if (form.repeat) {
      await call('pulse.api.recurring.create_recurring', {
        subject: form.subject.trim(), project: form.project,
        interval_count: form.interval_count || 1, interval_unit: form.interval_unit,
        priority: form.priority, task_type: form.task_type,
        assign_to: form.assignees[0] || null, description: form.description,
        generate_now: 1,
      })
      toast.success(`Recurring task created (${cadenceLabel.value})`)
      markCreated()
      form.subject = ''; form.description = ''; nextTick(() => first.value?.focus())
      return
    }
    const res = await call('pulse.api.spa.create_task', {
      project: form.project, module: form.module || null, subject: form.subject.trim(), state: form.state,
      task_type: form.task_type, priority: form.priority, description: form.description,
      assignees: JSON.stringify(form.assignees), pulse_sprint: form.pulse_sprint,
      exp_start_date: form.exp_start_date || null, exp_end_date: form.exp_end_date || null,
      expected_time: form.expected_time || 0, pulse_story_points: form.pulse_story_points || 0,
      pulse_labels: JSON.stringify(form.pulse_labels),
    })
    if (res.blocked && res.blocked.length) {
      toast.error(`${res.issue_key} created, but ${res.blocked.length} assignment(s) blocked by hierarchy`)
    } else if (res.assignees.length) {
      toast.success(`${res.issue_key} created & assigned`)
    } else {
      toast.success(`${res.issue_key} created`)
    }
    markCreated()
    form.subject = ''; form.description = ''; nextTick(() => first.value?.focus())
  } catch (e) {
    toast.error(e?.messages?.[0] || 'Could not create issue')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.ovl { position: fixed; inset: 0; z-index: 90; background: rgba(0, 0, 0, 0.5); display: grid; place-items: start center; padding-top: 8vh; }
.modal { width: 580px; max-width: calc(100vw - 32px); max-height: 84vh; overflow-y: auto; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 16px 48px rgb(0 0 0 / 16%); }
.head { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border-soft); }
.body { padding: 20px 24px; display: flex; flex-direction: column; gap: 14px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.row4 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
@media (max-width: 640px) { .row4 { grid-template-columns: 1fr 1fr; } }
.fld { display: flex; flex-direction: column; gap: 5px; }
.lbl { font-size: 11px; color: var(--muted); font-weight: 500; }
.in { width: 100%; background: var(--surface); border: 1px solid var(--border); color: var(--text); font-size: 13px; border-radius: 6px; padding: 7px 9px; outline: none; }
.in:focus { border-color: var(--accent); }
textarea.in { resize: vertical; font-family: inherit; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 9px 4px 4px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface-2); color: var(--muted); font-size: 12px; cursor: pointer; }
.chip:hover { color: var(--text); }
.chip.on { border-color: var(--accent); color: var(--text); background: color-mix(in srgb, var(--accent) 14%, transparent); }
.chip.on :deep(svg:last-child) { color: var(--accent); }
.foot { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-top: 1px solid var(--border-soft); position: sticky; bottom: 0; background: var(--surface); }
.btn { font-size: 13px; padding: 7px 14px; border-radius: 7px; }
.btn.ghost { border: 1px solid var(--border); background: transparent; color: var(--text); }
.btn.primary { background: var(--accent); color: var(--on-accent); }
.btn.primary:disabled { opacity: 0.45; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.16s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.form-section-title { margin-top: 10px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 13px; font-weight: 600; }
.load-error { font-size: 13px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media(max-width: 560px) { .body { padding: 18px; } .row, .row4 { grid-template-columns: 1fr; } }
.project-row { max-width: 280px; }
.additional-properties { border-top: 1px solid var(--border); margin-top: 2px; }
.additional-properties > summary { cursor: pointer; padding: 13px 0 0; font-size: 12px; font-weight: 500; }
.additional-properties > summary span { font-size: 11px; font-weight: 400; color: var(--muted); margin-left: 6px; }
.additional-content { display: flex; flex-direction: column; gap: 14px; margin-top: 16px; }
input[placeholder="What needs to be done?"] { font-size: 18px; font-weight: 500; padding: 5px 0; border: 0; border-radius: 0; }
textarea.in { border-color: transparent; padding: 6px 0; }
textarea.in:focus { border-color: var(--accent); padding: 6px 8px; }
.additional-properties > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.assignee-select { background: transparent; color: var(--muted); font-size: 12px; border: 1px solid var(--border); border-radius: 5px; padding: 4px 7px; min-height: 28px; max-width: 100%; }
.module-context { display: inline-flex; align-items: center; gap: 8px; align-self: flex-start; font-size: 12px; color: var(--muted); background: var(--surface-2); border: 1px solid var(--border); border-radius: 5px; padding: 4px 8px; }.module-context button { font-size: 16px; line-height: 16px; }
</style>
