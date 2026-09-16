<template>
  <transition name="fade">
    <div v-if="entityState.open" class="ovl" @click.self="close">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="entity-form-title">
        <div class="head">
          <span id="entity-form-title" class="font-semibold">{{ entityState.name ? 'Edit' : 'New' }} {{ singular }}</span>
          <button class="p-1 rounded hover-app text-muted" aria-label="Close form" @click="close"><X class="w-4 h-4" /></button>
        </div>

        <div v-if="loadingMeta" class="body"><div class="text-sm text-muted py-6 text-center">Loading form…</div></div>

        <div v-else class="body">
          <div v-for="f in fields" :key="f.fieldname" class="fld">
            <label :for="`entity-${f.fieldname}`" class="lbl">{{ f.label }}<b v-if="f.reqd" style="color:var(--accent)"> *</b></label>

            <textarea v-if="isText(f)" :id="`entity-${f.fieldname}`" v-model="model[f.fieldname]" rows="3" class="in" :placeholder="f.description || ''" />

            <select v-else-if="f.fieldtype === 'Select'" :id="`entity-${f.fieldname}`" v-model="model[f.fieldname]" class="in">
              <option v-for="o in selOpts(f)" :key="o" :value="o">{{ o || '—' }}</option>
            </select>

            <div v-else-if="f.fieldtype === 'Link'" class="link-picker">
              <input type="search" class="in" :aria-label="`Search ${f.label}`" :value="linkSearch[f.fieldname] || ''" placeholder="Search by name…" @input="searchLinks(f, $event.target.value)" />
              <select :id="`entity-${f.fieldname}`" v-model="model[f.fieldname]" class="in" :aria-busy="!!linkBusy[f.fieldname]">
                <option :value="null">— none —</option>
                <option v-for="o in (linkCache[f.fieldname] || [])" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
              <span v-if="linkBusy[f.fieldname]" class="text-xs text-muted" role="status">Loading options…</span>
              <span v-if="linkErrors[f.fieldname]" class="text-xs" role="alert">Options couldn't load. <button class="underline" @click="fetchLink(f)">Retry</button></span>
              <div class="flex justify-between gap-2 text-xs"><button v-if="linkOffset[f.fieldname]" @click="pageLinks(f, -1)">Previous options</button><button v-if="linkMore[f.fieldname]" @click="pageLinks(f, 1)">More options</button></div>
            </div>

            <label v-else-if="f.fieldtype === 'Check'" class="chk">
              <input :id="`entity-${f.fieldname}`" type="checkbox" :checked="!!model[f.fieldname]" @change="model[f.fieldname] = $event.target.checked ? 1 : 0" />
              <span class="text-xs text-muted">{{ f.description || 'Yes' }}</span>
            </label>

            <input v-else-if="f.fieldtype === 'Date'" type="date" :id="`entity-${f.fieldname}`" v-model="model[f.fieldname]" class="in" />
            <input v-else-if="f.fieldtype === 'Datetime'" type="datetime-local" :id="`entity-${f.fieldname}`" v-model="model[f.fieldname]" class="in" />
            <input v-else-if="isNumber(f)" type="number" :id="`entity-${f.fieldname}`" v-model="model[f.fieldname]" class="in" />
            <input v-else :id="`entity-${f.fieldname}`" v-model="model[f.fieldname]" class="in" :placeholder="f.description || ''" />
          </div>
          <div v-if="!fields.length" class="text-sm text-muted py-4 text-center">Nothing to edit.</div>
        </div>

        <div class="foot">
          <button v-if="entityState.name" class="btn danger" @click="remove" :disabled="busy">Delete</button>
          <span v-else />
          <div class="flex gap-2">
            <button class="btn ghost" @click="close">Cancel</button>
            <button class="btn primary" :disabled="!valid || busy" @click="save">{{ busy ? 'Saving…' : 'Save' }}</button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, reactive, computed, watch, onBeforeUnmount } from 'vue'
import { call } from 'frappe-ui'
import { entityState, closeEntity, markSaved } from '@/ui/entity'
import { toast } from '@/ui/toast'
import X from '~icons/lucide/x'

const loadingMeta = ref(false)
const busy = ref(false)
const fields = ref([])
const model = reactive({})
const metaCache = {}
const linkCache = reactive({})

const singular = computed(() => (entityState.doctype || '').replace(/^Pulse /, ''))
const valid = computed(() => !loadingMeta.value && fields.value.length > 0 && fields.value.every((f) => !f.reqd || (model[f.fieldname] !== undefined && model[f.fieldname] !== null && model[f.fieldname] !== '')))

function isText(f) { return ['Text', 'Long Text', 'Small Text', 'Text Editor', 'Markdown Editor', 'Code', 'HTML Editor'].includes(f.fieldtype) }
function isNumber(f) { return ['Int', 'Float', 'Currency', 'Percent'].includes(f.fieldtype) }
function selOpts(f) { return (f.options || '').split('\n') }

async function loadMeta(dt) {
  if (metaCache[dt]) return metaCache[dt]
  const m = await call('pulse.api.spa.get_form_meta', { doctype: dt })
  metaCache[dt] = m
  return m
}

