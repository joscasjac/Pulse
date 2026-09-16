// Exercise component save handlers against mocked transport, without a browser or database.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const { parse, compileScript } = require('../frontend/node_modules/@vue/compiler-sfc')
const { ref, reactive, computed } = require('../frontend/node_modules/vue')
function setup(file, props, call, extra = {}) {
  const { descriptor } = parse(fs.readFileSync(require('node:path').join(__dirname, '../frontend/src', file), 'utf8'))
  const code = compileScript(descriptor, { id: file }).content.replace(/^import .*$/gm, '').replace('export default', 'component =')
  const context = { component: null, ref, reactive, computed, useRoute: () => ({ query: {}, path: '/board' }), useRouter: () => ({ replace: async () => {}, resolve: () => ({ href: '/pulse/board' }) }), Maximize2: {}, Minimize2: {}, watch() {}, nextTick() {}, onBeforeUnmount() {}, call, toast: { success() {}, error() {} }, PersonalControls: {}, TaskModules: {}, TextEditor: {}, StatusPill: {}, TaskTime: {}, X: {}, Paperclip: {}, Avatar: {}, SquarePen: {}, Check: {}, createState: { open: false, defaults: {} }, closeCreate() {}, markCreated() {}, ...extra }
  vm.createContext(context); vm.runInContext(code, context)
  return context.component.setup(props, { expose() {}, emit() {} })
}
async function main() {
  const calls = []
  const drawer = setup('components/TaskDrawer.vue', { taskId: 'TASK-1' }, async (method, args) => {
    calls.push({ method, args })
    if (method.endsWith('update_task_state')) return { workflow_state: args.state, status: 'Working' }
    if (method.endsWith('activity')) return []
    return {}
  })
  drawer.task.value = { name: 'TASK-1', workflow_state: 'Backlog', description: '' }
  await drawer.save('workflow_state', 'In Progress')
  assert.equal(calls[0].method, 'pulse.api.spa.update_task_state')
  assert.equal(calls[0].args.state, 'In Progress')
  assert.equal(drawer.task.value.status, 'Working')
  calls.length = 0
  await drawer.save('expected_time', 4)
  assert.equal(calls[0].method, 'pulse.api.tasks.bulk_update')
  assert.equal(calls[0].args.fields.expected_time, 4)
  calls.length = 0
  drawer.descriptionDraft.value = '<p>New description</p>'
  await drawer.saveDescription()
  assert.equal(calls[0].args.fields.description, '<p>New description</p>')
  assert.equal(drawer.task.value.description, '<p>New description</p>')
  const modal = setup('components/CreateIssueModal.vue', {}, async () => { throw { messages: ['Session expired'] } })
  await modal.ensureData()
  assert.equal(modal.dataError.value, 'Session expired')
  assert.equal(modal.dataLoading.value, false)
  assert.equal(Boolean(modal.canSubmit.value), false)
  console.log('PASS task status/native response, explicit field and description payloads, recoverable project load failure')
}
main().catch(error => { console.error(error); process.exitCode = 1 })
