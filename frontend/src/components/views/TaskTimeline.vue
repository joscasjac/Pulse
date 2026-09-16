<template>
  <section ref="root" class="task-timeline" :class="{ expanded }" aria-label="Task timeline">
    <div class="timeline-toolbar">
      <div class="period-navigation"><button aria-label="Previous period" @click="navigate(-1)">‹</button><button aria-label="Next period" @click="navigate(1)">›</button><span>{{ months[0]?.label }}</span></div><span class="text-muted">{{ tasks.length }} tasks</span><slot name="actions" />
      <div class="zoom-options" aria-label="Timeline scale"><button v-for="option in ['week', 'month', 'quarter']" :key="option" :aria-pressed="zoom === option" @click="zoom = option">{{ option[0].toUpperCase() + option.slice(1) }}</button></div>
      <button @click="today">Today</button>
      <button :aria-label="expanded ? 'Exit expanded timeline' : 'Expand timeline'" :aria-pressed="expanded" @click="expanded = !expanded"><svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 7V3h4M13 3h4v4M17 13v4h-4M7 17H3v-4" /></svg></button>
    </div>
    <div ref="scroller" class="timeline-viewport" @scroll="hidePreview">
      <div class="timeline-canvas" :style="{ width: `${leftWidth + days.length * cellWidth}px`, '--day-width': `${cellWidth}px` }">
        <header class="timeline-heading"><div class="task-heading">Tasks <span>Duration</span></div><div class="date-heading"><div class="month-labels"><span v-for="segment in headingSegments" :key="segment.label" :style="{ width: `${segment.count * cellWidth}px` }">{{ segment.label }}</span></div><div class="day-labels"><time v-for="day in days" :key="day" :class="{ current: day === todayDate }" :datetime="day"><span>{{ weekday(day) }}</span><b>{{ Number(day.slice(-2)) }}</b></time></div></div></header>
        <div class="timeline-body" :style="{ minHeight: `${Math.max((rows.length + 1) * rowHeight + (creating ? 190 : 0), 240)}px` }">
          <div v-if="todayOffset >= 0" class="today-column" :style="{ left: `${leftWidth + todayOffset * cellWidth}px`, width: `${cellWidth}px` }" />
          <template v-for="row in rows" :key="row.key">
          <div v-if="row.type === 'group'" class="timeline-row timeline-group-row"><div class="task-label group-label"><span>{{ row.name }}</span><span class="group-count">{{ row.count }}</span></div><div class="group-track" /></div>
          <div v-else class="timeline-row">
            <button class="task-label" @click="emit('open', row.task.name)"><span class="task-key">{{ row.task.issue_key || row.task.name }}</span><span class="task-subject">{{ row.task.subject }}</span><span class="duration">{{ duration(row.task) }}</span></button>
            <div class="timeline-track" @dragover.prevent="dragOver($event, row.key)" @dragleave="dropTarget = null" @drop.prevent="drop($event)" :class="{ 'drop-active': dropTarget?.row === row.key }">
              <div class="date-create-cells" :class="{ 'interaction-active': dragged || resizePreview }">
                <span v-for="(day, index) in days" :key="day" class="date-create-cell">
                  <button v-if="!occupies(row.task, index) && writable(row.task)" class="date-create-button" type="button" :aria-label="`Schedule ${row.task.subject} on ${dateLabel(day)}`" :title="`Schedule task on ${dateLabel(day)}`" @click.stop="emit('schedule', row.task, day)">+</button>
                </span>
              </div>
              <div v-if="bounds(row.task)" class="task-bar" :style="barStyle(row.task)" :aria-describedby="hoverTask?.name === row.task.name ? previewId : undefined" @mouseenter="showPreview($event, row.task)" @mouseleave="hidePreview" @focusin="showPreview($event, row.task)" @focusout="blurPreview" :draggable="false" @dragstart="startDrag($event, row.task)" @dragend="dragged = null; dropTarget = null" @dblclick="emit('open', row.task.name)">
                <button class="resize-handle" :disabled="!writable(row.task)" :aria-label="`Resize start of ${row.task.subject}; arrow keys change by one day`" @pointerdown.stop.prevent="startResize($event, row.task, 'exp_start_date')" @keydown.left.prevent="nudge(row.task, 'exp_start_date', -1)" @keydown.right.prevent="nudge(row.task, 'exp_start_date', 1)" />
                <button class="bar-label" @pointerdown="startMove($event, row.task)" @click="openBar($event, row.task)" @keydown.left.prevent="moveBy(row.task, -1)" @keydown.right.prevent="moveBy(row.task, 1)">{{ row.task.subject }}</button>
                <button class="resize-handle" :disabled="!writable(row.task)" :aria-label="`Resize end of ${row.task.subject}; arrow keys change by one day`" @pointerdown.stop.prevent="startResize($event, row.task, 'exp_end_date')" @keydown.left.prevent="nudge(row.task, 'exp_end_date', -1)" @keydown.right.prevent="nudge(row.task, 'exp_end_date', 1)" />
              </div>
              <span v-else class="unscheduled">{{ row.task.exp_end_date ? 'Outside this period' : 'No dates set' }}</span>
              <span v-if="dropTarget?.row === row.key" class="drop-marker" :style="{ left: `${dropTarget.index * cellWidth}px` }">{{ dropTarget.date }}</span>
            </div>
          </div>
          </template>
          <svg class="dependency-lines" :style="{ left: `${leftWidth}px` }" :width="days.length * cellWidth" :height="rows.length * rowHeight" aria-label="Task dependency links"><defs><marker :id="markerId" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor" /></marker></defs><path v-for="(path, i) in paths" :key="i" :d="path" :marker-end="`url(#${markerId})`" fill="none" stroke="currentColor" stroke-width="1.4" /></svg>
          <div class="timeline-row create-task-row">
            <span class="task-label create-row-label">+ Add task on a date</span>
            <div class="timeline-track date-create-cells create-row-cells">
              <span v-for="day in days" :key="day" class="date-create-cell"><button class="date-create-button" type="button" :aria-label="`Add task on ${dateLabel(day)}`" :title="`Add task on ${dateLabel(day)}`" @click="beginCreate(day)">+</button></span>
            </div>
          </div>
          <div v-if="creating" ref="inlineEditor" class="timeline-inline-create" :style="inlineCreateStyle">
            <div class="inline-create-date">{{ dateLabel(creating.date) }}</div>
            <InlineTaskCreate :key="`${creating.date}:${creating.row || 'new'}`" :create-task="createTask" :project="project" :projects="projects" :date="creating.date" @cancel="creating = null" @created="revealInlineEditor" />
          </div>
          <p v-if="!tasks.length" class="empty">No tasks match this view. Choose a date above to add one.</p>
        </div>
      </div>
    </div>
    <Teleport to="body">
      <div v-if="hoverTask && !dragged && !resizePreview" :id="previewId" role="tooltip" class="timeline-preview" :style="previewStyle">
        <div class="preview-heading"><span>{{ hoverTask.issue_key || hoverTask.name }}</span><span class="preview-status"><span class="preview-status-icon" :class="statusClass(hoverTask)" aria-hidden="true">{{ statusGlyph(hoverTask) }}</span>{{ hoverTask.workflow_state || hoverTask.status || 'To Do' }}</span></div>
        <div class="preview-title">{{ hoverTask.subject }}</div>
        <div class="preview-footer"><span class="preview-priority" :class="`priority-${String(hoverTask.priority || '').toLowerCase()}`" :title="hoverTask.priority || 'No priority'" :aria-label="hoverTask.priority || 'No priority'">{{ priorityGlyph(hoverTask.priority) }}</span><span>{{ previewDates(hoverTask) }}</span></div>
      </div>
    </Teleport>
    <p class="timeline-hint">Drag a bar to move its dates. Drag either edge to resize, or focus an edge and use the arrow keys.</p>
  </section>
