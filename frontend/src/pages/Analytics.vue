<template>
  <div class="p-6">
    <h1 class="text-xl font-semibold mb-1">Agile &amp; Delivery Analytics</h1>
    <p class="text-sm text-muted mb-5">Summary of your team's agile report with the most useful metrics.</p>

    <div v-if="loading" class="text-muted py-20 text-center">Loading analytics...</div>
    <div v-else class="space-y-4">
      <!-- KPI row -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div v-for="k in kpiCards" :key="k.label" class="rounded-xl border border-app bg-surface p-4">
          <div class="text-xs text-muted">{{ k.label }}</div>
          <div class="text-3xl font-bold mt-1" :style="{ color: k.color }">{{ k.value }}</div>
          <div class="text-[10px] text-muted mt-1">Total Tasks</div>
        </div>
      </div>

      <!-- charts row 1 -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div class="card">
          <div class="card-title">Task Status Distribution</div>
          <Donut :data="a.status_distribution" center-label="tasks" />
        </div>
        <div class="card">
          <div class="card-title">Tasks Per Assignee</div>
          <Bars :data="a.workload" />
        </div>
        <div class="card">
          <div class="card-title">Task Type Distribution</div>
          <Donut :data="a.type_distribution" center-label="tasks" />
        </div>
        <div class="card">
          <div class="card-title">Task Completion</div>
          <Gauge :value="a.storypoints.pct" label="completed" />
          <div class="text-[10px] text-muted text-center">{{ a.storypoints.completed }} / {{ a.storypoints.estimated }} tasks</div>
        </div>
      </div>

      <!-- sprint progress -->
      <div class="card">
        <div class="card-title">Sprint Progress - by task count</div>
        <div class="space-y-3 mt-2">
          <div v-for="s in a.sprint_progress" :key="s.name">
            <div class="flex items-center justify-between text-xs mb-1">
              <span>{{ s.name }}</span>
              <span class="text-muted">{{ s.done }}/{{ s.total }}
                <span class="ml-2 px-1.5 py-0.5 rounded text-[9px]" :class="stClass(s.status)">{{ (s.status || '').toUpperCase() }}</span>
              </span>
            </div>
            <div class="h-3 rounded-full bg-surface-2 overflow-hidden">
              <div class="h-full rounded-full bg-green-500" :style="{ width: s.pct + '%' }" />
            </div>
          </div>
          <div v-if="!a.sprint_progress.length" class="text-xs text-muted">No sprints.</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from 'frappe-ui'
import Donut from '@/components/charts/Donut.vue'
import Bars from '@/components/charts/Bars.vue'
import Gauge from '@/components/charts/Gauge.vue'

const loading = ref(true)
const a = ref({ kpis: {}, status_distribution: [], type_distribution: [], workload: [], storypoints: {}, sprint_progress: [] })

const kpiCards = computed(() => [
  { label: 'Completed', value: a.value.kpis.completed || 0, color: '#22c55e' },
  { label: 'Blocked', value: a.value.kpis.blocked || 0, color: '#ef4444' },
  { label: 'Flagged', value: a.value.kpis.flagged || 0, color: '#f59e0b' },
  { label: 'Delayed', value: a.value.kpis.delayed || 0, color: '#6366f1' },
])

function stClass(s) {
  return { Active: 'bg-green-500/15 text-green-400', Completed: 'bg-gray-500/15 text-gray-400', Planned: 'bg-blue-500/15 text-blue-400' }[s] || 'bg-gray-500/15 text-gray-400'
}

onMounted(async () => {
  a.value = await call('pulse.api.analytics.get_analytics').catch(() => a.value)
  loading.value = false
})
</script>

<style scoped>
.card { border-radius: 0.75rem; border: 1px solid var(--border); background: var(--surface); padding: 1rem; }
.card-title { font-size: 0.75rem; font-weight: 500; color: var(--muted); margin-bottom: 0.5rem; }
</style>
