<!-- THESIS: One clear list of personal work. OWN-WORLD: Quiet tab bar and compact task rows. STORY: Filter assigned tasks, then act in the task drawer. FIRST VIEWPORT: Title, status tabs, search and grouped list. FORM: User-selected Plane workspace grammar. -->
<template>
  <div class="my-work">
    <header class="work-header"><div><h1>My work</h1><p>Project tasks and CRM follow-ups assigned to you.</p></div></header>
    <div class="work-toolbar">
      <nav class="work-tabs" aria-label="Task status"><button v-for="tab in tabs" :key="tab.value" :class="{ selected: selected === tab.value }" :aria-pressed="selected === tab.value" @click="selected = tab.value">{{ tab.label }}<span>{{ tab.count }}</span></button></nav>
      <label class="work-source">Source<select v-model="source"><option value="all">All work</option><option value="project">Project tasks</option><option value="crm">CRM tasks</option></select></label><label class="work-search"><span class="sr-only">Search your tasks</span><input v-model="query" type="search" placeholder="Search tasks…" /></label>
    </div>
    <p v-if="source === 'crm' && !crmAvailable && !loading" class="work-loading">Frappe CRM is not installed on this site. CRM tasks will appear here when it is available.</p><p v-if="crmError" role="alert" class="work-error">{{ crmError }} <button class="btn-ghost" @click="reload">Try again</button></p><div v-if="error" class="work-error" role="alert">{{ error }} <button class="btn-ghost" @click="reload">Try again</button></div>
    <div v-if="loading" class="work-loading" role="status">Loading your tasks…</div>
    <template v-else>
      <section v-for="group in groups" :key="group.title" class="work-group" :aria-label="group.title">
        <h2>{{ group.title }} <span>{{ group.tasks.length }}</span></h2>
        <div class="work-table-wrap"><table class="work-table"><thead><tr><th scope="col">Task</th><th scope="col">Priority</th><th scope="col">Status</th><th scope="col">Project / CRM record</th><th scope="col">Due date</th></tr></thead><tbody>
          <template v-for="task in group.tasks" :key="task.identity || task.name"><tr><td><button class="task-link" @click="task.source === 'frappe_crm' ? (crmOpen = crmOpen === task.identity ? null : task.identity) : (openId = task.name)"><span class="task-identifier">{{ task.issue_key || task.name }}</span><span class="task-title">{{ task.subject }}</span></button><span v-if="task.task_type" class="task-type">{{ task.task_type }}</span></td><td><PriorityDot :value="task.priority" show-label /></td><td><StatusPill :value="task.status" :label="task.workflow_state || task.status" /></td><td class="project-cell"><router-link v-if="task.project" :to="{ path: '/board', query: { project: task.project } }">{{ projectNames[task.project] || task.project }}</router-link><a v-else-if="task.reference_url" :href="task.reference_url">{{ task.reference_doctype.replace('CRM ', '') }} {{ task.reference_docname }}</a><span v-else>—</span></td><td :class="{ overdue: isOverdue(task) }">{{ task.exp_end_date ? formatDate(task.exp_end_date) : 'No date' }}</td></tr><tr v-if="crmOpen === task.identity && task.source === 'frappe_crm'"><td colspan="5"><CrmTaskEditor v-if="task.can_write" :task="task" @close="crmOpen = null" @saved="crmSaved" /><p v-else>You have read-only access to this CRM task.</p></td></tr></template>
        </tbody></table></div>
      </section>
      <div v-if="!groups.length" class="work-empty"><h2>{{ query ? 'No matching tasks' : selected === 'completed' ? 'No completed tasks yet' : selected === 'overdue' ? 'Nothing overdue' : 'No open tasks assigned to you' }}</h2><p>{{ query ? 'Try another task name, project, or task ID.' : selected === 'overdue' ? 'Your open tasks are on schedule or have no due date.' : 'Your assigned work will appear here as your team plans tasks.' }}</p><button v-if="query" class="btn-ghost" @click="query = ''">Clear search</button><router-link v-else to="/projects" class="btn-ghost">Browse projects</router-link></div>
    </template>
    <TaskDrawer :task-id="openId" @close="openId = null" @changed="reload" @open="openId = $event" />
  </div>
