<!-- Projects index follows the shared Plane-inspired workspace: flat rows, one creation action,
     searchable project context, and explicit tabs for templates and capacity planning. -->
<template>
  <div class="projects-page">
    <header class="page-heading">
      <div><h1>Projects</h1><p class="text-muted">Your team's projects and client work.</p></div>
      <button @click="openEntity('Project')" class="btn-primary"><Plus class="w-3.5 h-3.5" /> New project</button>
    </header>

    <nav class="project-tabs" aria-label="Project views">
      <button :class="{ selected: activeTab === 'projects' }" :aria-current="activeTab === 'projects' ? 'page' : undefined" @click="chooseTab('projects')">All projects <span>{{ projects.length }}</span></button>
      <button :class="{ selected: activeTab === 'templates' }" :aria-current="activeTab === 'templates' ? 'page' : undefined" @click="chooseTab('templates')">Templates <span>{{ templateCount }}</span></button>
      <button :class="{ selected: activeTab === 'workload' }" :aria-current="activeTab === 'workload' ? 'page' : undefined" @click="chooseTab('workload')">Workload</button>
    </nav>

    <div v-if="error" role="alert" class="error-notice">{{ error }} <button class="underline" @click="activeTab === 'workload' ? loadWorkload() : reload()">Retry</button></div>

    <template v-if="activeTab !== 'workload'">
      <div class="project-toolbar">
        <label class="search-field"><Search class="w-4 h-4" /><input v-model="search" type="search" placeholder="Search projects…" aria-label="Search projects by name, key, customer or order" /></label>
        <select v-model="statusFilter" class="field status-filter" aria-label="Filter by project status"><option value="">All statuses</option><option v-for="status in statuses" :key="status">{{ status }}</option></select>
      </div>
      <p v-if="activeTab === 'templates'" class="section-hint">Start repeatable work from a template. Mark any project as a template in its business details.</p>

      <form v-if="editing" class="project-editor" @submit.prevent="saveBusiness" @keydown.esc="editing = null">
        <div class="editor-heading"><h2>{{ editing.project_name }} <span class="text-muted">/ Business details</span></h2><button type="button" class="icon-control" aria-label="Close business details" @click="editing = null"><X class="w-4 h-4" /></button></div>
        <div class="editor-fields">
          <label>Customer<select v-model="customer" class="field" @change="salesOrder = ''; loadOptions()"><option value="">No customer</option><option v-for="c in options.customers" :key="c.name" :value="c.name">{{ c.customer_name }}</option></select></label>
          <label>Sales order<select v-model="salesOrder" class="field"><option value="">No sales order</option><option v-for="o in options.orders" :key="o.name" :value="o.name">{{ o.name }}</option></select></label>
        </div>
        <label class="template-check"><input v-model="isTemplate" type="checkbox" /> Use this project as a reusable template</label>
        <div class="editor-actions"><button type="button" class="btn-ghost" @click="editing = null">Cancel</button><button class="btn-primary" :disabled="busy">{{ busy ? 'Saving…' : 'Save details' }}</button></div>
      </form>
      <form v-if="cloning" class="project-editor" @submit.prevent="cloneProject" @keydown.esc="cloning = null">
        <div class="editor-heading"><h2>Create from {{ cloning.project_name }}</h2><button type="button" class="icon-control" aria-label="Close template form" @click="cloning = null"><X class="w-4 h-4" /></button></div>
        <p class="text-sm text-muted mb-4">Copies tasks, hierarchy, dependencies and checklists. Completion, assignments and time entries start fresh.</p>
        <label class="block text-sm">New project name<input v-model="cloneName" required class="field mt-1" placeholder="e.g. September client onboarding" /></label>
        <div class="editor-actions"><button type="button" class="btn-ghost" @click="cloning = null">Cancel</button><button class="btn-primary" :disabled="busy || !cloneName.trim()">{{ busy ? 'Creating…' : 'Create project' }}</button></div>
      </form>

      <div v-if="loading" class="project-list" aria-label="Loading projects"><div v-for="n in 5" :key="n" class="loading-row"><Skeleton width="35%" height="16px" /><Skeleton width="15%" height="14px" /></div></div>
      <div v-else-if="filteredProjects.length" class="project-list">
        <div class="list-heading" aria-hidden="true"><span>Project</span><span>Customer</span><span>Status</span><span>Tasks</span><span></span></div>
        <article v-for="p in filteredProjects" :key="p.name" class="project-row">
          <div class="project-identity"><span class="project-mark">{{ (p.project_name || p.name).slice(0, 1).toUpperCase() }}</span><div class="min-w-0"><button class="project-title" @click="goBoard(p.name)">{{ p.project_name || p.name }}</button><div class="project-subtitle"><span v-if="p.pulse_project_key">{{ p.pulse_project_key }}</span><span v-if="p.pulse_is_template" class="template-label">Template</span><span v-if="!p.pulse_project_key && !p.pulse_is_template">{{ p.name }}</span></div></div></div>
          <div class="project-customer"><span>{{ p.customer || '—' }}</span><small v-if="p.sales_order">{{ p.sales_order }}</small></div>
          <div class="project-status"><StatusPill v-if="p.status" :value="p.status" /></div>
          <span class="task-count tnum">{{ p.taskCount }}<span class="mobile-task-label"> tasks</span></span>
          <div class="project-actions">
            <details class="context-menu" @keydown.esc="closeMenu"><summary class="icon-control" :aria-label="`Actions for ${p.project_name || p.name}`"><MoreHorizontal class="w-4 h-4" /></summary><div class="menu-items">
              <PersonalControls class="menu-personal" doctype="Project" :name="p.name" :record-recent="false" />
              <button @click="goBoard(p.name); closeMenu($event)">Open tasks</button>
              <button @click="openEntity('Project', p.name); closeMenu($event)">Project details</button>
              <button v-if="p.can_write" @click="editBusiness(p); closeMenu($event)">Business details</button>
              <button v-if="p.pulse_is_template" @click="useTemplate(p); closeMenu($event)">Use template</button>
            </div></details>
          </div>
        </article>
      </div>
      <div v-else class="empty-state"><Folder class="w-7 h-7 text-muted" /><h2>{{ search || statusFilter ? 'No matching projects' : activeTab === 'templates' ? 'No templates yet' : 'Your projects start here' }}</h2><p>{{ search || statusFilter ? 'Try another search or clear the status filter.' : activeTab === 'templates' ? 'Open a project’s business details and enable reusable template.' : 'Create a project to organize tasks and bring your team together.' }}</p><button v-if="search || statusFilter" class="btn-ghost" @click="search = ''; statusFilter = ''">Clear filters</button><button v-else-if="activeTab === 'projects'" class="btn-ghost" @click="openEntity('Project')">Create your first project</button></div>
    </template>

    <section v-else class="workload-panel">
      <div class="workload-heading"><div><h2>Team capacity</h2><p class="text-sm text-muted mt-1">Compare estimated work with allocations and approved leave.</p></div><div class="flex gap-2"><button class="btn-ghost" @click="openEntity('Pulse Allocation')">Add allocation</button><button class="btn-ghost" @click="openEntity('Pulse Leave')">Add leave</button></div></div>
      <form class="workload-filters" @submit.prevent="loadWorkload">
        <label>From<input v-model="start" type="date" required class="field" /></label>
        <label>To<input v-model="end" type="date" required class="field" /></label>
        <label>Project<select v-model="workProject" class="field"><option value="">All accessible projects</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name }}</option></select></label>
        <button class="btn-primary" :disabled="workLoading">{{ workLoading ? 'Calculating…' : 'Calculate workload' }}</button>
      </form>
      <template v-if="work">
        <div class="overflow-x-auto"><table class="workload-table"><thead><tr><th>Team member</th><th>Estimated hours</th><th>Available hours</th><th>Capacity</th></tr></thead><tbody><tr v-for="r in work.rows" :key="r.user"><td>{{ r.user }}</td><td class="tnum">{{ r.estimated_hours }}</td><td class="tnum">{{ r.available_hours }}</td><td class="tnum" :class="{ 'over-capacity': r.over_hours }">{{ r.over_hours ? `${r.over_hours} h over` : 'Within capacity' }}</td></tr></tbody></table></div>
        <p v-if="!work.rows.length" class="text-sm text-muted py-6">No active allocations or assigned open tasks in this period.</p>
        <p class="text-sm mt-4">Unassigned estimates: <strong class="font-medium">{{ work.unassigned_hours }} hours</strong></p>
        <details class="calculation-note"><summary>How capacity is calculated</summary><p>{{ work.basis }}</p></details>
      </template>
      <div v-else class="workload-placeholder"><p>Select a date range and project, then calculate workload.</p><p class="text-sm mt-1">Availability uses active allocations and approved leave.</p></div>
    </section>
  </div>
