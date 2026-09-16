<template>
  <div class="task-board h-full flex flex-col">
    <Teleport v-if="toolbarReady" to="#task-toolbar-host">
    <header class="workspace-toolbar">
      <div class="work-breadcrumb"><router-link to="/projects">{{ projectLabel }}</router-link><span aria-hidden="true">/</span><h1>{{ moduleDetails?.title || 'Work items' }}</h1><span class="work-count">{{ visibleCount }}</span></div>
      <span v-if="movingTask" role="status" class="move-feedback">Moving task…</span>
      <div class="workspace-actions">
        <div class="workspace-modes" role="group" aria-label="Task layout"><button v-for="mode in modes" :key="mode.key" :class="{ active: view === mode.key }" :aria-pressed="view === mode.key" :aria-label="`${mode.label} view`" :title="`${mode.label} view`" @click="view = mode.key"><component :is="mode.icon" /></button></div>
        <select v-if="!route.query.project && !moduleId" aria-label="Project" v-model="project" @change="changeProject" class="ctl"><option :value="null">All projects</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option></select>
        <button class="toolbar-action" :aria-expanded="filtersOpen" @click="filtersOpen = !filtersOpen">Filters<span v-if="hasFilters" class="active-dot" /></button>
        <button class="toolbar-action" :aria-expanded="displayOpen" @click="displayOpen = !displayOpen">Display</button>
        <button class="btn-primary" @click="startToolbarAdd"><Plus class="w-3.5 h-3.5" /> Add work item</button>
        <details class="board-overflow"><summary aria-label="More task actions" title="More task actions"><Ellipsis aria-hidden="true" /></summary><div class="board-overflow-menu"><button @click="load">Refresh tasks</button><button @click="selectVisible(true)">Select visible tasks</button><button v-if="project" @click="settingsOpen = !settingsOpen">Task settings</button><router-link :to="{ path: '/analytics', query: project ? { project } : {} }">Analytics</router-link><router-link :to="{ path: '/reports', query: project ? { project } : {} }">Reports</router-link></div></details>
      </div>
    </header>
    </Teleport>
    <div v-if="filtersOpen" class="board-filters flex items-center flex-wrap gap-2 border-b border-soft">
      <div class="relative"><Search class="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" /><input v-model="filters.q" placeholder="Search tasks" aria-label="Search tasks" class="ctl task-search" /></div>
      <select aria-label="Filter by type" v-model="filters.type" class="ctl"><option value="">All types</option><option v-for="t in issueTypes" :key="t">{{ t }}</option></select>
      <select aria-label="Filter by priority" v-model="filters.priority" class="ctl"><option value="">All priorities</option><option>Urgent</option><option>High</option><option>Medium</option><option>Low</option></select>
      <select aria-label="Filter by assignee" v-model="filters.assignee" class="ctl"><option value="">Anyone</option><option v-for="a in assignees" :key="a" :value="a">{{ a.split('@')[0] }}</option></select>
      <button v-if="hasFilters" @click="clearFilters" class="toolbar-action">Clear filters</button>
    </div>
    <div v-if="displayOpen" class="display-panel border-b border-soft">
      <label><input type="checkbox" v-model="includeArchived" @change="load" /> Include archived</label><label><input type="checkbox" v-model="showCardDetails" /> Type, dates and estimates</label>
      <button v-if="['board', 'list'].includes(view)" class="toolbar-action" @click="selectVisible(true)">Select visible tasks</button>
      <button v-if="project" class="toolbar-action" @click="settingsOpen = !settingsOpen">Task settings</button>
      <template v-if="advancedMode"><button class="toolbar-action" @click="advancedPanel = advancedPanel === 'display' ? '' : 'display'">Grouping and columns</button><button class="toolbar-action" @click="advancedPanel = advancedPanel === 'filters' ? '' : 'filters'">Advanced filters</button><button class="toolbar-action" @click="advancedPanel = advancedPanel === 'save' ? '' : 'save'">Save view</button></template>
      <span class="text-xs text-muted">{{ visibleCount }} tasks</span>
    </div>
    <TaskSettings v-if="settingsOpen && project" :project="project" @close="settingsOpen = false" @changed="load" />
    <div v-if="selected.length && !advancedMode" class="selection-toolbar flex items-center flex-wrap gap-2 border-b border-soft text-xs">
      <label class="flex items-center gap-2"><input type="checkbox" :checked="allSelected" @change="selectVisible($event.target.checked)" /> Select visible</label>
      <template v-if="selected.length">
        <span>{{ selected.length }} selected</span>
        <select v-model="bulk.project" class="ctl" aria-label="Move selected to project" @change="loadBulkConfig"><option value="">Keep project</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option></select>
        <select v-model="bulk.workflow_state" class="ctl" aria-label="Bulk status"><option value="">Keep status</option><option v-for="s in bulkStatuses" :key="s.label">{{ s.label }}</option></select>
        <select v-model="bulk.priority" class="ctl" aria-label="Bulk priority"><option value="">Keep priority</option><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select>
        <select v-model="bulk.user" class="ctl" aria-label="Assign selected"><option value="">Assign to…</option><option v-for="u in users" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option></select>
        <button class="ctl" :disabled="bulkBusy" @click="applyBulk()">Apply changes</button>
        <button class="ctl" :disabled="bulkBusy" @click="applyBulk(1)">Archive</button><button v-if="includeArchived" class="ctl" :disabled="bulkBusy" @click="applyBulk(0)">Restore</button>
        <button @click="selected = []">Clear selection</button>
      </template>
    </div>
    <p v-if="loadError" role="alert" class="px-6 py-3 text-sm">{{ loadError }} <button class="underline" @click="load">Retry</button></p>
    <Views v-if="advancedMode" embedded :mode="view" :project="project" :task-names="visibleNames" :include-archived="includeArchived" :panel="advancedPanel" :refresh-key="refreshKey" :module="moduleId" :module-name="moduleDetails?.title" @changed="load" @close-panel="advancedPanel = ''" />
    <!-- Loading skeleton -->
    <div v-if="loading && !advancedMode && !movingTask && !cardBusy && !adding" class="flex gap-3 p-6 overflow-hidden">
      <div v-for="n in 5" :key="n" class="w-[264px] shrink-0">
        <Skeleton width="120px" height="14px" />
        <div class="mt-3 space-y-2">
          <div v-for="m in 3" :key="m" class="card-surface p-3">
            <Skeleton width="46px" height="10px" /><div class="mt-2"><Skeleton width="90%" height="12px" /></div>
            <div class="mt-3"><Skeleton width="60%" height="10px" /></div>
          </div>
        </div>
      </div>
    </div>

    <!-- BOARD -->
    <div v-else-if="view === 'board'" class="board-columns flex overflow-x-auto flex-1">
      <div v-for="col in cols" :key="col.name" :data-drop-state="col.name" :class="{ collapsed: collapsedColumns.includes(col.name) }" class="board-column shrink-0 flex flex-col"
        @dragover.prevent="dragOver = col.name; dragBefore = null" @dragleave="dragOver === col.name && (dragOver = null)" @drop.prevent="onDrop(col.name)">
        <div class="column-heading flex items-center gap-2">
          <component :is="statusIcon(col.name)" class="column-status-icon" :style="{ color: colColor(col.name) }" aria-hidden="true" />
          <span class="column-name">{{ col.name }}</span>
          <span class="column-count">{{ col.tasks.length }}</span>
          <button class="column-collapse" :aria-expanded="!collapsedColumns.includes(col.name)" :aria-label="`${collapsedColumns.includes(col.name) ? 'Expand' : 'Collapse'} ${col.name}`" :title="`${collapsedColumns.includes(col.name) ? 'Expand' : 'Collapse'} column`" @click="toggleColumn(col.name)"><component :is="collapsedColumns.includes(col.name) ? Expand : Collapse" /></button>
          <button v-if="!collapsedColumns.includes(col.name)" @click="startAdd(col.name)" class="column-add" :aria-label="`Add task to ${col.name}`" title="Add task"><Plus /></button>
        </div>
        <div v-show="!collapsedColumns.includes(col.name)" class="column-cards" :class="{ 'column-drop-active': dragOver === col.name }">

          <div v-for="t in col.tasks" :key="t.name" :data-drop-task="t.name" :draggable="!movingTask" @dragstart="startDrag($event, t)" @dragend="endDrag" @dragover.prevent.stop="dragOver = col.name; dragBefore = t.name" @drop.prevent.stop="onDrop(col.name, t.name)" @click="open(t.name)"
            :class="{ 'task-moving': movingTask === t.name, 'insert-before': dragTask && dragTask.name !== t.name && dragOver === col.name && dragBefore === t.name }" :aria-busy="movingTask === t.name" class="task-card group cursor-pointer">
            <div class="card-topline">
              <button type="button" class="drag-grip" :aria-label="`Drag ${t.issue_key || t.subject} to move or reorder`" title="Drag to move or reorder task" :disabled="!!movingTask" :draggable="false" @pointerdown.stop.prevent="startGripDrag($event, t)" @dragstart.stop.prevent @click.stop><GripVertical aria-hidden="true" /></button>
              <input type="checkbox" v-model="selected" :value="t.name" :aria-label="`Select ${t.subject}`" @click.stop />
              <span class="card-identifier">{{ t.issue_key || t.name }}</span>
              <TypeTag v-if="showCardDetails" :value="t.task_type" class="card-type" />
            </div>
            <button class="card-title" @click.stop="open(t.name)">{{ t.subject }}</button>
            <div v-if="showCardDetails && (t.exp_end_date || t.expected_time || t.pulse_story_points)" class="card-metadata">
              <span v-if="t.exp_end_date">Due {{ String(t.exp_end_date).slice(0, 10) }}</span><span v-if="t.expected_time">{{ t.expected_time }}h</span><span v-if="t.pulse_story_points">{{ t.pulse_story_points }} pts</span>
            </div>
            <div class="card-properties" @click.stop @pointerdown.stop @dragstart.stop.prevent>
              <label class="property-chip status-chip" :title="`Change status: ${t.workflow_state || col.name}`"><component :is="statusIcon(col.name)" class="chip-status-icon" :style="{ color: colColor(col.name) }" aria-hidden="true" /><select :value="t.workflow_state || col.name" :aria-label="`Status for ${t.subject}`" :disabled="Boolean(cardBusy) || Boolean(movingTask)" @focus="loadCardConfig(t.project)" @change="editCard(t, 'workflow_state', $event)"><option v-for="state in cardStatuses(t, col.name)" :key="state.label" :value="state.label">{{ state.label }}</option></select></label>
              <label class="property-chip priority-chip" title="Change priority"><PriorityDot :value="t.priority" /><select :value="t.priority || 'Low'" :aria-label="`Priority for ${t.subject}`" :disabled="Boolean(cardBusy) || Boolean(movingTask)" @change="editCard(t, 'priority', $event)"><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></label>
              <label class="property-chip assignee-chip" :title="t.assignees?.join(', ') || 'Assign task'"><Avatar v-if="t.assignees?.length" :name="t.assignees[0]" :size="16" /><UserRound v-else class="assignee-icon" /><select value="" :aria-label="`Assignees for ${t.subject}`" :disabled="Boolean(cardBusy) || Boolean(movingTask)" @change="editAssignment(t, $event)"><option value="" disabled>{{ t.assignees?.length ? `${t.assignees.length} assigned` : 'Assign' }}</option><optgroup label="Add assignee"><option v-for="user in users.filter(u => !t.assignees?.includes(u.name))" :key="user.name" :value="`add:${user.name}`">{{ user.full_name || user.name }}</option></optgroup><optgroup v-if="t.assignees?.length" label="Remove assignee"><option v-for="user in t.assignees" :key="user" :value="`remove:${user}`">{{ user }}</option></optgroup></select></label>
            </div>
          </div>
          <div v-if="dragTask && dragOver === col.name && !dragBefore" class="drop-insertion" aria-hidden="true" />
