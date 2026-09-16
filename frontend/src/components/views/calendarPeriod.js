const dayMs = 86400000
export function calendarPeriodDays(month, layout = 'month', anchor = `${month}-01`) {
  const first = Date.parse(layout === 'week' ? anchor : `${month}-01`)
  if (!Number.isFinite(first)) return []
  const offset = (new Date(first).getUTCDay() + 6) % 7
  const [year, value] = month.split('-').map(Number)
  const count = layout === 'week' ? 7 : Math.ceil((new Date(Date.UTC(year, value, 0)).getUTCDate() + offset) / 7) * 7
  return Array.from({ length: count }, (_, index) => new Date(first + (index - offset) * dayMs).toISOString().slice(0, 10))
}
export function shiftWeek(anchor, delta) { return new Date(Date.parse(anchor) + delta * 7 * dayMs).toISOString().slice(0,10) }
