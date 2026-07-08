<template>
  <transition name="slide">
    <div v-if="taskId" class="fixed inset-0 z-40 flex justify-end" @click.self="$emit('close')">
      <div class="absolute inset-0 bg-black/40" />
      <aside class="relative w-[460px] max-w-full h-full bg-surface text-app border-l border-app shadow-2xl overflow-y-auto">
        <div v-if="task" class="p-5">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono px-2 py-0.5 rounded bg-surface-2 text-blue-500">{{ task.issue_key || task.name }}</span>
            <button class="text-muted hover:text-app" @click="$emit('close')">Close</button>
          </div>

          <input v-model="task.subject" @change="save('subject', task.subject)"
            class="mt-2 w-full text-lg font-semibold bg-transparent outline-none border-b border-transparent focus:border-app" />

          <div class="grid grid-cols-2 gap-3 mt-4 text-sm">
            <label class="block">
              <span class="text-xs text-muted">Type</span>
              <select v-model="task.task_type" @change="save('task_type', task.task_type)" class="field">
                <option v-for="t in issueTypes" :key="t" :value="t">{{ t }}</option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs text-muted">Priority</span>
              <select v-model="task.priority" @change="save('priority', task.priority)" class="field">
                <option>Low</option><option>Medium</option><option>High</option><option>Critical</option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs text-muted">Story Points</span>
              <input type="number" v-model="task.pulse_story_points" @change="save('pulse_story_points', task.pulse_story_points)" class="field" />
            </label>
            <label class="block">
              <span class="text-xs text-muted">Due date</span>
              <input type="date" v-model="task.exp_end_date" @change="save('exp_end_date', task.exp_end_date)" class="field" />
            </label>
          </div>

          <div class="mt-4">
            <span class="text-xs text-muted">Description</span>
            <textarea v-model="task.description" @change="save('description', task.description)" rows="3" class="field" />
          </div>

          <!-- Assignees -->
          <div class="mt-5">
            <div class="text-xs text-muted mb-1">Assignees</div>
            <div class="flex flex-wrap items-center gap-1.5">
              <span v-for="a in task.assignees" :key="a" class="flex items-center gap-1 bg-blue-50 text-blue-700 text-xs rounded-full pl-2 pr-1 py-0.5">
                {{ a.replace(/@.*/, '') }}
                <button @click="unassign(a)" class="hover:text-red-600">x</button>
              </span>
              <select @change="assign($event)" class="text-xs border border-app bg-surface-2 text-app rounded-md px-1.5 py-1">
                <option value="">+ assign</option>
                <option v-for="u in assignable" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
              </select>
            </div>
          </div>

          <!-- Time tracked -->
          <div class="mt-5">
            <div class="text-xs text-muted mb-1.5 flex items-center justify-between">
              <span>Time tracked</span>
              <span class="mono text-app">{{ timeTotal.toFixed(2) }} h</span>
            </div>
            <div v-for="e in timeEntries" :key="e.name" class="flex items-center gap-2 py-0.5 text-xs">
              <span class="text-faint w-20">{{ e.date }}</span>
              <span class="mono">{{ Number(e.hours).toFixed(2) }} h</span>
              <span class="text-muted truncate flex-1">{{ e.description || '' }}</span>
            </div>
            <div class="flex gap-2 mt-1.5">
              <input v-model="newHours" type="number" step="0.25" min="0" placeholder="Hours" class="field w-24" />
              <input v-model="newHoursNote" placeholder="Note (optional)" class="field flex-1" @keyup.enter="logTime" />
              <button class="btn" @click="logTime">Log</button>
            </div>
          </div>

          <!-- Parent -->
          <div v-if="task.parent" class="mt-4 text-xs">
            <span class="text-muted">Parent: </span>
            <span class="mono text-blue-500">{{ task.parent.issue_key }}</span>
            <span class="text-muted"> · {{ task.parent.subject }}</span>
          </div>

          <!-- Sub-tasks -->
          <div class="mt-5">
            <div class="text-xs text-muted mb-1.5 flex items-center justify-between">
              <span>Sub-tasks</span>
              <span v-if="task.subtasks.length" class="text-faint">{{ doneSubs }}/{{ task.subtasks.length }} done</span>
            </div>
            <div v-if="task.subtasks.length" class="h-1 rounded-full bg-surface-2 mb-2 overflow-hidden">
              <div class="h-full rounded-full bg-green-500" :style="{ width: subPct + '%' }" />
            </div>
            <div v-for="s in task.subtasks" :key="s.name" class="flex items-center gap-2 py-1 cursor-pointer group" @click="$emit('open', s.name)">
              <span class="mono text-[10px] text-faint">{{ s.issue_key }}</span>
              <span class="text-sm flex-1 truncate" :class="s.status === 'Completed' ? 'line-through text-muted' : ''">{{ s.subject }}</span>
              <StatusPill :value="s.status" />
            </div>
            <div class="flex gap-2 mt-1.5">
              <input v-model="newSub" @keyup.enter="addSub" placeholder="Add sub-task…" class="field flex-1" />
              <button class="btn" @click="addSub">Add</button>
            </div>
          </div>

          <!-- Dependencies -->
          <div class="mt-5">
            <div class="text-xs text-muted mb-1.5">Blocked by</div>
            <div v-for="b in task.blocked_by" :key="b.dep" class="flex items-center gap-2 py-1">
              <span class="mono text-[10px] text-faint">{{ b.issue_key }}</span>
              <span class="text-sm flex-1 truncate">{{ b.subject }}</span>
              <StatusPill :value="b.status" />
              <button class="text-faint hover:text-red-500" @click="removeDep(b.dep)"><X class="w-3 h-3" /></button>
            </div>
            <div class="relative mt-1.5">
              <input v-model="depQ" @input="searchDeps" placeholder="Add a blocker (search tasks)…" class="field w-full" />
              <div v-if="depResults.length" class="absolute z-10 left-0 right-0 mt-1 rounded-md border border-app bg-surface shadow-app max-h-44 overflow-y-auto">
                <button v-for="r in depResults" :key="r.name" class="w-full text-left px-2.5 py-1.5 hover-app text-sm flex items-center gap-2" @click="addDep(r)">
                  <span class="mono text-[10px] text-faint">{{ r.issue_key }}</span><span class="truncate">{{ r.subject }}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Checklist -->
          <div class="mt-5">
            <div class="text-xs text-muted mb-1">Checklist</div>
            <div v-for="c in task.checklist" :key="c.name" class="flex items-center gap-2 py-0.5">
              <input type="checkbox" :checked="c.is_done" @change="toggleCheck(c)" />
              <span :class="c.is_done ? 'line-through text-muted' : ''" class="text-sm">{{ c.item }}</span>
            </div>
            <div class="flex gap-2 mt-1">
              <input v-model="newCheck" @keyup.enter="addCheck" placeholder="Add item..." class="field flex-1" />
              <button class="btn" @click="addCheck">Add</button>
            </div>
          </div>

          <!-- Comments -->
          <div class="mt-5">
            <div class="text-xs text-muted mb-1">Comments</div>
            <div v-for="c in task.comments" :key="c.name" class="text-sm border-l-2 border-app pl-2 py-1">
              <div class="text-app">{{ c.comment_text }}</div>
              <div class="text-[10px] text-muted">{{ c.owner }}</div>
            </div>
            <div class="flex gap-2 mt-1">
              <input v-model="newComment" @keyup.enter="postComment" placeholder="Write a comment..." class="field flex-1" />
              <button class="btn" @click="postComment">Send</button>
            </div>
          </div>
        </div>
        <div v-else class="p-10 text-center text-muted">Loading...</div>
      </aside>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { call } from 'frappe-ui'
