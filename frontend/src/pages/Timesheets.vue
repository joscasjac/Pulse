<template>
  <section class="timesheets-page">
    <header class="page-heading">
      <div><h1>Timesheets</h1><p>Track your work and review time entries.</p></div>
      <a class="time-control" href="/app/timesheet">Manage timesheets <span aria-hidden="true">↗</span></a>
    </header>
    <div class="time-toolbar">
      <label class="task-picker"><span>Record time</span>
        <select v-model="taskId" class="time-input"><option value="">Select an assigned task</option><option v-for="task in tasks" :key="task.name" :value="task.name">{{ task.issue_key || task.name }} · {{ task.subject }}</option></select>
      </label>
      <label class="date-filter"><span>From</span><input v-model="fromDate" class="time-input" type="date" @change="load"></label>
    </div>
    <div v-if="taskId" class="selected-task"><div class="selected-heading"><span>{{ taskId }}</span><button class="time-control" @click="taskId = ''">Close task</button></div><TaskTime :task-id="taskId" @changed="load" /></div>
    <div v-else-if="timer" class="running-timer">
      <p>{{ timer.restricted ? 'Your timer is on a task you can no longer access.' : 'A timer is running on ' + timer.task + '.' }}</p>
      <button v-if="!timer.restricted" class="time-control" @click="taskId = timer.task">View timer</button>
      <button v-else class="time-control" :disabled="busy" @click="discard">Discard timer</button>
    </div>
    <div v-if="error" role="alert" class="time-message">{{ error }} <button class="text-action" @click="load">Retry</button></div>
    <p v-if="loading" role="status" class="time-message">Loading your time…</p>
    <template v-else-if="data">
      <div class="entries-heading"><h2>Your entries</h2><p><strong>{{ hours(data.total_hours) }} h</strong> visible <span>·</span> {{ hours(data.draft_hours) }} h draft <span>·</span> {{ hours(data.submitted_hours) }} h submitted</p></div>
      <div v-if="!data.entries.length" class="time-empty"><h3>No time entries</h3><p>Select a task above to start recording time, or change the date range.</p><p>You can also record time from any task.</p></div>
      <div v-else class="entries-scroll" tabindex="0" role="region" aria-label="Your time entries">
        <table class="entries-table"><thead><tr><th scope="col">Date</th><th scope="col">Work</th><th scope="col" class="numeric">Hours</th><th scope="col">Billing</th><th scope="col">Timesheet</th></tr></thead>
          <tbody><tr v-for="entry in data.entries" :key="entry.name">
            <td class="entry-date">{{ entry.date }}</td>
            <td class="entry-work"><button v-if="entry.task" class="text-action task-link" @click="taskId = entry.task">{{ entry.task }}</button><span v-else>{{ entry.project || 'General activity' }}</span><p v-if="entry.description">{{ entry.description }}</p></td>
            <td class="numeric">{{ hours(entry.hours) }}</td><td>{{ entry.billable ? 'Billable' : 'Nonbillable' }}</td>
            <td><a class="entry-status" :href="'/app/timesheet/' + encodeURIComponent(entry.timesheet)" :aria-label="(entry.docstatus === 0 ? 'Review draft ' : 'View submitted timesheet ') + entry.timesheet"><span class="status-dot" :class="{ submitted: entry.docstatus !== 0 }" aria-hidden="true"></span>{{ entry.docstatus === 0 ? 'Draft' : 'Submitted' }} <span aria-hidden="true">↗</span></a></td>
          </tr></tbody>
        </table>
      </div>
      <p class="scope-note">Totals include only timesheets you have permission to read. New entries are saved as drafts.</p>
    </template>
  </section>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'
