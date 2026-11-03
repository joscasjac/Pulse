<template>
  <section class="field-settings" aria-labelledby="field-settings-heading">
    <h3 id="field-settings-heading">Task fields and stage requirements</h3>
    <p class="text-muted">Choose fields for this project's task form. Required fields are enforced when tasks enter or remain in the selected statuses.</p>
    <p v-if="loading" role="status">Loading fields…</p>
    <p v-if="error" role="alert">{{ error }} <button @click="load">Retry</button></p>
    <template v-if="config">
      <div v-for="(rule, index) in rules" :key="rule.fieldname" class="field-rule">
        <div class="rule-heading"><strong>{{ label(rule.fieldname) }}</strong><label><input v-model="rule.show_in_form" type="checkbox" :disabled="!config.can_manage" /> Show in task details</label><button :disabled="!config.can_manage || busy" @click="rules.splice(index, 1)">Remove rule</button></div>
        <fieldset><legend>Required in</legend><label v-for="status in statuses" :key="status.label"><input type="checkbox" :checked="required(rule, status.label)" :disabled="!config.can_manage || busy" @change="toggle(rule, status.label, $event.target.checked)" />{{ status.label }}</label></fieldset>
      </div>
      <form v-if="config.can_manage" class="add-rule" @submit.prevent="addRule"><label>Add project field<select v-model="selected" class="field-control" required><option value="">Choose a field</option><option v-for="field in available" :key="field.fieldname" :value="field.fieldname">{{ field.label }}</option></select></label><button class="field-control" :disabled="!selected || busy">Add field</button></form>
      <fieldset class="approval-stages"><legend>Require approval before entering</legend><label v-for="status in statuses" :key="status.label"><input v-model="approvalStatuses" type="checkbox" :value="status.label" :disabled="!config.can_manage || busy" />{{ status.label }}</label></fieldset>
      <button v-if="config.can_manage" class="field-control" :disabled="busy" @click="save">{{ busy ? 'Saving…' : 'Save task fields' }}</button>
      <details v-if="config.can_create" class="create-field"><summary>Create a company field</summary><p class="text-muted">This creates a native ERPNext Task custom field. Projects choose whether to display or require it.</p><form @submit.prevent="create"><label>Label<input v-model.trim="draft.label" class="field-control" required maxlength="80" /></label><label>Type<select v-model="draft.fieldtype" class="field-control"><option v-for="type in fieldTypes" :key="type">{{ type }}</option></select></label><label v-if="draft.fieldtype === 'Select'">Choices, one per line<textarea v-model="draft.options" class="field-control" required rows="3" maxlength="4000" /></label><button class="field-control" :disabled="busy || !draft.label">Create field</button></form></details>
      <p v-if="notice" role="status">{{ notice }}</p>
    </template>
  </section>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ project: String, statuses: { type: Array, default: () => [] } })
const emit = defineEmits(['changed'])
const approvalStatuses = ref([])
const config = ref(null), rules = ref([]), selected = ref(''), loading = ref(false), busy = ref(false), error = ref(''), notice = ref('')
const draft = ref({ label: '', fieldtype: 'Data', options: '' })
const fieldTypes = ['Data', 'Small Text', 'Text', 'Int', 'Float', 'Currency', 'Percent', 'Date', 'Check', 'Select']
const available = computed(() => (config.value?.fields || []).filter(field => !rules.value.some(rule => rule.fieldname === field.fieldname)))
const label = name => config.value?.fields.find(field => field.fieldname === name)?.label || name
const required = (rule, status) => (rule.required_statuses || '').split('\n').includes(status)
function toggle(rule, status, enabled) { const values = new Set((rule.required_statuses || '').split('\n').filter(Boolean)); enabled ? values.add(status) : values.delete(status); rule.required_statuses = [...values].join('\n') }
function message(e, fallback) { return e?.messages?.filter(m => typeof m === 'string').join(' ') || fallback }
let version = 0
async function load() { const token = ++version; loading.value = true; error.value = ''; try { const result = await call('pulse.api.task_config.get_field_config', { project: props.project }); if (token === version) { config.value = result; approvalStatuses.value = result.approval_statuses || []; rules.value = result.rules.map(rule => ({ ...rule, show_in_form: !!rule.show_in_form })) } } catch (e) { if (token === version) error.value = message(e, 'Could not load task fields.') } finally { if (token === version) loading.value = false } }
function addRule() { if (!selected.value) return; rules.value.push({ fieldname: selected.value, show_in_form: true, required_statuses: '' }); selected.value = '' }
async function save() { busy.value = true; error.value = ''; notice.value = ''; try { config.value = await call('pulse.api.task_config.save_field_config', { project: props.project, rules: JSON.stringify(rules.value), approval_statuses: JSON.stringify(approvalStatuses.value) }); notice.value = 'Task fields saved.'; emit('changed') } catch (e) { error.value = message(e, 'Could not save field rules. Save workflow status names first.') } finally { busy.value = false } }
async function create() { busy.value = true; error.value = ''; notice.value = ''; try { const result = await call('pulse.api.task_config.create_custom_task_field', { project: props.project, ...draft.value }); config.value = result.config; rules.value.push({ fieldname: result.fieldname, show_in_form: true, required_statuses: '' }); draft.value = { label: '', fieldtype: 'Data', options: '' }; notice.value = 'Company field created. Save task fields to use it in this project.' } catch (e) { error.value = message(e, 'Could not create company field.') } finally { busy.value = false } }
watch(() => props.project, () => { config.value = null; rules.value = []; notice.value = ''; load() }, { immediate: true })
</script>
<style scoped>
.field-settings{margin-top:24px;padding-top:20px;border-top:1px solid var(--border);font-size:13px;max-width:900px}.field-settings h3{font-weight:600}.field-settings p{margin:8px 0}.field-rule{border-bottom:1px solid var(--border);padding:14px 0}.rule-heading{display:flex;align-items:center;gap:18px;flex-wrap:wrap}.rule-heading strong{font-weight:500;margin-right:auto}.field-settings label{display:flex;gap:6px;align-items:center}.field-settings fieldset{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px}.field-settings legend{font-size:12px;color:var(--muted);margin-bottom:6px}.add-rule{display:flex;align-items:end;gap:10px;margin:16px 0}.add-rule label,.create-field label{display:grid;gap:6px}.field-control{border:1px solid var(--border);border-radius:6px;min-height:32px;padding:6px 8px;background:var(--surface);color:var(--text)}.create-field{margin-top:20px}.create-field form{display:grid;gap:12px;max-width:420px;margin-top:12px}.field-settings button{font-size:12px}.field-settings :disabled{opacity:.5}.field-settings :focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style>
