<template>
  <div class="toaster">
    <transition-group name="toast">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type" role="status">
        <component :is="icon(t.type)" class="ico" />
        <span class="msg">{{ t.message }}</span>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { toasts } from './toast'
import Check from '~icons/lucide/check'
import AlertTriangle from '~icons/lucide/triangle-alert'
import Info from '~icons/lucide/info'

function icon(type) {
  return type === 'error' ? AlertTriangle : type === 'info' ? Info : Check
}
</script>

<style scoped>
.toaster {
  position: fixed; bottom: 20px; right: 20px; z-index: 100;
  display: flex; flex-direction: column; gap: 8px; align-items: flex-end;
}
.toast {
  display: flex; align-items: center; gap: 9px;
  background: var(--surface); color: var(--text);
  border: 1px solid var(--border); border-left-width: 2px;
  border-radius: 8px; padding: 9px 14px 9px 12px;
  font-size: 13px; box-shadow: 0 12px 30px -12px rgba(0, 0, 0, 0.55);
  min-width: 180px; max-width: 340px;
}
.toast.success { border-left-color: #34d399; }
.toast.error { border-left-color: #f2726d; }
.toast.info { border-left-color: #6aa9ff; }
.ico { width: 15px; height: 15px; flex-shrink: 0; }
.toast.success .ico { color: #34d399; }
.toast.error .ico { color: #f2726d; }
.toast.info .ico { color: #6aa9ff; }
.msg { line-height: 1.35; }

.toast-enter-active, .toast-leave-active { transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1); }
.toast-enter-from { opacity: 0; transform: translateX(12px); }
.toast-leave-to { opacity: 0; transform: translateX(12px); }
@media (prefers-reduced-motion: reduce) {
  .toast-enter-active, .toast-leave-active { transition: opacity 0.15s; }
  .toast-enter-from, .toast-leave-to { transform: none; }
}
</style>
