const DAY = 86400000
export const dateOnly = value => String(value || '').slice(0, 10)
export const dayNumber = value => Date.parse(`${dateOnly(value)}T00:00:00Z`) / DAY
export const shiftDate = (date, delta) => new Date((dayNumber(date) + delta) * DAY).toISOString().slice(0, 10)
export function timelineRange(month, zoom) {
  const start = `${month}-01`
  const end = new Date(`${start}T00:00:00Z`)
  end.setUTCMonth(end.getUTCMonth() + (zoom === 'quarter' ? 3 : 1))
  const count = Math.round((end.getTime() / DAY) - dayNumber(start))
  return Array.from({ length: count }, (_, i) => shiftDate(start, i))
}
export function taskBounds(task, days) {
  if (!task.exp_end_date || !days.length) return null
  const start = dayNumber(task.exp_start_date || task.exp_end_date) - dayNumber(days[0])
  const end = dayNumber(task.exp_end_date) - dayNumber(days[0])
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < 0 || start >= days.length) return null
  return { start: Math.max(0, start), end: Math.min(days.length - 1, end) }
}
export function resizeDate(task, field, delta) {
  const value = shiftDate(task[field] || task.exp_end_date, delta)
  if (field === 'exp_start_date' && value > dateOnly(task.exp_end_date)) return dateOnly(task.exp_end_date)
  if (field === 'exp_end_date' && task.exp_start_date && value < dateOnly(task.exp_start_date)) return dateOnly(task.exp_start_date)
  return value
}

// Row coordinates include group headings and every occurrence of multi-valued tasks.
export function timelineRows(tasks, groups = []) {
  const sections = groups.length ? groups : [{ name: '', tasks }]
  return sections.flatMap((group, groupIndex) => [
    ...(group.name ? [{ key: `group:${groupIndex}`, type: 'group', group: groupIndex, name: group.name, count: group.tasks.length }] : []),
    ...group.tasks.map(task => ({ key: `task:${groupIndex}:${task.name}`, type: 'task', group: groupIndex, task })),
  ])
}
export function timelineDependencyPairs(rows, dependencies) {
  return dependencies.flatMap(link => {
    const prerequisites = rows.map((row, index) => ({ ...row, index })).filter(row => row.task?.name === link.target_task)
    const dependents = rows.map((row, index) => ({ ...row, index })).filter(row => row.task?.name === link.source_task)
    return dependents.flatMap(to => {
      const from = prerequisites.find(row => row.group === to.group) || prerequisites[0]
      return from ? [{ from, to }] : []
    })
  })
}
