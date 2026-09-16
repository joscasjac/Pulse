<template>
  <div>
    <p class="sync-state" role="status">{{ status }}</p>
    <p v-if="error" role="alert">{{ error }} <button class="btn-ghost" @click="synchronize">Retry sync</button></p>
    <TextEditor v-if="!ready" ref="seedEditor" :content="content" :mentions="mentionOptions" :editable="false" editor-class="prose prose-sm doc-editor" />
    <TextEditor v-else ref="editor" :extensions="extensions" :starterkit-options="{ undoRedo: false }" :fixed-menu="true" :mentions="mentionOptions" :upload-args="{ doctype: 'Pulse Document', docname: name, is_private: 1 }" placeholder="Write together. Type @ to mention a teammate." editor-class="prose prose-sm doc-editor" />
  </div>
</template>
<script setup>
import { ref, shallowRef, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { call, TextEditor } from 'frappe-ui'
import * as Y from 'yjs'
import Collaboration from '@tiptap/extension-collaboration'
import { prosemirrorToYDoc } from 'y-prosemirror'
import { applyStates, encodeState } from '../../utils/documentSync'
const props = defineProps({ name: String, content: String, mentions: Array })
const emit = defineEmits(['synced'])
const mentionOptions = { mentions: () => props.mentions || [] }
const ready = ref(false), seedEditor = ref(null), editor = ref(null), extensions = shallowRef([])
const error = ref(''), status = ref('Connecting to shared page…')
let doc = new Y.Doc(), sequence = 0, timer, inFlight, stopped = false, dirty = false, lastState = ''
const api = args => call('pulse.api.documents.sync_page', { name: props.name, ...args })
async function initialize() {
  const data = await api({})
  if (stopped) return
  sequence = data.sequence
  if (data.states.length) applyStates(doc, data.states)
  else {
    await nextTick()
    const seeded = prosemirrorToYDoc(seedEditor.value.editor.state.doc, 'default')
    const initialized = await api({ sequence, state: encodeState(seeded), content: props.content, initialize: 1 })
    seeded.destroy()
    if (stopped) return
    sequence = initialized.sequence
    applyStates(doc, initialized.states)
  }
  lastState = encodeState(doc)
  extensions.value = [Collaboration.configure({ document: doc })]
  doc.on('update', (_, origin) => { if (origin !== 'remote') { dirty = true; status.value = 'Saving shared changes…' } })
  ready.value = true
  status.value = 'Shared page · changes save automatically'
}
async function performSync() {
  error.value = ''
  if (!ready.value) return initialize()
  const state = encodeState(doc)
  const html = editor.value?.editor?.getHTML()
  const data = await api({ sequence, state: state === lastState && !dirty ? undefined : state, content: html })
  if (stopped) return
  sequence = data.sequence
  applyStates(doc, data.states)
  // Remote changes may require another round to persist a merged projection.
  const merged = encodeState(doc)
  dirty = merged !== state
  lastState = state
  emit('synced', data.modified)
  status.value = dirty ? 'Synchronizing shared changes…' : 'All shared changes saved'
}
async function synchronize() {
  if (inFlight) return inFlight
  inFlight = performSync().catch(e => {
    error.value = e.message || 'Changes could not sync. Keep this page open and retry.'
    status.value = 'Changes waiting to sync'
    throw e
  }).finally(() => { inFlight = null })
  return inFlight
}
async function flush() {
  await synchronize()
  // Fetch/merge can introduce a new state, so persist it before leaving.
  for (let attempt = 0; dirty && attempt < 5; attempt++) await synchronize()
  if (dirty) throw new Error('The page is still syncing. Please try again in a moment.')
}
function preventLoss(event) { if (dirty || inFlight) { event.preventDefault(); event.returnValue = '' } }
onMounted(async () => {
  window.addEventListener('beforeunload', preventLoss)
  try { await synchronize() } catch { /* recovery is visible */ }
  if (!stopped) timer = setInterval(() => { synchronize().catch(() => {}) }, 1200)
})
onBeforeUnmount(() => { stopped = true; clearInterval(timer); window.removeEventListener('beforeunload', preventLoss); doc.destroy() })
defineExpose({ flush })
</script>
<style scoped>
.sync-state{font-size:.875rem;color:var(--muted);padding:.7rem 0} [role=alert]{color:var(--text);padding:.7rem 0}
</style>
