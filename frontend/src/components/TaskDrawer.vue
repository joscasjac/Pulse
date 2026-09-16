<template>
  <transition name="slide">
    <div v-if="taskId" class="fixed inset-0 z-40 flex justify-end" @click.self="closeTask">
      <div class="absolute inset-0 bg-black/40" @click="closeTask" />
      <aside ref="drawerElement" tabindex="-1" role="dialog" aria-modal="true" aria-label="Task details" @keydown="handleDrawerKeydown" :class="{ 'task-fullscreen': fullscreen }" class="task-drawer relative max-w-full h-full bg-surface text-app border-l border-app overflow-y-auto">
        <div v-if="task" class="drawer-content">
          <div class="drawer-header flex items-center justify-between">
            <nav v-if="fullscreen" class="task-breadcrumbs" aria-label="Breadcrumb">
              <router-link v-if="task.project" :to="{ path: '/board', query: { project: task.project } }" @click="$emit('close')">{{ projectName || task.project }}</router-link>
              <span v-if="task.project" aria-hidden="true">/</span><router-link :to="{ path: '/board', query: task.project ? { project: task.project } : {} }" @click="$emit('close')">Work items</router-link><span aria-hidden="true">/</span><span aria-current="page">{{ task.issue_key || task.name }}</span>
            </nav>
            <span v-else class="text-xs font-medium text-muted">{{ task.issue_key || task.name }}</span>
            <PersonalControls :name="task.name" class="header-personal" />
            <div class="task-window-actions">
              <button v-if="fullscreen" class="window-action copy-link" @click="copyTaskLink">Copy link</button>
              <button class="window-action" :aria-label="fullscreen ? 'Minimize task view' : 'Open task in fullscreen'" :title="fullscreen ? 'Minimize task view' : 'Open task in fullscreen'" @click="fullscreen = !fullscreen"><Minimize2 v-if="fullscreen" /><Maximize2 v-else /></button>
              <button class="window-action" aria-label="Close task" @click="closeTask"><X /></button>
            </div>
          </div>

          <input v-model="task.subject" @change="save('subject', task.subject)"
            aria-label="Task title" class="task-title w-full bg-transparent border-b border-transparent focus:border-app" />

          <div class="primary-properties">
          <label class="block"><span class="text-xs text-muted">Status</span><select v-model="task.workflow_state" class="field" @change="save('workflow_state', task.workflow_state)"><option v-for="s in config.statuses" :key="s.label">{{ s.label }}</option></select></label>            <label class="block">
              <span class="text-xs text-muted">Priority</span>
              <select v-model="task.priority" @change="save('priority', task.priority)" class="field">
                <option>Low</option><option>Medium</option><option>High</option><option>Urgent</option>
              </select>
            </label>          <!-- Assignees -->
          <div class="primary-assignees">
            <div class="text-xs text-muted mb-1">Assignees</div>
            <div class="flex flex-wrap items-center gap-1.5">
              <span v-for="a in task.assignees" :key="a" class="flex items-center gap-1 pill text-xs pl-2 pr-1 py-0.5">
                {{ a.replace(/@.*/, '') }}
                <button @click="unassign(a)" class="hover:opacity-70">x</button>
              </span>
              <select aria-label="Assign task" @change="assign($event)" class="text-xs border border-app bg-surface-2 text-app rounded-md px-1.5 py-1">
                <option value="">+ assign</option>
                <option v-for="u in assignable" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
              </select>
            </div>
          </div>

          </div>
          <TaskModules :key="task.name" :task="task.name" @changed="$emit('changed')" />
          <nav class="drawer-tabs" aria-label="Task sections"><button :class="{ active: drawerTab === 'details' }" @click="drawerTab = 'details'">Details</button><button :class="{ active: drawerTab === 'activity' }" @click="drawerTab = 'activity'">Activity & comments <span>{{ task.comments.length }}</span></button></nav>
          <div v-show="drawerTab === 'details'" class="task-details-layout">
          <div class="mt-4 task-description">
            <div class="description-heading"><span>Description</span><button class="format-toggle" :aria-pressed="formattingOpen" @click="formattingOpen = !formattingOpen">Formatting</button></div>
            <TextEditor :key="task.name" :content="descriptionDraft" :fixed-menu="formattingOpen" :bubble-menu="true"
              :mentions="assignable.map(u => ({ id: u.name, label: u.full_name || u.name }))"
              :upload-args="{ doctype: 'Task', docname: task.name, is_private: 1 }"
              placeholder="Describe the work. Type @ to mention a teammate."
              editor-class="prose prose-sm min-h-16" @change="descriptionDraft = $event" />
            <button v-if="descriptionDraft !== (task.description || '')" class="btn mt-2" :disabled="descriptionSaving" @click="saveDescription">{{ descriptionSaving ? 'Saving…' : 'Save description' }}</button>
          </div>

          <details class="task-section task-properties"><summary>Properties <span>Dates, estimates, type & labels</span></summary>
          <div class="grid grid-cols-2 gap-3 mt-4 text-sm">


            <label class="block">
              <span class="text-xs text-muted">Type</span>
              <select v-model="task.task_type" @change="save('task_type', task.task_type)" class="field">
                <option v-for="t in issueTypes" :key="t" :value="t">{{ t }}</option>
              </select>
            </label>

            <label class="block">
              <span class="text-xs text-muted">Start date</span>
              <input type="date" v-model="task.exp_start_date" @change="save('exp_start_date', task.exp_start_date)" class="field" />
            </label>
            <label class="block">
              <span class="text-xs text-muted">Estimated hours</span>
              <input type="number" min="0" step="0.25" v-model.number="task.expected_time" @change="save('expected_time', task.expected_time)" class="field" />
            </label>
            <label class="block">
              <span class="text-xs text-muted">Story points</span>
              <input type="number" min="0" step="0.5" v-model.number="task.pulse_story_points" @change="save('pulse_story_points', task.pulse_story_points)" class="field" />
            </label>
            <label class="block">
              <span class="text-xs text-muted">Due date</span>
              <input type="date" v-model="task.exp_end_date" @change="save('exp_end_date', task.exp_end_date)" class="field" />
            </label>
          </div>

          <fieldset class="mt-4" v-if="config.labels.length"><legend class="text-xs text-muted mb-2">Labels</legend><div class="flex flex-wrap gap-3"><label v-for="l in config.labels" :key="l.name" class="text-sm flex gap-1 items-center"><input type="checkbox" :checked="task.pulse_labels.some(row => row.label === l.name)" @change="toggleLabel(l.name, $event.target.checked)" /><span :style="{ color: l.color }">●</span>{{ l.label_name }}</label></div></fieldset>
          <!-- Epic + Release -->
          <div class="grid grid-cols-2 gap-3 mt-3 text-sm">
            <label class="block">
              <span class="text-xs text-muted">Epic</span>
              <select v-model="task.pulse_epic" @change="save('pulse_epic', task.pulse_epic)" class="field">
                <option :value="null">— none —</option>
                <option v-for="e in epics" :key="e.name" :value="e.name">
                  {{ e.issue_key ? e.issue_key + ' · ' : '' }}{{ e.subject }}
                </option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs text-muted">Release</span>
              <input v-model="task.pulse_release" list="pulse-releases" placeholder="e.g. v1.2"
                @change="save('pulse_release', task.pulse_release)" class="field" />
              <datalist id="pulse-releases">
                <option v-for="r in releases" :key="r.release_name" :value="r.release_name" />
              </datalist>
            </label>
          </div>

          </details>
          <details class="task-section task-time"><summary>Time tracking</summary>
            <TaskTime :key="task.name" :task-id="task.name" @changed="$emit('changed')" />
          </details>

          <!-- Attachments -->
          <details class="task-section task-attachments"><summary>Attachments <span>{{ attachments.length || 'Add a file' }}</span></summary>
          <div class="section-body">
            <div class="text-xs text-muted mb-1.5 flex items-center justify-between">
              <span>Attachments</span>
              <label class="btn cursor-pointer">
                <input type="file" class="hidden" @change="uploadFile" :disabled="uploading" />
                {{ uploading ? 'Uploading…' : 'Attach' }}
              </label>
            </div>
            <div v-for="f in attachments" :key="f.name" class="flex items-center gap-2 py-0.5 text-sm">
              <Paperclip class="w-3.5 h-3.5 text-faint shrink-0" />
              <a :href="f.file_url" target="_blank" class="truncate flex-1 hover:underline" style="color:var(--accent)">{{ f.file_name }}</a>
              <span class="text-[10px] text-faint">{{ fmtSize(f.file_size) }}</span>
              <button class="text-faint hover:text-app" @click="removeAttachment(f.name)"><X class="w-3 h-3" /></button>
            </div>
            <p v-if="attachmentError" class="text-xs" role="alert">{{ attachmentError }} <button class="underline" @click="loadAttachments(props.taskId)">Retry</button></p>
            <div v-if="!attachments.length && !attachmentError" class="text-xs text-faint py-1">No files attached.</div>
          </div>

          </details>
          <details class="task-section task-relations"><summary>Relationships <span>{{ task.subtasks.length }} sub-tasks · {{ task.blocked_by.length }} blockers</span></summary>
          <!-- Parent -->
          <div v-if="task.parent" class="mt-4 text-xs">
            <span class="text-muted">Parent: </span>
            <span class="mono text-accent">{{ task.parent.issue_key }}</span>
            <span class="text-muted"> · {{ task.parent.subject }}</span>
          </div>

          <!-- Sub-tasks -->
          <div class="mt-5">
            <div class="text-xs text-muted mb-1.5 flex items-center justify-between">
              <span>Sub-tasks</span>
              <span v-if="task.subtasks.length" class="text-faint">{{ doneSubs }}/{{ task.subtasks.length }} done</span>
            </div>
            <div v-if="task.subtasks.length" class="h-1 rounded-full bg-surface-2 mb-2 overflow-hidden">
              <div class="h-full rounded-full" :style="{ width: subPct + '%', background: 'var(--term-green)' }" />
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
              <a v-if="b.sources?.includes('erpnext')" :href="`/app/task/${encodeURIComponent(props.taskId)}`" class="text-xs text-muted underline" title="This dependency is also managed in ERPNext">ERPNext</a>
              <button v-if="b.can_remove !== false" class="text-faint hover:text-app" @click="removeDep(b.dep)"><X class="w-3 h-3" /></button>
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

          </details>
          <!-- Checklist -->
          <details class="task-section task-checklist"><summary>Checklist <span>{{ task.checklist.filter(item => item.is_done).length }}/{{ task.checklist.length }}</span></summary>
          <div class="section-body">
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

          </details>
          <button class="archive-action" @click="archive">{{ task.pulse_archived ? 'Restore task' : 'Archive task' }}</button>
          </div>
          <div v-show="drawerTab === 'activity'">
          <section class="mt-5" aria-label="Task activity"><h3 class="text-xs text-muted mb-2">Activity</h3>
            <p v-if="activityError" role="alert" class="text-xs">{{ activityError }} <button class="underline" @click="loadActivity">Retry</button></p>
            <p v-if="!activity.length && !activityError" class="text-xs text-muted">No changes recorded yet.</p>
            <div v-for="entry in activity" :key="entry.name" class="text-xs py-2 border-b border-app">
              <div class="text-muted">{{ entry.user }} · {{ new Date(entry.at).toLocaleString() }}</div>
              <p v-if="entry.description">{{ entry.description }}</p>
              <p v-for="(change, i) in entry.changed" :key="i">{{ fieldLabel(change[0]) }}: {{ plainValue(change[1]) }} → {{ plainValue(change[2]) }}</p>
              <p v-for="(summary, i) in childActivity(entry)" :key="`row-${i}`">{{ summary }}</p>
            </div>
          </section>

          <!-- Comments -->
          <div class="mt-5">
            <div class="text-xs text-muted mb-1">Comments</div>
            <div v-for="c in task.comments" :key="c.name" class="comment-entry text-sm">
              <div class="text-app">{{ c.comment_text }}</div>
              <div class="text-[10px] text-muted">{{ c.owner }}</div>
            </div>
            <div class="flex gap-2 mt-1">
              <input v-model="newComment" @keyup.enter="postComment" placeholder="Write a comment..." class="field flex-1" />
              <button class="btn" @click="postComment">Send</button>
            </div>
          </div>
          </div>
        </div>
        <div v-else class="p-10 text-center text-muted">
          <p role="status">{{ loadError || 'Loading…' }}</p>
          <div class="mt-3 flex justify-center gap-2">
            <button v-if="loadError" class="btn" @click="loadTask(props.taskId)">Retry</button>
            <button class="btn" aria-label="Close task" @click="closeTask">Close</button>
          </div>
        </div>
      </aside>
    </div>
  </transition>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import Maximize2 from '~icons/lucide/maximize-2'
