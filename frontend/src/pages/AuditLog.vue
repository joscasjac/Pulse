<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-semibold">Audit Logs</h1>
        <p class="text-sm text-muted">Timestamped monitor log of activity across Pulse.</p>
      </div>
      <select v-model="project" @change="load" class="text-xs bg-surface border border-app rounded-md px-2 py-1.5">
        <option :value="null">All projects</option>
        <option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option>
      </select>
    </div>

    <div v-if="loading" class="text-muted py-20 text-center">Loading...</div>
    <table v-else class="w-full text-sm border-collapse">
      <thead>
        <tr class="text-left text-muted border-b border-app">
          <th class="py-2 font-medium w-44">Timestamp</th>
          <th class="py-2 font-medium">User</th>
          <th class="py-2 font-medium">Action</th>
          <th class="py-2 font-medium">Reference</th>
          <th class="py-2 font-medium">Detail</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(e, i) in entries" :key="i" class="border-b border-app/50 hover-app">
          <td class="py-2 text-muted font-mono text-xs">{{ fmt(e.timestamp) }}</td>
          <td class="py-2">
            <span class="inline-flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-blue-500 text-white text-[9px] grid place-items-center">{{ initials(e.user) }}</span>
              {{ (e.user || '').split('@')[0] }}
            </span>
          </td>
          <td class="py-2"><span class="text-[10px] px-1.5 py-0.5 rounded" :class="actionClass(e.action)">{{ e.action }}</span></td>
          <td class="py-2 font-mono text-xs text-muted">{{ e.reference || '-' }}</td>
          <td class="py-2 text-muted truncate max-w-xs">{{ e.detail || '-' }}</td>
        </tr>
        <tr v-if="!entries.length"><td colspan="5" class="py-10 text-center text-muted">No audit entries.</td></tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'

const loading = ref(true)
const entries = ref([])
const projects = ref([])
const project = ref(null)

function initials(e) { return (e || '?').replace(/@.*/, '').slice(0, 2).toUpperCase() }
function fmt(ts) { return ts ? ts.replace('T', ' ').slice(0, 19) : '' }
function actionClass(act) {
  if (/status/i.test(act)) return 'bg-amber-500/15 text-amber-400'
  if (/assign/i.test(act)) return 'bg-blue-500/15 text-blue-400'
  if (/comment/i.test(act)) return 'bg-green-500/15 text-green-400'
  if (/creat/i.test(act)) return 'bg-purple-500/15 text-purple-400'
  return 'bg-gray-500/15 text-gray-400'
}

async function load() {
  loading.value = true
  const [e, ps] = await Promise.all([
    call('pulse.api.audit.get_audit_log', { project: project.value, limit: 200 }),
    projects.value.length ? Promise.resolve(projects.value)
      : call('frappe.client.get_list', { doctype: 'Pulse Project', fields: ['name', 'project_name'], limit_page_length: 0 }),
  ])
  entries.value = e || []
  projects.value = ps
  loading.value = false
}
onMounted(load)
</script>
