<template>
  <section class="time-section" aria-label="Task time">
    <header class="time-header"><h2>Time tracking</h2><p v-if="summary" class="time-total"><strong>{{ hours(summary.actual_hours) }} h</strong> logged <span>/</span> {{ hours(summary.estimated_hours) }} h estimated</p></header>
    <p v-if="loading" class="time-message" role="status">Loading time entries…</p>
    <div v-if="error" class="time-message" role="alert"><p>{{ error }}</p><button class="time-button secondary" @click="load">Retry</button></div>
    <template v-if="summary">
      <div class="timer-actions">
        <button v-if="!timer" class="time-button" :disabled="busy" @click="operate('start_timer', { task: taskId, billable })"><span aria-hidden="true">▷</span> Start timer</button>
        <template v-else>
          <p class="timer-state"><span class="running-dot" aria-hidden="true"></span>Timer running {{ timer.restricted ? 'on a task you can no longer access' : timer.task === taskId ? 'on this task' : 'on ' + timer.task }}<small>Started {{ timer.started_at }}</small></p>
          <button class="time-button" :disabled="busy || timer.restricted" @click="operate('stop_timer', { note })">Stop &amp; save</button>
        </template>
        <button class="time-button secondary" :aria-expanded="showForm" @click="showForm = !showForm">{{ showForm ? 'Close entry' : 'Add time' }}</button>
      </div>
      <details class="time-options"><summary>Time options &amp; breakdown</summary><div class="options-content"><label><input v-model="billable" type="checkbox" :disabled="Boolean(timer)" /> Billable time</label><p>{{ hours(summary.billable_hours) }} h billable · {{ hours(summary.nonbillable_hours) }} h nonbillable · {{ hours(summary.draft_hours) }} h draft</p><p>Totals include draft and submitted entries you can access.</p><button v-if="timer" class="time-button secondary" :disabled="busy" @click="discard">Discard timer</button></div></details>
      <form v-if="showForm" class="entry-form" @submit.prevent="addTime">
        <div class="entry-fields"><label>Start time<input v-model="start" required type="datetime-local" class="time-field" /></label><label>Hours<input v-model.number="duration" required type="number" min="0.01" max="24" step="0.01" class="time-field" /></label></div>
        <label>Work description<textarea v-model="note" rows="2" class="time-field" placeholder="What did you work on?" /></label>
        <div class="form-footer"><span>Saved as a draft timesheet.</span><button class="time-button" :disabled="busy" type="submit">{{ busy ? 'Saving…' : 'Save time entry' }}</button></div>
      </form>
      <p v-if="!summary.entries.length" class="time-empty">No time recorded. Start a timer or add an entry.</p>
      <ul v-else class="time-entries"><li v-for="entry in summary.entries" :key="entry.name"><div class="entry-line"><span>{{ entry.date }}</span><strong>{{ hours(entry.hours) }} h</strong><span class="billing-label">{{ entry.billable ? 'Billable' : 'Nonbillable' }}</span><a :href="'/app/timesheet/' + encodeURIComponent(entry.timesheet)" :aria-label="'Open timesheet ' + entry.timesheet">{{ entry.docstatus === 0 ? 'Draft' : 'Submitted' }} <span aria-hidden="true">↗</span></a></div><p v-if="entry.description" class="entry-description">{{ entry.description }}</p><p class="entry-user">{{ entry.user }}</p></li></ul>
    </template>
  </section>
