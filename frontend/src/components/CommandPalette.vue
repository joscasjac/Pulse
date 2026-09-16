<template>
  <dialog ref="dialog" class="command-dialog bg-surface text-app rounded-xl p-0 border border-app" @close="$emit('close')" @click="backdrop">
    <form method="dialog" class="flex items-center border-b border-app p-3 gap-3">
      <input ref="input" v-model="query" aria-label="Search tasks, projects and pages" placeholder="Search tasks, projects and pages…" class="flex-1 min-w-0 bg-transparent outline-none p-2" @keydown.down.prevent="move(1)" @keydown.up.prevent="move(-1)" @keydown.enter.prevent="activate(options[selected])">
      <button aria-label="Close search" class="btn">Esc</button>
    </form>
    <div class="p-2 max-h-[60vh] overflow-auto">
      <p v-if="busy" class="p-3 text-muted" role="status">Searching…</p>
      <p v-else-if="error" class="p-3" role="alert">{{ error }} <button class="underline" @click="search">Retry</button></p>
      <p v-else-if="query.length > 1 && !options.length" class="p-3 text-muted">No matching tasks, projects or pages.</p>
      <p v-else-if="!query" class="p-3 text-muted text-xs">Favorites and recently opened</p>
      <button v-for="(item, i) in options" :key="item.url || item.name" :ref="el => optionElements[i] = el" :class="['command-row', { 'bg-app': selected === i }]" @click="activate(item)">
        <span class="truncate">{{ item.title }}</span><span class="text-muted text-xs shrink-0">{{ item.doctype }}</span>
      </button>
    </div>
    <p class="p-3 border-t border-app text-xs text-muted">↑ ↓ select · Enter opens · Ctrl/⌘ K search · N creates a task</p>
  </dialog>
</template>
<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { call } from 'frappe-ui'
import { openCreate } from '@/ui/create'
const props = defineProps({ open: Boolean }); const emit = defineEmits(['close'])
const route = useRoute()
const router = useRouter(), dialog = ref(), input = ref(), query = ref(''), results = ref([]), busy = ref(false), error = ref(''), selected = ref(0)
const commands = [
  { name: 'create', title: 'New task', doctype: 'Action' },
  { url: '/inbox', title: 'Open inbox', doctype: 'Navigate' },
  { url: '/views', title: 'Open views', doctype: 'Navigate' },
  { url: '/documents', title: 'Open pages', doctype: 'Navigate' },
]
const optionElements = ref([])
const options = computed(() => [...commands.filter(item => item.title.toLowerCase().includes(query.value.toLowerCase().trim())), ...results.value])
let timer, generation = 0
watch(() => props.open, async value => {
  if (value) { dialog.value.showModal(); query.value = ''; await nextTick(); input.value?.focus(); search() }
  else dialog.value?.close()
})
watch(query, () => { ++generation; selected.value = 0; results.value = []; clearTimeout(timer); timer = setTimeout(search, 200) })
async function search() {
  const request = ++generation; busy.value = true; error.value = ''
  try {
    let rows
    if (query.value.trim().length >= 2) rows = await call('pulse.api.personal.search', { q: query.value })
    else if (!query.value.trim()) {
      const items = await call('pulse.api.personal.items')
      const seen = new Set()
      rows = items.filter(r => r.kind !== 'Follow').sort((a,b) => Number(b.kind === 'Favorite') - Number(a.kind === 'Favorite')).filter(r => { const key = r.reference_doctype + r.reference_name; if (seen.has(key)) return false; seen.add(key); return true }).slice(0,20).map(r => ({ ...r, doctype: r.reference_doctype, name: r.reference_name }))
    } else rows = []
    if (request === generation) { results.value = rows; selected.value = 0 }
  } catch { if (request === generation) error.value = 'Search could not load.' }
  finally { if (request === generation) busy.value = false }
}
function move(delta) { selected.value = Math.max(0, Math.min(options.value.length - 1, selected.value + delta)); optionElements.value[selected.value]?.scrollIntoView({ block: 'nearest' }) }
function activate(item) { if (item?.name === 'create') return create(); if (item?.doctype === 'Navigate') return go(item.url); if (item) { call('pulse.api.personal.remember', { doctype: item.doctype, name: item.name }).catch(() => {}); go(item.url) } }
function go(url) { router.push(url); emit('close') }
function create() { emit('close'); openCreate(typeof route.query.project === 'string' ? { project: route.query.project } : {}) }
function backdrop(e) { if (e.target === dialog.value) { const r = dialog.value.getBoundingClientRect(); if(e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) emit('close') } }
onBeforeUnmount(() => { ++generation; clearTimeout(timer) })
</script>
<style scoped>
.command-dialog { width: min(640px, calc(100vw - 24px)); margin: 12vh auto auto; }
.command-dialog::backdrop { background: #0008; }
.command-row { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:12px; width:100%; text-align:left; border-radius:6px; }
.command-row:hover, .command-row:focus-visible { background:var(--surface-2); }
</style>
