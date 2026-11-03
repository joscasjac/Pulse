<template>
  <section class="team-panel" aria-labelledby="team-heading" :aria-busy="busy">
    <header><div><h2 id="team-heading">{{ project.project_name }} / Team</h2><p class="text-muted">Manage project membership and hand off assigned work.</p></div><button class="btn-ghost" @click="$emit('close')">Close</button></header>
    <p v-if="error" role="alert" class="team-error">{{ error }} <button @click="load">Retry</button></p>
    <p v-if="message" role="status">{{ message }}</p>
    <p v-if="loading">Loading team…</p>
    <template v-else-if="data">
      <p class="text-muted">Project owner: {{ data.owner }}</p>
      <ul><li v-for="member in data.members" :key="member.user"><div><strong>{{ member.full_name }}</strong><small>{{ member.user }}</small></div><button v-if="member.user !== data.owner" class="btn-ghost" :disabled="busy" @click="removing = member; replacement = ''">Remove member…</button><span v-else class="text-muted">Owner</span></li></ul>
      <p v-if="!data.members.length" class="text-muted">No project members yet. Add an existing ERP user below.</p>
      <form v-if="removing" class="handoff" @submit.prevent="remove">
        <h3>Remove {{ removing.full_name }}?</h3>
        <p>Open task assignments will be handed off or left unassigned. The ERP account stays active. ERPNext removes project shares; separate task shares may still provide access.</p>
        <label>Hand off assignments to<select v-model="replacement" class="field"><option value="">Leave tasks unassigned</option><option v-for="member in data.members.filter(m => m.user !== removing.user)" :key="member.user" :value="member.user">{{ member.full_name }}</option></select></label>
        <div class="team-actions"><button type="button" class="btn-ghost" :disabled="busy" @click="removing = null">Cancel</button><button class="btn-primary" :disabled="busy">{{ busy ? 'Removing…' : 'Remove member' }}</button></div>
      </form>
      <form class="handoff" @submit.prevent="transfer"><label>Transfer project ownership<select v-model="nextOwner" class="field" required :disabled="busy"><option value="">Choose an existing member</option><option v-for="member in data.members.filter(m => m.user !== data.owner)" :key="member.user" :value="member.user">{{ member.full_name }}</option></select></label><p class="text-muted">The new owner keeps project access through ownership. Membership and task assignments are preserved.</p><div class="team-actions"><button class="btn-ghost" :disabled="busy || !nextOwner">Transfer ownership</button></div></form>
      <form class="team-add" @submit.prevent="add"><label>Add an existing team member<select v-model="newUser" class="field" required :disabled="busy"><option value="">Choose a user</option><option v-for="user in candidates" :key="user.name" :value="user.name">{{ user.full_name }} · {{ user.name }}</option></select></label><button class="btn-primary" :disabled="busy || !newUser">{{ busy ? 'Saving…' : 'Add member' }}</button></form>
      <p class="text-muted">Existing accounts keep their roles. A Pulse contributor role is needed to use task details, labels and modules; administrators manage it in ERP User settings.</p>
      <details v-if="data.can_manage_accounts" class="account-tools"><summary>Invite a new ERP user</summary>
        <p>Create a system user with Projects User and Pulse Junior Developer roles, then send the ERP welcome email. Other ERP roles are managed in User settings.</p>
        <form @submit.prevent="invite" class="account-form"><label>Email<input v-model="inviteEmail" type="email" required class="field" :disabled="busy" /></label><label>First name<input v-model="inviteFirst" required class="field" :disabled="busy" /></label><label>Last name<input v-model="inviteLast" class="field" :disabled="busy" /></label><div class="team-actions"><button class="btn-primary" :disabled="busy">{{ busy ? 'Inviting…' : 'Create user and send invitation' }}</button></div></form>
      </details>
      <details v-if="data.can_manage_accounts" class="account-tools"><summary>Offboard an ERP account</summary>
        <p>This affects the whole ERP account across all projects. Review the plan before applying it. The account and its history are retained.</p>
        <form @submit.prevent="previewOffboarding" class="account-form"><label>Departing user<select v-model="offboardUser" required class="field" :disabled="busy" @change="clearPlan"><option value="">Choose a user</option><option v-for="user in offboardingUsers" :key="user.name" :value="user.name">{{ user.full_name }} · {{ user.name }}</option></select></label><label>Hand work to<select v-model="offboardReplacement" required class="field" :disabled="busy" @change="clearPlan"><option value="">Choose a replacement</option><option v-for="user in allUsers.filter(u => u.name !== offboardUser)" :key="user.name" :value="user.name">{{ user.full_name }} · {{ user.name }}</option></select></label><div class="team-actions"><button class="btn-ghost" :disabled="busy || !offboardUser || !offboardReplacement">Review offboarding plan</button></div></form>
        <section v-if="offboardPlan" class="offboard-plan" aria-label="Offboarding preview"><h3>Review changes for {{ offboardPlan.user }}</h3><p>{{ offboardPlan.assignments.length }} open ERP assignments will move to {{ offboardPlan.replacement }}. {{ offboardPlan.shares.length }} direct shares will be removed and {{ offboardPlan.external_grants.length }} external portal grants revoked.</p><ul><li v-for="project in offboardPlan.projects" :key="project.name"><span>{{ project.project_name }}<small>{{ project.owner === offboardPlan.user ? 'Transfer ownership and membership' : 'Replace membership' }}</small></span></li></ul><p>The replacement will join the projects above. The departing account will be disabled and its sessions ended. Other HR, accounting and payroll records are unchanged.</p><label class="confirm-offboard"><input v-model="offboardConfirmed" type="checkbox" :disabled="busy" /> I reviewed this organization-wide handoff and account disablement.</label><div class="team-actions"><button class="btn-ghost" :disabled="busy" @click="clearPlan">Cancel</button><button class="btn-primary" :disabled="busy || !offboardConfirmed" @click="offboard">{{ busy ? 'Applying handoff…' : 'Disable account and hand off work' }}</button></div></section>
      </details>
    </template>
  </section>
