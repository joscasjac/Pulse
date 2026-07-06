<template>
  <transition name="fade">
    <div v-if="createState.open" class="ovl" @click.self="close" @keydown.esc="close">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Create task">
        <div class="head">
          <div class="flex items-center gap-2">
            <SquarePen class="w-4 h-4" style="color:var(--accent)" />
            <span class="font-semibold">New task</span>
          </div>
          <button class="p-1 rounded hover-app text-muted" @click="close"><X class="w-4 h-4" /></button>
        </div>

        <div class="body">
          <!-- project + type -->
          <div class="row">
            <label class="fld">
              <span class="lbl">Project</span>
              <select v-model="form.project" @change="loadSprints" class="in">
                <option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option>
              </select>
            </label>
            <label class="fld">
              <span class="lbl">Type</span>
              <select v-model="form.task_type" class="in">
                <option v-for="t in issueTypes" :key="t" :value="t">{{ t }}</option>
              </select>
            </label>
          </div>

          <label class="fld">
            <span class="lbl">Summary <b style="color:var(--accent)">*</b></span>
            <input ref="first" v-model="form.subject" placeholder="What needs to be done?" class="in" @keyup.enter="focusDesc" />
          </label>

          <label class="fld">
            <span class="lbl">Description</span>
            <textarea v-model="form.description" rows="3" placeholder="Add detail, acceptance criteria…" class="in" />
          </label>

          <!-- priority + state + points + due -->
          <div class="row4">
            <label class="fld">
              <span class="lbl">Priority</span>
              <select v-model="form.priority" class="in"><option>Low</option><option>Medium</option><option>High</option><option>Critical</option><option>Urgent</option></select>
            </label>
            <label class="fld">
              <span class="lbl">Status</span>
              <select v-model="form.state" class="in"><option>Backlog</option><option>To Do</option><option>In Progress</option><option>In Review</option><option>Done</option></select>
            </label>
            <label class="fld">
              <span class="lbl">Points</span>
              <input v-model="form.pulse_story_points" type="number" min="0" class="in" />
            </label>
            <label class="fld">
              <span class="lbl">Due date</span>
              <input v-model="form.exp_end_date" type="date" class="in" />
            </label>
          </div>

          <label class="fld" v-if="sprints.length">
            <span class="lbl">Sprint</span>
            <select v-model="form.pulse_sprint" class="in">
              <option :value="null">— none —</option>
              <option v-for="s in sprints" :key="s.name" :value="s.name">{{ s.sprint_name || s.name }} ({{ s.status }})</option>
            </select>
          </label>

          <!-- assignees -->
          <div class="fld">
            <span class="lbl">Assign to <span class="text-faint">(you can assign at or below your level)</span></span>
            <div v-if="!assignable.length" class="text-xs text-faint py-1">No one available to assign.</div>
            <div class="chips">
              <button v-for="u in assignable" :key="u.name" type="button"
                class="chip" :class="{ on: form.assignees.includes(u.name) }" @click="toggle(u.name)">
                <Avatar :name="u.name" :size="18" />
                <span>{{ u.full_name || u.name.split('@')[0] }}</span>
                <Check v-if="form.assignees.includes(u.name)" class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>

        <div class="foot">
          <span class="text-xs text-faint">{{ form.assignees.length }} assignee{{ form.assignees.length === 1 ? '' : 's' }}</span>
          <div class="flex gap-2">
            <button class="btn ghost" @click="close">Cancel</button>
            <button class="btn primary" :disabled="!canSubmit || submitting" @click="submit">
              {{ submitting ? 'Creating…' : 'Create task' }}
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

const projects = ref([])
const issueTypes = ref([])
const assignable = ref([])
const sprints = ref([])
const submitting = ref(false)
const first = ref(null)

const form = reactive({
  project: null, task_type: 'Task', subject: '', description: '',
  priority: 'Medium', state: 'Backlog', pulse_story_points: 0,
  exp_end_date: '', pulse_sprint: null, assignees: [],
})

const canSubmit = computed(() => form.project && form.subject.trim())

