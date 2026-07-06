import { reactive } from 'vue'

// Global create/edit dialog for any Pulse doctype.
export const entityState = reactive({ open: false, doctype: null, name: null, defaults: {}, saved: 0 })

export function openEntity(doctype, name = null, defaults = {}) {
  entityState.doctype = doctype
  entityState.name = name
  entityState.defaults = { ...defaults }
  entityState.open = true
}
export function closeEntity() { entityState.open = false }
export function markSaved() { entityState.saved++ }
