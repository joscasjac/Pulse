<template>
  <main class="views" :class="{ embedded }">
    <header v-if="!embedded" class="view-header">
      <div><h1>Views</h1><p>Work across your projects, organized your way.</p></div>
      <button class="btn-primary" :aria-expanded="savePanel" aria-controls="save-view-panel" @click="savePanel = !savePanel">Save view</button>
    </header>
    <div v-if="!embedded" class="view-context">
      <label class="saved-selection"><span class="sr-only">Saved view</span><select v-model="selected" @change="openSaved"><option value="">Personal workspace</option><option v-for="view in saved" :key="view.name" :value="view.name">{{ view.title }}{{ view.shared ? ' · Shared' : '' }}</option></select></label>
      <span class="context-note">{{ selectedView?.shared ? 'Shared view' : 'Personal view' }}</span>
      <span v-if="!loading" class="context-note">{{ tasks.length }} {{ tasks.length === 1 ? 'task' : 'tasks' }}</span>
    </div>
    <div v-if="!embedded" class="view-toolbar">
      <div class="layout-switch" role="group" aria-label="View layout">
        <button v-for="mode in layouts" :key="mode.key" :aria-pressed="config.layout === mode.key" :class="{ active: config.layout === mode.key }" @click="config.layout = mode.key"><svg viewBox="0 0 20 20" width="15" height="15" aria-hidden="true"><path :d="mode.icon" /></svg>{{ mode.label }}</button>
      </div>
      <div class="display-controls">
        <button class="btn-ghost" :class="{ 'control-active': settings === 'filters' }" :aria-expanded="settings === 'filters'" aria-controls="filter-panel" @click="settings = settings === 'filters' ? '' : 'filters'">Filters<span v-if="filterCount" class="filter-count">{{ filterCount }}</span></button>
        <button class="btn-ghost" :class="{ 'control-active': settings === 'display' }" :aria-expanded="settings === 'display'" aria-controls="display-panel" @click="settings = settings === 'display' ? '' : 'display'">Display</button>
        <button class="btn-ghost" :disabled="loading" @click="load">Refresh</button>
      </div>
    </div>
    <section v-if="settings === 'filters'" id="filter-panel" class="settings-panel" aria-label="View filters">
      <div class="panel-heading"><div><h2>Filter tasks</h2><p>Combine rules to narrow the work in this view.</p></div><button class="btn-ghost" aria-label="Close filters" @click="settings = ''; emit('close-panel')">Close</button></div>
      <FilterGroup v-model="config.filter" />
      <div class="panel-actions"><button class="btn-primary" @click="load">Apply filters</button><button class="btn-ghost" @click="config.filter = { op: 'and', rules: [] }; load()">Clear filters</button></div>
    </section>
    <section v-if="settings === 'display'" id="display-panel" class="settings-panel" aria-label="Display preferences">
      <div class="panel-heading"><div><h2>Display</h2><p>These layout preferences are saved for you.</p></div><button class="btn-ghost" aria-label="Close display preferences" @click="settings = ''; emit('close-panel')">Close</button></div>
      <label v-if="embedded" class="group-select">Saved view<select v-model="selected" @change="openSaved"><option value="">Personal workspace</option><option v-for="savedView in saved" :key="savedView.name" :value="savedView.name">{{ savedView.title }}{{ savedView.shared ? ' · Shared' : '' }}</option></select></label>
      <label class="group-select">Group tasks by<select v-model="config.group"><option value="">No grouping</option><option v-for="key in groupFields" :key="key" :value="key">{{ labels[key] }}</option></select></label>
      <div class="display-order"><label>Order by<select v-model="config.order_by"><option value="pulse_rank">Manual rank</option><option value="creation">Created date</option><option value="modified">Updated date</option><option value="exp_start_date">Start date</option><option value="exp_end_date">Due date</option><option value="priority">Priority</option><option v-if="!orderFields.includes(config.order_by)" :value="config.order_by">{{ labels[config.order_by] }}</option></select></label><label>Direction<select v-model="config.order_direction"><option value="asc">Ascending</option><option value="desc">Descending</option></select></label><label class="subtasks-option"><input v-model="config.show_subtasks" type="checkbox" /> Show subtasks</label></div>
      <fieldset><legend>Table properties</legend><label class="column-search"><span class="sr-only">Search properties</span><input v-model="columnSearch" type="search" placeholder="Search properties" /></label><p class="field-note">Task ID and title stay pinned. Choose other properties and their order.</p><div class="column-options"><div v-for="key in filteredColumnOrder" :key="key" class="column-option"><label><input type="checkbox" :checked="key === 'subject' || config.columns.includes(key)" :disabled="key === 'subject'" @change="toggleColumn(key)" /> {{ labels[key] }}</label><button class="btn-ghost" :disabled="columnOrder.indexOf(key) === 0 || key === 'subject'" :aria-label="`Move ${labels[key]} earlier`" @click="moveColumn(columnOrder.indexOf(key), -1)">↑</button><button class="btn-ghost" :disabled="columnOrder.indexOf(key) === columnOrder.length - 1 || key === 'subject'" :aria-label="`Move ${labels[key]} later`" @click="moveColumn(columnOrder.indexOf(key), 1)">↓</button></div></div></fieldset>
    </section>
    <form v-if="savePanel" id="save-view-panel" class="settings-panel" @submit.prevent="save">
      <div class="panel-heading"><div><h2>{{ selected ? 'Save changes or create a copy' : 'Save this view' }}</h2><p>Keep this layout, grouping and filters for later.</p></div><button type="button" class="btn-ghost" @click="savePanel = false; emit('close-panel')">Cancel</button></div>
      <div class="save-fields"><label>View name<input v-model.trim="title" required maxlength="140" placeholder="e.g. Client delivery" /></label><label class="share-option"><input v-model="shared" type="checkbox" /> Share with the workspace</label></div>
      <p v-if="selectedView && !selectedView.can_write" class="field-note">You can save your own copy of this shared view.</p>
      <div class="panel-actions"><button class="btn-primary" :disabled="saving">{{ saving ? 'Saving…' : selected ? 'Save as new view' : 'Create view' }}</button><button v-if="selectedView?.can_write" type="button" class="btn-ghost" :disabled="saving || !title" @click="save(true)">Update selected view</button></div>
    </form>
    <p v-if="error" class="view-error" role="alert">{{ error }} <button class="btn-ghost" @click="load">Retry</button></p><p v-if="notice" role="status" class="view-notice">{{ notice }}</p><p v-if="loading" class="loading-state" role="status">Loading work…</p>
    <template v-else>
      <div v-if="config.layout === 'calendar'" class="date-toolbar">
        <div class="month-navigation">
          <button class="month-arrow" :aria-label="`Previous ${config.calendar_layout}`" @click="shiftMonth(-1)">‹</button>
          <h2>{{ monthLabel }}</h2>
          <button class="month-arrow" :aria-label="`Next ${config.calendar_layout}`" @click="shiftMonth(1)">›</button>
          

        </div>
        <div class="date-actions">
          <button v-if="unscheduled.length" class="btn-ghost" :aria-expanded="unscheduledOpen" @click="unscheduledOpen = !unscheduledOpen">Unscheduled ({{ unscheduled.length }})</button>
          <button class="btn-ghost today-button" @click="goToToday">Today</button>
          <details class="calendar-options"><summary>Options <span aria-hidden="true">⌄</span></summary><div class="options-menu">
            <button class="calendar-layout-option" :aria-pressed="config.calendar_layout === 'month'" @click="config.calendar_layout = 'month'">Month layout <span v-if="config.calendar_layout === 'month'">✓</span></button>
            <button class="calendar-layout-option" :aria-pressed="config.calendar_layout === 'week'" @click="config.calendar_layout = 'week'">Week layout <span v-if="config.calendar_layout === 'week'">✓</span></button>
            <label class="weekend-option">Show weekends<input :checked="!config.hide_weekends" role="switch" type="checkbox" @change="config.hide_weekends = !$event.target.checked" /></label>
          </div></details>
        </div>
      </div>
      <form v-if="config.layout === 'timeline' && dependencyEditor" class="dependency-editor" @submit.prevent="link">
        <label>Task<select v-model="dependent" required><option value="">Choose task</option><option v-for="t in tasks.filter(t => t.can_write)" :key="t.name" :value="t.name">{{ t.subject }}</option></select></label>
        <label>Depends on<select v-model="prerequisite" required><option value="">Choose prerequisite</option><option v-for="t in tasks" :key="t.name" :value="t.name">{{ t.subject }}</option></select></label>
        <button class="btn-ghost" :disabled="!dependent || !prerequisite || dependent === prerequisite">Add dependency</button>
      </form>
      <div class="work-pane" :class="`layout-${config.layout}`">
      <div class="groups-scroll">
      <TaskTimeline v-if="config.layout === 'timeline'" :tasks="sortedTasks" :groups="groups" :dependencies="dependencies" :month="month" :pending="pending" @open="openTaskId = $event" @edit="edit" @reschedule="rescheduleTask" @schedule="scheduleTimelineTask" :create-task="createInlineTask" :project="project" :projects="creationProjects" @period-change="month = $event"><template #actions><button class="btn-ghost" :aria-expanded="dateEditor" @click="dateEditor = !dateEditor">Edit dates</button><button class="btn-ghost" :aria-expanded="dependencyEditor" @click="dependencyEditor = !dependencyEditor">Dependencies</button></template></TaskTimeline>
      <section v-for="(group, groupIndex) in displayedGroups" :key="group.name" class="task-group"><h2 v-if="config.group" class="font-semibold">{{ group.name }} <span class="text-muted">({{ group.tasks.length }})</span></h2>
        <div v-if="config.layout === 'calendar'" class="calendar-scroll">
          <div class="calendar-weekdays" :style="{ '--day-columns': config.hide_weekends ? 5 : 7 }"><span v-for="weekday in visibleWeekdays" :key="weekday">{{ weekday }}</span></div>
          <div class="calendar" :style="{ '--week-count': calendarDays.length / 7, '--day-columns': config.hide_weekends ? 5 : 7 }">
            <div v-for="day in visibleCalendarDays" :key="day" class="calendar-day" :class="{ 'outside-month': !day.startsWith(month), 'is-today': day === today }" @dragover.prevent @drop.prevent="drop($event, day)">
              <div class="day-heading"><time :datetime="day" :aria-label="day">{{ day.endsWith('-01') ? new Date(day + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : Number(day.slice(-2)) }}</time></div><button class="day-add" :aria-label="`Add task on ${day}`" :aria-expanded="activeDay === `${groupIndex}:${day}`" @click="activeDay = activeDay === `${groupIndex}:${day}` ? null : `${groupIndex}:${day}`">+ Add work item</button>
              <div v-if="activeDay === `${groupIndex}:${day}`" class="day-menu" @keydown.esc="activeDay = null"><button @click="createOnDay(day, groupIndex)">Create task</button><button @click="showTaskPicker(day)">Add existing tasks</button></div>
              <InlineTaskCreate v-if="inlineDay === `${groupIndex}:${day}`" :create-task="createInlineTask" :project="project" :projects="creationProjects" :date="day" @cancel="inlineDay = null" />
              <div class="day-tasks"><button v-for="task in group.tasks.filter(t => dateValue(t.exp_end_date) === day)" :key="task.name" class="calendar-task" :class="{ 'task-focused': focused === task.name }" :draggable="task.can_write && !pending.has(task.name)" :title="`${task.subject} · ${task.workflow_state || ''}`" @dragstart="drag($event, task)" @click="focusDates(task)"><span class="calendar-key">{{ task.issue_key }}</span><span>{{ task.subject }}</span></button></div>
            </div>
          </div>
        </div>
        <TaskSpreadsheet v-if="config.layout === 'spreadsheet'" :grouped="Boolean(config.group)" :tasks="group.tasks" :columns="config.columns" :labels="labels" :pending="pending" :project-configs="projectConfigs" :order-by="config.order_by" :order-direction="config.order_direction" :create-task="createInlineTask" :project="project" :projects="creationProjects" @edit="edit" @open="openTaskId = $event" @sort="sortBy" />
        <div v-if="dateEditor && config.layout === 'timeline'" class="table-scroll" :class="{ 'date-editor': config.layout !== 'spreadsheet' }"><table><caption class="sr-only">Editable tasks{{ config.layout !== 'spreadsheet' ? ' and accessible date controls' : '' }}</caption><thead><tr><th v-for="key in visibleColumns" :key="key">{{ labels[key] }}</th></tr></thead><tbody><tr v-for="task in group.tasks" :key="task.name" :class="{ focused: focused === task.name }"><td v-for="key in visibleColumns" :key="key"><input v-if="['assignees', 'labels'].includes(key)" :aria-label="`${labels[key]} for ${task.subject}, comma separated`" :value="task[key]?.join(', ')" placeholder="Comma-separated values" :disabled="!task.can_write || pending.has(task.name)" @change="edit(task, key, $event.target.value)" /><select v-else-if="['workflow_state', 'priority', 'type'].includes(key)" :aria-label="`${labels[key]} for ${task.subject}`" :value="key.includes('date') ? dateValue(task[key]) : task[key]" :disabled="!task.can_write || pending.has(task.name)" @change="edit(task, key, $event.target.value)"><option v-for="option in optionsFor(task, key)" :key="option" :value="option">{{ option }}</option></select><input v-else :aria-label="`${labels[key]} for ${task.subject}`" :type="key.includes('date') ? 'date' : ['expected_time', 'pulse_story_points'].includes(key) ? 'number' : 'text'" :value="key.includes('date') ? dateValue(task[key]) : task[key]" :disabled="!task.can_write || pending.has(task.name)" @change="edit(task, key, $event.target.value)" /></td></tr></tbody></table></div>
      </section>
      <div v-if="!sortedTasks.length" class="empty-work"><h2>No matching tasks</h2><p>Adjust your filters or create a task to start planning.</p></div>
      </div>
      <div v-if="config.layout === 'spreadsheet' && config.group" class="grouped-create-footer"><InlineTaskCreate v-if="tableCreating" variant="table" :create-task="createInlineTask" :project="project" :projects="creationProjects" @cancel="tableCreating = false" /><button v-else @click="tableCreating = true">+ Add work item</button></div>
      <aside v-if="config.layout !== 'spreadsheet' && unscheduledOpen" class="unscheduled-pane" aria-label="Unscheduled tasks">
        <div class="unscheduled-heading"><h2>Unscheduled <span class="count-badge">{{ unscheduled.length }}</span></h2><button class="btn-ghost" aria-label="Close unscheduled tasks" @click="unscheduledOpen = false">×</button></div>
        <p class="field-note">Drag onto a day, or choose a due date.</p>
        <div class="unscheduled-list"><div v-for="task in unscheduled" :key="task.name" class="unscheduled-task" :draggable="task.can_write && !pending.has(task.name)" @dragstart="drag($event, task)"><span class="calendar-key">{{ task.issue_key }}</span><p>{{ task.subject }}</p><input type="date" :aria-label="`Schedule ${task.subject}`" :disabled="!task.can_write || pending.has(task.name)" @change="edit(task, 'exp_end_date', $event.target.value)" /></div><p v-if="!unscheduled.length" class="field-note">Every task has a due date.</p></div>
      </aside>
      </div>
    </template>
    <CalendarTaskPicker :tasks="pickerTasks" :open="Boolean(pickerDay)" :date="pickerDay || ''" :pending="pickerPending" :loading="pickerLoading" :error="pickerError" @close="closeTaskPicker" @confirm="schedulePicked" />
    <TaskDrawer :task-id="openTaskId" @close="openTaskId = null" @changed="load" @open="openTaskId = $event" />
  </main>
</template>
<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { call } from 'frappe-ui'
import { calendarPeriodDays, shiftWeek } from '../components/views/calendarPeriod.js'
import FilterGroup from '../components/views/FilterGroup.vue'
import TaskDrawer from '../components/TaskDrawer.vue'
import TaskSpreadsheet from '../components/views/TaskSpreadsheet.vue'
import TaskTimeline from '../components/views/TaskTimeline.vue'
import CalendarTaskPicker from '../components/views/CalendarTaskPicker.vue'
import { createState } from '../ui/create'
import InlineTaskCreate from '../components/views/InlineTaskCreate.vue'
const props = defineProps({ embedded: Boolean, mode: { type: String, default: 'spreadsheet' }, project: { type: String, default: null }, module: { type: String, default: null }, moduleName: { type: String, default: '' }, taskNames: { type: Array, default: null }, includeArchived: Boolean, panel: { type: String, default: '' }, refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['close-panel', 'changed'])
const labels = { subject: 'Title', workflow_state: 'Status', priority: 'Priority', project: 'Project', exp_start_date: 'Start date', exp_end_date: 'Due date', type: 'Type', assignees: 'Assignees', labels: 'Labels', expected_time: 'Estimated hours', pulse_story_points: 'Points', creation: 'Created date', modified: 'Updated date', owner: 'Created by', modules: 'Modules', name: 'Link' }
// ERPNext Date fields can arrive as midnight datetime strings. Keep their calendar day, not a timezone conversion.
const dateValue = value => value ? String(value).slice(0, 10) : ''
const groupFields = ['workflow_state', 'assignees', 'priority', 'project', 'labels']
const defaultConfig = () => ({ order_by: 'pulse_rank', order_direction: 'asc', show_subtasks: true, hide_weekends: true, calendar_layout: 'month', layout: 'spreadsheet', group: '', columns: ['subject', 'workflow_state', 'priority', 'project', 'exp_start_date', 'exp_end_date'], filter: { op: 'and', rules: [] } })
const config = ref(defaultConfig())
const tasks = ref([]), dependencies = ref([]), saved = ref([]), selected = ref(''), title = ref(''), shared = ref(false), settings = ref(''), loading = ref(true), saving = ref(false), error = ref(''), notice = ref(''), focused = ref(''), pending = ref(new Set()), dependent = ref(''), prerequisite = ref('')
const savePanel = ref(false), dateEditor = ref(false), unscheduledOpen = ref(false), dependencyEditor = ref(false)
function localMonth() { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}` }
const today = (() => { const now = new Date(); return `${localMonth()}-${String(now.getDate()).padStart(2, '0')}` })()
const weekAnchor = ref(today)
function goToToday() { month.value = localMonth(); weekAnchor.value = today }
const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const visibleWeekdays = computed(() => config.value.hide_weekends ? weekdays.slice(0, 5) : weekdays)
const visibleCalendarDays = computed(() => config.value.hide_weekends ? calendarDays.value.filter((_, index) => index % 7 < 5) : calendarDays.value)
const tableCreating = ref(false)
const inlineDay = ref(null), creationProjects = ref([]), locallyCreated = ref(new Set())
const activeDay = ref(null), pickerDay = ref(null), pickerTasks = ref([]), pickerPending = ref(false), pickerLoading = ref(false), pickerError = ref('')
let pickerVersion = 0
function createOnDay(day, groupIndex = 0) { activeDay.value = null; inlineDay.value = `${groupIndex}:${day}` }
async function createInlineTask({subject, project, date}) {
  const projectName = props.project || project
  if (!projectConfigs.value[projectName]) projectConfigs.value[projectName] = await call('pulse.api.task_config.get_config', { project: projectName })
  const types = projectConfigs.value[projectName]?.task_types || []
  const result = await call('pulse.api.spa.create_task', { subject, task_type: types.includes('Task') ? 'Task' : types[0] || null, project: projectName, module: props.module || null, exp_start_date: date || null, exp_end_date: date && config.value.layout === 'timeline' ? new Date(Date.parse(date) + 86400000).toISOString().slice(0, 10) : date || null })
  locallyCreated.value.add(result.name)
  await load({ background: true })
  emit('changed')
  notice.value = `${result.issue_key || 'Task'} created.`
  return result
}
function closeTaskPicker() { if (pickerPending.value) return; ++pickerVersion; pickerDay.value = null; pickerLoading.value = false }
async function showTaskPicker(day) {
  activeDay.value = null; pickerDay.value = day; pickerTasks.value = []; pickerError.value = ''; pickerLoading.value = true
  const token = ++pickerVersion
  try {
    const filter = { op: 'and', rules: props.project ? [{ field: 'project', op: 'eq', value: props.project }] : [] }
    const result = await call('pulse.api.views.tasks', { config: { ...defaultConfig(), filter } })
    if (token === pickerVersion) pickerTasks.value = result.tasks.filter(task => task.can_write)
  } catch (e) { if (token === pickerVersion) pickerError.value = e.message || 'Tasks could not be loaded. Close and try again.' }
  finally { if (token === pickerVersion) pickerLoading.value = false }
}
async function schedulePicked(names) {
  if (pickerPending.value || pickerLoading.value || !pickerDay.value || !names.length) return
  pickerPending.value = true; pickerError.value = ''
  try {
    await call('pulse.api.views.schedule_tasks', { tasks: names, date: pickerDay.value, module: props.module || null })
    pickerDay.value = null; notice.value = 'Tasks scheduled.'; emit('changed')
    await load()
  } catch (e) { pickerError.value = e.message || 'Tasks could not be scheduled. Nothing was changed; try again.' }
  finally { pickerPending.value = false }
}
watch(() => createState.created, () => { if (!restoring) load() })
const unscheduled = computed(() => sortedTasks.value.filter(task => !task.exp_end_date))
const openTaskId = ref(null)
function focusDates(task) { focused.value = task.name; openTaskId.value = task.name }
function shiftMonth(delta) { if (config.value.calendar_layout === 'week') { weekAnchor.value = shiftWeek(weekAnchor.value, delta); month.value = weekAnchor.value.slice(0,7); return } const [year, value] = (month.value || localMonth()).split('-').map(Number); const next = new Date(year, value - 1 + delta, 1); month.value = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}` }
const monthLabel = computed(() => {
  if (config.value.calendar_layout === 'week') {
    const dates = calendarDays.value
    if (!dates.length) return 'Choose a week'
    const format = day => new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    return `${format(dates[0])} – ${format(dates[config.value.hide_weekends ? 4 : 6])}, ${dates[0].slice(0,4)}`
  }
  return new Date(`${month.value}-01T12:00:00`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
})
const calendarDays = computed(() => calendarPeriodDays(month.value, config.value.calendar_layout, weekAnchor.value))
watch(() => config.value.calendar_layout, layout => { if (layout === 'week' && !weekAnchor.value.startsWith(month.value)) weekAnchor.value = `${month.value}-01` })

const layouts = [
  { key: 'spreadsheet', label: 'Spreadsheet', icon: 'M3 3h14v14H3z M3 8h14 M8 3v14 M3 12h14' },
  { key: 'calendar', label: 'Calendar', icon: 'M3 5h14v12H3z M6 2v5 M14 2v5 M3 9h14' },
  { key: 'timeline', label: 'Timeline', icon: 'M4 3v14 M8 5h8 M8 10h5 M11 15h6' },
]
const selectedView = computed(() => saved.value.find(view => view.name === selected.value))
const countRules = node => node.rules ? node.rules.reduce((sum, rule) => sum + countRules(rule), 0) : 1
const filterCount = computed(() => countRules(config.value.filter))
const projectConfigs = ref({})
const personalConfig = ref(null)
function optionsFor(task, key) { const cfg = projectConfigs.value[task.project]; const options = key === 'priority' ? ['Low', 'Medium', 'High', 'Urgent'] : key === 'workflow_state' ? (cfg?.statuses || []).map(s => s.label) : cfg?.task_types || []; return [...new Set([task[key] || '', ...options])] }
const columnOrder = ref(Object.keys(labels)), month = ref(localMonth()), columnSearch = ref('')
const orderFields = ['pulse_rank','creation','modified','exp_start_date','exp_end_date','priority']
const filteredColumnOrder = computed(() => columnOrder.value.filter(key => labels[key].toLowerCase().includes(columnSearch.value.trim().toLowerCase())))
const priorityRank = { Low: 1, Medium: 2, High: 3, Critical: 4, Urgent: 5 }
const sortedTasks = computed(() => {
  const rows = tasks.value.filter(task => config.value.show_subtasks !== false || !task.parent_task)
  const key = config.value.order_by || 'pulse_rank', direction = config.value.order_direction === 'desc' ? -1 : 1
  const value = task => key === 'priority' ? priorityRank[task.priority] ?? 0 : key === 'name' ? task.name : task[key]
  return [...rows].sort((a,b) => {
    let x = value(a), y = value(b)
    const emptyX = x == null || x === '', emptyY = y == null || y === ''
    if (emptyX || emptyY) return emptyX === emptyY ? a.name.localeCompare(b.name) : emptyX ? 1 : -1
    if (['pulse_rank','expected_time','pulse_story_points','priority'].includes(key)) return (Number(x)-Number(y))*direction || a.name.localeCompare(b.name)
    if (Array.isArray(x)) x=x.join(', ')
    if (Array.isArray(y)) y=y.join(', ')
    return String(x).localeCompare(String(y),undefined,{numeric:true,sensitivity:'base'})*direction || a.name.localeCompare(b.name)
  })
})
function sortBy(key) { if (config.value.order_by === key) config.value.order_direction = config.value.order_direction === 'asc' ? 'desc' : 'asc'; else { config.value.order_by = key; config.value.order_direction = 'asc' } }
async function scheduleTimelineTask(task, day) {
  if (!task.can_write || pending.value.has(task.name)) return
  pending.value.add(task.name); error.value = ''
  const duration = task.exp_start_date && task.exp_end_date ? Math.max(0, Date.parse(dateValue(task.exp_end_date)) - Date.parse(dateValue(task.exp_start_date))) : 86400000
  const end = new Date(Date.parse(day) + duration).toISOString().slice(0, 10)
  try {
    await call('pulse.api.tasks.bulk_update', { tasks: [task.name], fields: { exp_start_date: day, exp_end_date: end } })
    await load({ background: true }); notice.value = 'Task scheduled.'
  } catch (e) { error.value = e.message || 'Task could not be scheduled.' }
  finally { pending.value.delete(task.name) }
}
const optimisticDateTasks = new Set()
async function rescheduleTask(name, day) {
  const task = tasks.value.find(task => task.name === name)
  if (!task?.can_write || pending.value.has(name)) return
  pending.value.add(name); optimisticDateTasks.add(name); error.value = ''; ++version
  const previous = { exp_start_date: task.exp_start_date, exp_end_date: task.exp_end_date }
  const duration = task.exp_start_date && task.exp_end_date ? Math.max(0, Date.parse(dateValue(task.exp_end_date)) - Date.parse(dateValue(task.exp_start_date))) : 0
  task.exp_end_date = day
  if (task.exp_start_date) task.exp_start_date = new Date(Date.parse(day) - duration).toISOString().slice(0, 10)
  try { await call('pulse.api.views.schedule_tasks', { tasks: [name], date: day }) }
  catch(e) { Object.assign(task, previous); error.value = e.message || 'Task could not be rescheduled.' }
  finally { optimisticDateTasks.delete(name); pending.value.delete(name); await load({ background: true }) }
}

watch(month, () => { activeDay.value = null; inlineDay.value = null })
const visibleColumns = computed(() => config.value.layout === 'spreadsheet' ? config.value.columns : ['subject', 'exp_start_date', 'exp_end_date'])
const monthOffset = computed(() => days.value.length ? (new Date(days.value[0] + 'T12:00:00').getDay() + 6) % 7 : 0)
const days = computed(() => { if (!/^\d{4}-\d{2}$/.test(month.value)) return []; const [y, m] = month.value.split('-').map(Number); return Array.from({ length: new Date(y, m, 0).getDate() }, (_, i) => `${month.value}-${String(i + 1).padStart(2, '0')}`) })
const groups = computed(() => { if (!config.value.group) return [{ name: '', tasks: sortedTasks.value }]; const result = new Map(); for (const task of sortedTasks.value) { const value = task[config.value.group]; const keys = Array.isArray(value) ? value.length ? value : ['Unassigned'] : [value || 'None']; for (const key of keys) { if (!result.has(key)) result.set(key, []); result.get(key).push(task) } } return result.size ? [...result].map(([name, tasks]) => ({ name, tasks })) : [{ name: '', tasks: [] }] })
const displayedGroups = computed(() => config.value.layout === 'timeline' && !dateEditor.value ? [] : groups.value)
function scopedConfiguration() {
  if (!props.project) return config.value
  const rules = config.value.filter.op === 'and' && config.value.filter.rules ? [...config.value.filter.rules] : [config.value.filter]
  rules.push({ field: 'project', op: 'eq', value: props.project })
  return { ...config.value, filter: { op: 'and', rules } }
}
watch(() => props.mode, mode => { if (props.embedded && !restoring && loadedContext === preferenceContext.value) config.value.layout = mode })
watch(() => props.panel, panel => { settings.value = ['filters', 'display'].includes(panel) ? panel : ''; savePanel.value = panel === 'save' })
const preferenceContext = computed(() => props.embedded ? `view:${props.project || 'all'}${props.module ? `:module:${props.module}` : ''}` : null)
watch(preferenceContext, () => { flushPreferences(); restorePreferences() })
watch(() => [props.taskNames, props.includeArchived, props.refreshKey], () => { if (!restoring) load({ background: true }) })
let version = 0, restoring = true, persistTimer, loadedContext
async function load(options = {}) { if (options?.background && optimisticDateTasks.size) return; const v = ++version; if (!options?.background) { loading.value = true; error.value = '' } try { const result = await call('pulse.api.views.tasks', { config: scopedConfiguration(), include_archived: Number(props.includeArchived) }); if (v === version) { tasks.value = props.taskNames ? result.tasks.filter(task => props.taskNames.includes(task.name) || locallyCreated.value.has(task.name)) : result.tasks; dependencies.value = result.dependencies; for (const project of [...new Set(result.tasks.map(t => t.project).filter(Boolean))]) { if (!projectConfigs.value[project]) { try { projectConfigs.value[project] = await call('pulse.api.task_config.get_config', { project }) } catch { /* Current value remains available when vocabulary is not readable. */ } } } } } catch (e) { if (v === version) error.value = e.message || 'Work could not be loaded.' } finally { if (v === version) loading.value = false } }
async function edit(task, key, value) {
  if (!task.can_write || pending.value.has(task.name)) return
  if (['exp_start_date', 'exp_end_date'].includes(key)) {
    const previous = task[key]; ++version; optimisticDateTasks.add(task.name); pending.value.add(task.name); error.value = ''; task[key] = value || null
    try { await call('pulse.api.tasks.bulk_update', { tasks: [task.name], fields: { [key]: value || null } }) }
    catch (e) { task[key] = previous; error.value = e.message || 'Task dates could not be updated.' }
    finally { optimisticDateTasks.delete(task.name); pending.value.delete(task.name); await load({ background: true }) }
    return
  }
  pending.value.add(task.name); error.value = ''
  try {
    const values = ['assignees', 'labels'].includes(key) ? [...new Set((Array.isArray(value) ? value : value.split(',')).map(v => v.trim()).filter(Boolean))] : null
    const args = { tasks: [task.name], fields: key === 'assignees' ? {} : { [key === 'labels' ? 'pulse_labels' : key]: values || (value === '' ? null : value) } }
    if (key === 'assignees') { args.assign = values.filter(v => !task.assignees.includes(v)); args.unassign = task.assignees.filter(v => !values.includes(v)) }
    await call('pulse.api.tasks.bulk_update', args); await load({ background: true }); notice.value = 'Task updated.'
  } catch (e) { await load({ background: true }); error.value = e.message || 'Task could not be updated.' }
  finally { pending.value.delete(task.name) }
}
function toggleColumn(key) { const enabled = new Set(config.value.columns); if (enabled.has(key) && enabled.size === 1) { notice.value = 'Keep at least one column visible.'; return } enabled.has(key) ? enabled.delete(key) : enabled.add(key); config.value.columns = columnOrder.value.filter(k => enabled.has(k)) }
function moveColumn(i, delta) { const next = [...columnOrder.value]; [next[i], next[i + delta]] = [next[i + delta], next[i]]; columnOrder.value = next; config.value.columns = next.filter(k => config.value.columns.includes(k)) }
async function save(update = false) { saving.value = true; error.value = ''; try { const view = await call('pulse.api.views.save_view', { title: title.value, config: scopedConfiguration(), shared: Number(shared.value), name: update === true ? selected.value : null }); saved.value = await call('pulse.api.views.saved_views'); selected.value = view.name; notice.value = 'View saved.'; savePanel.value = false; emit('close-panel') } catch (e) { error.value = e.message || 'View could not be saved.' } finally { saving.value = false } }
function openSaved() { const view = saved.value.find(v => v.name === selected.value); if (!view) { if (personalConfig.value) config.value = JSON.parse(JSON.stringify(personalConfig.value)); title.value = ''; shared.value = false; if (props.embedded) config.value.layout = props.mode; load(); return } config.value = typeof view.configuration === 'string' ? JSON.parse(view.configuration) : view.configuration; if (props.embedded) config.value.layout = props.mode; title.value = view.title; shared.value = Boolean(view.shared); columnOrder.value = [...config.value.columns, ...Object.keys(labels).filter(k => !config.value.columns.includes(k))]; load() }
function drag(event, task) { if (event.target.closest('.resize')) { event.preventDefault(); return } event.dataTransfer.setData('text/plain', task.name); event.dataTransfer.effectAllowed = 'move' }
async function drop(event, day) { const task = tasks.value.find(t => t.name === event.dataTransfer.getData('text/plain')); if (!task || !task.can_write || pending.value.has(task.name)) return; pending.value.add(task.name); const duration = task.exp_start_date && task.exp_end_date ? Math.max(0, (Date.parse(dateValue(task.exp_end_date)) - Date.parse(dateValue(task.exp_start_date))) / 86400000) : 0; const fields = { exp_end_date: day }; if (task.exp_start_date) fields.exp_start_date = new Date(Date.parse(day) - duration * 86400000).toISOString().slice(0, 10); try { await call('pulse.api.tasks.bulk_update', { tasks: [task.name], fields }); await load() } catch (e) { error.value = e.message || 'Task could not be rescheduled.' } finally { pending.value.delete(task.name) } }
async function link() { try { await call('pulse.api.spa.add_dependency', { task: dependent.value, depends_on: prerequisite.value }); await load(); notice.value = 'Dependency added.' } catch (e) { error.value = e.message || 'Dependency could not be added.' } }
let pendingPreferences = null, preferenceWrites = Promise.resolve(), restoreVersion = 0, disposed = false
function flushPreferences() {
  clearTimeout(persistTimer)
  if (!pendingPreferences) return preferenceWrites
  const snapshot = pendingPreferences
  pendingPreferences = null
  preferenceWrites = preferenceWrites.then(() => call('pulse.api.views.preferences', snapshot)).catch(e => {
    if (!disposed && snapshot.context === preferenceContext.value) error.value = e.message || 'Layout preferences could not be saved.'
  })
  return preferenceWrites
}
watch(config, () => {
  if (restoring) return
  const snapshot = JSON.parse(JSON.stringify(config.value))
  if (!selected.value) personalConfig.value = snapshot
  pendingPreferences = { config: snapshot, context: loadedContext }
  clearTimeout(persistTimer)
  persistTimer = setTimeout(flushPreferences, 500)
}, { deep: true, flush: 'sync' })
async function restorePreferences() {
  const token = ++restoreVersion
  const context = preferenceContext.value
  ++version // Ignore any task request started under the previous project.
  restoring = true
  loading.value = true
  error.value = ''
  selected.value = ''; title.value = ''; shared.value = false; inlineDay.value = null; locallyCreated.value.clear(); openTaskId.value = null; activeDay.value = null; pickerDay.value = null; ++pickerVersion; pickerPending.value = false; pickerLoading.value = false
  try {
    await preferenceWrites
    const prefs = await call('pulse.api.views.preferences', { context })
    if (token !== restoreVersion || disposed) return
    config.value = props.embedded ? { ...prefs, layout: props.mode } : prefs
    personalConfig.value = JSON.parse(JSON.stringify(prefs))
    columnOrder.value = [...prefs.columns, ...Object.keys(labels).filter(k => !prefs.columns.includes(k))]
  } catch (e) {
    if (token !== restoreVersion || disposed) return
    config.value = { ...defaultConfig(), layout: props.embedded ? props.mode : 'spreadsheet' }
    error.value = e.message || 'Saved preferences could not be loaded.'
  } finally {
    if (token === restoreVersion && !disposed) { loadedContext = context; restoring = false; await load() }
  }
}
onBeforeUnmount(() => { disposed = true; ++restoreVersion; ++version; flushPreferences() })
onMounted(async () => {
  settings.value = ['filters', 'display'].includes(props.panel) ? props.panel : ''
  savePanel.value = props.panel === 'save'
  await Promise.all([call('frappe.client.get_list', { doctype: 'Project', fields: ['name', 'project_name', 'pulse_project_key'], limit_page_length: 0 }).then(rows => { creationProjects.value = rows }).catch(e => { error.value = e.message || 'Projects could not be loaded.' }), restorePreferences(), call('pulse.api.views.saved_views').then(views => { if (!disposed) saved.value = views }).catch(e => { if (!disposed) error.value = e.message || 'Saved views could not be loaded.' })])
})
</script>
<style scoped>
.views { max-width: 100%; min-width: 0; flex: 1; height: 100%; min-height: 0; overflow: hidden; padding: 16px 24px 0; display: flex; flex-direction: column; gap: 10px; box-sizing: border-box; }
.views > :not(.work-pane) { flex-shrink: 0; }
.views.embedded { padding: 0; flex: 1; height: auto; overflow: hidden; gap: 0; }
.views.embedded > .settings-panel { margin: 10px 16px; }
.views.embedded > .view-error, .views.embedded > .view-notice { padding: 4px 16px; }
.view-header, .panel-heading { display: flex; justify-content: space-between; align-items: start; gap: 16px; }
.view-header h1 { font-size: 22px; font-weight: 600; margin: 0; }
.view-header p, .panel-heading p { color: var(--muted); font-size: 13px; margin: 5px 0 0; }
.view-context { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.saved-selection select { max-width: min(360px, 100%); font-weight: 500; }
.context-note { font-size: 12px; color: var(--muted); }
.view-toolbar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; border-block: 1px solid var(--border); padding: 10px 0; }
.layout-switch, .display-controls { display: flex; flex-wrap: wrap; gap: 4px; }
.layout-switch button { display: flex; gap: 6px; align-items: center; padding: 6px 9px; border-radius: 5px; font-size: 13px; color: var(--muted); min-height: 32px; }
.layout-switch button.active, .control-active { background: var(--surface-2); color: var(--text); }
.layout-switch button:hover { background: var(--hover); color: var(--text); }
.layout-switch svg { fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.filter-count { margin-inline-start: 5px; font-size: 11px; color: var(--accent); }
.settings-panel { max-height: 45%; overflow: auto; border: 1px solid var(--border); border-radius: 6px; padding: 16px; display: flex; flex-direction: column; gap: 16px; background: var(--surface); }
.panel-heading h2 { font-size: 14px; font-weight: 600; }
.panel-actions, .save-fields { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.save-fields > label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.save-fields > .share-option { flex-direction: row; align-items: center; margin-top: 20px; }
.display-order { display: flex; gap: 16px; flex-wrap: wrap; align-items: end; }
.display-order label { display: flex; flex-direction: column; gap: 5px; font-size: 12px; }
.display-order .subtasks-option { flex-direction: row; align-items: center; padding-bottom: 6px; }
.column-search { display: block; margin-top: 10px; }
.column-search input { width: min(100%, 320px); }
.group-select { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; font-size: 13px; }
legend { font-size: 13px; font-weight: 500; }
.field-note { font-size: 12px; color: var(--muted); margin-top: 4px; }
.column-options { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0 24px; margin-top: 8px; }
.column-option { display: flex; align-items: center; gap: 4px; border-bottom: 1px solid var(--border); padding-block: 4px; font-size: 13px; }
.column-option label { display: flex; align-items: center; gap: 8px; flex: 1; }
.view-error { color: var(--danger); font-size: 13px; }
.view-notice, .loading-state { color: var(--muted); font-size: 13px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; }
.toolbar label { display: flex; gap: 6px; flex-direction: column; font-size: 13px; }
input, select { border: 1px solid var(--border); background: var(--surface); padding: 6px 8px; border-radius: 5px; max-width: 100%; font-size: 13px; }
input[type="checkbox"] { accent-color: var(--accent); }
input:focus-visible, select:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.layout-spreadsheet { flex-direction: column; }
.grouped-create-footer { flex-shrink:0;border-top:1px solid var(--border);background:var(--surface); }
.grouped-create-footer > button { min-height:38px;width:100%;text-align:left;padding:10px 14px;font-size:12px;color:var(--muted); }
.work-pane { flex: 1; min-height: 0; display: flex; overflow: hidden; border-top: 1px solid var(--border); }
.groups-scroll { flex: 1; min-width: 0; min-height: 0; overflow: auto; }
.task-group { min-width: 0; }
.task-group > h2 { position: sticky; left: 0; padding: 10px 12px; background: var(--surface-2); border-bottom: 1px solid var(--border); font-size: 12px; }
.work-pane.layout-calendar .groups-scroll > .task-group:only-of-type, .work-pane.layout-spreadsheet .groups-scroll > .task-group:only-of-type { height: 100%; display: flex; flex-direction: column; }
.table-scroll, .timeline-scroll { overflow: auto; }
.table-scroll { min-height: 0; }
.date-editor { flex-shrink: 0; max-height: 240px; border-top: 1px solid var(--border); }
.calendar-scroll { flex: 1; min-height: 360px; display: flex; flex-direction: column; overflow: visible; }
.calendar-weekdays { display: grid; grid-template-columns: repeat(var(--day-columns, 7), minmax(100px, 1fr)); min-width: calc(var(--day-columns, 7) * 100px); position: sticky; top: 0; z-index: 2; background: var(--surface); border-bottom: 1px solid var(--border); }
.calendar-weekdays span { padding: 14px 12px; text-align:right; background:var(--surface-2); color: var(--muted); font-size: 11px; }
.date-toolbar { min-height: 60px; display: flex; flex-wrap: wrap; gap: 6px 16px; justify-content: space-between; align-items: center; padding: 6px 12px; }
.month-navigation, .date-actions { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.month-navigation h2 { font-size: 13px; font-weight: 600; min-width: 128px; text-align: center; }
.month-arrow { width: 28px; height: 28px; border-radius: 4px; font-size: 20px; color: var(--muted); }
.month-arrow:hover { background: var(--hover); color: var(--text); }
.month-picker { margin-left: 4px; }
.month-picker input { width: 136px; font-size: 11px; padding: 4px 6px; }
.count-badge { font-size: 11px; color: var(--muted); margin-left: 4px; }
.dependency-editor { padding: 10px 12px; border-top: 1px solid var(--border); display: flex; align-items: end; gap: 10px; flex-wrap: wrap; }
.dependency-editor label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
.dependency-editor select { max-width: 260px; }
.unscheduled-pane { width: 260px; flex-shrink: 0; min-height: 0; display: flex; flex-direction: column; border-left: 1px solid var(--border); background: var(--surface); padding: 12px; }
.unscheduled-heading { display: flex; align-items: center; justify-content: space-between; }
.unscheduled-heading h2 { font-size: 13px; font-weight: 600; }
.unscheduled-list { overflow: auto; min-height: 0; margin-top: 12px; }
.unscheduled-task { padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 12px; }
.unscheduled-task p { margin: 4px 0 8px; }
.empty-work { padding: 40px 20px; text-align: center; }
.empty-work h2 { font-size: 14px; font-weight: 500; }
.empty-work p { margin-top: 6px; font-size: 13px; color: var(--muted); }
table { border-collapse: collapse; width: 100%; text-align: left; }
th, td { border-bottom: 1px solid var(--border); padding: 4px 8px; font-size: 13px; }
th { position: sticky; top: 0; z-index: 1; white-space: nowrap; color: var(--muted); font-size: 12px; font-weight: 500; padding-block: 9px; background: var(--surface-2); }
td input, td select { width: 100%; min-width: 125px; border-color: transparent; background: transparent; }
td:first-child input { min-width: 240px; }
td input:focus, td select:focus { background: var(--surface); border-color: var(--accent); }
tbody tr:hover, tr.focused { background: var(--hover); }
tbody tr:last-child td { border-bottom: 0; }
.calendar { flex: 1; display: grid; grid-template-columns: repeat(var(--day-columns, 7), minmax(100px, 1fr)); grid-template-rows: repeat(var(--week-count), minmax(130px, auto)); min-width: calc(var(--day-columns, 7) * 100px); }
.calendar-day { position: relative; min-width: 0; min-height: 0; display: flex; flex-direction: column; padding: 5px 6px; border-right: 1px solid var(--border); border-bottom: 1px solid var(--border); font-size: 12px; }

.calendar-day time { display: grid; place-items: center; min-width: 24px; height: 24px; font-size: 11px; color: var(--muted); }
.day-heading { display: flex; align-items: center; justify-content: flex-end; min-height: 26px; }
.day-add { opacity: 0; width: 100%; min-height: 28px; padding: 5px 8px; text-align: left; color: var(--muted); background: var(--surface-2); font-size: 11px; border-radius: 4px; flex-shrink: 0; }
.calendar-day:hover .day-add, .calendar-day:focus-within .day-add { opacity: 1; }
.day-add:hover { background: var(--hover); color: var(--text); }
.day-menu { position: absolute; top: 60px; left: 6px; right: 6px; z-index: 6; min-width: 156px; padding: 4px; background: var(--surface); border: 1px solid var(--border); border-radius: 5px; }
.day-menu button { display: block; width: 100%; padding: 7px 8px; text-align: left; white-space: nowrap; }
.day-menu button:hover { background: var(--hover); }
.calendar-options { position: relative; font-size: 12px; }
.calendar-options summary { padding: 6px 9px; border: 1px solid var(--border); border-radius: 5px; cursor: pointer; list-style: none; }
.calendar-options summary::-webkit-details-marker { display: none; }
.options-menu { position: absolute; right: 0; top: calc(100% + 4px); z-index: 8; width: 220px; padding: 8px; background: var(--surface); border: 1px solid var(--border); border-radius: 5px; }
.calendar-layout-option { display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 8px 5px; text-align: left; border-radius: 4px; }
.calendar-layout-option:hover { background: var(--hover); }
.options-menu .weekend-option { justify-content: space-between; border-top: 1px solid var(--border); margin-top: 4px; }
.weekend-option input { width: 28px; accent-color: var(--accent); }
.options-menu label { display: flex; align-items: center; gap: 8px; padding: 7px 5px; }
@media (hover: none) { .day-add { opacity: 1; } }
.calendar-day.is-today time { background: var(--accent); color: var(--on-accent); border-radius: 50%; }
.calendar-day.outside-month { background: var(--surface-2); }
.day-tasks { overflow: visible; min-height: 0; }
.calendar-task { display: flex; flex-direction: row; align-items:center;gap:6px;min-height:32px; width: 100%; text-align: left; margin-top: 3px; padding: 5px 6px; border-radius: 4px; background: var(--surface); border: 1px solid var(--border); font-size: 12px; }
.calendar-task:hover, .calendar-task.task-focused { border-color: var(--accent); }
.calendar-task > span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.calendar-task .calendar-key { flex-shrink:0; }
.calendar-key { color: var(--muted); font-size: 10px; }
@media (max-width: 640px) {
  .views { padding: 12px 12px 0; }
  .views.embedded { padding: 0; }
  .view-header p, .context-note { display: none; }
  .date-toolbar { padding: 6px 8px; }
  .date-actions { width: 100%; justify-content: flex-end; }
  .unscheduled-pane { width: 220px; }
  .work-pane:has(.unscheduled-pane) .groups-scroll { display: none; }
  .unscheduled-pane { flex: 1; border-left: 0; }
}
</style>
