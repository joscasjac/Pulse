<template>
  <details class="task-approvals" @toggle="open($event)"><summary>Approvals <span class="text-muted">Review current task content</span></summary>
    <p v-if="loading" role="status">Loading approvals…</p><p v-if="error" role="alert">{{ error }} <button @click="load">Retry</button></p>
    <template v-if="data">
      <p class="text-muted">Approvals apply to the task's current title, description, dates, estimates, labels, assignments and configured project fields. Editing them requires a new approval.</p>
      <ol><li v-for="approval in data.approvals" :key="approval.name"><div><strong>{{ approval.decision }}</strong> · {{ approval.reviewer }} <span v-if="!approval.current" class="text-muted">· Earlier task version</span></div><p v-if="approval.note">{{ approval.note }}</p><small class="text-muted">Requested by {{ approval.requested_by }} · {{ approval.creation }}</small><form v-if="approval.can_decide" @submit.prevent="decide(approval, 'Approved')"><label>Decision note<textarea v-model="notes[approval.name]" rows="2" maxlength="5000" :disabled="busy" /></label><div class="approval-actions"><button class="btn" :disabled="busy">Approve current version</button><button type="button" class="btn-ghost" :disabled="busy" @click="decide(approval, 'Rejected')">Reject</button></div></form></li></ol>
      <p v-if="!data.approvals.length" class="text-muted">No approval requests yet.</p>
      <p v-if="data.can_request && !data.reviewers.length" class="text-muted">No other enabled user can review this task yet. Ask a project administrator to add a reviewer with task write access.</p>
      <form v-if="data.can_request" @submit.prevent="request"><label>Request review from<select v-model="reviewer" required :disabled="busy"><option value="">Choose a reviewer</option><option v-for="user in data.reviewers" :key="user.name" :value="user.name">{{ user.full_name }} · {{ user.name }}</option></select></label><button class="btn" :disabled="busy || !reviewer">{{ busy ? 'Saving…' : 'Request approval' }}</button></form>
      <p v-if="notice" role="status">{{ notice }}</p>
    </template>
  </details>
</template>
<script setup>
import { ref, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ task: String })
const data = ref(null), notes = ref({}), reviewer = ref(''), loading = ref(false), busy = ref(false), error = ref(''), notice = ref('')
let version = 0
async function load() { const token = ++version; loading.value = true; error.value = ''; try { const result = await call('pulse.api.approvals.get_approvals', { task: props.task }); if (token === version) data.value = result } catch (e) { if (token === version) error.value = e?.messages?.join(' ') || 'Could not load task approvals.' } finally { if (token === version) loading.value = false } }
function open(event) { if (event.target.open) load() }
async function action(method, values, success) { busy.value = true; error.value = ''; notice.value = ''; try { await call('pulse.api.approvals.' + method, values); await load(); notice.value = success } catch (e) { error.value = e?.messages?.join(' ') || 'Could not save approval. Refresh the task and try again.' } finally { busy.value = false } }
async function request() { await action('request_approval', { task: props.task, reviewer: reviewer.value }, 'Approval requested.') }
async function decide(approval, decision) { await action('decide', { name: approval.name, decision, note: notes.value[approval.name] || '' }, 'Approval decision saved.') }
watch(() => props.task, () => { version++; data.value = null; notes.value = {}; reviewer.value = ''; notice.value = '' })
</script>
<style scoped>
.task-approvals{padding:16px 0;border-top:1px solid var(--border);font-size:13px}.task-approvals summary{cursor:pointer;font-weight:500}.task-approvals summary span{font-size:12px;margin-left:8px;font-weight:400}.task-approvals p{margin:8px 0;white-space:pre-wrap}.task-approvals li{padding:12px 0;border-bottom:1px solid var(--border)}.task-approvals strong{font-weight:600}.task-approvals form{display:grid;gap:10px;margin-top:12px}.task-approvals label{display:grid;gap:6px}.task-approvals textarea,.task-approvals select{padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text);width:100%}.task-approvals button{justify-self:start}.approval-actions{display:flex;gap:10px}.task-approvals :focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style>