</template>
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { call } from 'frappe-ui'
import PersonalControls from '@/components/PersonalControls.vue'
import StatusPill from '@/ui/StatusPill.vue'
import Skeleton from '@/ui/Skeleton.vue'
import { openEntity, entityState } from '@/ui/entity'
import Plus from '~icons/lucide/plus'
import Search from '~icons/lucide/search'
import MoreHorizontal from '~icons/lucide/more-horizontal'
import Folder from '~icons/lucide/folder'
import X from '~icons/lucide/x'

const router = useRouter()
const loading = ref(true)
const projects = ref([])
const activeTab = ref('projects'), search = ref(''), statusFilter = ref('')
const statuses = computed(() => [...new Set(projects.value.map(p => p.status).filter(Boolean))].sort())
const templateCount = computed(() => projects.value.filter(p => p.pulse_is_template).length)
const filteredProjects = computed(() => projects.value.filter(p => {
  const query = search.value.trim().toLowerCase()
  return (activeTab.value !== 'templates' || p.pulse_is_template)
    && (!statusFilter.value || p.status === statusFilter.value)
    && (!query || [p.project_name, p.pulse_project_key, p.customer, p.sales_order].some(value => String(value || '').toLowerCase().includes(query)))
}))
function chooseTab(tab) { activeTab.value = tab; editing.value = null; cloning.value = null; error.value = '' }
function closeMenu(event) { event.currentTarget.closest('details')?.removeAttribute('open') }
function useTemplate(p) { editing.value = null; cloning.value = p; cloneName.value = '' }