import Minimize2 from '~icons/lucide/minimize-2'
import PersonalControls from './PersonalControls.vue'
import TaskModules from './tasks/TaskModules.vue'
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { call, TextEditor } from 'frappe-ui'
import { toast } from '@/ui/toast'
import StatusPill from '@/ui/StatusPill.vue'
import TaskTime from './TaskTime.vue'
import X from '~icons/lucide/x'
import Paperclip from '~icons/lucide/paperclip'

const props = defineProps({ taskId: { type: String, default: null } })
const emit = defineEmits(['close', 'changed', 'open'])
const route = useRoute(), router = useRouter()
const fullscreen = ref(route.query.task_view === 'full')
const projectName = ref('')
function closeTask() {
  emit('close')
  if (route.query.task === props.taskId) {
    const query = { ...route.query }; delete query.task; delete query.task_view
    router.replace({ path: route.path, query }).catch(() => {})
  }
}
async function copyTaskLink() {
  const href = router.resolve({ path: '/board', query: { project: task.value.project || undefined, task: task.value.name, task_view: 'full' } }).href
  try { await navigator.clipboard.writeText(new URL(href, window.location.origin).href); toast.success('Task link copied') }
  catch { toast.error('Could not copy the task link. Please allow clipboard access and retry.') }
}

