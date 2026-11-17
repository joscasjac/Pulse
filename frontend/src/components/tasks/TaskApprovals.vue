<template>
  <details class="task-approvals" @toggle="open($event)"><summary>{{ __('Approvals') }} <span class="text-muted">{{ __('Review current task content') }}</span></summary>
    <p v-if="loading" role="status">{{ __('Loading approvals…') }}</p><p v-if="error" role="alert">{{ error }} <button @click="load">{{ __('Retry') }}</button></p>
    <template v-if="data">
      <p class="text-muted">{{ __("Approvals apply to the task's current title, description, dates, estimates, labels, assignments and configured project fields. Editing them requires a new approval.") }}</p>
      <ol><li v-for="approval in data.approvals" :key="approval.name"><div><strong>{{ __(approval.decision) }}</strong> · {{ approval.reviewer }} <span v-if="!approval.current" class="text-muted">· {{ __('Earlier task version') }}</span></div><p v-if="approval.note">{{ approval.note }}</p><small class="text-muted">{{ __('Requested by {0} · {1}', [approval.requested_by, approval.creation]) }}</small><form v-if="approval.can_decide" @submit.prevent="decide(approval, 'Approved')"><label>{{ __('Decision note') }}<textarea v-model="notes[approval.name]" rows="2" maxlength="5000" :disabled="busy" /></label><div class="approval-actions"><button class="btn" :disabled="busy">{{ __('Approve current version') }}</button><button type="button" class="btn-ghost" :disabled="busy" @click="decide(approval, 'Rejected')">{{ __('Reject') }}</button></div></form></li></ol>
      <p v-if="!data.approvals.length" class="text-muted">{{ __('No approval requests yet.') }}</p>
      <p v-if="data.can_request && !data.reviewers.length" class="text-muted">{{ __('No other enabled user can review this task yet. Ask a project administrator to add a reviewer with task write access.') }}</p>
      <form v-if="data.can_request" @submit.prevent="request"><label>{{ __('Request review from') }}<select v-model="reviewer" required :disabled="busy"><option value="">{{ __('Choose a reviewer') }}</option><option v-for="user in data.reviewers" :key="user.name" :value="user.name">{{ user.full_name }} · {{ user.name }}</option></select></label><button class="btn" :disabled="busy || !reviewer">{{ busy ? __('Saving…') : __('Request approval') }}</button></form>
      <p v-if="notice" role="status">{{ notice }}</p>
    </template>
  </details>
</template>
<script setup>
import { ref, watch } from 'vue'
import { call } from 'frappe-ui'
import { __ } from '@/translation'
const props = defineProps({ task: String })
const data = ref(null), notes = ref({}), reviewer = ref(''), loading = ref(false), busy = ref(false), error = ref(''), notice = ref('')
let version = 0
async function load() { const token = ++version; loading.value = true; error.value = ''; try { const result = await call('pulse.api.approvals.get_approvals', { task: props.task }); if (token === version) data.value = result } catch (e) { if (token === version) error.value = e?.messages?.join(' ') || __('Could not load task approvals.') } finally { if (token === version) loading.value = false } }
function open(event) { if (event.target.open) load() }
async function action(method, values, success) { busy.value = true; error.value = ''; notice.value = ''; try { await call('pulse.api.approvals.' + method, values); await load(); notice.value = success } catch (e) { error.value = e?.messages?.join(' ') || __('Could not save approval. Refresh the task and try again.') } finally { busy.value = false } }
async function request() { await action('request_approval', { task: props.task, reviewer: reviewer.value }, __('Approval requested.')) }
async function decide(approval, decision) { await action('decide', { name: approval.name, decision, note: notes.value[approval.name] || '' }, __('Approval decision saved.')) }
watch(() => props.task, () => { version++; data.value = null; notes.value = {}; reviewer.value = ''; notice.value = '' })
</script>
<style scoped>
.task-approvals{padding:16px 0;border-top:1px solid var(--border);font-size:13px}.task-approvals summary{cursor:pointer;font-weight:500}.task-approvals summary span{font-size:12px;margin-left:8px;font-weight:400}.task-approvals p{margin:8px 0;white-space:pre-wrap}.task-approvals li{padding:12px 0;border-bottom:1px solid var(--border)}.task-approvals strong{font-weight:600}.task-approvals form{display:grid;gap:10px;margin-top:12px}.task-approvals label{display:grid;gap:6px}.task-approvals textarea,.task-approvals select{padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text);width:100%}.task-approvals button{justify-self:start}.approval-actions{display:flex;gap:10px}.task-approvals :focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style>
