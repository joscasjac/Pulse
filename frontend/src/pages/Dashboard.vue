<template>
  <div class="p-6 max-w-[1400px]">
    <!-- header -->
    <div class="flex items-start justify-between gap-4 flex-wrap mb-5">
      <div>
        <h1 class="text-2xl font-bold">Dashboard</h1>
        <p class="text-sm text-muted mt-0.5">Plan, prioritise and accomplish your work with ease.</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="openEntity('Project')" class="new-btn flex items-center gap-1.5 px-4 py-2 text-sm font-medium">
          <Plus class="w-4 h-4" /> Add project
        </button>
        <router-link to="/dashboard/custom" class="ghost-btn flex items-center gap-1.5 px-4 py-2 text-sm font-medium">
          <LayoutDashboard class="w-4 h-4" /> Customise
        </router-link>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div v-for="n in 4" :key="n" class="card-surface p-5"><Skeleton width="60%" height="12px" /><div class="mt-3"><Skeleton width="40%" height="26px" /></div></div>
    </div>

    <template v-else>
      <!-- stat cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div v-for="(s, i) in stats" :key="s.label" class="card-surface p-5"
          :style="i === 0 ? { background: 'var(--accent)', borderColor: 'var(--accent)' } : {}">
          <div class="flex items-start justify-between">
            <span class="text-sm" :style="{ color: i === 0 ? 'var(--on-accent)' : 'var(--muted)' }">{{ s.label }}</span>
            <span class="w-7 h-7 rounded-full grid place-items-center shrink-0"
              :style="i === 0 ? { background: 'rgba(0,0,0,.14)', color: 'var(--on-accent)' } : { background: 'var(--surface-2)', color: 'var(--muted)' }">
              <ArrowUpRight class="w-3.5 h-3.5" />
            </span>
          </div>
          <div class="text-3xl font-bold mt-2 tnum" :style="{ color: i === 0 ? 'var(--on-accent)' : 'var(--text)' }">{{ s.value }}</div>
          <div class="text-[11px] mt-1.5" :style="{ color: i === 0 ? 'var(--on-accent)' : 'var(--faint)' }">{{ s.hint }}</div>
        </div>
      </div>

      <!-- middle row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <div class="card-surface p-5 lg:col-span-2">
          <div class="flex items-center justify-between mb-1">
            <h2 class="text-base font-semibold">Project analytics</h2>
            <span class="tele text-[10px] text-faint">last 7 days</span>
          </div>
          <p class="text-xs text-faint mb-4">Tasks completed per day.</p>
          <div class="flex items-end gap-3 h-40">
            <div v-for="(d, i) in data.throughput" :key="i" class="flex-1 flex flex-col items-center gap-2 h-full">
              <div class="w-full flex-1 flex items-end">
                <div class="w-full rounded-lg transition-all"
                  :style="{ height: barHeight(d.value), background: d.value ? 'var(--accent)' : 'var(--surface-2)' }"
                  :title="`${d.value} completed on ${d.date}`" />
              </div>
              <span class="text-[11px] text-faint">{{ d.label }}</span>
            </div>
          </div>
        </div>

        <div class="card-surface p-5 flex flex-col">
          <h2 class="text-base font-semibold mb-3">Reminders</h2>
          <template v-if="data.next_meeting">
            <div class="text-lg font-semibold leading-snug">{{ data.next_meeting.title }}</div>
            <div class="text-xs text-muted mt-1">{{ data.next_meeting.date }}<span v-if="data.next_meeting.organizer"> · {{ data.next_meeting.organizer }}</span></div>
          </template>
          <template v-else>
            <div class="text-sm text-muted">No upcoming meetings.</div>
            <div class="text-xs text-faint mt-1">Schedule one in the Meetings module.</div>
          </template>
          <router-link to="/m/meetings" class="new-btn mt-auto flex items-center justify-center gap-2 py-2.5 text-sm font-medium">
            <Users class="w-4 h-4" /> Open meetings
          </router-link>
        </div>
      </div>

      <!-- bottom row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <div class="card-surface p-5">
          <h2 class="text-base font-semibold mb-3">Team collaboration</h2>
          <div v-for="t in data.team" :key="t.user" class="flex items-center gap-3 py-2">
            <Avatar :name="t.user" :size="30" />
            <div class="min-w-0 flex-1">
              <div class="text-sm font-medium truncate">{{ t.user.split('@')[0] }}</div>
              <div class="text-[11px] text-muted truncate">Working on <span class="text-app">{{ t.task }}</span></div>
            </div>
            <StatusPill :value="t.state" />
          </div>
          <div v-if="!data.team.length" class="text-sm text-faint py-6 text-center">Nothing assigned yet.</div>
        </div>

        <div class="card-surface p-5 flex flex-col">
          <h2 class="text-base font-semibold mb-2">Project progress</h2>
          <div class="flex-1 grid place-items-center">
            <Gauge :value="data.tasks.pct" label="completed" />
          </div>
          <div class="flex items-center gap-4 text-[11px] text-muted mt-3 flex-wrap justify-center">
            <span class="inline-flex items-center gap-1.5"><i class="dot" style="background:var(--accent)" />Done {{ data.tasks.done }}</span>
            <span class="inline-flex items-center gap-1.5"><i class="dot" style="background:var(--term-green)" />In progress {{ data.tasks.in_progress }}</span>
            <span class="inline-flex items-center gap-1.5"><i class="dot" style="background:var(--faint)" />Pending {{ data.tasks.pending }}</span>
          </div>
        </div>

        <div class="flex flex-col gap-4">
          <div class="card-surface p-5">
            <div class="flex items-center justify-between mb-2">
              <h2 class="text-base font-semibold">Projects</h2>
              <router-link to="/projects" class="text-xs text-accent">View all</router-link>
            </div>
            <div v-for="p in data.upcoming" :key="p.name" class="flex items-center gap-2.5 py-1.5">
              <span class="w-7 h-7 rounded-lg grid place-items-center mono text-[9px] font-bold shrink-0"
                :style="{ background: 'var(--surface-2)', color: 'var(--accent)' }">{{ (p.key || '·').slice(0, 3) }}</span>
              <div class="min-w-0 flex-1">
                <div class="text-sm truncate">{{ p.title }}</div>
                <div class="text-[11px] text-faint">{{ p.due ? 'Due ' + p.due : 'No due date' }}</div>
              </div>
            </div>
            <div v-if="!data.upcoming.length" class="text-sm text-faint py-4 text-center">No active projects.</div>
          </div>

          <div class="card-surface p-5" :style="{ background: 'var(--surface-2)' }">
            <h2 class="text-sm font-semibold text-muted">Time tracked this week</h2>
            <div class="text-3xl font-bold mono mt-1.5 tnum">{{ data.hours_this_week.toFixed(2) }}<span class="text-base text-muted"> h</span></div>
            <p class="text-[11px] text-faint mt-1.5">Measured in Super Productivity and synced — not entered by hand.</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { call } from 'frappe-ui'