const drawerElement = ref(null)
let returnFocus = null
const formattingOpen = ref(false)
const drawerTab = ref('details')
const task = ref(null)
const config = ref({ statuses: [], labels: [] })
const activity = ref([])
const activityError = ref(''), attachmentError = ref(''), loadError = ref('')
let taskRequest = 0
const descriptionDraft = ref('')
const descriptionSaving = ref(false)
const assignable = ref([])
const issueTypes = ref([])
const newCheck = ref('')
const newComment = ref('')
const newSub = ref('')
const depQ = ref('')
const depResults = ref([])
const attachments = ref([])
const uploading = ref(false)
const epics = ref([])
const releases = ref([])

const doneSubs = computed(() => (task.value?.subtasks || []).filter((s) => s.status === 'Completed').length)
const subPct = computed(() => task.value?.subtasks?.length ? Math.round((doneSubs.value / task.value.subtasks.length) * 100) : 0)
async function loadAttachments(id) {
  attachmentError.value = ''
  try { const rows = await call('pulse.api.spa.list_attachments', { task: id }); if (props.taskId === id) attachments.value = rows }
  catch (e) { if (props.taskId === id) attachmentError.value = 'Could not load attachments.' }
}
async function uploadFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file, file.name)
    fd.append('doctype', 'Task')
    fd.append('docname', props.taskId)
    fd.append('is_private', '1')
    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' },
      body: fd,
    })
    if (!res.ok) throw new Error('HTTP ' + res.status)
    await loadAttachments(props.taskId)
    toast.success('File attached')
  } catch (err) { toast.error('Upload failed') }
  finally { uploading.value = false }
}
async function removeAttachment(name) {
  try { await call('pulse.api.spa.delete_attachment', { name }); await loadAttachments(props.taskId) }
  catch (e) { toast.error('Could not remove attachment. Please retry.') }
}
function fmtSize(b) {
  if (!b) return ''
  if (b < 1024) return b + ' B'
  if (b < 1048576) return (b / 1024).toFixed(0) + ' KB'
  return (b / 1048576).toFixed(1) + ' MB'
}

