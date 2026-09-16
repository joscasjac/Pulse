import test from 'node:test'
import assert from 'node:assert/strict'
import { timelineRange, taskBounds, shiftDate, resizeDate } from '../src/components/views/timelineMath.js'
test('month and quarter ranges cross years and include leap days', () => {
 assert.equal(timelineRange('2024-02', 'month').length, 29)
 const quarter = timelineRange('2026-12', 'quarter')
 assert.equal(quarter[0], '2026-12-01')
 assert.equal(quarter.at(-1), '2027-02-28')
})
test('visible bars clip both edges and reject out of period tasks', () => {
 const days = timelineRange('2026-09', 'month')
 assert.deepEqual(taskBounds({ exp_start_date: '2026-08-30', exp_end_date: '2026-09-03' }, days), {start:0,end:2})
 assert.equal(taskBounds({ exp_end_date:'2026-10-01'}, days),null)
 assert.deepEqual(taskBounds({ exp_end_date:'2026-09-16 00:00:00'}, days),{start:15,end:15})
})
test('resize preserves chronological ranges and date shifts ignore DST', () => {
 const task = {exp_start_date:'2026-09-16',exp_end_date:'2026-09-18'}
 assert.equal(resizeDate(task,'exp_start_date',6),'2026-09-18')
 assert.equal(resizeDate(task,'exp_end_date',-6),'2026-09-16')
 assert.equal(shiftDate('2026-03-08',1),'2026-03-09')
})

test('group rows retain repeated task memberships and distinct anchors', async () => {
 const {timelineRows,timelineDependencyPairs}=await import('../src/components/views/timelineMath.js')
 const a={name:'A'},b={name:'B'}
 const rows=timelineRows([a,b],[{name:'Alice',tasks:[a,b]},{name:'Bob',tasks:[b]}])
 assert.deepEqual(rows.map(row=>row.type),['group','task','task','group','task'])
 assert.equal(new Set(rows.map(row=>row.key)).size,5)
 const pairs=timelineDependencyPairs(rows,[{target_task:'A',source_task:'B'}])
 assert.deepEqual(pairs.map(({from,to})=>[from.index,to.index]),[[1,2],[1,4]])
 const plain=timelineRows([a,b])
 assert.deepEqual(plain.map(row=>row.task.name),['A','B'])
})
test('dependencies prefer matching group occurrence and skip missing tasks', async () => {
 const {timelineRows,timelineDependencyPairs}=await import('../src/components/views/timelineMath.js')
 const a={name:'A'},b={name:'B'}
 const rows=timelineRows([a,b],[{name:'One',tasks:[a,b]},{name:'Two',tasks:[a,b]}])
 assert.deepEqual(timelineDependencyPairs(rows,[{target_task:'A',source_task:'B'}]).map(({from,to})=>[from.index,to.index]),[[1,2],[4,5]])
 assert.deepEqual(timelineDependencyPairs(rows,[{target_task:'MISSING',source_task:'B'}]),[])
})
