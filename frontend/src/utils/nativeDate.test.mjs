import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { nativeDateDay, formatNativeDate } from './nativeDate.js'

test('Date and native Datetime values display the same written calendar day', () => {
  for (const value of ['2026-11-04', '2026-11-04 12:00:00', '2026-11-04 00:00:00.123456', '2026-11-04T00:00:00Z', '2026-11-04T23:59:59-06:00']) {
    assert.equal(nativeDateDay(value), '2026-11-04')
    assert.equal(formatNativeDate(value, 'en-US'), 'Nov 4')
  }
  assert.equal(formatNativeDate('2026-11-04', 'en-US', { month: 'short', day: 'numeric', year: 'numeric' }), 'Nov 4, 2026')
})

test('invalid and absent input has a stable fallback without rolling into another day', () => {
  for (const value of [null, undefined, '', {}, 'Invalid Date', '2026-02-30', '2026-13-04', '0000-01-01', '2026-11-04 25:00:00', '2026-11-04garbage']) {
    assert.equal(nativeDateDay(value), '')
    assert.equal(formatNativeDate(value, 'en-US'), '—')
  }
  assert.equal(nativeDateDay('2024-02-29 00:00:00'), '2024-02-29')
})

test('date-only and datetime display do not move across browser timezones', () => {
  const url = new URL('./nativeDate.js', import.meta.url).href
  const script = `import {formatNativeDate} from ${JSON.stringify(url)}; console.log(JSON.stringify(['2026-11-04','2026-11-04 00:00:00','2026-11-04T23:59:59-06:00'].map(value=>formatNativeDate(value,'en-US'))))`
  for (const zone of ['America/Guatemala', 'America/Los_Angeles', 'Pacific/Kiritimati']) {
    assert.deepEqual(JSON.parse(execFileSync(process.execPath, ['--input-type=module', '-e', script], { env: { ...process.env, TZ: zone }, encoding: 'utf8' })), ['Nov 4', 'Nov 4', 'Nov 4'])
  }
})
