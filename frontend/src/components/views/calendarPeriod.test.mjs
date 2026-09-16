import assert from 'node:assert/strict'
import { calendarPeriodDays, shiftWeek } from './calendarPeriod.js'
assert.deepEqual(calendarPeriodDays('2026-09','week','2026-09-16'), ['2026-09-14','2026-09-15','2026-09-16','2026-09-17','2026-09-18','2026-09-19','2026-09-20'])
assert.equal(shiftWeek('2026-12-30',1),'2027-01-06')
const month=calendarPeriodDays('2026-02');assert.equal(month[0],'2026-01-26');assert.equal(month.at(-1),'2026-03-01');assert.equal(month.length%7,0)
assert.deepEqual(calendarPeriodDays('2026-09','week','2026-09-16').filter((_,i)=>i<5), ['2026-09-14','2026-09-15','2026-09-16','2026-09-17','2026-09-18'])
console.log('Calendar month/week boundaries, navigation and weekday-only display pass')