import TaskTime from '@/components/TaskTime.vue'
const data = ref(null), tasks = ref([]), timer = ref(null), taskId = ref(''), error = ref(''), loading = ref(false), busy = ref(false)
const fromDate = ref(''), hours = value => Number(value || 0).toFixed(2)
let request = 0
async function load() {
  const seq = ++request
  loading.value = true; error.value = ''
  try {
    const [entries, active] = await Promise.all([call('pulse.api.time.get_my_time', { from_date: fromDate.value || null }), call('pulse.api.time.get_timer')])
    if (seq === request) { data.value = entries; timer.value = active }
  } catch (e) { if (seq === request) { data.value = null; error.value = e?.messages?.[0] || 'Could not load time entries. Check your access and retry.' } }
  finally { if (seq === request) loading.value = false }
}
async function discard() {
  if (!window.confirm('Discard this timer without saving its elapsed time?')) return
  busy.value = true
  try { await call('pulse.api.time.discard_timer'); await load() }
  catch { error.value = 'Could not discard your timer. Try again.' }
  finally { busy.value = false }
}
onMounted(async () => {
  await load()
  try { tasks.value = await call('pulse.api.time.my_tasks') }
  catch { error.value = 'Assigned tasks could not load. Open a task directly to record time.' }
})
</script>
<style scoped>
.timesheets-page { padding: 24px 28px; max-width: 1280px; margin: 0 auto; }
.page-heading,.time-toolbar,.entries-heading,.running-timer,.selected-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.page-heading { margin-bottom: 24px; }.page-heading h1 { margin: 0; font-size: 22px; font-weight: 600; }.page-heading p { margin: 5px 0 0; color: var(--muted); font-size: 13px; }
.time-control { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 32px; padding: 5px 10px; border: 1px solid var(--border); border-radius: 6px; color: var(--text); background: var(--surface); font-size: 13px; white-space: nowrap; }
.time-control:hover { background: var(--surface-2); }.time-control:disabled { opacity: .5; cursor: wait; }
.time-toolbar { justify-content: flex-start; padding-bottom: 16px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }.time-toolbar label { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--muted); }.task-picker { flex: 1; min-width: 240px; }.date-filter { margin-left: auto; }
.time-input { min-width: 0; min-height: 32px; padding: 5px 9px; background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: 6px; font-size: 13px; }.task-picker select { flex: 1; max-width: 440px; }
.selected-task { padding: 16px; margin-bottom: 24px; border: 1px solid var(--border); border-radius: 8px; }.selected-heading { font-size: 13px; color: var(--muted); }.selected-task :deep(.time-section) { margin-top: 12px; }
.running-timer { padding: 12px 0; margin-bottom: 20px; border-bottom: 1px solid var(--border); font-size: 13px; }.time-message { margin: 16px 0; font-size: 13px; }
.entries-heading { margin-bottom: 12px; }.entries-heading h2 { font-size: 14px; font-weight: 600; }.entries-heading p { color: var(--muted); font-size: 12px; }.entries-heading strong { color: var(--text); font-weight: 500; }.entries-heading p span { margin: 0 5px; }
.entries-scroll { overflow-x: auto; }.entries-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }.entries-table th { color: var(--muted); font-weight: 500; background: var(--surface-2); font-size: 12px; }.entries-table th,.entries-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }.entries-table th:first-child,.entries-table td:first-child { padding-left: 10px; }.entries-table tbody tr:hover { background: var(--surface-2); }.entry-date { white-space: nowrap; color: var(--muted); }.entry-work { width: 55%; min-width: 200px; }.entry-work p { color: var(--muted); margin-top: 4px; overflow-wrap: anywhere; }.numeric { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }.text-action { color: var(--accent); }.text-action:hover { text-decoration: underline; }.task-link { color: var(--text); text-align: left; }.entry-status { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; font-size: 12px; }.entry-status:hover { text-decoration: underline; }.status-dot { width: 7px; height: 7px; border-radius: 50%; border: 1px solid var(--muted); }.status-dot.submitted { background: var(--accent); border-color: var(--accent); }
.time-empty { padding: 52px 20px; text-align: center; border-bottom: 1px solid var(--border); }.time-empty h3 { font-size: 14px; font-weight: 500; }.time-empty p { font-size: 13px; color: var(--muted); margin-top: 6px; }.scope-note { font-size: 12px; color: var(--muted); margin-top: 16px; }
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,.entries-scroll:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media(max-width: 640px) { .timesheets-page { padding: 20px 16px; }.time-toolbar label { width: 100%; }.task-picker { min-width: 0; }.task-picker select { max-width: none; }.date-filter { margin-left: 0; }.selected-task { padding: 12px; }.entries-heading { gap: 5px; } }
</style>
