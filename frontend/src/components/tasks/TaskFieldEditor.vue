<template>
  <section v-if="fields.length || error" class="task-extra-fields" aria-label="Project task fields">
    <h3>Project fields</h3><p v-if="error" role="alert">{{ error }} <button @click="load">Retry</button></p>
    <form v-if="fields.length" @submit.prevent="save">
      <label v-for="field in fields" :key="field.fieldname">{{ field.label }}
        <select v-if="field.fieldtype === 'Select'" v-model="values[field.fieldname]" :disabled="!canWrite || busy"><option value="">Choose…</option><option v-for="choice in field.options.split('\n').filter(Boolean)" :key="choice">{{ choice }}</option></select>
        <input v-else-if="field.fieldtype === 'Check'" v-model="values[field.fieldname]" type="checkbox" :disabled="!canWrite || busy" />
        <textarea v-else-if="['Small Text', 'Text', 'Text Editor'].includes(field.fieldtype)" v-model="values[field.fieldname]" rows="3" :disabled="!canWrite || busy" />
        <input v-else v-model="values[field.fieldname]" :type="field.fieldtype === 'Date' ? 'date' : ['Int','Float','Currency','Percent'].includes(field.fieldtype) ? 'number' : 'text'" :step="field.fieldtype === 'Int' ? '1' : 'any'" :disabled="!canWrite || busy" />
      </label><button v-if="canWrite" class="btn" :disabled="busy">{{ busy ? 'Saving…' : 'Save project fields' }}</button><p v-if="notice" role="status">{{ notice }}</p>
    </form>
  </section>
</template>
<script setup>
import { ref, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ task: { type: String, required: true } })
const emit = defineEmits(['changed'])
const fields = ref([]), values = ref({}), canWrite = ref(false), busy = ref(false), error = ref(''), notice = ref('')
let version = 0
function apply(result) { fields.value = result.fields; values.value = Object.fromEntries(result.fields.map(field => [field.fieldname, field.fieldtype === 'Check' ? !!result.values[field.fieldname] : result.values[field.fieldname] ?? ''])); canWrite.value = result.can_write }
async function load() { const token = ++version; error.value = ''; try { const result = await call('pulse.api.task_config.get_task_fields', { task: props.task }); if (token === version) apply(result) } catch (e) { if (token === version) error.value = e?.messages?.join(' ') || 'Could not load project fields.' } }
async function save() { busy.value = true; error.value = ''; notice.value = ''; const token = version; try { const result = await call('pulse.api.task_config.update_task_fields', { task: props.task, values: JSON.stringify(values.value) }); if (token === version) { apply(result); notice.value = 'Project fields saved.'; emit('changed') } } catch (e) { if (token === version) error.value = e?.messages?.join(' ') || 'Could not save project fields.' } finally { if (token === version) busy.value = false } }
watch(() => props.task, () => { fields.value = []; notice.value = ''; busy.value = false; load() }, { immediate: true })
</script>
<style scoped>
.task-extra-fields{padding-top:16px;margin-top:16px;border-top:1px solid var(--border);font-size:13px}.task-extra-fields h3{font-weight:500;margin-bottom:10px}.task-extra-fields form{display:grid;gap:12px}.task-extra-fields label{display:grid;gap:6px}.task-extra-fields input:not([type=checkbox]),.task-extra-fields textarea,.task-extra-fields select{border:1px solid var(--border);border-radius:6px;padding:6px 8px;background:var(--surface);color:var(--text);width:100%}.task-extra-fields button{justify-self:start}.task-extra-fields :focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style>
