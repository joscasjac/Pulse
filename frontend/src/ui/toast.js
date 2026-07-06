import { reactive } from 'vue'

let seq = 0
export const toasts = reactive([])

export function toast(message, type = 'success', timeout = 2600) {
  const id = ++seq
  toasts.push({ id, message, type })
  setTimeout(() => dismiss(id), timeout)
  return id
}

export function dismiss(id) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i >= 0) toasts.splice(i, 1)
}

toast.success = (m) => toast(m, 'success')
toast.error = (m) => toast(m, 'error', 4200)
toast.info = (m) => toast(m, 'info')