<form v-if="adding === col.name" class="inline-task-form" @submit.prevent="submitAdd(col.name)" @keydown.esc.stop.prevent="cancelAdd">
          <label v-if="!project && !moduleDetails?.project" class="inline-project"><span>Project</span><select v-model="addProject" required :disabled="addBusy"><option value="" disabled>Choose project</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option></select></label>
          <div class="inline-task-line"><span class="inline-prefix">{{ addProjectLabel }}</span><input ref="addInput" v-model="newSubject" aria-label="New work item title" placeholder="Work item title" :disabled="addBusy" maxlength="140" required autocomplete="off" /></div>
          <p v-if="addError" class="inline-error" role="alert">{{ addError }}</p><div class="inline-task-hint"><span>{{ addBusy ? 'Creating…' : `Press 'Enter' to add another work item` }}</span><button type="button" :disabled="addBusy" @click="cancelAdd" aria-label="Cancel new task"><X /></button></div>
        </form>
        <button v-if="!collapsedColumns.includes(col.name) && adding !== col.name" @click="startAdd(col.name)" class="column-new-task"><Plus /> New work item</button>
        </div>
      </div>
    </div>

    <!-- LIST -->
    <div v-else-if="view === 'list'" class="task-list flex-1 overflow-auto">
      <div v-for="col in cols" :key="col.name" :data-drop-state="col.name" class="list-group" :class="{ 'drop-active': dragOver === col.name }" @dragover.prevent="dragOver = col.name; dragBefore = null" @drop.prevent="onDrop(col.name)">
        <div class="list-status-heading flex items-center gap-2 sticky top-0">
          <component :is="statusIcon(col.name)" class="column-status-icon" :style="{ color: colColor(col.name) }" aria-hidden="true" />
          <span class="text-[13px] font-medium">{{ col.name }}</span>
          <span class="text-[11px] text-faint tnum">{{ col.tasks.length }}</span>
          <button class="list-group-add" :aria-label="`Add task to ${col.name}`" :title="`Add task to ${col.name}`" @click="startAdd(col.name)"><Plus /></button>
        </div>
        <div v-for="t in col.tasks" :key="t.name" :data-drop-task="t.name" :draggable="!movingTask" @dragstart="startDrag($event, t)" @dragend="endDrag" @dragover.prevent.stop="dragOver = col.name; dragBefore = t.name" @drop.prevent.stop="onDrop(col.name, t.name)" @click="open(t.name)"
          :class="{ 'task-moving': movingTask === t.name, 'insert-before': dragTask && dragTask.name !== t.name && dragOver === col.name && dragBefore === t.name }" :aria-busy="movingTask === t.name" class="list-row flex items-center gap-3 px-2 py-2 hover-app cursor-pointer">
          <button type="button" class="drag-grip" :aria-label="`Drag ${t.issue_key || t.subject} to move or reorder`" title="Drag to move or reorder task" :disabled="!!movingTask" :draggable="false" @pointerdown.stop.prevent="startGripDrag($event, t)" @dragstart.stop.prevent @click.stop><GripVertical aria-hidden="true" /></button>
          <input type="checkbox" v-model="selected" :value="t.name" :aria-label="`Select ${t.subject}`" @click.stop />
          <span class="list-identifier">{{ t.issue_key || t.name }}</span>
          <TypeTag v-if="showCardDetails" :value="t.task_type" />
          <button class="list-task-title flex-1 truncate text-[13px]" @click.stop="open(t.name)">{{ t.subject }}</button>
            <div class="card-properties list-properties" @click.stop @pointerdown.stop @dragstart.stop.prevent>
              <label class="property-chip status-chip" :title="`Change status: ${t.workflow_state || col.name}`"><component :is="statusIcon(col.name)" class="chip-status-icon" :style="{ color: colColor(col.name) }" aria-hidden="true" /><select :value="t.workflow_state || col.name" :aria-label="`Status for ${t.subject}`" :disabled="Boolean(cardBusy) || Boolean(movingTask)" @focus="loadCardConfig(t.project)" @change="editCard(t, 'workflow_state', $event)"><option v-for="state in cardStatuses(t, col.name)" :key="state.label" :value="state.label">{{ state.label }}</option></select></label>
              <label class="property-chip priority-chip" title="Change priority"><PriorityDot :value="t.priority" /><select :value="t.priority || 'Low'" :aria-label="`Priority for ${t.subject}`" :disabled="Boolean(cardBusy) || Boolean(movingTask)" @change="editCard(t, 'priority', $event)"><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></label>
              <label class="property-chip assignee-chip" :title="t.assignees?.join(', ') || 'Assign task'"><Avatar v-if="t.assignees?.length" :name="t.assignees[0]" :size="16" /><UserRound v-else class="assignee-icon" /><select value="" :aria-label="`Assignees for ${t.subject}`" :disabled="Boolean(cardBusy) || Boolean(movingTask)" @change="editAssignment(t, $event)"><option value="" disabled>{{ t.assignees?.length ? `${t.assignees.length} assigned` : 'Assign' }}</option><optgroup label="Add assignee"><option v-for="user in users.filter(u => !t.assignees?.includes(u.name))" :key="user.name" :value="`add:${user.name}`">{{ user.full_name || user.name }}</option></optgroup><optgroup v-if="t.assignees?.length" label="Remove assignee"><option v-for="user in t.assignees" :key="user" :value="`remove:${user}`">{{ user }}</option></optgroup></select></label>
            </div>
        </div>
        <p v-if="!col.tasks.length && dragTask" class="empty-drop">Drop a task here</p>