function goBoard(name) { router.push(`/board?project=${encodeURIComponent(name)}`) }

const error = ref(''), busy = ref(false), editing = ref(null), cloning = ref(null), cloneName = ref('')
const customer = ref(''), salesOrder = ref(''), isTemplate = ref(false)
const options = ref({ customers: [], orders: [] })
const start = ref(new Date().toISOString().slice(0, 10))
const end = ref(new Date(Date.now() + 13 * 86400000).toISOString().slice(0, 10))
const workProject = ref(''), work = ref(null), workLoading = ref(false)
function fail(e) { error.value = e.messages?.join(' ') || e.message || 'Unable to complete this action. Try again.' }
async function loadOptions() {
  try { options.value = await call('pulse.api.business.commercial_options', { customer: customer.value }) } catch (e) { fail(e) }
}
async function editBusiness(p) {
  cloning.value = null; editing.value = p; customer.value = p.customer || ''; salesOrder.value = p.sales_order || ''; isTemplate.value = !!p.pulse_is_template
  await loadOptions()
}
async function saveBusiness() {
  busy.value = true; error.value = ''
  try {
    await call('pulse.api.business.update_project', { project: editing.value.name, customer: customer.value, sales_order: salesOrder.value, is_template: isTemplate.value ? 1 : 0 })
    editing.value = null; await reload()
  } catch (e) { fail(e) } finally { busy.value = false }
}
async function cloneProject() {
  busy.value = true; error.value = ''
  try {
    const result = await call('pulse.api.business.clone_template', { template: cloning.value.name, project_name: cloneName.value })
    cloning.value = null; await reload(); goBoard(result.project)
  } catch (e) { fail(e) } finally { busy.value = false }
}
async function loadWorkload() {
  workLoading.value = true; error.value = ''
  try { work.value = await call('pulse.api.business.workload', { start: start.value, end: end.value, project: workProject.value || null }) }
  catch (e) { fail(e) } finally { workLoading.value = false }
}
async function reload() {
  loading.value = true; error.value = ''
  try { projects.value = await call('pulse.api.business.projects') }
  catch (e) { fail(e) } finally { loading.value = false }
}
watch(() => entityState.saved, reload)
onMounted(reload)
</script>

