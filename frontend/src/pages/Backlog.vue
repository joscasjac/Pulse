<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold mb-4">Backlog</h1>
    <div v-if="loading" class="text-muted py-20 text-center">Loading...</div>
    <div v-else class="space-y-1">
      <div
        v-for="t in tasks"
        :key="t.name"
        class="flex items-center gap-3 px-3 py-2 rounded-md border border-app bg-surface hover-app"
      >
        <span class="px-1.5 py-0.5 rounded bg-surface-2 text-xs">{{ t.task_type || 'Task' }}</span>
        <span class="flex-1 text-sm text-app">{{ t.subject }}</span>
        <span class="text-xs text-muted">{{ t.status }}</span>
      </div>
      <div v-if="!tasks.length" class="py-10 text-center text-muted">Backlog is empty.</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'

const loading = ref(true)
const tasks = ref([])

onMounted(async () => {
  tasks.value = await call('frappe.client.get_list', {
    doctype: 'Task',
    fields: ['name', 'subject', 'type as task_type', 'status'],
    order_by: 'pulse_rank asc, modified desc',
    limit_page_length: 0,
  }).catch(() => [])
  loading.value = false
})
</script>
