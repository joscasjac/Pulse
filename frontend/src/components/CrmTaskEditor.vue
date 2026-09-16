<!-- THESIS: Edit a CRM follow-up in place. OWN-WORLD: Existing compact neutral form controls. STORY: Change details on the original CRM task. FIRST VIEWPORT: Title, status, priority and timing. FORM: Inline expansion inside My work. -->
<template>
  <form class="crm-editor" @submit.prevent="save">
    <label class="crm-title">Title<input v-model="draft.title" required :disabled="saving" /></label>
    <label>Status<select v-model="draft.status"><option v-for="value in statuses" :key="value">{{ value }}</option></select></label>
    <label>Priority<select v-model="draft.priority"><option v-for="value in ['Low', 'Medium', 'High']" :key="value">{{ value }}</option></select></label>
    <label>Start date<input v-model="draft.start_date" type="date" /></label>
    <label>Due date<input v-model="draft.due_date" type="datetime-local" /></label>
    <p v-if="error" class="crm-error" role="alert">{{ error }}</p>
    <div class="crm-actions"><button type="button" class="btn-ghost" :disabled="saving" @click="$emit('close')">Cancel</button><button class="btn-primary" :disabled="saving">{{ saving ? 'Saving…' : 'Save changes' }}</button></div>
  </form>
</template>
<script setup>
import { reactive, ref } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ task: { type: Object, required: true } })
const emit = defineEmits(['saved', 'close'])
const statuses = ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled']
const draft = reactive({ title: props.task.subject, status: props.task.crm_status, priority: props.task.priority || 'Medium', start_date: props.task.start_date || '', due_date: (props.task.due_date || '').replace(' ', 'T').slice(0, 16) })
const saving = ref(false), error = ref('')
async function save() {
  saving.value = true; error.value = ''
  try {
    const row = await call('pulse.api.crm_tasks.update', { task: props.task.name, modified: props.task.modified, fields: { ...draft, start_date: draft.start_date || null, due_date: draft.due_date ? draft.due_date.replace('T', ' ') : null } })
    emit('saved', row)
  } catch { error.value = 'Could not save. The task may have changed or your access changed. Cancel and refresh before trying again.' }
  finally { saving.value = false }
}
</script>
<style scoped>
.crm-editor { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; padding: 16px; background: var(--surface-2); }
.crm-editor label { display: grid; gap: 6px; color: var(--muted); font-size: 12px; }.crm-title { grid-column: 1 / -1; }
.crm-editor input, .crm-editor select { min-width: 0; height: 34px; border: 1px solid var(--border); background: var(--surface); border-radius: 6px; padding: 0 8px; color: var(--text); }
.crm-actions, .crm-error { grid-column: 1 / -1; }.crm-actions { display: flex; justify-content: flex-end; gap: 8px; }.crm-error { color: var(--danger); }
@media (max-width: 768px) { .crm-editor { grid-template-columns: 1fr; } }
</style>