<style scoped>
.projects-page { padding: 24px 32px; max-width: 1600px; margin: 0 auto; }
.page-heading, .workload-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
h1 { font-size: 22px; font-weight: 600; line-height: 1.3; }
.page-heading p { font-size: 13px; margin-top: 5px; }
h2 { font-size: 14px; font-weight: 600; }
.project-tabs { display: flex; gap: 24px; border-bottom: 1px solid var(--border); margin-top: 24px; }
.project-tabs button { padding: 10px 0 12px; color: var(--muted); font-size: 13px; border-bottom: 2px solid transparent; }
.project-tabs button.selected { color: var(--text); border-bottom-color: var(--accent); font-weight: 500; }
.project-tabs span { margin-left: 5px; font-size: 11px; color: var(--muted); }
.project-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 0; }
.search-field { display: flex; align-items: center; gap: 8px; color: var(--muted); min-width: 0; }
.search-field input { width: 250px; max-width: 100%; background: transparent; border: 0; outline: none; color: var(--text); font-size: 13px; padding: 6px 0; }
.search-field:focus-within { color: var(--accent); }
.status-filter { max-width: 160px; }
.section-hint { font-size: 13px; color: var(--muted); margin-bottom: 18px; }
.project-list { border-top: 1px solid var(--border); }
.list-heading, .project-row { display: grid; grid-template-columns: minmax(220px, 2fr) minmax(120px, 1fr) 120px 65px 84px; align-items: center; column-gap: 20px; }
.list-heading { font-size: 12px; color: var(--muted); padding: 12px; background: var(--surface-2); }
.project-row { min-height: 76px; padding: 14px 12px; border-bottom: 1px solid var(--border); }
.project-row:hover { background: var(--hover); }
.project-identity { display: flex; align-items: center; gap: 12px; min-width: 0; }
.project-mark { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; flex-shrink: 0; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); font-size: 13px; font-weight: 500; color: var(--muted); }
.project-title { display: block; text-align: left; font-size: 14px; font-weight: 500; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-title:hover { color: var(--accent); }
.project-subtitle { display: flex; gap: 8px; margin-top: 4px; color: var(--muted); font-size: 11px; }
.template-label { color: var(--accent); }
.project-customer { font-size: 13px; min-width: 0; overflow-wrap: anywhere; }
.project-customer small { display: block; margin-top: 3px; font-size: 11px; color: var(--muted); }
.task-count { font-size: 12px; color: var(--muted); }
.mobile-task-label { display: none; }
.project-actions { display: flex; align-items: center; justify-content: flex-end; gap: 4px; }
.icon-control { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 5px; color: var(--muted); cursor: pointer; }
.icon-control:hover { background: var(--surface-2); color: var(--text); }
.context-menu { position: relative; }
.context-menu summary { list-style: none; }
.context-menu summary::-webkit-details-marker { display: none; }
.menu-items { position: absolute; right: 0; top: 32px; z-index: 10; width: 170px; border: 1px solid var(--border); border-radius: 6px; padding: 4px; background: var(--surface); }
.menu-items button { width: 100%; text-align: left; padding: 8px; border-radius: 4px; font-size: 12px; }
.menu-personal :deep(button) { width: 100%; text-align: left; padding: 8px; border-radius: 4px; font-size: 12px; }
.menu-items button:hover { background: var(--hover); }
.project-editor { border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; max-width: 760px; background: var(--surface); }
.editor-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.editor-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.editor-fields label, .workload-filters label { display: grid; gap: 5px; font-size: 12px; color: var(--muted); }
.template-check { display: flex; align-items: center; gap: 8px; font-size: 13px; margin-top: 18px; }
.editor-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.loading-row { display: flex; justify-content: space-between; padding: 24px 12px; border-bottom: 1px solid var(--border); }
.empty-state { padding: 72px 20px; display: flex; align-items: center; flex-direction: column; gap: 12px; text-align: center; }
.empty-state p { font-size: 13px; color: var(--muted); max-width: 380px; }
.error-notice { margin-top: 18px; font-size: 13px; color: var(--danger); }
.workload-panel { padding-top: 24px; }
.workload-filters { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 12px; margin: 24px 0; }
.workload-filters label:nth-child(3) { min-width: 200px; }
.workload-table { width: 100%; text-align: left; font-size: 13px; white-space: nowrap; }
.workload-table th { font-size: 12px; color: var(--muted); font-weight: 500; background: var(--surface-2); }
.over-capacity { color: var(--danger); }
.workload-table td, .workload-table th { padding: 12px; border-bottom: 1px solid var(--border); }
.calculation-note { color: var(--muted); font-size: 12px; margin-top: 20px; max-width: 700px; }
.calculation-note summary { cursor: pointer; }
.calculation-note p { margin-top: 8px; line-height: 1.6; }
.workload-placeholder { border-top: 1px solid var(--border); padding: 48px 20px; color: var(--muted); text-align: center; font-size: 13px; }
button:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 1000px) { .list-heading, .project-row { grid-template-columns: minmax(170px, 2fr) minmax(100px, 1fr) 95px 45px 75px; column-gap: 12px; } }
@media (max-width: 760px) {
  .projects-page { padding: 20px 16px; }
  .page-heading p { display: none; }
  .project-tabs { gap: 20px; }
  .search-field { flex: 1; }
  .search-field input { width: 100%; }
  .status-filter { max-width: 120px; }
  .list-heading { display: none; }
  .project-row { grid-template-columns: minmax(0, 1fr) auto; gap: 10px; padding: 16px 0; }
  .project-identity { grid-column: 1; grid-row: 1; }
  .project-actions { grid-column: 2; grid-row: 1; }
  .project-customer { grid-column: 1; padding-left: 44px; font-size: 12px; }
  .project-status { grid-column: 2; grid-row: 2; justify-self: end; }
  .task-count { grid-column: 1; padding-left: 44px; }
  .mobile-task-label { display: inline; }
  .editor-fields { grid-template-columns: 1fr; }
  .project-editor { padding: 16px; }
  .workload-heading { align-items: flex-start; flex-direction: column; }
  .workload-filters label { flex: 1; min-width: 130px; }
}
</style>