import { toast } from '@/ui/toast'
import StatusPill from '@/ui/StatusPill.vue'
import X from '~icons/lucide/x'

const props = defineProps({ taskId: { type: String, default: null } })
const emit = defineEmits(['close', 'changed', 'open'])

const task = ref(null)
const assignable = ref([])
const issueTypes = ref([])
const newCheck = ref('')
const newComment = ref('')
const newSub = ref('')
const depQ = ref('')
const depResults = ref([])
const timeEntries = ref([])
const newHours = ref('')
const newHoursNote = ref('')

const doneSubs = computed(() => (task.value?.subtasks || []).filter((s) => s.status === 'Completed').length)
const subPct = computed(() => task.value?.subtasks?.length ? Math.round((doneSubs.value / task.value.subtasks.length) * 100) : 0)
const timeTotal = computed(() => timeEntries.value.reduce((s, e) => s + Number(e.hours || 0), 0))

async function loadTime(id) {
  timeEntries.value = await call('pulse.api.time.get_task_time_detail', { task: id }).catch(() => [])
}
async function logTime() {
  const h = parseFloat(newHours.value)
  if (!h || h <= 0) return
  try {
    await call('pulse.api.time.log_time', { task: props.taskId, hours: h, note: newHoursNote.value || null })
    newHours.value = ''; newHoursNote.value = ''
    await loadTime(props.taskId)
    toast.success(`Logged ${h}h`)
  } catch (e) { toast.error('Could not log time') }
}