</template>
<script setup>
import { ref, watch } from 'vue'
import { call } from 'frappe-ui'
import { toast } from '@/ui/toast'
const props = defineProps({ taskId: { type: String, required: true } })
const emit = defineEmits(['changed'])
const summary = ref(null), timer = ref(null), error = ref(''), loading = ref(false), busy = ref(false)
const showForm = ref(false), billable = ref(false), duration = ref(1), note = ref('')
const local = new Date(Date.now() - 3600000)
const start = ref(new Date(local.getTime() - local.getTimezoneOffset() * 60000).toISOString().slice(0, 16))
const hours = value => Number(value || 0).toFixed(2)
let request = 0
async function load() {
  const seq = ++request, task = props.taskId
  loading.value = true; error.value = ''
  try {
    const [data, active] = await Promise.all([
      call('pulse.api.time.get_time_summary', { task }), call('pulse.api.time.get_timer'),
    ])
    if (seq !== request) return
    summary.value = data; timer.value = active
  } catch (e) { if (seq === request) { summary.value = null; error.value = e?.messages?.[0] || 'Could not load time. Check your access and try again.' } }
  finally { if (seq === request) loading.value = false }
}
async function operate(method, args) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    await call('pulse.api.time.' + method, args)
    toast.success(method === 'start_timer' ? 'Timer started' : method === 'discard_timer' ? 'Timer discarded' : 'Draft time saved')
    if (method === 'log_time') { showForm.value = false; note.value = '' }
    await load(); emit('changed')
  } catch (e) { error.value = e?.messages?.[0] || 'Could not save time. Check for overlapping entries and try again.' }
  finally { busy.value = false }
}
function discard() {
  if (window.confirm('Discard this timer without saving its elapsed time?')) operate('discard_timer', {})
}
function addTime() {
  return operate('log_time', { task: props.taskId, hours: duration.value,
    from_time: start.value.replace('T', ' '), note: note.value, billable: billable.value ? 1 : 0 })
}
watch(() => props.taskId, () => { summary.value = null; showForm.value = false; note.value = ''; billable.value = false; load() }, { immediate: true })
</script>

<style scoped>
.time-section { margin-top: 24px; border-top: 1px solid var(--border); padding-top: 16px; font-size: 13px; }
.time-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; }.time-header h2 { font-size: 14px; font-weight: 600; }.time-total { font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }.time-total strong { color: var(--text); font-weight: 500; }.time-total span { margin: 0 4px; color: var(--muted); }
.timer-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 16px; }.timer-state { flex: 1 1 180px; font-size: 13px; overflow-wrap: anywhere; }.timer-state small { display: block; color: var(--muted); font-size: 12px; margin-top: 3px; }.running-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--accent); margin-right: 6px; }
.time-button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 32px; padding: 5px 10px; font-size: 13px; font-weight: 500; border: 1px solid transparent; border-radius: 6px; background: var(--accent); color: var(--on-accent); white-space: nowrap; }.time-button.secondary { background: var(--surface); color: var(--text); border-color: var(--border); }.time-button:hover { filter: brightness(.97); }.time-button.secondary:hover { background: var(--surface-2); }.time-button:disabled { opacity: .5; cursor: wait; }
.time-options { margin-top: 12px; font-size: 12px; color: var(--muted); }.time-options summary { cursor: pointer; width: fit-content; padding: 3px 0; }.options-content { display: grid; gap: 8px; padding: 10px 0 2px; }.options-content label { display: flex; align-items: center; gap: 7px; color: var(--text); }.options-content button { justify-self: start; }
.entry-form { display: grid; gap: 12px; background: var(--surface-2); padding: 14px; margin-top: 16px; border-radius: 6px; }.entry-form label { display: block; font-size: 12px; color: var(--muted); }.entry-fields { display: grid; grid-template-columns: minmax(0, 2fr) minmax(80px, 1fr); gap: 12px; }.time-field { display: block; width: 100%; min-width: 0; margin-top: 5px; padding: 6px 8px; min-height: 32px; background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: 6px; font-size: 13px; }.time-field::placeholder { color: var(--muted); }.form-footer { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; align-items: center; }.form-footer span { color: var(--muted); font-size: 12px; }
.time-message { margin-top: 12px; }.time-message button { margin-top: 6px; }.time-empty { padding: 20px 0 8px; color: var(--muted); }.time-entries { margin-top: 16px; }.time-entries li { padding: 10px 0; border-top: 1px solid var(--border); }.entry-line { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }.entry-line strong { color: var(--text); font-weight: 500; margin-left: auto; }.entry-line a { color: var(--text); }.entry-line a:hover { text-decoration: underline; }.entry-description { margin-top: 5px; overflow-wrap: anywhere; }.entry-user { margin-top: 3px; font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
.time-button:focus-visible,.time-field:focus-visible,summary:focus-visible,a:focus-visible,input:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media(max-width: 480px) { .entry-fields { grid-template-columns: 1fr; }.billing-label { margin-left: 0; }.entry-line { gap: 8px; }.time-total { width: 100%; } }
</style>