<form v-if="adding === col.name" class="inline-task-form" @submit.prevent="submitAdd(col.name)" @keydown.esc.stop.prevent="cancelAdd">
          <label v-if="!project && !moduleDetails?.project" class="inline-project"><span>Project</span><select v-model="addProject" required :disabled="addBusy"><option value="" disabled>Choose project</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option></select></label>
          <div class="inline-task-line"><span class="inline-prefix">{{ addProjectLabel }}</span><input ref="addInput" v-model="newSubject" aria-label="New work item title" placeholder="Work item title" :disabled="addBusy" maxlength="140" required autocomplete="off" /></div>
          <p v-if="addError" class="inline-error" role="alert">{{ addError }}</p><div class="inline-task-hint"><span>{{ addBusy ? 'Creating…' : `Press 'Enter' to add another work item` }}</span><button type="button" :disabled="addBusy" @click="cancelAdd" aria-label="Cancel new task"><X /></button></div>
        </form>
        <button v-if="adding !== col.name" class="list-new-task" @click="startAdd(col.name)"><Plus /> New work item</button>
      </div>
    </div>

    <div v-if="pointerDragging" class="pointer-preview" :style="{ left: `${pointerPosition.x + 16}px`, top: `${pointerPosition.y + 16}px` }" aria-hidden="true">{{ dragTask?.issue_key }} · {{ dragTask?.subject }}</div>
    <TaskDrawer :task-id="openId" @close="openId = null" @changed="load" @open="open" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { call } from 'frappe-ui'
