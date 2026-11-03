import test from 'node:test'
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { File } from 'node:buffer'
import { createPrivateEditorUpload } from './privateEditorUpload.js'

const require = createRequire(import.meta.url)
const { buildSync } = require('esbuild')
const compiled = buildSync({ entryPoints: [new URL('../../node_modules/frappe-ui/src/utils/useFileUpload.ts', import.meta.url).pathname], bundle: true, platform: 'node', format: 'cjs', write: false }).outputFiles[0].text
const module = { exports: {} }
new Function('module', 'exports', 'require', compiled)(module, module.exports, require)
const { useFileUpload } = module.exports

test('actual Frappe UI upload sends private flag and canonical Task/document binding', async () => {
  const requests = []
  class FakeXHR {
    static DONE = 4
    upload = { addEventListener() {} }
    addEventListener() {}
    open(method, url) { this.method = method; this.url = url }
    setRequestHeader() {}
    send(body) {
      requests.push({ method: this.method, url: this.url, body })
      this.status = 200; this.readyState = 4
      this.responseText = JSON.stringify({ message: { name: 'FILE-QA', file_name: 'private.png', file_url: '/private/files/private.png', is_private: 1 } })
      this.onreadystatechange()
    }
  }
  const oldWindow = globalThis.window, oldXHR = globalThis.XMLHttpRequest
  globalThis.window = { csrf_token: 'test-only' }; globalThis.XMLHttpRequest = FakeXHR
  try {
    let reference = { doctype: 'Task', docname: 'TASK-2026-00155' }
    const upload = createPrivateEditorUpload((file, options) => useFileUpload().upload(file, options), () => reference)
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'private.png', { type: 'image/png' })
    assert.equal((await upload(file)).is_private, 1)
    reference = { doctype: 'Pulse Document', docname: 'canonical-page-id' }
    await upload(file)
    for (const [index, expected] of [{ doctype: 'Task', docname: 'TASK-2026-00155' }, reference].entries()) {
      assert.equal(requests[index].method, 'POST')
      assert.equal(requests[index].url, '/api/method/upload_file')
      assert.equal(requests[index].body.get('is_private'), '1')
      assert.equal(requests[index].body.get('doctype'), expected.doctype)
      assert.equal(requests[index].body.get('docname'), expected.docname)
      assert.equal(requests[index].body.get('file').name, 'private.png')
    }
  } finally { globalThis.window = oldWindow; globalThis.XMLHttpRequest = oldXHR }
})

test('unsaved or unrelated parents are rejected before any upload request', async () => {
  let calls = 0
  for (const reference of [{ doctype: 'Pulse Document', docname: undefined }, { doctype: 'Task', docname: '' }, { doctype: 'User', docname: 'Administrator' }]) {
    const upload = createPrivateEditorUpload(async () => { calls++ }, () => reference)
    await assert.rejects(upload({}), /before uploading/)
  }
  assert.equal(calls, 0)
})

test('public/unconfirmed responses are never inserted as protected editor images', async () => {
  for (const response of [{ is_private: 0, file_url: '/files/public.png' }, { is_private: 1, file_url: '/files/public.png' }, { file_url: '/private/files/unconfirmed.png' }]) {
    const upload = createPrivateEditorUpload(async () => response, () => ({ doctype: 'Task', docname: 'TASK-1' }))
    await assert.rejects(upload({}), /did not return a private attachment/)
  }
})