async function loadTask(id) {
  const request = ++taskRequest
  drawerTab.value = 'details'
  projectName.value = ''
  formattingOpen.value = false
  task.value = null; loadError.value = ''; activity.value = []; attachments.value = []; config.value = { statuses: [], labels: [] }
  activityError.value = ''; attachmentError.value = ''
  if (!id) return
  try {
  const [t, users, types] = await Promise.all([
    call('pulse.api.spa.get_task', { task: id }),
    assignable.value.length ? Promise.resolve(assignable.value) : call('pulse.api.spa.get_assignable_users'),
    issueTypes.value.length ? Promise.resolve(issueTypes.value)
      : call('frappe.client.get_list', { doctype: 'Task Type', fields: ['name'], limit_page_length: 0 }).then(r => r.map(x => x.name)),
  ])
  if (props.taskId !== id || request !== taskRequest) return
  const projectConfig = t.project ? await call('pulse.api.task_config.get_config', { project: t.project }) : { statuses: [], labels: [] }
  if (props.taskId !== id || request !== taskRequest) return
  t.exp_start_date = t.exp_start_date ? String(t.exp_start_date).slice(0, 10) : ''
  t.exp_end_date = t.exp_end_date ? String(t.exp_end_date).slice(0, 10) : ''
  task.value = t
  if (t.project) {
    call('frappe.client.get_value', { doctype: 'Project', filters: t.project, fieldname: 'project_name' })
      .then(result => { if (props.taskId === id && request === taskRequest) projectName.value = result?.project_name || t.project })
      .catch(() => { if (props.taskId === id && request === taskRequest) projectName.value = t.project })
  }
  descriptionDraft.value = t.description || ''
  assignable.value = users
  issueTypes.value = types
  config.value = projectConfig
  if (config.value.task_types) issueTypes.value = config.value.task_types
  await loadActivity()
  loadAttachments(id)
  // epic choices are project-scoped; releases are free-text suggestions
  const [epicRows, releaseRows] = await Promise.all([call('pulse.api.planning.epic_options', { project: t.project }), call('pulse.api.planning.list_releases')])
  if (request === taskRequest) { epics.value = epicRows; releases.value = releaseRows }
  } catch (e) { if (request === taskRequest) { loadError.value = e?.messages?.[0] || 'Could not load task details.'; toast.error(loadError.value) } }
}
watch(() => props.taskId, loadTask, { immediate: true })
function restoreFocus() {
  if (returnFocus?.isConnected) returnFocus.focus()
  returnFocus = null
}
watch(() => props.taskId, async (id, previous) => {
  if (id) {
    if (!previous) { returnFocus = document.activeElement; fullscreen.value = route.query.task_view === 'full' }
    await nextTick()
    drawerElement.value?.focus()
  } else restoreFocus()
}, { immediate: true })
onBeforeUnmount(restoreFocus)
function handleDrawerKeydown(event) {
  if (event.key === 'Escape') { event.preventDefault(); closeTask(); return }
  if (event.key !== 'Tab') return
  const focusable = [...(drawerElement.value?.querySelectorAll('button, summary, [href], input, select, textarea, [tabindex], [contenteditable="true"]') || [])]
    .filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length)
  if (!focusable.length) { event.preventDefault(); drawerElement.value?.focus(); return }
  const first = focusable[0], last = focusable[focusable.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === drawerElement.value)) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && (document.activeElement === last || document.activeElement === drawerElement.value)) { event.preventDefault(); first.focus() }
}