import { io } from 'socket.io-client'
import Views from './Views.vue'
import { moveTaskToGroup, trackGripDrag } from '@/utils/taskLayout.js'
import Calendar from '~icons/lucide/calendar-days'
import Timeline from '~icons/lucide/chart-gantt'
import Table from '~icons/lucide/table-2'
import TaskSettings from '@/components/tasks/TaskSettings.vue'
import TaskDrawer from '@/components/TaskDrawer.vue'
import Avatar from '@/ui/Avatar.vue'
import TypeTag from '@/ui/TypeTag.vue'
import PriorityDot from '@/ui/PriorityDot.vue'
import Skeleton from '@/ui/Skeleton.vue'
import { toast } from '@/ui/toast'
import { openCreate, createState } from '@/ui/create'
import SquareKanban from '~icons/lucide/square-kanban'
import List from '~icons/lucide/list'
import Search from '~icons/lucide/search'
import Plus from '~icons/lucide/plus'
import X from '~icons/lucide/x'
import Expand from '~icons/lucide/chevrons-left-right'
import Collapse from '~icons/lucide/chevrons-right-left'
import UserRound from '~icons/lucide/user-round'
import GripVertical from '~icons/lucide/grip-vertical'
import CircleDashed from '~icons/lucide/circle-dashed'
import Circle from '~icons/lucide/circle'
import CircleDot from '~icons/lucide/circle-dot'
import CircleCheck from '~icons/lucide/circle-check'
import Ellipsis from '~icons/lucide/ellipsis'

const collapsedColumns = ref([]), cardBusy = ref(null), cardConfigs = ref({})
function toggleColumn(name) { collapsedColumns.value = collapsedColumns.value.includes(name) ? collapsedColumns.value.filter(c => c !== name) : [...collapsedColumns.value, name] }
function statusClass(name) {
  const state = Object.values(cardConfigs.value).flatMap(c => c.statuses || []).find(s => s.label === name)
  const category = state?.category || name
  return ['Done', 'Completed'].includes(category) ? 'done' : ['In Progress', 'In Review', 'Working'].includes(category) ? 'active' : category === 'Backlog' ? 'backlog' : 'pending'
}
function statusIcon(name) { return { done: CircleCheck, active: CircleDot, backlog: CircleDashed, pending: Circle }[statusClass(name)] }
async function loadCardConfig(projectName) {
  if (!projectName || cardConfigs.value[projectName]) return
  try { cardConfigs.value[projectName] = await call('pulse.api.task_config.get_config', { project: projectName }) }
  catch { toast.error('Task statuses could not be loaded. Try again.') }
}
function cardStatuses(task, current) { return cardConfigs.value[task.project]?.statuses || [{ label: task.workflow_state || current }] }
async function editCard(task, field, event) {
  const value = event.target.value, previous = task[field]
  if (cardBusy.value || movingTask.value) { event.target.value = previous; return }
  cardBusy.value = task.name
  try { await call('pulse.api.tasks.bulk_update', { tasks: [task.name], fields: { [field]: value } }); await load(); toast.success('Task updated') }
  catch (error) { event.target.value = previous; toast.error(error?.messages?.[0] || 'Could not update this task. Try again.') }
  finally { cardBusy.value = null }
}
async function editAssignment(task, event) {
  const action = event.target.value, removing = action.startsWith('remove:'), user = action.slice(removing ? 7 : 4)
  event.target.value = ''
  if (!user || cardBusy.value || movingTask.value) return
  cardBusy.value = task.name
  try { await call('pulse.api.tasks.bulk_update', { tasks: [task.name], [removing ? 'unassign' : 'assign']: [user] }); await load(); toast.success(removing ? 'Assignee removed' : 'Task assigned') }
  catch (error) { toast.error(error?.messages?.[0] || 'Could not change the assignment. Try again.') }
  finally { cardBusy.value = null }
}

const toolbarReady = ref(false)
const route = useRoute()
const moduleId = computed(() => typeof route.query.module === 'string' ? route.query.module : '')
const moduleDetails = ref(null)
const moduleTaskNames = computed(() => new Set(moduleDetails.value?.tasks?.map(t => t.name) || []))
const showCardDetails = ref(false)
const settingsOpen = ref(false), includeArchived = ref(false), selected = ref([]), users = ref([]), bulkBusy = ref(false), loadError = ref('')
const bulk = reactive({ project: '', workflow_state: '', priority: '', user: '' })
const bulkStatuses = ref([])
const allSelected = computed(() => visibleCount.value > 0 && cols.value.every(c => c.tasks.every(t => selected.value.includes(t.name))))
function selectVisible(checked) { selected.value = checked ? cols.value.flatMap(c => c.tasks.map(t => t.name)).slice(0, 200) : [] }
async function loadBulkConfig() {
  bulk.workflow_state = ''
  const target = bulk.project || project.value
  bulkStatuses.value = target ? (await call('pulse.api.task_config.get_config', { project: target })).statuses : board.value.columns.map(c => ({ label: c.name }))
}
async function applyBulk(archived) {
  bulkBusy.value = true
  try {
    const fields = Object.fromEntries(['project', 'workflow_state', 'priority'].filter(k => bulk[k]).map(k => [k, bulk[k]]))
    if (archived !== undefined) fields.pulse_archived = archived
    if (!Object.keys(fields).length && !bulk.user) { toast.error('Choose a change to apply'); return }
    await call('pulse.api.tasks.bulk_update', { tasks: selected.value, fields, assign: bulk.user ? [bulk.user] : [] })
    toast.success(`${selected.value.length} tasks updated`); selected.value = []; Object.assign(bulk, { project: '', workflow_state: '', priority: '', user: '' }); await load()
  } catch (e) { toast.error(e?.messages?.[0] || 'Could not update selected tasks. No changes were applied.') }
  finally { bulkBusy.value = false }
}
const loading = ref(true)
const view = ref('list')
const modes = [{ key: 'list', label: 'List', icon: List }, { key: 'board', label: 'Board', icon: SquareKanban }, { key: 'calendar', label: 'Calendar', icon: Calendar }, { key: 'timeline', label: 'Timeline', icon: Timeline }, { key: 'spreadsheet', label: 'Spreadsheet', icon: Table }]
const advancedMode = computed(() => ['calendar', 'timeline', 'spreadsheet'].includes(view.value))
const filtersOpen = ref(false), displayOpen = ref(false), advancedPanel = ref(''), refreshKey = ref(0)
const visibleNames = computed(() => cols.value.flatMap(c => c.tasks.map(t => t.name)))
watch(view, () => { selected.value = []; advancedPanel.value = '' })
const board = ref({ columns: [], total: 0 })
const projects = ref([])
const issueTypes = ref([])
const project = ref(route.query.project || null)
watch(() => [route.query.project, route.query.module], ([value]) => { project.value = value || null; moduleDetails.value = null; selected.value = []; changeProject() })
const movingTask = ref(null)
const dragTask = ref(null)
const dragOver = ref(null)
const dragBefore = ref(null)
const openId = ref(route.query.task || null)
watch(() => route.query.task, value => { openId.value = value || null })
const adding = ref(null)
const newSubject = ref(''), addBusy = ref(false), addError = ref(''), addProject = ref('')
const projectLabel = computed(() => projects.value.find(p => p.name === project.value)?.project_name || project.value || 'Projects')
const addProjectLabel = computed(() => { const name = project.value || moduleDetails.value?.project || addProject.value; const selectedProject = projects.value.find(p => p.name === name); return selectedProject?.pulse_project_key || name || 'PROJECT' })
const addInput = ref(null)
const filters = reactive({ q: '', type: '', priority: '', assignee: '' })
let restoringPreferences = true, preferenceTimer = null, preferenceVersion = 0, pendingPreference = null, preferenceWrites = Promise.resolve()
const preferenceContext = () => `board:${project.value || 'all'}${moduleId.value ? `:module:${moduleId.value}` : ''}`
function flushPreference() {
  clearTimeout(preferenceTimer)
  if (!pendingPreference) return preferenceWrites
  const snapshot = pendingPreference; pendingPreference = null
  preferenceWrites = preferenceWrites.then(() => call('pulse.api.views.preferences', snapshot)).catch(() => toast.error('Workspace preferences could not be saved.'))
  return preferenceWrites
}
async function restorePreferences() {
  const version = ++preferenceVersion
  clearTimeout(preferenceTimer); restoringPreferences = true
  try {
    const prefs = await call('pulse.api.views.preferences', { context: preferenceContext() })
    if (version !== preferenceVersion) return
    view.value = prefs.layout || 'list'
    Object.assign(filters, { q: '', type: '', priority: '', assignee: '' }, prefs.filters)
    includeArchived.value = Boolean(prefs.include_archived)
    filtersOpen.value = Boolean(prefs.filters_open); displayOpen.value = Boolean(prefs.display_open)
    await nextTick()
  } catch (e) { toast.error('Could not restore your workspace preferences.') }
  finally { if (version === preferenceVersion) restoringPreferences = false }
}
async function changeProject() { selected.value = []; await flushPreference(); await restorePreferences(); await load() }
watch([view, filters, includeArchived, filtersOpen, displayOpen], () => {
  if (restoringPreferences) return
  clearTimeout(preferenceTimer)
  const context = preferenceContext()
  const config = { layout: view.value, filters: { ...filters }, include_archived: includeArchived.value, filters_open: filtersOpen.value, display_open: displayOpen.value }
  pendingPreference = { context, config }
  preferenceTimer = setTimeout(flushPreference, 250)
}, { deep: true })