import Avatar from '@/ui/Avatar.vue'
import StatusPill from '@/ui/StatusPill.vue'
import Skeleton from '@/ui/Skeleton.vue'
import Gauge from '@/components/charts/Gauge.vue'
import { createState } from '@/ui/create'
import { openEntity, entityState } from '@/ui/entity'
import Plus from '~icons/lucide/plus'
import LayoutDashboard from '~icons/lucide/layout-dashboard'
import ArrowUpRight from '~icons/lucide/arrow-up-right'
import Users from '~icons/lucide/users'

const loading = ref(true)
const data = ref({
  projects: { total: 0, ended: 0, running: 0, pending: 0 },
  tasks: { total: 0, done: 0, in_progress: 0, pending: 0, pct: 0 },
  throughput: [], upcoming: [], team: [], next_meeting: null, hours_this_week: 0,
})

const stats = computed(() => [
  { label: 'Total projects', value: data.value.projects.total, hint: 'All projects in Pulse' },
  { label: 'Ended projects', value: data.value.projects.ended, hint: 'Marked completed' },
  { label: 'Running projects', value: data.value.projects.running, hint: 'Currently open' },
  { label: 'Cancelled', value: data.value.projects.pending, hint: 'Closed without completing' },
])

const maxThroughput = computed(() =>
  Math.max(...(data.value.throughput || []).map((d) => d.value), 1))

function barHeight(v) {
  return `${Math.max((v / maxThroughput.value) * 100, 4)}%`
}

async function reload() {
  data.value = await call('pulse.api.overview.summary').catch(() => data.value)
  loading.value = false
}

watch(() => createState.created, reload)
watch(() => entityState.saved, reload)
onMounted(reload)
</script>

<style scoped>
.ghost-btn {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 999px;
}
.ghost-btn:hover { background: var(--hover); }
.new-btn { background: var(--accent); transition: filter 0.12s; }
.new-btn:hover { filter: brightness(1.06); }
.dot { width: 8px; height: 8px; border-radius: 999px; display: inline-block; }
</style>