</template>
<script setup>
import { ref, computed, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ project: { type: Object, required: true } })
defineEmits(['close'])
const data = ref(null), loading = ref(true), busy = ref(false), error = ref(''), message = ref('')
const nextOwner = ref('')
const newUser = ref(''), removing = ref(null), replacement = ref('')
const inviteEmail = ref(''), inviteFirst = ref(''), inviteLast = ref('')
const offboardUser = ref(''), offboardReplacement = ref(''), offboardPlan = ref(null), offboardConfirmed = ref(false)
const offboardingUsers = computed(() => data.value?.offboarding_candidates || [])
const allUsers = computed(() => data.value?.candidates || [])
const candidates = computed(() => (data.value?.candidates || []).filter(u => !data.value.members.some(m => m.user === u.name)))
function requestError(error, fallback) {
  const messages = Array.isArray(error?.messages) ? error.messages.filter(m => typeof m === 'string' && m.trim()) : []
  return messages.length ? [...new Set(messages)].join(' ') : fallback
}
let generation = 0
async function load() {
  const request = ++generation; loading.value = true; error.value = ''
  try { const result = await call('pulse.api.team.get_team', { project: props.project.name }); if (request === generation) data.value = result }
  catch (e) { if (request === generation) error.value = requestError(e, 'Unable to load project team.') }
  finally { if (request === generation) loading.value = false }
}
async function add() {
  busy.value = true; error.value = ''; message.value = ''
  try { data.value = await call('pulse.api.team.add_member', { project: props.project.name, user: newUser.value }); newUser.value = ''; message.value = 'Project member added.' }
  catch (e) { error.value = requestError(e, 'Unable to add member.') }
  finally { busy.value = false }
}
async function transfer() {
  busy.value = true; error.value = ''; message.value = ''
  try { await call('pulse.api.team.transfer_owner', { project: props.project.name, user: nextOwner.value }); nextOwner.value = ''; await load(); message.value = 'Project ownership transferred.' }
  catch (e) { error.value = requestError(e, 'Unable to transfer ownership.') }
  finally { busy.value = false }
}
async function remove() {
  busy.value = true; error.value = ''; message.value = ''
  try { const result = await call('pulse.api.team.remove_member', { project: props.project.name, user: removing.value.user, replacement: replacement.value || null }); removing.value = null; await load(); message.value = `Member removed. ${result.tasks.length} task assignments updated.` }
  catch (e) { error.value = requestError(e, 'Unable to remove member. No changes were saved.') }
  finally { busy.value = false }
}
function clearPlan() { offboardPlan.value = null; offboardConfirmed.value = false }
async function invite() {
  busy.value = true; error.value = ''; message.value = ''
  try { const result = await call('pulse.api.team.invite_member', { project: props.project.name, email: inviteEmail.value, first_name: inviteFirst.value, last_name: inviteLast.value }); data.value = result.team; inviteEmail.value = ''; inviteFirst.value = ''; inviteLast.value = ''; message.value = 'User created and welcome email queued. Delivery depends on ERP email processing.' }
  catch (e) { error.value = requestError(e, 'Unable to invite user. Check the ERP outgoing email configuration and try again.') }
  finally { busy.value = false }
}
async function previewOffboarding() {
  busy.value = true; error.value = ''; message.value = ''; clearPlan()
  try { offboardPlan.value = await call('pulse.api.team.preview_offboarding', { user: offboardUser.value, replacement: offboardReplacement.value }) }
  catch (e) { error.value = requestError(e, 'Unable to prepare offboarding. Check the users and your access to their records.') }
  finally { busy.value = false }
}
async function offboard() {
  if (!offboardConfirmed.value || !offboardPlan.value) return
  busy.value = true; error.value = ''; message.value = ''
  try { const result = await call('pulse.api.team.offboard_user', { user: offboardPlan.value.user, replacement: offboardPlan.value.replacement, preview_token: offboardPlan.value.preview_token }); clearPlan(); offboardUser.value = ''; offboardReplacement.value = ''; await load(); message.value = `Account disabled. ${result.assignments_updated} assignments handed off across ${result.projects_updated} projects.` }
  catch (e) { clearPlan(); error.value = requestError(e, 'Unable to apply offboarding. Review a fresh preview and try again.') }
  finally { busy.value = false }
}
watch(() => props.project.name, () => { data.value = null; removing.value = null; newUser.value = ''; nextOwner.value = ''; replacement.value = ''; message.value = ''; clearPlan(); load() }, { immediate: true })
</script>
<style scoped>
.team-panel{margin:16px 0;padding:20px;border:1px solid var(--border-color,#e6e8ec);border-radius:8px}.team-panel header,.team-actions,.team-add{display:flex;align-items:center;justify-content:space-between;gap:16px}.team-panel h2{font-size:16px;font-weight:600}.team-panel p{margin:8px 0;font-size:13px}.team-panel ul{margin:16px 0}.team-panel li{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border-color,#e6e8ec)}.team-panel strong{font-weight:500}.team-panel small{display:block;color:var(--text-muted,#60646c)}.team-panel label{display:grid;gap:6px;flex:1;font-size:13px}.handoff{padding:16px 0}.team-actions{justify-content:flex-end;margin-top:12px}.team-error{color:var(--text-color,#202124)}.team-error button{text-decoration:underline}
.account-tools{border-top:1px solid var(--border-color,#e6e8ec);padding-top:16px;margin-top:20px}.account-tools summary{cursor:pointer;font-weight:500;font-size:14px}.account-form{display:grid;gap:12px;margin-top:16px}.offboard-plan{margin-top:16px;padding:16px;background:var(--surface-color,#f7f8fa);border-radius:6px}.team-panel .confirm-offboard{display:flex;align-items:flex-start;gap:8px}.team-panel button:focus-visible,.team-panel summary:focus-visible{outline:2px solid var(--accent-color,#3b5bdb);outline-offset:2px}
</style>