const COL_COLORS = { Backlog: '#8994a3', 'To Do': '#b491ff', 'In Progress': '#f5b45a', 'In Review': '#6aa9ff', Done: '#34d399' }
function colColor(c) { return board.value.columns.find(col => col.name === c)?.color || COL_COLORS[c] || '#8994a3' }

const assignees = computed(() => {
  const s = new Set()
  for (const c of board.value.columns) for (const t of c.tasks) for (const a of (t.assignees || [])) s.add(a)
  return [...s]
})
const hasFilters = computed(() => filters.q || filters.type || filters.priority || filters.assignee)
function clearFilters() { filters.q = ''; filters.type = ''; filters.priority = ''; filters.assignee = '' }

const cols = computed(() => board.value.columns.map((c) => ({
  name: c.name,
  tasks: c.tasks.filter((t) => {
    if (moduleId.value && !moduleTaskNames.value.has(t.name)) return false
    if (filters.q && !(`${t.issue_key} ${t.subject}`.toLowerCase().includes(filters.q.toLowerCase()))) return false
    if (filters.type && t.task_type !== filters.type) return false
    if (filters.priority && t.priority !== filters.priority) return false
    if (filters.assignee && !(t.assignees || []).includes(filters.assignee)) return false
    return true
  }),
})))
const visibleCount = computed(() => cols.value.reduce((n, c) => n + c.tasks.length, 0))

let loadVersion = 0, deferredBoardRefresh = false
async function load() {
  if (movingTask.value || dragTask.value) { deferredBoardRefresh = true; return }
  const version = ++loadVersion
  loading.value = !board.value.columns.length
  loadError.value = ''
  try {
  const [b, ps, its, moduleData] = await Promise.all([
    call('pulse.api.spa.get_board', { project: project.value, include_archived: includeArchived.value ? 1 : 0 }),
    projects.value.length ? Promise.resolve(projects.value)
      : call('frappe.client.get_list', { doctype: 'Project', fields: ['name', 'project_name', 'pulse_project_key'], limit_page_length: 0 }),
    issueTypes.value.length ? Promise.resolve(issueTypes.value)
      : call('frappe.client.get_list', { doctype: 'Task Type', fields: ['name'], limit_page_length: 0 }).then((r) => r.map((x) => x.name)),
    moduleId.value ? call('pulse.api.modules.get_module', { name: moduleId.value }) : Promise.resolve(null),
  ])
  if (version !== loadVersion) return
  if (movingTask.value || dragTask.value) { deferredBoardRefresh = true; return }
  moduleDetails.value = moduleData
  board.value = b; refreshKey.value++; projects.value = ps; issueTypes.value = its
  selected.value = selected.value.filter(name => b.columns.some(c => c.tasks.some(t => t.name === name)))
  if (!users.value.length) users.value = await call('pulse.api.spa.get_assignable_users')
  if (project.value) { const config = await call('pulse.api.task_config.get_config', { project: project.value }); issueTypes.value = config.task_types; cardConfigs.value[project.value] = config }
  await loadBulkConfig()
  } catch (e) { if (version === loadVersion) loadError.value = e?.messages?.[0] || 'Could not load tasks.' }
  finally { if (version === loadVersion) loading.value = false }
}

