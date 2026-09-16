<template>
  <section class="settings" aria-label="Project task settings">
    <div class="flex justify-between items-center"><h2 class="text-sm font-semibold">Task settings</h2><button @click="$emit('close')">Close</button></div>
    <p class="text-sm text-muted my-3">Define this project's workflow. Status order sets the board column order. Categories keep reporting consistent. Move tasks before removing a status or changing its category.</p>
    <p v-if="error" role="alert" class="text-sm text-red-600">{{ error }}</p>
    <div v-for="(s, i) in statuses" :key="i" class="status-row">
      <input v-model="s.color" type="color" :aria-label="`Color for ${s.label}`" />
      <input v-model="s.label" class="control" :aria-label="`Status ${i + 1} name`" />
      <select v-model="s.category" class="control" :aria-label="`Category for ${s.label}`"><option v-for="c in categories" :key="c">{{ c }}</option></select>
      <div class="status-actions">
        <button class="control" @click="moveStatus(i, -1)" :disabled="saving || i === 0" :aria-label="`Move ${s.label} up`">Up</button>
        <button class="control" @click="moveStatus(i, 1)" :disabled="saving || i === statuses.length - 1" :aria-label="`Move ${s.label} down`">Down</button>
        <button @click="statuses.splice(i, 1)" :disabled="saving || statuses.length === 1" :aria-label="`Remove ${s.label}`">Remove</button>
      </div>
    </div>
    <button class="control my-2" @click="statuses.push({ label: '', color: '#64748b', category: 'To Do' })">Add status</button>
    <h3 class="font-medium mt-4 mb-2">Allowed task types</h3>
    <p class="text-xs text-muted mb-2">No selection allows all task types.</p>
    <div class="flex flex-wrap gap-3"><label v-for="t in types" :key="t" class="text-sm flex gap-1"><input type="checkbox" v-model="selectedTypes" :value="t" />{{ t }}</label></div>
    <button class="control mt-4" :disabled="saving" @click="save">{{ saving ? 'Saving…' : 'Save workflow' }}</button>
    <h3 class="font-medium mt-6 mb-2">Labels</h3>
    <div v-for="label in labels" :key="label.name" class="label-row">
      <input type="color" v-model="label.color" :aria-label="`Color for ${label.label_name}`" />
      <input class="control" v-model="label.label_name" aria-label="Label name" />
      <button :disabled="saving" @click="saveLabel(label)">Save label</button>
    </div>
    <div class="label-row mt-2"><input type="color" v-model="newLabel.color" aria-label="New label color" /><input class="control" v-model="newLabel.label_name" placeholder="New label name" aria-label="New label name" /><button :disabled="saving || !newLabel.label_name.trim()" @click="saveLabel(newLabel)">Add label</button></div>
  </section>
</template>
<script setup>
import { ref, reactive, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ project: String })
const emit = defineEmits(['close', 'changed'])
const statuses = ref([]), labels = ref([]), types = ref([]), selectedTypes = ref([]), saving = ref(false), error = ref('')
const newLabel = reactive({ label_name: '', color: '#3b82f6' })
const categories = ['Backlog', 'To Do', 'In Progress', 'In Review', 'Blocked', 'Done', 'Cancelled']
function moveStatus(index, direction) {
  const target = index + direction
  if (saving.value || target < 0 || target >= statuses.value.length) return
  const [status] = statuses.value.splice(index, 1)
  statuses.value.splice(target, 0, status)
}
watch(() => props.project, async project => {
  try {
    const [config, all] = await Promise.all([call('pulse.api.task_config.get_config', { project }), call('frappe.client.get_list', { doctype: 'Task Type', fields: ['name'], limit_page_length: 0 })])
    statuses.value = config.statuses; labels.value = config.labels; selectedTypes.value = config.task_types; types.value = all.map(t => t.name)
  } catch (e) { error.value = e?.messages?.[0] || 'Could not load task settings.' }
}, { immediate: true })
async function save() {
  saving.value = true; error.value = ''
  try { await call('pulse.api.task_config.save_config', { project: props.project, statuses: JSON.stringify(statuses.value), task_types: JSON.stringify(selectedTypes.value) }); emit('changed') }
  catch (e) { error.value = e?.messages?.[0] || 'Could not save workflow. Check status names and categories.' }
  finally { saving.value = false }
}
async function saveLabel(label) {
  saving.value = true; error.value = ''
  try { const result = await call('pulse.api.task_config.save_label', { project: props.project, ...label }); if (!label.name) { labels.value.push(result); newLabel.label_name = '' } emit('changed') }
  catch (e) { error.value = e?.messages?.[0] || 'Could not save label.' }
  finally { saving.value = false }
}
</script>
<style scoped>
.settings { padding: 20px 24px; border-bottom: 1px solid var(--border); max-height: 65vh; overflow: auto; background: var(--surface); }
.status-row { display: grid; grid-template-columns: 36px minmax(100px, 1fr) minmax(100px, 1fr) auto; align-items: center; gap: 10px; margin: 8px 0; max-width: 750px; }
.label-row { display: flex; gap: 10px; align-items: center; }
.status-actions { display: flex; align-items: center; gap: 8px; }
.status-actions .control:hover:not(:disabled) { background: var(--surface-2); }
.control { border: 1px solid var(--border); border-radius: 6px; background: var(--surface); min-height: 32px; padding: 6px 8px; color: var(--text); min-width: 0; }
input[type=color] { width: 32px; height: 30px; background: transparent; }
button:disabled { opacity: .5; }
@media(max-width: 600px) { .settings { padding: 16px; } .status-row { grid-template-columns: 32px 1fr; } .label-row { flex-wrap: wrap; } }
button { font-size: 12px; }
button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