</template>
<script setup>
import { computed, nextTick, onBeforeUnmount, ref, useId } from 'vue'
import InlineTaskCreate from './InlineTaskCreate.vue'
import { dateOnly, dayNumber, shiftDate, timelineRange, taskBounds, resizeDate, timelineRows, timelineDependencyPairs } from './timelineMath.js'
const props = defineProps({ groups: { type: Array, default: () => [] }, createTask: { type: Function, required: true }, project: { type: String, default: null }, projects: { type: Array, default: () => [] }, tasks: { type: Array, default: () => [] }, dependencies: { type: Array, default: () => [] }, month: { type: String, required: true }, pending: { type: Set, default: () => new Set() } })
const emit = defineEmits(['open', 'reschedule', 'schedule', 'edit', 'period-change'])
const zoom = ref('month'), expanded = ref(false), scroller = ref(null), root = ref(null), dragged = ref(null), dropTarget = ref(null), resizePreview = ref(null)
const rows = computed(() => timelineRows(props.tasks, props.groups))
const creating = ref(null), inlineEditor = ref(null)
const hoverTask = ref(null), previewPosition = ref({left: 0, top: 0})
const previewId = `timeline-preview-${useId()}`
const previewStyle = computed(() => ({ left: `${previewPosition.value.left}px`, top: `${previewPosition.value.top}px`, width: `${previewPosition.value.width || 300}px` }))
function showPreview(event, task) {
  if (dragged.value || resizePreview.value) return
  const bar = event.currentTarget.getBoundingClientRect(), width = Math.min(300, window.innerWidth - 24), height = 148
  previewPosition.value = { width, left: Math.max(12, Math.min(bar.left, window.innerWidth - width - 12)), top: bar.bottom + height + 12 <= window.innerHeight ? bar.bottom + 10 : Math.max(12, bar.top - height - 10) }
  hoverTask.value = task
}
function hidePreview() { hoverTask.value = null }
function blurPreview(event) { if (!event.currentTarget.contains(event.relatedTarget)) hidePreview() }
function statusClass(task) { const state = `${task.workflow_state || ''} ${task.status || ''}`.toLowerCase(); return /done|completed/.test(state) ? 'status-done' : /progress|working|review/.test(state) ? 'status-active' : /backlog/.test(state) ? 'status-backlog' : 'status-open' }
function statusGlyph(task) { return statusClass(task) === 'status-done' ? '✓' : statusClass(task) === 'status-active' ? '◉' : '○' }
function priorityGlyph(priority) { return ({Urgent:'!',High:'▂▅▇',Medium:'▂▅',Low:'▂'})[priority] || '⊘' }
function previewDates(task) { const format = value => new Date(`${String(value).slice(0,10)}T00:00:00Z`).toLocaleDateString(undefined,{month:'short',day:'numeric',timeZone:'UTC'}); if (!task.exp_end_date) return 'No dates'; const end = format(task.exp_end_date); return task.exp_start_date ? `${format(task.exp_start_date)} – ${end}` : end }
const inlineCreateStyle = computed(() => { if (!creating.value) return {}; const index = Math.max(0, days.value.indexOf(creating.value.date)); const row = rows.value.findIndex(row => row.key === creating.value.row); return { left: `${leftWidth + Math.max(0, Math.min(index * cellWidth.value, days.value.length * cellWidth.value - 320))}px`, top: `${(row < 0 ? rows.value.length : row) * rowHeight + 8}px` } })
async function revealInlineEditor() {
  await nextTick()
  const viewport = scroller.value, editor = inlineEditor.value
  if (!viewport || !editor) return
  const area = viewport.getBoundingClientRect(), box = editor.getBoundingClientRect(), margin = 12
  // Scroll only this pane; browser scrollIntoView may move the whole workspace.
  if (box.right > area.right - margin) viewport.scrollLeft += box.right - area.right + margin
  else if (box.left < area.left + leftWidth + margin && area.width > leftWidth + box.width + margin * 2) viewport.scrollLeft -= area.left + leftWidth + margin - box.left
  if (box.bottom > area.bottom - margin) viewport.scrollTop += box.bottom - area.bottom + margin
  else if (box.top < area.top + 66 + margin) viewport.scrollTop -= area.top + 66 + margin - box.top
}
async function beginCreate(date, row = null) { creating.value = { date, row }; await revealInlineEditor() }
const markerId = `timeline-arrow-${useId()}`
const leftWidth = 360, rowHeight = 54
const cellWidth = computed(() => zoom.value === 'week' ? 100 : zoom.value === 'quarter' ? 24 : 42)
const days = computed(() => timelineRange(props.month, zoom.value))
const todayDate = (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` })()
const todayOffset = computed(() => days.value.indexOf(todayDate))
const months = computed(() => { const result = []; for (const day of days.value) { const label = new Date(`${day}T00:00:00Z`).toLocaleDateString(undefined, { month: 'long', year: 'numeric', timeZone: 'UTC' }); if (result.at(-1)?.label === label) result.at(-1).count++; else result.push({ label, count: 1 }) } return result })
const headingSegments = computed(() => { if (zoom.value !== 'week') return months.value; const result = []; for (const day of days.value) { const d = new Date(`${day}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7)); const first = new Date(Date.UTC(d.getUTCFullYear(), 0, 1)); const week = Math.ceil((((d - first) / 86400000) + 1) / 7); const label = `Week ${week}`; if (result.at(-1)?.label === label) result.at(-1).count++; else result.push({label, count: 1}) } return result })
const weekday = day => new Date(`${day}T00:00:00Z`).toLocaleDateString(undefined, { weekday: 'narrow', timeZone: 'UTC' })
const writable = task => task.can_write && !props.pending.has(task.name)
const movePreview = ref(null)
const renderedTask = task => movePreview.value?.name === task.name ? { ...task, exp_start_date: shiftDate(task.exp_start_date || task.exp_end_date, movePreview.value.delta), exp_end_date: shiftDate(task.exp_end_date, movePreview.value.delta) } : resizePreview.value?.name === task.name ? { ...task, [resizePreview.value.field]: resizePreview.value.value } : task
const bounds = task => taskBounds(renderedTask(task), days.value)
const occupies = (task, index) => { const b = bounds(task); return b && index >= b.start && index <= b.end }
const dateLabel = day => new Date(`${day}T00:00:00Z`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
const duration = task => task.exp_start_date && task.exp_end_date ? `${dayNumber(task.exp_end_date) - dayNumber(task.exp_start_date) + 1}d` : '—'
const barStyle = task => { const b = bounds(task); return { left: `${b.start * cellWidth.value + 2}px`, width: `${(b.end - b.start + 1) * cellWidth.value - 4}px` } }
const paths = computed(() => timelineDependencyPairs(rows.value, props.dependencies).flatMap(({ from, to }) => { const a = bounds(from.task), b = bounds(to.task); if (!a || !b) return []; const x = (a.end + 1) * cellWidth.value, y = b.start * cellWidth.value; return [`M${x} ${from.index * rowHeight + rowHeight / 2} H${x + 10} V${to.index * rowHeight + rowHeight / 2} H${y}`] }))
function navigate(direction) { const date = new Date(`${props.month}-01T00:00:00Z`); date.setUTCMonth(date.getUTCMonth() + direction * (zoom.value === 'quarter' ? 3 : 1)); emit('period-change', date.toISOString().slice(0, 7)) }
async function today() { emit('period-change', todayDate.slice(0, 7)); await nextTick(); if (scroller.value) scroller.value.scrollLeft = Math.max(0, todayOffset.value * cellWidth.value - 100) }
function startDrag(event, task) { hidePreview(); if (!writable(task) || event.target.closest('.resize-handle')) { event.preventDefault(); return } dragged.value = task; event.dataTransfer.setData('text/plain', task.name); event.dataTransfer.effectAllowed = 'move'; dragged.value = { ...task, grabOffset: Math.max(0, Math.floor((event.clientX - event.currentTarget.getBoundingClientRect().left) / cellWidth.value)) + Math.max(0, dayNumber(days.value[0]) - dayNumber(task.exp_start_date || task.exp_end_date)) } }
function dragOver(event, row) { if (!dragged.value) return; const rect = event.currentTarget.getBoundingClientRect(); const index = Math.max(0, Math.min(days.value.length - 1, Math.floor((event.clientX - rect.left) / cellWidth.value))); dropTarget.value = { row, index, date: days.value[index] } }
function drop() { if (!dragged.value || !dropTarget.value) return; const task = dragged.value; const delta = dayNumber(dropTarget.value.date) - dayNumber(task.exp_start_date || task.exp_end_date) - task.grabOffset; emit('reschedule', task.name, shiftDate(task.exp_end_date, delta)); dragged.value = null; dropTarget.value = null }
function nudge(task, field, delta) { if (writable(task)) emit('edit', task, field, resizeDate(task, field, delta)) }
let cleanupMove, suppressClick = false
function openBar(event, task) { if (suppressClick) { suppressClick = false; event.preventDefault(); return } emit('open', task.name) }
function moveBy(task, delta) { if(writable(task) && delta) emit('reschedule', task.name, shiftDate(task.exp_end_date, delta)) }
function startMove(event, task) {
  if (event.button !== 0 || !writable(task)) return
  hidePreview(); cleanupMove?.(); suppressClick = false
  const initial = event.clientX, initialScroll = scroller.value?.scrollLeft || 0
  let delta = 0, moved = false
  const move = e => { const distance = e.clientX - initial + (scroller.value?.scrollLeft || 0) - initialScroll; if(Math.abs(distance) < 4 && !moved)return; moved = true; delta = Math.round(distance / cellWidth.value); movePreview.value = {name:task.name,delta} }
  const cancel = () => { window.removeEventListener('pointermove', move);window.removeEventListener('pointerup',finish);window.removeEventListener('pointercancel',cancel);movePreview.value=null }
  const finish = () => { suppressClick = moved;cancel();moveBy(task,delta) }
  cleanupMove = cancel;window.addEventListener('pointermove',move);window.addEventListener('pointerup',finish);window.addEventListener('pointercancel',cancel)
}
let cleanupResize
function startResize(event, task, field) { hidePreview(); if (!writable(task)) return; cleanupResize?.(); const initial = event.clientX; const move = e => { resizePreview.value = { name: task.name, field, value: resizeDate(task, field, Math.round((e.clientX - initial) / cellWidth.value)) } }; const cancel = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', finish); window.removeEventListener('pointercancel', cancel); resizePreview.value = null }; const finish = e => { const delta = Math.round((e.clientX - initial) / cellWidth.value); cancel(); if (delta) nudge(task, field, delta) }; cleanupResize = cancel; window.addEventListener('pointermove', move); window.addEventListener('pointerup', finish); window.addEventListener('pointercancel', cancel) }
onBeforeUnmount(() => { cleanupResize?.(); cleanupMove?.() })
</script>
<style scoped>
.task-timeline{display:flex;flex-direction:column;min-height:360px;height:100%;min-width:0;overflow:hidden;background:var(--surface)}.task-timeline.expanded{position:fixed;inset:12px;z-index:1000;border:1px solid var(--border);border-radius:10px;box-shadow:0 12px 60px #0003}.timeline-toolbar{display:flex;justify-content:flex-end;align-items:center;gap:12px;min-height:48px;padding:6px 16px;border-bottom:1px solid var(--border);flex-shrink:0;font-size:13px}.timeline-toolbar button{padding:5px 9px;border-radius:5px;color:var(--text)}.period-navigation{display:flex;align-items:center;gap:4px;margin-right:auto}.zoom-options{display:flex;gap:4px}.zoom-options button[aria-pressed=true]{background:var(--surface-2);font-weight:600}.timeline-viewport{flex:1;min-height:0;overflow:auto;overscroll-behavior:contain}.timeline-heading{display:flex;height:66px;position:sticky;top:0;z-index:8;background:var(--surface);border-bottom:1px solid var(--border)}.task-heading{width:360px;flex-shrink:0;position:sticky;left:0;z-index:9;background:var(--surface);border-right:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 16px;font-size:13px;font-weight:600}.task-heading span{font-weight:400;color:var(--text-muted)}.date-heading{flex:1}.month-labels{display:flex;height:32px;align-items:center;font-size:13px}.month-labels span{padding-left:8px;border-right:1px solid var(--border);flex-shrink:0}.day-labels{display:flex;height:34px}.day-labels time{width:var(--day-width);flex-shrink:0;border-right:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;padding:0 4px;font-size:11px;color:var(--text-muted)}.day-labels b{font-weight:500;color:var(--text)}.day-labels .current{background:color-mix(in srgb,var(--accent) 15%,transparent)}.day-labels .current b{background:var(--accent);color:white;border-radius:4px;padding:2px}.timeline-body{position:relative;background:repeating-linear-gradient(to right,transparent 0,transparent calc(var(--day-width) - 1px),var(--border) calc(var(--day-width) - 1px),var(--border) var(--day-width));background-position:360px 0}.timeline-row{display:flex;height:54px;border-bottom:1px solid color-mix(in srgb,var(--border) 45%,transparent)}.task-label{position:sticky;left:0;z-index:5;background:var(--surface);border-right:1px solid var(--border);width:360px;flex-shrink:0;display:flex;gap:9px;align-items:center;text-align:left;padding:0 16px;font-size:13px}.task-label:hover{background:var(--surface-2)}.task-key{color:var(--text-muted);font-size:11px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.task-subject{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}.duration{font-size:11px;color:var(--text-muted)}.timeline-track{position:relative;flex:1}.task-bar{position:absolute;top:12px;height:30px;display:flex;align-items:center;border-radius:5px;background:var(--accent);color:var(--on-accent);z-index:3;cursor:grab}.bar-label{font-size:11px;text-overflow:ellipsis;white-space:nowrap;overflow:hidden;flex:1;text-align:left;cursor:grab}.resize-handle{height:100%;width:8px;flex-shrink:0;cursor:ew-resize;touch-action:none}.resize-handle:hover,.resize-handle:focus-visible{background:#ffffff55}.unscheduled{position:sticky;left:375px;font-size:11px;color:var(--text-muted);line-height:54px;margin-left:12px}.today-column{position:absolute;inset-block:0;background:color-mix(in srgb,var(--accent) 9%,transparent);pointer-events:none}.dependency-lines{position:absolute;top:0;pointer-events:none;z-index:4;color:var(--text-muted)}.drop-active{background:color-mix(in srgb,var(--accent) 5%,transparent)}.drop-marker{position:absolute;top:0;height:100%;border-left:2px solid var(--accent);font-size:10px;color:var(--accent);padding:2px;z-index:6;background:var(--surface)}.timeline-hint{font-size:11px;color:var(--text-muted);padding:7px 16px;border-top:1px solid var(--border);margin:0}.empty{padding:24px;color:var(--text-muted);font-size:13px}@media(max-width:640px){.timeline-toolbar{gap:4px;padding-inline:6px}.timeline-toolbar>span{display:none}.timeline-hint{display:none}}

.date-create-cells{position:absolute;inset:0;display:flex}.date-create-cell{width:var(--day-width);height:100%;flex-shrink:0;display:flex;align-items:center;justify-content:center}.date-create-button{display:flex;align-items:center;justify-content:center;width:min(30px, calc(var(--day-width) - 4px));height:30px;border:1px solid var(--border);border-radius:5px;background:var(--surface);color:var(--text-muted);font-size:19px;line-height:1;opacity:0;cursor:pointer}.date-create-cell:hover .date-create-button,.date-create-button:focus-visible{opacity:1;color:var(--accent);border-color:var(--accent)}.date-create-button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}.interaction-active{pointer-events:none}.interaction-active .date-create-button{opacity:0}.unscheduled{pointer-events:none}.create-row-label{color:var(--text-muted);font-size:12px}.create-row-cells{position:relative;inset:auto}.create-row-cells .date-create-button{opacity:1;background:transparent;border-color:transparent}.create-row-cells .date-create-button:hover,.create-row-cells .date-create-button:focus-visible{border-color:var(--accent);background:var(--surface-2)}@media(hover:none){.date-create-button{opacity:1}}

.timeline-inline-create{position:absolute;width:320px;z-index:10;background:var(--surface);border:1px solid var(--border);border-radius:7px;box-shadow:0 4px 16px #00000012;padding:8px}.inline-create-date{font-size:11px;color:var(--text-muted);padding:2px 4px 7px}
.timeline-group-row{background:var(--surface-2)}.timeline-group-row .group-label{background:var(--surface-2);font-weight:600;justify-content:space-between}.group-count{font-size:11px;font-weight:400;color:var(--text-muted)}.group-track{flex:1;background:var(--surface-2)}

.task-bar{background:var(--surface-2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding-inline:9px;overflow:visible}.task-bar:hover,.task-bar:focus-within{border-color:var(--accent)}.bar-label{min-width:0}.resize-handle{position:absolute;top:50%;transform:translateY(-50%);width:10px;height:10px;border-radius:50%;border:2px solid var(--surface);background:var(--accent);opacity:0;z-index:2}.resize-handle:first-child{left:-5px}.resize-handle:last-child{right:-5px}.task-bar:hover .resize-handle,.task-bar:focus-within .resize-handle{opacity:1}.resize-handle:disabled{visibility:hidden}.resize-handle:hover,.resize-handle:focus-visible{background:var(--accent);box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 25%,transparent)}
.timeline-preview{position:fixed;z-index:1500;pointer-events:none;padding:14px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:9px;box-shadow:0 6px 24px #00000014;box-sizing:border-box}.preview-heading{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:11px;color:var(--text-muted)}.preview-heading>span:first-child{max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.preview-status{display:flex;align-items:center;gap:5px;white-space:nowrap;max-width:145px;overflow:hidden;text-overflow:ellipsis}.preview-status-icon{font-size:15px}.status-done{color:#16944d}.status-active{color:#d68a00}.status-backlog{color:var(--text-muted)}.preview-title{font-size:13px;font-weight:500;margin:12px 0 16px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}.preview-footer{display:flex;align-items:center;gap:9px;font-size:11px;color:var(--text-muted)}.preview-priority{font-size:13px;min-width:17px}.priority-high{color:#df7c14}.priority-medium{color:#b98218}.priority-low{color:var(--accent)}.priority-urgent{color:var(--danger);font-weight:700}@media(hover:none){.task-bar .resize-handle{opacity:1}}
.bar-label{touch-action:none;user-select:none}
</style>