const pointerDragging = ref(false), pointerPosition = reactive({ x: 0, y: 0 })
let cancelGripDrag = null
function startGripDrag(event, task) {
  if (movingTask.value || event.button !== 0) return
  cancelGripDrag?.()
  ++loadVersion // Discard responses requested before this gesture.
  dragTask.value = task
  event.currentTarget.setPointerCapture?.(event.pointerId)
  cancelGripDrag = trackGripDrag(event, {
    onMove: ({ state, before, x, y }) => { pointerDragging.value = true; dragOver.value = state; dragBefore.value = before; pointerPosition.x = x; pointerPosition.y = y },
    onDrop: ({ state, before }) => { pointerDragging.value = false; cancelGripDrag = null; onDrop(state, before) },
    onCancel: () => { pointerDragging.value = false; cancelGripDrag = null; endDrag() },
  })
}
function startDrag(event, task) { if (movingTask.value) { event.preventDefault(); return } ++loadVersion; dragTask.value = task; event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData('text/plain', task.name) }
function endDrag() { dragTask.value = null; dragOver.value = null; dragBefore.value = null; if (deferredBoardRefresh) { clearTimeout(rtTimer); rtTimer = setTimeout(() => { deferredBoardRefresh = false; load() }, 400) } }
async function onDrop(colName, beforeName = null) {
  const task = dragTask.value; endDrag()
  if (!task || movingTask.value) return
  movingTask.value = task.name
  clearTimeout(rtTimer)
  try {
    const changed = await moveTaskToGroup(board.value.columns, task.name, colName, (name, state, before, after) => call('pulse.api.tasks.move_task', { task: name, state, before, after }), beforeName)
    if (changed) { toast.success(`${task.issue_key || task.subject} moved to ${colName}`); deferredBoardRefresh = true }
  } catch (e) { toast.error(e?.messages?.[0] || 'Could not move task'); deferredBoardRefresh = true }
  finally { movingTask.value = null; if (deferredBoardRefresh) { deferredBoardRefresh = false; await load() } }
}

function focusInlineInput() { nextTick(() => { const input = Array.isArray(addInput.value) ? addInput.value.find(el => el?.isConnected) : addInput.value; input?.focus?.() }) }
function startAdd(col) {
  if (addBusy.value) return
  if (adding.value !== col) { newSubject.value = ''; addError.value = '' }
  adding.value = col; collapsedColumns.value = collapsedColumns.value.filter(name => name !== col)
  addProject.value = project.value || moduleDetails.value?.project || ''
  focusInlineInput()
}
async function startToolbarAdd() {
  if (!['board', 'list'].includes(view.value)) { view.value = 'list'; await nextTick() }
  if (cols.value.length) startAdd(cols.value[0].name)
  else toast.error('Choose a project with task statuses first.')
}
function dismissInlineOutside(event) { if (adding.value && !event.target.closest('.inline-task-form')) cancelAdd() }
function cancelAdd() { if (!addBusy.value) { adding.value = null; newSubject.value = ''; addError.value = '' } }
async function submitAdd(col) {
  if (addBusy.value) return
  const subject = newSubject.value.trim(), proj = project.value || moduleDetails.value?.project || addProject.value
  if (!subject) return
  if (!proj) { addError.value = 'Choose a project for this task.'; return }
  addBusy.value = true; addError.value = ''
  try {
    const task = await call('pulse.api.spa.create_task', { project: proj, subject, state: col, module: moduleId.value || undefined })
    newSubject.value = ''
    await load()
    toast.success(`Created ${task.issue_key || subject}`)
  } catch (error) { addError.value = error?.messages?.[0] || 'Task could not be created. Your title is still here; try again.' }
  finally { addBusy.value = false; focusInlineInput() }
}

function open(name) { openId.value = name }
// reload when an issue is created from the global New Issue dialog
watch(() => createState.created, load)

// --- real-time: refresh the board when anyone changes it (needs socketio) ---
let socket = null
let rtTimer = null

// Frappe's socketio is per-site: the socket.io NAMESPACE must equal the site
// name, and the backend publishes events under the real site name (e.g.
// "pulse.local"). When the app is reached by IP the server would otherwise
// derive the site from the Origin hostname and we'd sit in the wrong namespace,
// so we state the site explicitly via X-Frappe-Site-Name (honoured first by
// the socketio auth middleware). That header only rides on the polling
// handshake, hence polling-first — socket.io upgrades to websocket after.
function realtimeSite() {
  return window.sitename || location.hostname
}
function realtimeUrl() {
  const port = window.socketio_port || 9000
  return `${location.protocol}//${location.hostname}:${port}/${realtimeSite()}`
}

function connectRealtime() {
  const url = realtimeUrl()
  try {
    socket = io(url, {
      withCredentials: true,
      transports: ['polling', 'websocket'],
      transportOptions: { polling: { extraHeaders: { 'X-Frappe-Site-Name': realtimeSite() } } },
    })
    socket.on('connect', () => { window.__pulseRealtime = `connected ${url}` })
    socket.on('connect_error', (e) => {
      // realtime is optional — surface why instead of failing silently
      window.__pulseRealtime = `error: ${e?.message || e}`
      console.warn('[pulse] realtime unavailable:', e?.message || e, url)
    })
    socket.on('pulse:board', () => { clearTimeout(rtTimer); if (movingTask.value || dragTask.value) { deferredBoardRefresh = true; return } rtTimer = setTimeout(load, 400) })
  } catch (e) {
    window.__pulseRealtime = `threw: ${e}`
    console.warn('[pulse] realtime init failed', e)
  }
}
onMounted(async () => { document.addEventListener('pointerdown', dismissInlineOutside, true); toolbarReady.value = true; await restorePreferences(); load(); connectRealtime() })
onUnmounted(() => { document.removeEventListener('pointerdown', dismissInlineOutside, true); flushPreference(); cancelGripDrag?.(); try { socket && socket.disconnect() } catch (e) {} clearTimeout(rtTimer) })
</script>

