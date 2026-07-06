<template>
  <div class="p-6">
    <h1 class="text-lg font-semibold tracking-tight mb-4">My Work</h1>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="flex items-center gap-4 py-2 border-b border-soft">
        <Skeleton width="52px" height="12px" /><Skeleton width="40%" height="13px" />
        <Skeleton width="60px" height="16px" radius="5px" /><div class="ml-auto"><Skeleton width="80px" height="12px" /></div>
      </div>
    </div>

    <table v-else class="w-full text-sm border-collapse">
      <thead>
        <tr class="text-left text-faint border-b border-app text-[11px] uppercase tracking-wide">
          <th class="py-2 font-medium w-16">Key</th>
          <th class="py-2 font-medium">Issue</th>
          <th class="py-2 font-medium w-24">Type</th>
          <th class="py-2 font-medium w-28">Priority</th>
          <th class="py-2 font-medium w-32">Status</th>
          <th class="py-2 font-medium">Project</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in tasks" :key="t.name" class="border-b border-soft hover-app cursor-pointer" @click="openId = t.name">
          <td class="py-2.5 mono text-[11px] text-faint">{{ t.issue_key }}</td>
          <td class="py-2.5 font-medium text-app">{{ t.subject }}</td>
          <td class="py-2.5"><TypeTag :value="t.task_type" /></td>
          <td class="py-2.5"><PriorityDot :value="t.priority" show-label /></td>
          <td class="py-2.5"><StatusPill :value="t.status" /></td>
          <td class="py-2.5 text-muted">{{ t.project || '-' }}</td>
        </tr>
        <tr v-if="!tasks.length"><td colspan="6" class="py-16 text-center text-faint">No tasks assigned to you yet.</td></tr>
      </tbody>
    </table>
    <TaskDrawer :task-id="openId" @close="openId = null" @changed="reload" @open="openId = $event" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'
import TaskDrawer from '@/components/TaskDrawer.vue'
import TypeTag from '@/ui/TypeTag.vue'
import PriorityDot from '@/ui/PriorityDot.vue'
import StatusPill from '@/ui/StatusPill.vue'
import Skeleton from '@/ui/Skeleton.vue'

const loading = ref(true)
const tasks = ref([])
const openId = ref(null)

async function reload() {
  const me = await call('frappe.auth.get_logged_user')
  tasks.value = await call('frappe.client.get_list', {
    doctype: 'Pulse Task',
    fields: ['name', 'issue_key', 'subject', 'task_type', 'priority', 'status', 'project'],
    filters: [['_assign', 'like', `%${me}%`]],
    order_by: 'modified desc',
    limit_page_length: 0,
  })
  loading.value = false
}
onMounted(reload)
</script>