function toggle(u) {
  const i = form.assignees.indexOf(u)
  i >= 0 ? form.assignees.splice(i, 1) : form.assignees.push(u)
}
function focusDesc() {}

async function ensureData() {
  if (!projects.value.length) {
    projects.value = await call('frappe.client.get_list', { doctype: 'Pulse Project', fields: ['name', 'project_name'], limit_page_length: 0 }).catch(() => [])
  }
  if (!issueTypes.value.length) {
    issueTypes.value = await call('frappe.client.get_list', { doctype: 'Pulse Issue Type', fields: ['name'], limit_page_length: 0 }).then((r) => r.map((x) => x.name)).catch(() => ['Task'])
  }
  if (!assignable.value.length) {
    assignable.value = await call('pulse.api.spa.get_assignable_users').catch(() => [])
  }
}

async function loadSprints() {
  if (!form.project) { sprints.value = []; return }
  sprints.value = await call('frappe.client.get_list', {
    doctype: 'Pulse Sprint', filters: { project: form.project },
    fields: ['name', 'sprint_name', 'status'], limit_page_length: 0,
  }).catch(() => [])
}

watch(() => createState.open, async (open) => {
  if (!open) return
  await ensureData()
  Object.assign(form, {
    project: createState.defaults.project || projects.value[0]?.name || null,
    task_type: 'Task', subject: '', description: '', priority: 'Medium',
    state: createState.defaults.state || 'Backlog', pulse_story_points: 0,
    exp_end_date: '', pulse_sprint: null, assignees: [],
  })
  await loadSprints()
  nextTick(() => first.value?.focus())
})

function close() { closeCreate() }

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    const res = await call('pulse.api.spa.create_task', {
      project: form.project, subject: form.subject.trim(), state: form.state,
      task_type: form.task_type, priority: form.priority, description: form.description,
      assignees: JSON.stringify(form.assignees), pulse_sprint: form.pulse_sprint,
      exp_end_date: form.exp_end_date || null, pulse_story_points: form.pulse_story_points || 0,
    })
    if (res.blocked && res.blocked.length) {
      toast.error(`${res.issue_key} created, but ${res.blocked.length} assignment(s) blocked by hierarchy`)
    } else if (res.assignees.length) {
      toast.success(`${res.issue_key} created & assigned`)
    } else {
      toast.success(`${res.issue_key} created`)
    }
    markCreated()
    closeCreate()
  } catch (e) {
    toast.error(e?.messages?.[0] || 'Could not create issue')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.ovl { position: fixed; inset: 0; z-index: 90; background: rgba(0, 0, 0, 0.5); display: grid; place-items: start center; padding-top: 8vh; }
.modal { width: 560px; max-width: calc(100vw - 32px); max-height: 84vh; overflow-y: auto; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); }
.head { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--border-soft); }
.body { padding: 16px; display: flex; flex-direction: column; gap: 13px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.row4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
@media (max-width: 560px) { .row4 { grid-template-columns: 1fr 1fr; } }
.fld { display: flex; flex-direction: column; gap: 5px; }
.lbl { font-size: 11px; color: var(--muted); font-weight: 500; }
.in { width: 100%; background: var(--surface-2); border: 1px solid var(--border); color: var(--text); font-size: 13px; border-radius: 7px; padding: 7px 9px; outline: none; }
.in:focus { border-color: var(--accent); }
textarea.in { resize: vertical; font-family: inherit; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 9px 4px 4px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface-2); color: var(--muted); font-size: 12px; cursor: pointer; }
.chip:hover { color: var(--text); }
.chip.on { border-color: var(--accent); color: var(--text); background: rgba(109, 124, 255, 0.12); }
.chip.on :deep(svg:last-child) { color: var(--accent); }
.foot { display: flex; align-items: center; justify-content: space-between; padding: 13px 16px; border-top: 1px solid var(--border-soft); position: sticky; bottom: 0; background: var(--surface); }
.btn { font-size: 13px; padding: 7px 14px; border-radius: 7px; }
.btn.ghost { border: 1px solid var(--border); background: transparent; color: var(--text); }
.btn.primary { background: var(--accent); color: #fff; }
.btn.primary:disabled { opacity: 0.45; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.16s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
