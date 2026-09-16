import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import { test } from 'node:test'

// Exercise the actual view handlers with a delayed transport, including failures.
const source = readFileSync(new URL('../src/pages/Views.vue', import.meta.url), 'utf8')
const move = source.slice(source.indexOf('async function rescheduleTask('), source.indexOf('\nwatch(month,'))
const edit = source.slice(source.indexOf('async function edit(task,'), source.indexOf('\nfunction toggleColumn'))
function harness() {
  const task = { name: 'TASK-QA', can_write: true, exp_start_date: '2026-09-09', exp_end_date: '2026-09-12' }
  const pending = { value: new Set() }, error = { value: '' }, optimistic = new Set(), requests = [], loads = []
  const call = (method, args) => new Promise((resolve, reject) => requests.push({ method, args, resolve, reject }))
  const handlers = new Function('tasks', 'pending', 'error', 'optimisticDateTasks', 'call', 'load', 'dateValue', `let version = 0; const notice = {value:''}; ${move}; ${edit}; return {rescheduleTask, edit}`)(
    {value:[task]}, pending, error, optimistic, call, async options => loads.push(options), value => String(value).slice(0,10))
  return { task, pending, error, optimistic, requests, loads, ...handlers }
}
test('moving keeps new dates throughout a delayed save and preserves duration', async () => {
  const h = harness(), saving = h.rescheduleTask('TASK-QA', '2026-09-14')
  assert.equal(h.task.exp_start_date, '2026-09-11')
  assert.equal(h.task.exp_end_date, '2026-09-14')
  assert.ok(h.optimistic.has(h.task.name))
  assert.equal(h.loads.length, 0)
  await h.rescheduleTask('TASK-QA', '2026-09-20')
  assert.equal(h.requests.length, 1)
  h.requests[0].resolve(); await saving
  assert.equal(h.task.exp_end_date, '2026-09-14')
  assert.deepEqual(h.loads, [{background:true}])
  assert.equal(h.optimistic.size, 0)
})
test('resizing stays extended while pending and restores dates if rejected', async () => {
  const h = harness(), saving = h.edit(h.task, 'exp_end_date', '2026-09-18')
  assert.equal(h.task.exp_end_date, '2026-09-18')
  assert.deepEqual(h.requests[0].args.fields, {exp_end_date:'2026-09-18'})
  h.requests[0].reject(Error('Write access revoked')); await saving
  assert.equal(h.task.exp_end_date, '2026-09-12')
  assert.equal(h.task.exp_start_date, '2026-09-09')
  assert.equal(h.error.value, 'Write access revoked')
  assert.equal(h.pending.value.size, 0)
})
test('failed moves restore both dates, and read-only tasks do not mutate', async () => {
  const h = harness(), saving = h.rescheduleTask('TASK-QA', '2026-10-02')
  h.requests[0].reject(Error('Offline')); await saving
  assert.equal(h.task.exp_start_date, '2026-09-09')
  assert.equal(h.task.exp_end_date, '2026-09-12')
  h.task.can_write = false
  await h.rescheduleTask('TASK-QA','2026-10-02')
  await h.edit(h.task,'exp_end_date','2026-10-02')
  assert.equal(h.requests.length,1)
})
