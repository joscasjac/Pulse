/** Show the drop immediately; restore the original rows if persistence rejects it. */
export async function moveTaskToGroup(columns, taskName, state, persist, beforeName = null) {
  const source = columns.find(column => column.tasks.some(task => task.name === taskName))
  const target = columns.find(column => column.name === state)
  if (!source || !target || beforeName === taskName) return false
  const task = source.tasks.find(task => task.name === taskName)
  const rows = target.tasks.filter(row => row.name !== taskName)
  const index = beforeName ? rows.findIndex(row => row.name === beforeName) : rows.length
  if (index < 0) return false
  const before = rows.slice(index).find(row => row.project === task.project)?.name || null
  const after = rows.slice(0, index).reverse().find(row => row.project === task.project)?.name || null
  if (source === target && source.tasks.indexOf(task) === index) return false
  const originalIndex = source.tasks.indexOf(task)
  source.tasks.splice(originalIndex, 1)
  target.tasks.splice(index, 0, { ...task, workflow_state: state })
  try {
    await persist(taskName, state, before, after)
  } catch (error) {
    target.tasks.splice(target.tasks.findIndex(row => row.name === taskName), 1)
    source.tasks.splice(originalIndex, 0, task)
    throw error
  }
  return true
}

/** Track a grip gesture independently of browser HTML5 drag initiation. */
export function trackGripDrag(event, { onMove, onDrop, onCancel, eventTarget = window, hitTest = (x, y) => document.elementFromPoint(x, y) }) {
  const pointerId = event.pointerId
  const origin = { x: event.clientX, y: event.clientY }
  let active = false
  function targetAt(e) {
    const element = hitTest(e.clientX, e.clientY)
    return { state: element?.closest('[data-drop-state]')?.dataset.dropState || null,
      before: element?.closest('[data-drop-task]')?.dataset.dropTask || null }
  }
  function move(e) {
    if (e.pointerId !== pointerId) return
    if (!active && Math.hypot(e.clientX - origin.x, e.clientY - origin.y) < 5) return
    active = true; e.preventDefault()
    onMove({ ...targetAt(e), x: e.clientX, y: e.clientY })
  }
  function cleanup() {
    eventTarget.removeEventListener('pointermove', move)
    eventTarget.removeEventListener('pointerup', finish)
    eventTarget.removeEventListener('pointercancel', cancel)
  }
  function finish(e) {
    if (e.pointerId !== pointerId) return
    cleanup()
    const target = targetAt(e)
    if (active && target.state) onDrop(target)
    else onCancel()
  }
  function cancel() { cleanup(); onCancel() }
  eventTarget.addEventListener('pointermove', move, { passive: false })
  eventTarget.addEventListener('pointerup', finish)
  eventTarget.addEventListener('pointercancel', cancel)
  return cancel
}