const linkSearch = reactive({}), linkOffset = reactive({}), linkMore = reactive({}), linkBusy = reactive({}), linkErrors = reactive({})
const linkRequests = {}, linkTimers = {}
async function fetchLink(field) {
  const key = field.fieldname, request = (linkRequests[key] || 0) + 1
  linkRequests[key] = request; linkBusy[key] = true; linkErrors[key] = false
  try {
    const rows = await call('pulse.api.spa.link_options', { doctype: field.options, txt: linkSearch[key] || '', selected: model[key] || null, start: linkOffset[key] || 0 })
    if (request !== linkRequests[key]) return
    linkCache[key] = rows; linkMore[key] = rows.length >= 50
  } catch { if (request === linkRequests[key]) linkErrors[key] = true }
  finally { if (request === linkRequests[key]) linkBusy[key] = false }
}
function searchLinks(field, value) {
  const key = field.fieldname
  linkSearch[key] = value; linkOffset[key] = 0; linkRequests[key] = (linkRequests[key] || 0) + 1
  clearTimeout(linkTimers[key]); linkTimers[key] = setTimeout(() => fetchLink(field), 200)
}
function pageLinks(field, direction) { linkOffset[field.fieldname] = Math.max(0, (linkOffset[field.fieldname] || 0) + direction * 50); fetchLink(field) }
async function fetchLinks(flds) {
  for (const state of [linkCache, linkSearch, linkOffset, linkMore, linkErrors]) Object.keys(state).forEach(key => delete state[key])
  await Promise.all(flds.filter(f => f.fieldtype === 'Link' && f.options).map(fetchLink))
}
onBeforeUnmount(() => Object.values(linkTimers).forEach(clearTimeout))

watch(() => entityState.open, async (open) => {
  if (!open) return
  loadingMeta.value = true
  try {
    const meta = await loadMeta(entityState.doctype)
    fields.value = meta.fields

    // reset model
    Object.keys(model).forEach((k) => delete model[k])
    for (const f of meta.fields) model[f.fieldname] = f.fieldtype === 'Check' ? (parseInt(f.default) || 0) : (f.default ?? '')
    Object.assign(model, entityState.defaults)

    if (entityState.name) {
      const rec = await call('pulse.api.spa.get_entity', { doctype: entityState.doctype, name: entityState.name })
      if (rec) for (const f of meta.fields) if (rec[f.fieldname] !== undefined && rec[f.fieldname] !== null) model[f.fieldname] = rec[f.fieldname]
    }
    await fetchLinks(meta.fields)
  } catch (e) {
    // never leave the dialog stuck on "Loading form…" — surface and close
    toast.error(e?.messages?.[0] || e?.message || 'Could not load form')
    closeEntity()
  } finally {
    loadingMeta.value = false
  }
})

function close() { closeEntity() }

async function save() {
  if (!valid.value) return
  busy.value = true
  const doc = { doctype: entityState.doctype, ...model }
  if (entityState.name) doc.name = entityState.name
  try {
    await call('pulse.api.spa.save_entity', { doc: JSON.stringify(doc) })
    toast.success(`${singular.value} saved`)
    markSaved()
    closeEntity()
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || 'Could not save')
  } finally { busy.value = false }
}

async function remove() {
  if (!confirm(`Delete this ${singular.value.toLowerCase()}?`)) return
  busy.value = true
  try {
    await call('pulse.api.spa.delete_entity', { doctype: entityState.doctype, name: entityState.name })
    toast.success(`${singular.value} deleted`)
    markSaved()
    closeEntity()
  } catch (e) {
    toast.error(e?.messages?.[0] || 'Could not delete')
  } finally { busy.value = false }
}
</script>

<style scoped>
.ovl { position: fixed; inset: 0; z-index: 90; background: rgba(0, 0, 0, 0.5); display: grid; place-items: start center; padding-top: 8vh; }
.modal { width: 520px; max-width: calc(100vw - 32px); max-height: 84vh; overflow-y: auto; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); }
.head { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--border-soft); }
.body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.link-picker { display:flex; flex-direction:column; gap:6px; }
.fld { display: flex; flex-direction: column; gap: 5px; }
.lbl { font-size: 11px; color: var(--muted); font-weight: 500; }
.in { width: 100%; background: var(--surface-2); border: 1px solid var(--border); color: var(--text); font-size: 13px; border-radius: 7px; padding: 7px 9px; outline: none; }
.in:focus { border-color: var(--accent); }
textarea.in { resize: vertical; font-family: inherit; }
.chk { display: flex; align-items: center; gap: 8px; }
.foot { display: flex; align-items: center; justify-content: space-between; padding: 13px 16px; border-top: 1px solid var(--border-soft); position: sticky; bottom: 0; background: var(--surface); }
.btn { font-size: 13px; padding: 7px 14px; border-radius: 7px; }
.btn.ghost { border: 1px solid var(--border); background: transparent; color: var(--text); }
.btn.primary { background: var(--accent); color: var(--on-accent); }
.btn.primary:disabled { opacity: 0.45; }
.btn.danger { border: 1px solid rgba(242,114,109,0.4); color: #f2726d; background: transparent; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.16s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
