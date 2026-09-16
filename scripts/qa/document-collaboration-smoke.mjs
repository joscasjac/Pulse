/** Disposable QA site only. Real HTTP sessions + Yjs updates, without a browser.
 * PULSE_ADMIN_PASSWORD_FILE points to a private local file; no credentials logged.
 * Unique fixtures are removed even when an assertion fails.
 */
import { readFileSync, statSync } from 'node:fs'
import assert from 'node:assert/strict'
import * as Y from '../../frontend/node_modules/yjs/dist/yjs.mjs'
import { encodeState, applyStates } from '../../frontend/src/utils/documentSync.js'
const base = process.env.PULSE_HTTP_URL || 'http://127.0.0.1:18016'
const site = process.env.PULSE_SITE || 'pulse-qa.localhost'
const passwordFile = process.env.PULSE_ADMIN_PASSWORD_FILE
assert.ok(passwordFile, 'PULSE_ADMIN_PASSWORD_FILE is required')
assert.equal(statSync(passwordFile).mode & 0o077, 0, 'Password file must be private')
const suffix = Date.now().toString(36), created = [], documents = []
function client() {
  return { cookie: '', csrf: '', async request(method, data) {
    const response = await fetch(`${base}/api/method/${method}`, { method: 'POST', headers: {
      Host: site, 'X-Frappe-Site-Name': site, 'Content-Type': 'application/json',
      ...(this.cookie ? { Cookie: this.cookie } : {}), ...(this.csrf ? { 'X-Frappe-CSRF-Token': this.csrf } : {}),
    }, body: JSON.stringify(data || {}), redirect: 'manual', signal: AbortSignal.timeout(30000) })
    const cookies = response.headers.getSetCookie()
    if (cookies.some(value => value.startsWith('sid='))) this.cookie = cookies.map(value => value.split(';')[0]).join('; ')
    let json; try { json = await response.json() } catch { json = {} }
    return { status: response.status, json }
  }, async rpc(method, data) {
    const result = await this.request(method, data)
    assert.equal(result.status, 200, `${method}: HTTP ${result.status} ${result.json.exc_type || ''}`)
    return result.json.message
  }, async login(user, password) {
    await this.rpc('login', { usr: user, pwd: password })
    const response = await fetch(`${base}/pulse`, { headers: { Host: site, 'X-Frappe-Site-Name': site, Cookie: this.cookie }, signal: AbortSignal.timeout(30000) })
    const html = await response.text()
    this.csrf = html.match(/csrf_token["'\]\s]*[:=]\s*["']([^"']+)/)?.[1] || ''
  } }
}
const admin = client(), alice = client(), bob = client(), viewer = client(), outsider = client(), guest = client()
const method = name => `pulse.api.documents.${name}`
async function create(doc) { const result = await admin.rpc('frappe.client.insert', { doc }); created.push([result.doctype, result.name]); return result }
async function denied(session, args) { const result = await session.request(method('sync_page'), args); assert.ok([403, 404].includes(result.status), `Expected denied sync, got ${result.status}`) }
function ydoc() { const doc = new Y.Doc(); documents.push(doc); return doc }
function paragraph(doc) { return doc.getXmlFragment('default').get(0).get(0) }
function html(doc) { return doc.getXmlFragment('default').toString().replaceAll('<paragraph>', '<p>').replaceAll('</paragraph>', '</p>') }
try {
  await admin.login('Administrator', readFileSync(passwordFile, 'utf8').trim())
  const password = `QA!${crypto.randomUUID()}`
  const people = []
  for (const [label, role] of [['Alice', 'Pulse Senior Developer'], ['Bob', 'Pulse Senior Developer'], ['Viewer', 'Pulse Viewer'], ['Outsider', 'Pulse Senior Developer']]) {
    people.push(await create({ doctype: 'User', email: `pulse-doc-${label.toLowerCase()}-${suffix}@example.com`, first_name: label,
      send_welcome_email: 0, new_password: password, roles: [{ role }] }))
  }
  const companies = await admin.rpc('frappe.client.get_list', { doctype: 'Company', fields: ['name'], limit_page_length: 1 })
  const project = await create({ doctype: 'Project', project_name: `Collaboration QA ${suffix}`, company: companies[0].name,
    users: people.slice(0, 3).map(person => ({ user: person.name, welcome_email_sent: 1 })) })
  for (const [index, session] of [alice, bob, viewer, outsider].entries()) await session.login(people[index].name, password)
  const page = await admin.rpc(method('save_page'), { project: project.name, title: `Shared page ${suffix}`, content: '<p>Shared plan</p>' })
  created.push(['Pulse Document', page.name])
  const seed = ydoc(), node = new Y.XmlElement('paragraph'), text = new Y.XmlText()
  text.insert(0, 'Shared plan'); node.insert(0, [text]); seed.getXmlFragment('default').insert(0, [node])
  await alice.rpc(method('sync_page'), { name: page.name, sequence: 0, state: encodeState(seed), initialize: 1, content: html(seed) })
  const [aRead, bRead] = await Promise.all([alice.rpc(method('sync_page'), { name: page.name }), bob.rpc(method('sync_page'), { name: page.name })])
  assert.equal(aRead.sequence, bRead.sequence)
  const a = ydoc(), b = ydoc(); applyStates(a, aRead.states); applyStates(b, bRead.states)
  paragraph(a).insert(0, 'Alice: '); paragraph(b).insert(paragraph(b).length, ' + Bob')
  const firstStates = [encodeState(a), encodeState(b)]
  await Promise.all([
    alice.rpc(method('sync_page'), { name: page.name, sequence: aRead.sequence, state: firstStates[0], content: html(a) }),
    bob.rpc(method('sync_page'), { name: page.name, sequence: bRead.sequence, state: firstStates[1], content: html(b) }),
  ])
  const persisted = await alice.rpc(method('sync_page'), { name: page.name })
  applyStates(a, persisted.states); applyStates(b, [...persisted.states].reverse())
  assert.equal(html(a), '<p>Alice: Shared plan + Bob</p>', 'Concurrent edit was lost')
  assert.equal(html(a), html(b), 'Clients did not converge')
  const compacted = await alice.rpc(method('sync_page'), { name: page.name, sequence: persisted.sequence, state: encodeState(a), content: html(a) })
  assert.equal(compacted.states.length, 1)
  const saved = await admin.rpc(method('get_page'), { name: page.name })
  assert.equal(saved.content, html(a), 'Canonical HTML projection is stale')
  const fresh = ydoc(); applyStates(fresh, (await viewer.rpc(method('sync_page'), { name: page.name })).states)
  assert.equal(html(fresh), html(a), 'Reload lost merged edits')
  console.log('PASS two HTTP editors: simultaneous same-paragraph edits, convergence, compacted persistence, canonical HTML, fresh viewer reload')

  // Replay an old request after compaction: no lost edits or stale HTML.
  await bob.rpc(method('sync_page'), { name: page.name, sequence: bRead.sequence, state: firstStates[1], content: '<p>STALE</p>' })
  const retried = await alice.rpc(method('sync_page'), { name: page.name })
  const replay = ydoc(); applyStates(replay, retried.states)
  assert.equal(html(replay), html(a))
  assert.equal((await admin.rpc(method('get_page'), { name: page.name })).content, html(a))
  const staleMetadata = await bob.request(method('save_page'), { project: project.name, name: page.name, modified: page.modified,
    title: 'Stale title', content: '<p>STALE</p>' })
  assert.notEqual(staleMetadata.status, 200)
  assert.equal(staleMetadata.json.exc_type, 'TimestampMismatchError')
  console.log('PASS stale CRDT retry is idempotent; stale metadata and HTML cannot overwrite the shared page')

  for (const session of [outsider, guest]) { await denied(session, { name: page.name }); await denied(session, { name: page.name, state: encodeState(a) }) }
  await denied(viewer, { name: page.name, sequence: retried.sequence, state: encodeState(a) })
  const latestProject = await admin.rpc('frappe.client.get', { doctype: 'Project', name: project.name })
  latestProject.users = latestProject.users.filter(row => row.user !== people[1].name)
  await admin.rpc('frappe.client.save', { doc: latestProject })
  await denied(bob, { name: page.name }); await denied(bob, { name: page.name, state: firstStates[1], sequence: retried.sequence })
  assert.equal((await admin.rpc(method('sync_page'), { name: page.name })).sequence, retried.sequence, 'Denied update mutated state')
  assert.equal((await admin.rpc(method('get_page'), { name: page.name })).content, html(a))
  console.log('PASS viewer write denial; outsider/guest/revoked-editor read and write denial; denied requests do not mutate persisted state')
} finally {
  for (const doc of documents) doc.destroy()
  for (const [doctype, name] of created) {
    if (doctype !== 'Project') continue
    const response = await admin.request('frappe.client.get_list', { doctype: 'Pulse Activity Log', filters: { project: name }, fields: ['name'], limit_page_length: 0 })
    for (const row of response.json?.message || []) await admin.request('frappe.client.delete', { doctype: 'Pulse Activity Log', name: row.name })
  }
  let pending = 0
  for (const [doctype, name] of created.reverse()) {
    const result = await admin.request('frappe.client.delete', { doctype, name })
    if (result.status !== 200) { pending++; console.log(`CLEANUP pending ${doctype} ${name}: HTTP ${result.status}`) }
  }
  if (!pending && created.length) console.log('PASS all disposable collaboration fixtures removed')
}
