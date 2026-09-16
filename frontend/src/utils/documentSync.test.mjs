import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import * as Y from 'yjs'
import { applyStates, encodeState } from './documentSync.js'

// Two editors share a baseline, disconnect, and change the same paragraph.
const seed = new Y.Doc()
const paragraph = new Y.XmlElement('paragraph')
const text = new Y.XmlText()
text.insert(0, 'Shared plan')
paragraph.insert(0, [text])
seed.getXmlFragment('default').insert(0, [paragraph])
const baseline = encodeState(seed)
const alice = new Y.Doc(), bob = new Y.Doc()
applyStates(alice, [baseline]); applyStates(bob, [baseline])
alice.getXmlFragment('default').get(0).get(0).insert(0, 'Alice: ')
bob.getXmlFragment('default').get(0).get(0).insert(11, ' + Bob')
const states = [encodeState(alice), encodeState(bob)]
// Server appends both full updates when the second writer's cursor is stale.
applyStates(alice, states); applyStates(bob, [...states].reverse())
assert.equal(alice.getXmlFragment('default').toString(), bob.getXmlFragment('default').toString())
assert.match(alice.getXmlFragment('default').toString(), /Alice: Shared plan \+ Bob/)
// A fresh reader converges from the persisted compacted snapshot alone.
const reader = new Y.Doc()
applyStates(reader, [encodeState(alice)])
assert.equal(reader.getXmlFragment('default').toString(), bob.getXmlFragment('default').toString())
// Retries and out-of-order delivery are idempotent.
applyStates(reader, [...states, baseline, ...states])
assert.equal(reader.getXmlFragment('default').toString(), bob.getXmlFragment('default').toString())
console.log('Yjs concurrent rich paragraph convergence, persisted snapshot and retries passed')

// The same real update fixtures pass through the permission-checked server
// persistence tests, including stale cursor union and merged compaction.
const fixture = JSON.parse(readFileSync(new URL('../../../pulse/tests/fixtures/document_crdt.json', import.meta.url)))
const persisted = new Y.Doc(), compacted = new Y.Doc()
applyStates(persisted, [fixture.bob, fixture.alice])
applyStates(compacted, [fixture.merged])
assert.equal(persisted.getXmlFragment('default').toString(), fixture.expected)
assert.equal(compacted.getXmlFragment('default').toString(), fixture.expected)
console.log('Persisted server fixture updates and compaction converge')
