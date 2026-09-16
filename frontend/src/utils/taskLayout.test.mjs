import assert from 'node:assert/strict'
import { moveTaskToGroup } from './taskLayout.js'
const columns = [{ name: 'To Do', tasks: [{ name: 'a' }, { name: 'b' }] }, { name: 'Done', tasks: [] }]
const calls = []
const persist = async (...args) => calls.push(args)
assert.equal(await moveTaskToGroup(columns, 'a', 'Done', persist), true)
assert.deepEqual(calls.pop(), ['a', 'Done', null, null])
assert.equal(columns[1].tasks[0].workflow_state, 'Done')
await moveTaskToGroup(columns, 'a', 'To Do', persist, 'b')
assert.deepEqual(calls.pop(), ['a', 'To Do', 'b', null])
await moveTaskToGroup(columns, 'b', 'To Do', persist, 'a')
assert.deepEqual(calls.pop(), ['b', 'To Do', 'a', null])
assert.deepEqual(columns[0].tasks.map(t => t.name), ['b', 'a'])
assert.equal(await moveTaskToGroup(columns, 'b', 'To Do', persist, 'b'), false)
const snapshot = JSON.stringify(columns)
await assert.rejects(moveTaskToGroup(columns, 'b', 'Done', async () => { throw Error('Forbidden') }))
assert.equal(JSON.stringify(columns), snapshot)
console.log('Task layout moves: empty group, cross-state position, same-state reorder, self-drop and permission rejection passed.')
const { trackGripDrag } = await import('./taskLayout.js')
const handlers = new Map()
const eventTarget = { addEventListener: (name, handler) => handlers.set(name, handler), removeEventListener: name => handlers.delete(name) }
const element = { closest: selector => selector === '[data-drop-state]' ? { dataset: { dropState: 'Ready' } } : { dataset: { dropTask: 'b' } } }
let pointerDrop, moves = 0
trackGripDrag({ pointerId: 7, clientX: 10, clientY: 10 }, { eventTarget, hitTest: () => element,
  onMove: () => moves++, onDrop: target => { pointerDrop = target }, onCancel: () => { throw Error('Unexpected cancel') } })
handlers.get('pointermove')({ pointerId: 7, clientX: 80, clientY: 80, preventDefault() {} })
handlers.get('pointerup')({ pointerId: 7, clientX: 80, clientY: 80 })
assert.equal(moves, 1)
assert.deepEqual(pointerDrop, { state: 'Ready', before: 'b' })
assert.equal(handlers.size, 0)
console.log('Pointer grip move/drop uses hit-tested state + row and removes all listeners.')

// A slow network must not leave the dropped card at its old position.
let finishSave
const pendingMove = moveTaskToGroup(columns, 'b', 'Done', () => new Promise(resolve => { finishSave = resolve }))
assert.equal(columns[0].tasks.some(task => task.name === 'b'), false)
assert.equal(columns[1].tasks[0].name, 'b')
finishSave()
await pendingMove
// A rejected cross-column move restores exact ordering and task properties.
const beforeReorder = JSON.stringify(columns)
await assert.rejects(moveTaskToGroup(columns, 'a', 'Done', async () => { throw Error('Offline') }, 'b'))
assert.equal(JSON.stringify(columns), beforeReorder)
console.log('Optimistic drop renders before the save resolves and rolls back rejected moves.')