<style scoped>
.work-breadcrumb { display: flex; align-items: center; gap: 10px; min-width: 0; color: var(--muted); font-size: 12px; }.work-breadcrumb > a { max-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }.work-breadcrumb h1 { color: var(--text); }.work-count { font-size: 11px; border-radius: 4px; padding: 1px 5px; background: var(--surface-2); }
.board-overflow { position: relative; }.board-overflow > summary { cursor: pointer; list-style: none; padding: 7px; color: var(--muted); }.board-overflow > summary::-webkit-details-marker { display: none; }.board-overflow-menu { position: absolute; right: 0; top: 100%; z-index: 40; width: 170px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 5px; }.board-overflow-menu > * { display: block; text-align: left; width: 100%; padding: 7px; font-size: 12px; }.board-overflow-menu > *:hover { background: var(--hover); }
.inline-task-form { flex-shrink: 0; margin: 0; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.inline-task-form:focus-within { border-color: var(--accent); }
.inline-task-line { display: flex; align-items: center; gap: 12px; min-height: 47px; padding: 11px 16px; }
.inline-prefix { flex-shrink: 0; font-size: 12px; color: var(--muted); width: 76px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.inline-task-line input { min-width: 0; flex: 1; width: 100%; border: 0; background: transparent; font-size: 13px; padding: 2px 0; color: var(--text); outline: none; }
.inline-task-line input::placeholder { color: var(--muted); }
.inline-task-hint { display: flex; justify-content: space-between; align-items: center; min-height: 31px; padding: 7px 12px; background: var(--surface-2); font-size: 11px; color: var(--muted); }
.inline-task-hint > span { font-style: italic; }.inline-task-hint button svg { width: 13px; height: 13px; }
.inline-error { font-size: 12px; color: var(--danger); padding: 7px 12px; }
.inline-project { display: flex; align-items: center; gap: 8px; font-size: 11px; padding: 8px 12px; color: var(--muted); border-bottom: 1px solid var(--border); }.inline-project select { width: 100%; min-width: 0; font-size: 12px; background: var(--surface); border: 1px solid var(--border); padding: 3px; border-radius: 4px; }
.column-cards .inline-task-line { flex-direction: column; align-items: stretch; gap: 9px; padding: 12px; min-height: 81px; }.column-cards .inline-prefix { width: auto; }.column-cards .inline-task-line input { flex: none; }
.list-group .inline-task-form { margin: 0 16px 0 32px; border-radius: 5px; }
.board-overflow > summary svg { width: 16px; height: 16px; }.drag-grip svg { width: 14px; height: 14px; }.chip-status-icon { width: 11px; height: 11px; flex-shrink: 0; }

@media(max-width: 1100px) { .work-breadcrumb > a { max-width: 100px; }.workspace-toolbar { gap: 8px; } }
@media(max-width: 800px) { .workspace-toolbar { flex-wrap: wrap; }.work-breadcrumb { flex: 1; }.workspace-actions { margin-left: 0; flex-wrap: wrap; }.work-breadcrumb h1 { display: block; } }
.task-board { min-width: 0; background: var(--surface); }
.board-display-controls { min-width: 0; max-width: 100%; }
.board-display-controls select { min-width: 0; max-width: 200px; }
.board-display-controls button { white-space: nowrap; }
.ctl.task-search { width: 208px; padding-left: 32px; }
.workspace-toolbar { position: relative; flex: 1; min-width: 0; width: 100%; display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 6px 16px; flex-wrap: nowrap; }
.workspace-toolbar h1 { white-space: nowrap; font-size: 14px; font-weight: 600; margin: 0; }
.workspace-modes { display: flex; gap: 1px; padding: 2px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 5px; }
.workspace-modes button { display: flex; align-items: center; gap: 5px; padding: 4px 6px; min-height: 26px; color: var(--muted); border-radius: 3px; font-size: 12px; }
.workspace-modes svg { width: 15px; height: 15px; flex-shrink: 0; }
.workspace-modes button.active { color: var(--text); background: var(--surface); }
.workspace-modes button:hover, .toolbar-action:hover { background: var(--hover); color: var(--text); }
.workspace-actions { flex-shrink: 0; display: flex; align-items: center; gap: 5px; margin-left: auto; }
.workspace-actions > select { max-width: 140px; }
.workspace-actions .btn-primary { display: flex; align-items: center; gap: 5px; font-size: 12px; }
.toolbar-action { border: 1px solid var(--border); display: inline-flex; align-items: center; gap: 5px; color: var(--muted); font-size: 12px; padding: 6px 8px; border-radius: 5px; min-height: 30px; }
.active-dot { width: 5px; height: 5px; background: var(--accent); border-radius: 50%; }
.display-panel { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; padding: 8px 16px; }
.display-panel label { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.task-list { padding: 0; }
.list-group { min-width: 740px; margin-bottom: 0; min-height: 84px; padding: 0; border: 0; }
.list-group.drop-active { border-color: var(--accent); background: var(--surface-2); }
.list-status-heading { min-height: 40px; background: var(--surface-2); padding: 6px 24px; border-radius: 0; z-index: 3; }
.list-group-add { margin-left: auto; width: 26px; height: 26px; display: grid; place-items: center; color: var(--muted); border-radius: 4px; }.list-group-add:hover { color: var(--text); background: var(--hover); }.list-group-add svg, .list-new-task svg { width: 14px; height: 14px; }
.list-new-task { display: flex; align-items: center; gap: 8px; width: 100%; min-height: 44px; padding: 10px 48px; text-align: left; color: var(--muted); font-size: 12px; }.list-new-task:hover { color: var(--text); background: var(--hover); }.list-task-title { text-align: left; min-width: 120px; }.list-task-title:hover { color: var(--accent); }
.list-row .list-properties { margin-top: 0; flex-wrap: nowrap; flex-shrink: 0; }.list-properties .status-chip { max-width: 125px; }.list-properties .assignee-chip { max-width: 115px; }
.list-row { position: relative; border-bottom: 1px solid var(--border-soft); min-height: 48px; padding: 9px 24px 9px 48px; }
.list-row { cursor: grab; user-select: none; touch-action: pan-y; }
.drag-grip { display: grid; place-items: center; color: var(--muted); font-size: 18px; width: 24px; height: 28px; flex-shrink: 0; touch-action: none; cursor: grab; border-radius: 4px; }
.drag-grip:hover { color: var(--text); background: var(--surface-2); }
.drag-grip:active { cursor: grabbing; }
.pointer-preview { position: fixed; z-index: 100; pointer-events: none; max-width: 320px; padding: 8px 12px; border: 1px solid var(--accent); border-radius: 5px; background: var(--surface); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-drop { font-size: 12px; color: var(--muted); padding: 8px 20px; }
.move-feedback { position: absolute; top: 100%; inset-inline-start: 16px; z-index: 30; padding: 4px 8px; border-radius: 4px; background: var(--surface); color: var(--muted); font-size: 12px; }
.task-moving { opacity: 0.55; cursor: progress; }
.list-row:active { cursor: grabbing; }
@media (max-width: 800px) { .workspace-modes button span { display: none; } .workspace-modes button { padding: 7px; } .workspace-toolbar { gap: 8px; } }
@media (max-width: 480px) { .workspace-toolbar { padding-inline: 10px; } .workspace-toolbar h1 { display: none; } .workspace-actions { margin-left: 0; flex-wrap: wrap; } }
.board-filters { padding: 8px 16px; }
.selection-toolbar { padding: 9px 24px; color: var(--muted); min-height: 42px; }
.board-columns { min-height: 0; padding: 16px; gap: 16px; background: var(--surface); align-items: stretch; }
.board-column { position: relative; width: 336px; min-height: 0; max-height: 100%; background: #f8f8f8; border-radius: 8px; padding: 8px; overflow: hidden; }
:global(.dark) .board-column { background: var(--surface-2); }
.column-heading { flex-shrink: 0; min-height: 38px; padding: 0 5px 7px; }
.status-mark { width: 9px; height: 9px; border-radius: 3px; flex-shrink: 0; }
.ctl { background: var(--surface); border: 1px solid var(--border); color: var(--text); font-size: 12px; border-radius: 6px; min-height: 32px; padding: 6px 9px; outline: none; }
.ctl:focus, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.seg, .seg-on { padding: 7px 10px; display: grid; place-items: center; }
.seg { color: var(--muted); background: var(--surface); }
.seg-on { color: var(--text); background: var(--surface-2); }
.task-card { position: relative; flex-shrink: 0; padding: 12px; border: 1px solid var(--border); border-radius: 7px; background: var(--surface); }
.insert-before::before { content: ''; position: absolute; top: -5px; left: 0; right: 0; height: 3px; border-radius: 2px; background: var(--accent); pointer-events: none; z-index: 2; }
.drop-insertion { position: absolute; inset-inline: 10px; bottom: 42px; height: 2px; background: var(--accent); border-radius: 2px; pointer-events: none; z-index: 2; }
.task-card:hover { border-color: var(--muted); }
.task-card:focus-within { outline: 2px solid var(--accent); outline-offset: 1px; }
.card-metadata { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; color: var(--muted); margin-top: 10px; }
.column-name { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.column-count { font-size: 12px; color: var(--muted); }
.column-collapse { margin-inline-start: auto; }.column-collapse, .column-add { width: 24px; height: 24px; display: grid; place-items: center; color: var(--muted); border-radius: 4px; flex-shrink: 0; }.column-collapse svg, .column-add svg { width: 14px; height: 14px; }.column-collapse:hover, .column-add:hover { background: var(--hover); color: var(--text); }
.column-status-icon { width: 15px; height: 15px; flex-shrink: 0; stroke-width: 1.75; }
.column-cards { display: flex; flex-direction: column; gap: 8px; min-height: 0; flex: 1; padding: 0; overflow-y: auto; overscroll-behavior-y: contain; overscroll-behavior-x: auto; scrollbar-width: thin; }.column-drop-active { background: color-mix(in srgb, var(--accent) 7%, transparent); border-radius: 6px; }
.column-new-task { display: flex; align-items: center; gap: 6px; padding: 11px 7px 5px; color: var(--muted); font-size: 12px; text-align: start; flex-shrink: 0; }.column-new-task svg { width: 14px; height: 14px; }.column-new-task:hover { color: var(--text); }
.card-topline { display: flex; align-items: center; gap: 6px; margin-bottom: 7px; }.card-topline .drag-grip { width: 16px; height: 18px; font-size: 15px; }.card-topline input { width: 13px; height: 13px; }.card-identifier { color: var(--muted); font-size: 12px; }.card-title { display: block; width: 100%; text-align: start; font-size: 13px; font-weight: 400; line-height: 1.5; color: var(--text); overflow-wrap: anywhere; }.card-title:hover { color: var(--accent); }
.card-properties { display: flex; flex-wrap: nowrap; align-items: center; gap: 5px; margin-top: 14px; }.property-chip { display: inline-flex; align-items: center; gap: 4px; min-width: 0; max-width: 100%; padding: 3px 5px; border: 1px solid var(--border); border-radius: 4px; height: 20px; background: var(--surface); }.property-chip select { min-width: 0; max-width: 108px; border: 0; padding: 0 10px 0 0; height: auto; background-color: transparent; color: var(--muted); font-size: 11px; cursor: pointer; }.property-chip select:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }.property-chip select:disabled { cursor: progress; opacity: .6; }.chip-status-dot { width: 7px; height: 7px; flex-shrink: 0; border-radius: 50%; }.assignee-icon { width: 12px; height: 12px; color: var(--muted); }
.board-column.collapsed { width: 46px; padding: 8px 5px; }.collapsed .column-heading { flex-direction: column; height: 100%; padding: 0; gap: 12px; }.collapsed .column-name { writing-mode: vertical-rl; max-height: 240px; }.collapsed .column-collapse { margin-inline-start: 0; order: -1; }
.work-count { background: color-mix(in srgb, var(--accent) 10%, var(--surface)); color: var(--accent); }
.card-topline { min-height: 18px; }.card-topline > .drag-grip, .card-topline > input { position: absolute; top: 10px; opacity: 0; }.card-topline > .drag-grip { right: 12px; }.card-topline > input { right: 36px; }.task-card:hover .card-topline > :is(.drag-grip,input), .task-card:focus-within .card-topline > :is(.drag-grip,input), .card-topline > input:checked { opacity: 1; }.card-type { margin-inline-start: auto; margin-inline-end: 44px; }
.list-identifier { width: 76px; flex-shrink: 0; color: var(--muted); font-size: 12px; }.list-row > .drag-grip, .list-row > input { position: absolute; opacity: 0; }.list-row > .drag-grip { left: 3px; }.list-row > input { left: 28px; width: 13px; height: 13px; }.list-row:hover > :is(.drag-grip,input), .list-row:focus-within > :is(.drag-grip,input), .list-row > input:checked { opacity: 1; }
.assignee-chip { position: relative; width: 22px; min-width: 22px; padding: 1px; justify-content: center; }.assignee-chip select { position: absolute; inset: 0; opacity: 0; width: 100%; max-width: none; height: 100%; cursor: pointer; }.assignee-chip:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }.card-properties .status-chip { max-width: 148px; }.card-properties .priority-chip { max-width: 96px; }.property-chip select { text-overflow: ellipsis; }.column-new-task { padding: 5px 8px 10px; }
@media(hover: none) { .card-topline > :is(.drag-grip,input), .list-row > :is(.drag-grip,input) { opacity: 1; } }
@media(max-width: 600px) { .board-header { padding: 14px 16px 0; } .selection-toolbar { padding: 9px 16px; } .board-columns { padding: 14px 10px; } .board-column { width: 264px; } }
</style>
