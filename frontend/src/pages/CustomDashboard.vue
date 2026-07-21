<template>
  <div class="p-6">
    <header class="flex items-center justify-between mb-5">
      <div>
        <h1 class="text-2xl font-bold">My Dashboard</h1>
        <p class="text-sm text-muted">Customize your widgets - drag sizes, add, remove, and save.</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-secondary" @click="showPalette = !showPalette">+ Add widget</button>
        <button class="btn-secondary" @click="reset" :disabled="saving">Reset</button>
        <button class="btn-primary" @click="save" :disabled="saving">
          {{ saving ? 'Saving...' : dirty ? 'Save changes' : 'Saved' }}
        </button>
      </div>
    </header>

    <!-- Add-widget palette -->
    <div v-if="showPalette" class="mb-4 p-3 border border-app rounded-lg bg-surface">
      <div class="text-xs font-medium text-muted mb-2">Add a widget</div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="c in catalog"
          :key="c.widget_type"
          class="px-3 py-1.5 text-sm rounded-md border border-app hover-app"
          @click="addWidget(c)"
        >
          {{ c.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-muted py-20 text-center">Loading dashboard...</div>

    <!-- Widget grid (12-col) -->
    <div v-else class="grid grid-cols-12 gap-3 auto-rows-[52px]">
      <div
        v-for="(w, i) in widgets"
        :key="i"
        draggable="true"
        @dragstart="dragIdx = i"
        @dragover.prevent
        @drop="onReorder(i)"
        class="relative card-surface p-3.5 overflow-hidden group cursor-move transition-colors"
        :class="{ 'border-accent': dragIdx === i }"
        :style="cellStyle(w)"
      >
        <div class="flex items-start justify-between">
          <div class="text-[11px] font-medium uppercase tracking-wide text-faint flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full" :style="{ background: w.color || 'var(--accent)' }" />{{ w.title || w.widget_type }}
          </div>
          <div class="opacity-0 group-hover:opacity-100 flex gap-1 text-muted">
            <button title="Narrower" @click="resize(w, 'w', -1)">&lt;</button>
            <button title="Wider" @click="resize(w, 'w', 1)">&gt;</button>
            <button title="Shorter" @click="resize(w, 'h', -1)">-</button>
            <button title="Taller" @click="resize(w, 'h', 1)">+</button>
            <button title="Remove" class="text-muted hover:text-app" @click="remove(i)">x</button>
          </div>
        </div>
        <DashboardWidget :widget="w" :stats="stats" :series="series" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from 'frappe-ui'
import DashboardWidget from '@/components/DashboardWidget.vue'
import { toast } from '@/ui/toast'

const loading = ref(true)
const saving = ref(false)
const dirty = ref(false)
const showPalette = ref(false)
const widgets = ref([])
const catalog = ref([])
const stats = ref({})
const series = ref({})
const dragIdx = ref(null)

function cellStyle(w) {
  return {
    gridColumn: `span ${Math.min(w.w || 4, 12)} / span ${Math.min(w.w || 4, 12)}`,
    gridRow: `span ${w.h || 3} / span ${w.h || 3}`,
  }
}

function markDirty() { dirty.value = true }

function addWidget(c) {
  widgets.value.push({
    widget_type: c.widget_type,
    title: c.label,
    metric: c.metrics && c.metrics[0],
    w: 4, h: 3, x: 0, y: 0,
    color: 'var(--accent)',
  })
  showPalette.value = false
  markDirty()
}

function remove(i) { widgets.value.splice(i, 1); markDirty() }
function resize(w, dim, d) {
  if (dim === 'w') w.w = Math.max(2, Math.min(12, (w.w || 4) + d * 2))
  else w.h = Math.max(2, Math.min(10, (w.h || 3) + d))
  markDirty()
}
function onReorder(target) {
  const from = dragIdx.value
  dragIdx.value = null
  if (from === null || from === target) return
  const [moved] = widgets.value.splice(from, 1)
  widgets.value.splice(target, 0, moved)
  markDirty()
}

async function load() {
  loading.value = true
  const [dash, cat, s, ser] = await Promise.all([
    call('pulse.api.dashboards.get_my_dashboard'),
    call('pulse.api.dashboards.get_widget_catalog'),
    call('pulse.api.dashboards.get_dashboard_stats').catch(() => ({})),
    call('pulse.api.dashboards.get_dashboard_series').catch(() => ({})),
  ])
  widgets.value = dash.widgets || []
  catalog.value = cat || []
  stats.value = s || {}
  series.value = ser || {}
  dirty.value = false
  loading.value = false
}

async function save() {
  saving.value = true
  await call('pulse.api.dashboards.save_dashboard', { widgets: JSON.stringify(widgets.value) })
  dirty.value = false
  saving.value = false
  toast.success('Dashboard saved')
}

async function reset() {
  saving.value = true
  const dash = await call('pulse.api.dashboards.reset_dashboard')
  widgets.value = dash.widgets || []
  dirty.value = false
  saving.value = false
}

onMounted(load)
</script>

<style scoped>
.btn-primary, .btn-secondary { padding: 0.375rem 0.75rem; font-size: 0.875rem; border-radius: 0.375rem; }
.btn-primary { background: var(--accent); color: var(--on-accent); }
.btn-primary:hover { background: #1d4ed8; }
.btn-secondary { border: 1px solid var(--border); background: var(--surface); color: var(--text); }
.btn-primary:disabled, .btn-secondary:disabled { opacity: 0.5; }
</style>
