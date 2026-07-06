import { reactive } from 'vue'

// Global "create issue" dialog state, so a New Issue button anywhere can open it.
export const createState = reactive({ open: false, defaults: {}, created: 0 })

export function openCreate(defaults = {}) {
  createState.defaults = { ...defaults }
  createState.open = true
}
export function closeCreate() { createState.open = false }
export function markCreated() { createState.created++ }