function fieldLabel(field) { return ({ workflow_state: 'Status', status: 'ERPNext status', priority: 'Priority', subject: 'Title', description: 'Description', project: 'Project', pulse_archived: 'Archived', pulse_labels: 'Labels', depends_on: 'Dependencies', expected_time: 'Estimated hours', pulse_story_points: 'Story points', exp_start_date: 'Start date', exp_end_date: 'Due date', type: 'Type' })[field] || field.replaceAll('_', ' ') }
function plainValue(value) { return String(value ?? '—').replace(/<[^>]*>/g, '').slice(0, 180) }
function childActivity(entry) {
  const summaries = []
  for (const [key, verb] of [['added', 'Added'], ['removed', 'Removed']]) {
    for (const [field, row] of entry[key] || []) {
      if (field === 'pulse_labels') {
        const label = config.value.labels.find(item => item.name === row?.label)
        summaries.push(`${verb} label: ${label?.label_name || 'No longer available in this project'}`)
      } else {
        summaries.push(`${verb} ${fieldLabel(field).toLowerCase()} entry`)
      }
    }
  }
  for (const row of entry.row_changed || []) summaries.push(`Updated ${fieldLabel(row[0]).toLowerCase()} entry`)
  return summaries
}
async function loadActivity() {
  const id = props.taskId; activityError.value = ''
  try { const rows = await call('pulse.api.tasks.activity', { task: id }); if (props.taskId === id) activity.value = rows }
  catch (e) { if (props.taskId === id) activityError.value = 'Could not load activity.' }
}
async function toggleLabel(name, checked) {
  const rows = task.value.pulse_labels.filter(row => row.label !== name)
  if (checked) rows.push({ label: name })
  try { await call('pulse.api.tasks.bulk_update', { tasks: [props.taskId], fields: { pulse_labels: rows } }); task.value.pulse_labels = rows; await loadActivity(); emit('changed') }
  catch (e) { toast.error(e?.messages?.[0] || 'Could not update labels') }
}
async function archive() { await save('pulse_archived', task.value.pulse_archived ? 0 : 1); task.value = await call('pulse.api.spa.get_task', { task: props.taskId }) }
async function saveDescription() {
  if (descriptionSaving.value) return
  descriptionSaving.value = true
  try {
    await call('pulse.api.tasks.bulk_update', { tasks: [task.value.name], fields: { description: descriptionDraft.value } })
    task.value.description = descriptionDraft.value
    await loadActivity()
    toast.success('Description saved'); emit('changed')
  } catch (e) { toast.error(e?.messages?.[0] || 'Description could not be saved. Your text has been kept.') }
  finally { descriptionSaving.value = false }
}
async function save(field, value) {
  try {
    const id = props.taskId
    if (field === 'workflow_state') {
      const result = await call('pulse.api.spa.update_task_state', { task: id, state: value })
      if (props.taskId === id) Object.assign(task.value, result)
    } else {
      await call('pulse.api.tasks.bulk_update', { tasks: [id], fields: { [field]: value } })
    }
    await loadActivity()
    toast.success('Saved')
    emit('changed')
  } catch (e) {
    toast.error(e?.messages?.[0] || 'Could not save changes')
    const id = props.taskId
    try { const fresh = await call('pulse.api.spa.get_task', { task: id }); if (props.taskId === id) task.value[field] = fresh[field] } catch { /* Keep the draft available for retry. */ }
  }
}
async function assign(e) {
  const user = e.target.value
  e.target.value = ''
  if (!user) return
  try {
    const r = await call('pulse.api.spa.assign_task', { task: props.taskId, user })
    task.value.assignees = r.assignees
    await loadActivity()
    toast.success(`Assigned ${user.split('@')[0]}`)
    emit('changed')
  } catch (e2) { toast.error(e2?.messages?.[0] || 'Assignment not allowed') }
}
async function unassign(user) {
  const r = await call('pulse.api.spa.unassign_task', { task: props.taskId, user })
  task.value.assignees = r.assignees
  await loadActivity()
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
  await loadTask(props.taskId)
  toast.success(`Now blocked by ${r.issue_key}`)
  emit('changed')
}
async function removeDep(dep) {
  await call('pulse.api.spa.remove_dependency', { name: dep })
  await loadTask(props.taskId)
  emit('changed')
}
</script>

