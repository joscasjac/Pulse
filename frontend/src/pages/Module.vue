<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-bold">{{ cfg?.title || 'Module' }}</h1>
      <button v-if="cfg" @click="openEntity(cfg.doctype)" class="btn-primary">
        <Plus class="w-3.5 h-3.5" /> New {{ singular }}
      </button>
    </div>
    <div v-if="loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="flex gap-4 py-2 border-b border-soft"><Skeleton width="30%" height="13px" /><Skeleton width="16%" height="13px" /><div class="ml-auto"><Skeleton width="80px" height="13px" /></div></div>
    </div>
    <div v-else class="card-surface overflow-x-auto">
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="c in cfg.columns" :key="c.key">{{ c.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.name" class="cursor-pointer" @click="openEntity(cfg.doctype, row.name)">
          <td v-for="c in cfg.columns" :key="c.key"
              :class="c.primary ? 'font-medium text-app' : 'text-muted'">
            <template v-if="c.type === 'percent'">
              <div class="flex items-center gap-2">
                <div class="w-20 h-1.5 rounded-full bg-surface-2">
                  <div class="h-full rounded-full" :style="{ width: (row[c.key] || 0) + '%', background: 'var(--accent)' }" />
                </div>
                <span class="text-xs">{{ Math.round(row[c.key] || 0) }}%</span>
              </div>
            </template>
            <template v-else-if="c.type === 'badge'">
              <span v-if="row[c.key]" class="text-xs px-1.5 py-0.5 rounded bg-surface-2">{{ row[c.key] }}</span>
              <span v-else class="text-muted">-</span>
            </template>
            <template v-else-if="c.type === 'check'">
              <span :class="row[c.key] ? 'term-green' : 'text-muted'">{{ row[c.key] ? 'Yes' : 'No' }}</span>
            </template>
            <template v-else>{{ row[c.key] ?? '-' }}</template>
          </td>
        </tr>
        <tr v-if="!rows.length"><td :colspan="cfg.columns.length" class="py-16 text-center text-faint">No records yet. Create your first {{ singular.toLowerCase() }}.</td></tr>
      </tbody>
    </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { call } from 'frappe-ui'
import { MODULES } from '@/modules'
import { openEntity, entityState } from '@/ui/entity'
import Skeleton from '@/ui/Skeleton.vue'
import Plus from '~icons/lucide/plus'

const route = useRoute()
const loading = ref(true)
const rows = ref([])
const cfg = ref(null)
const singular = computed(() => (cfg.value?.doctype || '').replace(/^Pulse /, ''))

async function load() {
  cfg.value = MODULES[route.params.mod]
  if (!cfg.value) { rows.value = []; loading.value = false; return }
  loading.value = true
  rows.value = await call('frappe.client.get_list', {
    doctype: cfg.value.doctype,
    fields: ['name', ...cfg.value.columns.map((c) => c.key)],
    order_by: 'modified desc',
    limit_page_length: 0,
  }).catch(() => [])
  loading.value = false
}

watch(() => route.params.mod, load, { immediate: true })
watch(() => entityState.saved, load)
</script>

<style scoped>
.new-btn { background: var(--accent); transition: filter 0.12s; }
.new-btn:hover { filter: brightness(1.08); }
</style>
