<template>
  <section class="transfer-panel" aria-labelledby="transfer-heading" :aria-busy="busy">
    <header><div><h2 id="transfer-heading">{{ project.project_name }} / Import and export</h2><p class="text-muted">Move tasks with a UTF-8 CSV file. Import up to 500 rows at a time.</p></div><button class="btn-ghost" @click="$emit('close')">Close</button></header>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <div class="transfer-actions"><button class="btn-ghost" :disabled="busy" @click="template">Download template</button><button class="btn-ghost" :disabled="busy" @click="exportCsv">Export accessible tasks</button></div>
    <form @submit.prevent="preview">
      <label>Choose CSV file<input type="file" accept=".csv,text/csv" :disabled="busy" @change="readFile" /></label>
      <label>Or paste CSV<textarea v-model="content" rows="6" class="field" :disabled="busy" spellcheck="false" placeholder="subject,priority&#10;Prepare launch,High" @input="invalidate" /></label>
      <p class="text-muted">Leave name blank to create a task. Use an exported task ID to update it. Only columns included in the CSV are changed. Formula-like export cells are prefixed with an apostrophe for spreadsheet safety.</p>
      <button class="btn-primary" :disabled="busy || !content.trim()">{{ busy ? 'Working…' : 'Preview import' }}</button>
    </form>
    <section v-if="plan" class="import-preview" aria-label="Import preview">
      <h3>{{ plan.create }} to create · {{ plan.update }} to update</h3><p class="text-muted">Headers and record access checked. Import validates every task and saves the whole batch together. Preview shows the first ten rows.</p>
      <div class="preview-scroll"><table><thead><tr><th>Task ID</th><th>Subject</th><th>Priority</th></tr></thead><tbody><tr v-for="(row, index) in plan.rows" :key="index"><td>{{ row.name || 'New task' }}</td><td>{{ row.subject }}</td><td>{{ row.priority || 'Default' }}</td></tr></tbody></table></div>
      <button class="btn-primary" :disabled="busy" @click="importCsv">{{ busy ? 'Importing…' : `Import ${plan.count} tasks` }}</button>
    </section>
  </section>
</template>
<script setup>
import { ref } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['close', 'changed'])
const content = ref(''), plan = ref(null), busy = ref(false), error = ref(''), notice = ref('')
function message(e, fallback) { return Array.isArray(e?.messages) && e.messages.length ? e.messages.join(' ') : fallback }
async function perform(action, fallback) { busy.value = true; error.value = ''; try { await action() } catch (e) { error.value = message(e, fallback) } finally { busy.value = false } }
function download(result) { const url = URL.createObjectURL(new Blob([result.content], { type: 'text/csv;charset=utf-8' })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = result.filename; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000) }
let fileGeneration = 0
function invalidate() { fileGeneration++; plan.value = null; notice.value = '' }
async function readFile(event) { const generation = ++fileGeneration; plan.value = null; notice.value = ''; error.value = ''; const file = event.target.files?.[0]; if (!file) return; if (file.size > 2000000) { error.value = 'Choose a CSV file smaller than 2 MB.'; return } try { const text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()); if (generation === fileGeneration) { content.value = text; plan.value = null; notice.value = '' } } catch { if (generation === fileGeneration) error.value = 'This file could not be read. Try pasting the CSV instead.' } }
function template() { return perform(async () => download(await call('pulse.api.transfer.csv_template', { project: props.project.name })), 'Unable to download CSV template.') }
function exportCsv() { return perform(async () => { const result = await call('pulse.api.transfer.export_tasks', { project: props.project.name }); download(result); notice.value = `Exported ${result.count} accessible tasks.` }, 'Unable to export tasks.') }
function preview() { return perform(async () => { plan.value = null; notice.value = ''; plan.value = await call('pulse.api.transfer.preview_import', { project: props.project.name, content: content.value }) }, 'Unable to preview the CSV. Check its headers and row values.') }
function importCsv() { return perform(async () => { const result = await call('pulse.api.transfer.import_tasks', { project: props.project.name, content: content.value }); notice.value = result.replayed ? 'This exact batch was already imported. No duplicate tasks were created.' : `Imported ${result.created.length} new tasks and updated ${result.updated.length} tasks.`; plan.value = null; emit('changed') }, 'Import failed. No changes were saved. Check row values and try again.') }
</script>
<style scoped>
.transfer-panel{margin:16px 0;padding:20px;border:1px solid var(--border-color,#e6e8ec);border-radius:8px}.transfer-panel header,.transfer-actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.transfer-panel h2{font-size:16px;font-weight:600}.transfer-panel p{font-size:13px;margin:8px 0}.transfer-actions{justify-content:flex-start;margin:16px 0}.transfer-panel label{display:grid;gap:6px;margin:12px 0;font-size:13px}.transfer-panel textarea{width:100%;resize:vertical;min-height:120px}.import-preview{margin-top:20px;padding-top:16px;border-top:1px solid var(--border-color,#e6e8ec)}.preview-scroll{overflow:auto;max-height:280px;margin:12px 0}.transfer-panel table{width:100%;font-size:13px;border-collapse:collapse}.transfer-panel th,.transfer-panel td{text-align:left;padding:8px;border-bottom:1px solid var(--border-color,#e6e8ec);overflow-wrap:anywhere}
</style>