<style scoped>
.task-drawer { width: 600px; box-shadow: -12px 0 36px rgb(0 0 0 / 8%); }
.drawer-content { padding: 0 24px 24px; }
.drawer-header { height: 52px; margin: 0 -24px; padding: 0 20px; border-bottom: 1px solid var(--border); background: var(--surface); }
.task-title { font-size: 21px; line-height: 1.4; font-weight: 600; padding: 20px 0 12px; outline: none; }
.drawer-tabs { display: flex; gap: 24px; border-bottom: 1px solid var(--border); margin: 14px 0 18px; }
.drawer-tabs button { padding: 10px 0; font-size: 13px; color: var(--muted); border-bottom: 2px solid transparent; }
.drawer-tabs button.active { color: var(--accent); border-color: var(--accent); }
.drawer-tabs span { margin-left: 5px; font-size: 11px; }
.section-heading { font-size: 13px; font-weight: 600; padding-top: 24px; margin-top: 24px; border-top: 1px solid var(--border); }
.field { width: 100%; min-height: 32px; margin-top: 5px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; padding: 5px 9px; outline: none; background: var(--surface); color: var(--text); }
.field:focus, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.btn { font-size: 12px; min-height: 30px; padding: 5px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-weight: 500; }
.btn:hover { background: var(--surface-2); }
.btn:disabled { opacity: .5; }
.archive-action { margin-top: 28px; color: var(--muted); font-size: 12px; text-decoration: underline; }
.comment-entry { padding: 12px 0; border-bottom: 1px solid var(--border); }
.slide-enter-active, .slide-leave-active { transition: opacity .15s; }
.slide-enter-from, .slide-leave-to { opacity: 0; }
@media(max-width: 600px) { .drawer-content { padding: 0 18px 24px; } .drawer-header { margin: 0 -18px; padding: 0 18px; } .task-title { font-size: 20px; } }
.primary-properties { display: flex; gap: 8px; align-items: flex-start; flex-wrap: wrap; margin: 3px 0 12px; }
.primary-properties > label { flex: 0 1 132px; }
.primary-properties .field { border-color: transparent; background: transparent; min-height: 29px; margin-top: 3px; font-size: 12px; padding: 4px 7px; }
.primary-properties .field:hover, .primary-properties .field:focus { border-color: var(--border); background: var(--surface-2); }
.primary-assignees { flex: 1 1 180px; min-width: 0; }
.primary-assignees > div:first-child { margin-bottom: 3px; }
.header-personal { margin-left: auto; margin-right: 14px; }
.header-personal :deep(button) { border: 0; background: transparent; color: var(--muted); padding: 2px 5px; font-size: 11px; min-height: 26px; }
.description-heading { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.format-toggle { font-size: 11px; padding: 3px 5px; border-radius: 4px; }
.format-toggle:hover, .format-toggle[aria-pressed=true] { background: var(--surface-2); color: var(--text); }
.task-section { border-top: 1px solid var(--border); }
.task-section:first-of-type { margin-top: 22px; }
.task-section > summary { cursor: pointer; padding: 13px 0; font-size: 12px; font-weight: 500; }
.task-section > summary span { font-size: 11px; color: var(--muted); font-weight: 400; margin-left: 8px; }
.task-section[open] { padding-bottom: 16px; }
.task-section > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.section-body { padding-top: 3px; }
.task-section :deep(section) { margin-top: 0; }
@media(max-width: 600px) { .header-personal { margin-right: 6px; gap: 2px; } .primary-properties > label { flex: 1 1 100px; } .primary-assignees { flex-basis: 100%; } .task-section > summary span { display: inline-block; } }
.task-window-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.window-action { display: inline-flex; align-items: center; justify-content: center; min-width: 28px; height: 28px; border-radius: 4px; color: var(--muted); font-size: 11px; padding: 4px; }
.window-action:hover { background: var(--surface-2); color: var(--text); }.window-action svg { width: 15px; height: 15px; }
.task-fullscreen { width: 100%; border: 0; box-shadow: none; }
.task-fullscreen .drawer-content { max-width: 1180px; margin: 0 auto; padding: 0 40px 40px; }
.task-fullscreen .drawer-header { min-height: 56px; margin: 0 -40px 12px; padding: 0 24px; }
.task-breadcrumbs { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-width: 0; font-size: 12px; color: var(--muted); }
.task-breadcrumbs a:hover { color: var(--text); text-decoration: underline; }.task-breadcrumbs [aria-current] { color: var(--text); }.task-breadcrumbs a { max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-fullscreen .task-title { font-size: 27px; }
.task-fullscreen .task-details-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; column-gap: 48px; align-items: start; }
.task-fullscreen .task-description { grid-column: 1; grid-row: 1 / span 2; margin-top: 0; min-width: 0; }
.task-fullscreen .task-properties { grid-column: 2; grid-row: 1; margin-top: 0; }
.task-fullscreen .task-time { grid-column: 2; grid-row: 2; }
.task-fullscreen .task-attachments { grid-column: 1; grid-row: 3; margin-top: 20px; }
.task-fullscreen .task-relations { grid-column: 1; grid-row: 4; }
.task-fullscreen .task-checklist { grid-column: 1; grid-row: 5; }
.task-fullscreen .archive-action { grid-column: 2; grid-row: 3; justify-self: start; }
@media(max-width: 800px) { .task-fullscreen .drawer-content { padding: 0 20px 24px; }.task-fullscreen .drawer-header { height: auto; min-height: 56px; margin: 0 -20px 8px; padding: 10px 16px; flex-wrap: wrap; gap: 8px; }.task-fullscreen .task-details-layout { display: block; }.task-fullscreen .task-title { font-size: 22px; }.task-fullscreen .task-properties { margin-top: 22px; }.task-fullscreen .task-breadcrumbs { flex: 1 1 calc(100% - 90px); }.task-fullscreen .header-personal { order: 3; margin: 0; width: 100%; }.task-fullscreen .copy-link { display: none; }.task-breadcrumbs a { max-width: 140px; } }
</style>