watch(() => props.taskId, async (id) => {
  task.value = null
  if (!id) return
  const [t, users, types] = await Promise.all([
    call('pulse.api.spa.get_task', { task: id }),
    assignable.value.length ? Promise.resolve(assignable.value) : call('pulse.api.spa.get_assignable_users'),
    issueTypes.value.length ? Promise.resolve(issueTypes.value)
      : call('frappe.client.get_list', { doctype: 'Task Type', fields: ['name'], limit_page_length: 0 }).then(r => r.map(x => x.name)),
  ])
  task.value = t
  assignable.value = users
  issueTypes.value = types
  loadTime(id)
})

async function save(field, value) {
  try {
    await call('pulse.api.spa.update_task', { task: props.taskId, [field]: value })
    toast.success('Saved')
    emit('changed')
  } catch (e) { toast.error('Could not save changes') }
}
async function assign(e) {
  const user = e.target.value
  e.target.value = ''
  if (!user) return
  try {
    const r = await call('pulse.api.spa.assign_task', { task: props.taskId, user })
    task.value.assignees = r.assignees
    toast.success(`Assigned ${user.split('@')[0]}`)
    emit('changed')
  } catch (e2) { toast.error(e2?.messages?.[0] || 'Assignment not allowed') }
}
async function unassign(user) {
  const r = await call('pulse.api.spa.unassign_task', { task: props.taskId, user })
  task.value.assignees = r.assignees
  emit('changed')
}
async function addCheck() {
  if (!newCheck.value) return
  const r = await call('pulse.api.spa.add_checklist_item', { task: props.taskId, item: newCheck.value })
  task.value.checklist.push(r)
  newCheck.value = ''
}
async function toggleCheck(c) {
  await call('pulse.api.spa.toggle_checklist_item', { name: c.name, is_done: c.is_done ? 0 : 1 })
  c.is_done = c.is_done ? 0 : 1
}
async function postComment() {
  if (!newComment.value) return
  const r = await call('pulse.api.spa.add_comment', { task: props.taskId, text: newComment.value })
  task.value.comments.push(r)
  newComment.value = ''
}
async function addSub() {
  if (!newSub.value.trim()) return
  const s = await call('pulse.api.spa.add_subtask', { parent: props.taskId, subject: newSub.value.trim() })
  task.value.subtasks.push(s)
  newSub.value = ''
  toast.success(`Sub-task ${s.issue_key} added`)
  emit('changed')
}
let depTimer
function searchDeps() {
  clearTimeout(depTimer)
  depTimer = setTimeout(async () => {
    if (!depQ.value.trim()) { depResults.value = []; return }
    depResults.value = await call('pulse.api.spa.search_tasks', { q: depQ.value.trim(), exclude: props.taskId }).catch(() => [])
  }, 220)
}
async function addDep(r) {
  depQ.value = ''; depResults.value = []
  await call('pulse.api.spa.add_dependency', { task: props.taskId, depends_on: r.name })
  task.value.blocked_by.push({ dep: 'new', task: r.name, issue_key: r.issue_key, subject: r.subject, status: '' })
  toast.success(`Now blocked by ${r.issue_key}`)
  emit('changed')
}
async function removeDep(dep) {
  await call('pulse.api.spa.remove_dependency', { name: dep })
  task.value.blocked_by = task.value.blocked_by.filter((b) => b.dep !== dep)
}
</script>

<style scoped>
.field { width: 100%; margin-top: 0.125rem; font-size: 0.875rem; border: 1px solid var(--border); border-radius: 0.375rem; padding: 0.25rem 0.5rem; outline: none; background: var(--surface-2); color: var(--text); }
.field:focus { border-color: #60a5fa; }
.btn { font-size: 0.875rem; padding: 0.25rem 0.625rem; border-radius: 0.375rem; background: #2563eb; color: #fff; }
.btn:hover { background: #1d4ed8; }
.slide-enter-active, .slide-leave-active { transition: opacity 0.15s; }
.slide-enter-from, .slide-leave-to { opacity: 0; }
</style>