</template>
<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { call } from 'frappe-ui'
import CrmTaskEditor from '@/components/CrmTaskEditor.vue'
import TaskDrawer from '@/components/TaskDrawer.vue'
import PriorityDot from '@/ui/PriorityDot.vue'
import StatusPill from '@/ui/StatusPill.vue'
import { createState } from '@/ui/create'
const loading = ref(true), tasks = ref([]), openId = ref(null), error = ref(''), query = ref(''), selected = ref('open'), projectNames = ref({})
const source = ref('all'), crmAvailable = ref(false), crmError = ref(''), crmOpen = ref(null)
function normalizeCrm(row) { return { ...row, subject: row.title, issue_key: `CRM-${row.name}`, task_type: 'CRM task', crm_status: row.status, status: row.status === 'Done' ? 'Completed' : row.status === 'Canceled' ? 'Cancelled' : 'Open', workflow_state: row.status, exp_end_date: row.due_date?.slice(0, 10) || null } }
function crmSaved(row) { tasks.value = tasks.value.map(task => task.identity === row.identity ? normalizeCrm(row) : task); crmOpen.value = null }
const scopedTasks = computed(() => tasks.value.filter(task => source.value === 'all' || (source.value === 'crm' ? task.source === 'frappe_crm' : task.source !== 'frappe_crm')))
const now = new Date(), today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
const isOpen = task => !['Completed', 'Cancelled'].includes(task.status)
const isOverdue = task => isOpen(task) && task.exp_end_date && task.exp_end_date < today
const tabs = computed(() => [{ value: 'open', label: 'Open', count: scopedTasks.value.filter(isOpen).length }, { value: 'overdue', label: 'Overdue', count: scopedTasks.value.filter(isOverdue).length }, { value: 'completed', label: 'Completed', count: scopedTasks.value.filter(t => t.status === 'Completed').length }, { value: 'all', label: 'All', count: scopedTasks.value.length }])
const visible = computed(() => scopedTasks.value.filter(task => {
  if (selected.value === 'open' && !isOpen(task)) return false
  if (selected.value === 'overdue' && !isOverdue(task)) return false
  if (selected.value === 'completed' && task.status !== 'Completed') return false
  return [task.subject, task.issue_key, task.name, projectNames.value[task.project], task.project, task.reference_docname].join(' ').toLowerCase().includes(query.value.toLowerCase().trim())
}))
const groups = computed(() => {
  if (selected.value !== 'open') return visible.value.length ? [{ title: tabs.value.find(t => t.value === selected.value).label + ' tasks', tasks: visible.value }] : []
  return [{ title: 'Overdue', tasks: visible.value.filter(isOverdue) }, { title: 'Due today', tasks: visible.value.filter(t => t.exp_end_date === today) }, { title: 'Upcoming', tasks: visible.value.filter(t => t.exp_end_date > today) }, { title: 'No due date', tasks: visible.value.filter(t => !t.exp_end_date) }].filter(g => g.tasks.length)
})
function formatDate(date) { return new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }
let requestId = 0
async function reload() {
  const request = ++requestId
  loading.value = true; error.value = ''; crmError.value = ''
  try {
    const me = await call('frappe.auth.get_logged_user')
    const [native, projectResult, crmResult] = await Promise.allSettled([
      call('frappe.client.get_list', { doctype: 'Task', fields: ['name', 'issue_key', 'subject', 'type as task_type', 'priority', 'status', 'workflow_state', 'project', 'exp_end_date', '_assign'], filters: [['_assign', 'like', `%${me}%`], ['pulse_archived', '=', 0]], order_by: 'exp_end_date asc, modified desc', limit_page_length: 0 }),
      call('frappe.client.get_list', { doctype: 'Project', fields: ['name', 'project_name'], limit_page_length: 0 }),
      call('pulse.api.crm_tasks.mine')
    ])
    if (request !== requestId) return
    tasks.value = native.status === 'fulfilled' ? (native.value || []).filter(task => { try { return JSON.parse(task._assign || '[]').includes(me) } catch { return false } }) : []
    if (native.status === 'rejected') error.value = 'Project tasks could not be loaded. Please try again.'
    if (crmResult.status === 'fulfilled') { crmAvailable.value = crmResult.value.available; tasks.value.push(...(crmResult.value.tasks || []).map(normalizeCrm)) }
    else crmError.value = 'CRM tasks could not be loaded. Please try again.'
    projectNames.value = Object.fromEntries((projectResult.status === 'fulfilled' ? projectResult.value || [] : []).map(p => [p.name, p.project_name]))
  } catch { if (request === requestId) error.value = 'Your tasks could not be loaded. Please try again.' }
  finally { if (request === requestId) loading.value = false }
}
watch(() => createState.created, reload)
onMounted(() => { reload(); window.addEventListener('focus', reload) })
onBeforeUnmount(() => { requestId++; window.removeEventListener('focus', reload) })
</script>
<style scoped>
.my-work { padding: 28px 32px 64px; }
.work-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 26px; }
h1 { font-size: 22px; font-weight: 600; }.work-header p { margin-top: 6px; color: var(--muted); font-size: 13px; }
.work-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
.work-tabs { display: flex; gap: 22px; }.work-tabs button { min-height: 44px; border-bottom: 2px solid transparent; color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 7px; white-space: nowrap; }.work-tabs button.selected { border-color: var(--accent); color: var(--text); }.work-tabs span { font-size: 11px; background: var(--surface-2); border-radius: 4px; padding: 1px 5px; color: var(--muted); }
.work-source { display: flex; gap: 6px; align-items: center; color: var(--muted); font-size: 12px; }.work-source select { height: 32px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); padding: 0 8px; }.work-search input { width: 200px; height: 32px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0 10px; color: var(--text); font-size: 12px; }.work-search input::placeholder { color: var(--muted); }
.work-group { margin-bottom: 24px; }.work-group h2 { font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 8px; padding: 10px 12px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 6px 6px 0 0; }.work-group h2 span { font-weight: 400; color: var(--muted); }
.work-table-wrap { overflow-x: auto; }.work-table { width: 100%; border-collapse: collapse; min-width: 680px; font-size: 12px; }.work-table th { font-weight: 400; text-align: left; color: var(--muted); padding: 9px 12px; border-bottom: 1px solid var(--border); }.work-table td { padding: 12px; border-bottom: 1px solid var(--border-soft); color: var(--muted); }.work-table tr:hover td { background: var(--hover); }.work-table th:first-child { width: 45%; }.task-link { text-align: left; display: flex; gap: 12px; align-items: baseline; width: 100%; }.task-link:hover .task-title { color: var(--accent); }.task-identifier { font-size: 11px; color: var(--muted); white-space: nowrap; }.task-title { color: var(--text); font-size: 13px; }.task-type { display: block; margin-top: 4px; font-size: 10px; color: var(--muted); }.project-cell { max-width: 190px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.project-cell a:hover { color: var(--accent); }.work-table td.overdue { color: var(--danger); }.work-table td:last-child { white-space: nowrap; }
.work-empty { padding: 64px 20px; text-align: center; }.work-empty h2 { font-size: 15px; font-weight: 500; }.work-empty p { font-size: 13px; color: var(--muted); margin: 10px 0 20px; }.work-error { color: var(--danger); font-size: 13px; margin-bottom: 20px; }.work-loading { color: var(--muted); padding: 32px 0; font-size: 13px; }
@media (max-width: 768px) { .my-work { padding: 24px 16px; }.work-toolbar { flex-wrap: wrap; padding-bottom: 10px; gap: 10px; }.work-tabs { gap: 16px; }.work-header { align-items: flex-start; }.work-header .btn-primary { white-space: nowrap; }.work-search, .work-search input { width: 100%; } }
</style>
