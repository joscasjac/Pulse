/** Native ERP Date/Datetime values represent a calendar day in the site's date UI.
 * Keep that written day rather than converting a due date through the browser zone.
 */
export function nativeDateDay(value) {
  if (typeof value !== 'string') return ''
  const match = value.trim().match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-](?:[01]\d|2[0-3]):?[0-5]\d)?)?$/)
  if (!match || Number(match[1]) < 1) return ''
  const [, year, month, day] = match
  const date = new Date(0)
  date.setUTCFullYear(Number(year), Number(month) - 1, Number(day))
  date.setUTCHours(12, 0, 0, 0)
  if (date.getUTCFullYear() !== Number(year) || date.getUTCMonth() !== Number(month) - 1 || date.getUTCDate() !== Number(day)) return ''
  return `${year}-${month}-${day}`
}

export function formatNativeDate(value, locale, options = { month: 'short', day: 'numeric' }) {
  const day = nativeDateDay(value)
  return day ? new Date(`${day}T12:00:00Z`).toLocaleDateString(locale, { ...options, timeZone: 'UTC' }) : '—'
}
