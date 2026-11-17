<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-1">
      <h1 class="text-2xl font-bold">{{ __('Recurring Tasks') }}</h1>
      <button @click="openCreate({ repeat: true })" class="btn-primary">
        <Plus class="w-3.5 h-3.5" /> {{ __('New recurring task') }}
      </button>
    </div>
    <p class="text-xs text-faint mb-4"><template v-for="(part, i) in __('Routine work that regenerates on a schedule — a fresh task lands in {0} each cycle, so it never rots in the backlog.').split('{0}')" :key="i"><b v-if="i">{{ __('To Do') }}</b>{{ part }}</template></p>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 3" :key="n" class="card-surface p-4"><Skeleton width="40%" height="14px" /></div>
    </div>

    <div v-else class="space-y-2.5">
      <div v-for="r in rows" :key="r.name" class="card-surface p-4" :class="{ 'opacity-60': !r.is_active }">
        <div class="flex items-center justify-between gap-3">
          <div class="min-w-0">
            <div class="font-medium text-app truncate">{{ r.subject }}</div>
            <div class="flex items-center gap-4 mt-1.5 text-xs text-muted flex-wrap">
              <span class="tele text-accent">{{ cadence(r) }}</span>
              <span>{{ r.project }}</span>
              <span class="inline-flex items-center gap-1.5"><CalendarDays class="w-3.5 h-3.5" />{{ __('next: {0}', [r.next_run || '—']) }}</span>
              <span v-if="r.last_generated" class="text-faint">{{ __('last: {0}', [r.last_generated]) }}</span>
              <span v-if="!r.is_active" class="tele text-[10px] text-faint">{{ __('paused') }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button class="icon-btn" :title="__('Generate a task now')" @click="runNow(r)"><Play class="w-4 h-4" /></button>
            <button class="icon-btn" :title="r.is_active ? __('Pause') : __('Resume')" @click="toggle(r)">
              <Pause v-if="r.is_active" class="w-4 h-4" />
              <RotateCw v-else class="w-4 h-4" />
            </button>
            <button class="icon-btn danger" :title="__('Delete')" @click="remove(r)"><Trash2 class="w-4 h-4" /></button>
          </div>
        </div>
      </div>
      <div v-if="!rows.length" class="py-16 text-center text-faint">{{ __('No recurring tasks yet. Create one so routine work never rots in the backlog.') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'
import Skeleton from '@/ui/Skeleton.vue'
import { openCreate, createState } from '@/ui/create'
import { toast } from '@/ui/toast'
import { __ } from '@/translation'
import Plus from '~icons/lucide/plus'
import Play from '~icons/lucide/play'
import Pause from '~icons/lucide/pause'
import RotateCw from '~icons/lucide/rotate-cw'
import Trash2 from '~icons/lucide/trash-2'
import CalendarDays from '~icons/lucide/calendar-days'

const loading = ref(true)
const rows = ref([])

function cadence(r) {
  const count = Number(r.interval_count) || 1
  const unit = r.interval_unit || 'Week'
  const one = { Day: __('every day'), Week: __('every week'), Month: __('every month') }
  const many = { Day: __('every {0} days', [count]), Week: __('every {0} weeks', [count]), Month: __('every {0} months', [count]) }
  return (count === 1 ? one[unit] : many[unit]) || r.cadence
}

async function reload() {
  loading.value = true
  rows.value = await call('pulse.api.recurring.list_recurring').catch(() => [])
  loading.value = false
}
async function toggle(r) {
  await call('pulse.api.recurring.toggle_recurring', { name: r.name, is_active: r.is_active ? 0 : 1 }).catch(() => {})
  reload()
}
async function runNow(r) {
  try { await call('pulse.api.recurring.generate_now', { name: r.name }); toast.success(__('Task generated in To Do')); reload() }
  catch (e) { toast.error(__('Could not generate task')) }
}
async function remove(r) {
  if (!confirm(__('Delete recurring "{0}"? Tasks already generated are kept.', [r.subject]))) return
  await call('pulse.api.recurring.delete_recurring', { name: r.name }).catch(() => {})
  reload()
}
watch(() => createState.created, reload)
onMounted(reload)
</script>

<style scoped>
.new-btn { background: var(--accent); transition: filter 0.12s; }
.new-btn:hover { filter: brightness(1.08); }
.icon-btn { padding: 6px; border-radius: 9px; border: 1px solid var(--border); color: var(--muted); background: transparent; }
.icon-btn:hover { color: var(--text); border-color: var(--accent); }
.icon-btn.danger:hover { color: var(--danger); border-color: var(--danger); }
</style>
