<template>
  <div class="intake-page">
    <header class="intake-header">
      <div><h1>Intake</h1><p class="text-muted">Review requests before adding them to your project.</p></div>
      <button class="btn-primary" :aria-expanded="creating" aria-controls="new-request-form" @click="toggleCreate">{{ creating ? 'Close form' : '+ New request' }}</button>
    </header>

    <form v-if="creating" id="new-request-form" class="request-form create-form" @submit.prevent="create">
      <h2>New request</h2>
      <div class="property-grid">
        <label>Project<select v-model="draft.project" required class="intake-input"><option value="" disabled>Select a project</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option></select></label>
        <label>Reviewer <span class="text-muted">(optional)</span><select v-model="draft.reviewer" class="intake-input" :disabled="!draft.project"><option value="">Unassigned</option><option v-for="user in draftReviewers" :key="user.name" :value="user.name">{{ user.full_name }} · {{ user.name }}</option></select></label>
      </div>
      <label>Title<input v-model.trim="draft.title" required maxlength="140" class="intake-input" placeholder="What needs to be done?" /></label>
      <label>Description<textarea v-model="draft.description" rows="3" maxlength="20000" class="intake-input" placeholder="Describe the request and the outcome you need." /></label>
      <p v-if="createError" role="alert" class="form-error">{{ createError }}</p>
      <div class="form-actions"><button class="btn-primary" :disabled="busy">{{ busy ? 'Submitting…' : 'Submit request' }}</button><button type="button" class="btn-ghost" @click="creating = false">Cancel</button></div>
    </form>

    <div class="intake-toolbar">
      <nav class="status-tabs" aria-label="Filter requests by status">
        <button v-for="state in statuses" :key="state" :aria-pressed="status === state" @click="status = state">{{ state }}</button>
        <button :aria-pressed="status === ''" @click="status = ''">All</button>
      </nav>
      <label class="project-filter"><span class="sr-only">Project</span><select v-model="project" class="intake-input"><option value="">All projects</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option></select></label>
    </div>

    <details v-if="canManage && project" class="public-settings">
      <summary>Public request form <span class="text-muted">{{ publicForm?.enabled ? 'Enabled' : 'Settings' }}</span></summary>
      <div class="settings-content">
        <p class="text-muted">Anyone with the enabled link can submit a request. Only the title and instructions below appear publicly.</p>
        <p v-if="formLoading" role="status">Loading form settings…</p>
        <form v-else-if="publicForm" class="request-form" @submit.prevent="savePublicForm">
          <label>Public title<input v-model.trim="publicForm.public_title" required maxlength="140" class="intake-input" /></label>
          <label>Public instructions<textarea v-model="publicForm.public_description" maxlength="2000" rows="2" class="intake-input" /></label>
          <label class="checkbox-label"><input v-model="publicForm.enabled" type="checkbox" /> Enable submissions</label>
          <div><button class="btn-ghost" :disabled="formBusy">{{ formBusy ? 'Saving…' : 'Save public form' }}</button></div>
          <p v-if="publicForm.url" class="share-link">Share this link: <a class="task-link" :href="publicForm.url" target="_blank" rel="noopener noreferrer">{{ publicForm.url }}</a></p>
          <p class="text-muted">Disabling stops new submissions. Enabling again creates a new link.</p>
        </form>
        <p v-if="formError" role="alert" class="form-error">{{ formError }} <button class="btn-ghost" @click="loadPublicForm">Retry</button></p>
      </div>
    </details>

    <p v-if="reviewerError" role="alert" class="page-message form-error">{{ reviewerError }}</p>
    <p v-if="projectError" role="alert" class="page-message form-error">{{ projectError }} <button class="btn-ghost" @click="loadProjects">Retry projects</button></p>
    <p v-if="error" role="alert" class="page-message form-error">{{ error }} <button class="btn-ghost" @click="load">Retry</button></p>
    <p v-if="loading" role="status" class="page-message text-muted">Loading requests…</p>
    <div v-else class="intake-layout">
      <section aria-label="Request queue" class="request-queue">
        <div class="queue-heading"><h2>{{ status || 'All requests' }}</h2><span class="text-muted">{{ requests.length }}</span></div>
        <button v-for="r in requests" :key="r.name" class="request-choice" :aria-current="selected === r.name ? 'true' : undefined" :disabled="busy" @click="selected = r.name">
          <span class="request-title">{{ r.title }}</span>
          <span class="request-meta"><span class="status-marker" :data-status="r.status" />{{ r.status }}<span v-if="!project"> · {{ projectName(r.project) }}</span></span>
          <span v-if="r.reviewer" class="request-reviewer text-muted">{{ r.reviewer }}</span>
        </button>
        <div v-if="!requests.length" class="queue-empty"><h3>No {{ status ? status.toLowerCase() : '' }} requests</h3><p class="text-muted">New requests will appear here for review.</p><button class="btn-ghost" @click="toggleCreate">Create a request</button></div>
      </section>
      <section class="request-detail" aria-label="Request details">
        <p v-if="detailLoading" role="status" class="text-muted">Loading request…</p>
        <p v-if="detailError" role="alert" class="form-error">{{ detailError }} <button class="btn-ghost" @click="loadDetail">Retry details</button></p>
        <template v-if="detail && !detailLoading">
          <header class="detail-header"><p class="detail-context text-muted">{{ projectName(detail.project) }} <span> / </span> {{ detail.name }}</p><h2>{{ detail.title }}</h2><p class="request-meta"><span class="status-marker" :data-status="detail.status" />{{ detail.status }}</p></header>
          <p class="description">{{ descriptionText(detail.description) }}</p>
          <div v-if="detail.accepted_task" class="accepted-notice"><p>This request has been accepted.</p><RouterLink class="task-link" :to="{ path: '/board', query: { project: detail.project, task: detail.accepted_task } }">Open task {{ detail.accepted_task }} →</RouterLink></div>
          <form v-else-if="detail.can_review" class="request-form review-form" @submit.prevent="review">
            <h3>Review</h3>
            <div class="property-grid">
              <label>Reviewer<select v-model="reviewer" class="intake-input"><option value="">Unassigned</option><option v-for="user in reviewers" :key="user.name" :value="user.name">{{ user.full_name }} · {{ user.name }}</option></select></label>
              <label>Decision<select v-model="decision" class="intake-input"><option>Incoming</option><option>Deferred</option><option>Rejected</option><option>Duplicate</option></select></label>
            </div>
            <label v-if="decision === 'Duplicate'">Original request ID<input v-model.trim="duplicate" required class="intake-input" placeholder="Request ID" /></label>
            <label>Review note<textarea v-model="note" rows="2" class="intake-input" placeholder="Add context for your decision…" /></label>
            <p v-if="actionError" role="alert" class="form-error">{{ actionError }}</p>
            <div class="form-actions"><button v-if="['Incoming', 'Deferred'].includes(detail.status) && ['Incoming', 'Deferred'].includes(decision)" type="button" class="btn-primary" :disabled="busy" @click="accept">{{ busy ? 'Saving…' : 'Accept and create task' }}</button><button :class="['Incoming', 'Deferred'].includes(detail.status) && ['Incoming', 'Deferred'].includes(decision) ? 'btn-ghost' : 'btn-primary'" :disabled="busy">Save review</button></div>
          </form>
          <p v-else class="text-muted review-access">The assigned reviewer or a project lead can review this request.</p>
          <section class="request-history"><h3>Activity</h3><ol><li v-for="(event, index) in detail.activity || []" :key="event.name || index" class="history-entry"><p><span class="history-action">{{ event.action || 'Updated' }}</span> · {{ event.status }}<span v-if="event.note"> — {{ event.note }}</span></p><p class="history-meta text-muted">{{ event.by || 'Unknown user' }} · {{ formatDate(event.at) }}</p><p v-if="event.reviewer || event.duplicate_of" class="history-meta text-muted"><span v-if="event.reviewer">Reviewer: {{ event.reviewer }}</span><span v-if="event.duplicate_of"> · Duplicate of {{ event.duplicate_of }}</span></p></li></ol><p v-if="!detail.activity?.length" class="text-muted">No recorded activity yet.</p></section>
        </template>
        <div v-else-if="!detailLoading && !detailError" class="detail-empty text-muted">Select a request to review its details and activity.</div>
      </section>
    </div>
    <p v-if="notice" role="status" class="page-message text-muted">{{ notice }}</p>
  </div>
</template>
<script setup>
import { onMounted, ref, watch } from 'vue'
import { call } from 'frappe-ui'
import { useRoute, useRouter } from 'vue-router'
const route = useRoute(), router = useRouter()
const queryProject = () => typeof route.query.project === 'string' ? route.query.project : ''
function toggleCreate() {
  if (!creating.value && !draft.value.title) draft.value.project = project.value
  creating.value = !creating.value
}
function projectName(name) { return projects.value.find(item => item.name === name)?.project_name || name }
function descriptionText(value) {
  if (!value) return 'No description provided.'
  return new DOMParser().parseFromString(value.replace(/<\/p>|<br\s*\/?>/gi, '\n'), 'text/html').body.textContent || 'No description provided.'
}
const statuses = ['Incoming', 'Deferred', 'Rejected', 'Duplicate', 'Accepted']
const projects = ref([]), requests = ref([]), project = ref(queryProject()), status = ref('Incoming'), selected = ref(''), detail = ref(null)
const loading = ref(true), detailLoading = ref(false), busy = ref(false), error = ref(''), detailError = ref(''), actionError = ref(''), createError = ref(''), notice = ref('')
const projectError = ref(''), reviewers = ref([]), draftReviewers = ref([]), reviewerError = ref('')
const canManage = ref(false), publicForm = ref(null), formLoading = ref(false), formBusy = ref(false), formError = ref('')
let formVersion = 0, reviewerVersion = 0, draftReviewerVersion = 0
const creating = ref(false), draft = ref({ project: queryProject(), title: '', description: '', reviewer: '' })
const reviewer = ref(''), decision = ref('Incoming'), duplicate = ref(''), note = ref('')
let listVersion = 0, detailVersion = 0
async function load() {
  const version = ++listVersion; loading.value = true; error.value = ''
  try { const rows = await call('pulse.api.intake.list_requests', { project: project.value || null, status: status.value || null }); if (version === listVersion) { requests.value = rows; if (!rows.some(r => r.name === selected.value)) selected.value = rows[0]?.name || '' } }
  catch (e) { if (version === listVersion) error.value = e.message || 'Requests could not be loaded.' }
  finally { if (version === listVersion) loading.value = false }
}
async function loadDetail() {
  const name = selected.value, version = ++detailVersion; detail.value = null; detailError.value = ''; actionError.value = ''; detailLoading.value = Boolean(name)
  if (!name) return
  try { const row = await call('pulse.api.intake.get_request', { name }); if (version === detailVersion) { detail.value = row; reviewer.value = row.reviewer || ''; decision.value = row.status; duplicate.value = row.duplicate_of || ''; note.value = ''; loadReviewers(row.project) } }
  catch (e) { if (version === detailVersion) detailError.value = e.message || 'Request details could not be loaded.' }
  finally { if (version === detailVersion) detailLoading.value = false }
}
async function create() {
  if (busy.value) return
  busy.value = true; createError.value = ''; notice.value = ''
  try { const result = await call('pulse.api.intake.create_request', { ...draft.value }); project.value = draft.value.project; draft.value = { project: draft.value.project, title: '', description: '', reviewer: '' }; creating.value = false; status.value = 'Incoming'; await load(); selected.value = result.name || selected.value; notice.value = 'Request submitted for review.' }
  catch (e) { createError.value = e.message || 'Your request could not be submitted. Your text has been kept.' }
  finally { busy.value = false }
}
async function review() {
  if (busy.value || !detail.value) return
  busy.value = true; actionError.value = ''; notice.value = ''
  try { await call('pulse.api.intake.review_request', { name: selected.value, status: decision.value, reviewer: reviewer.value, duplicate_of: decision.value === 'Duplicate' ? duplicate.value : null, note: note.value }); await load(); await loadDetail(); notice.value = 'Review saved.' }
  catch (e) { actionError.value = e.message || 'The review could not be saved.' }
  finally { busy.value = false }
}
async function accept() {
  if (busy.value || !detail.value) return
  busy.value = true; actionError.value = ''; notice.value = ''
  try { const result = await call('pulse.api.intake.accept_request', { name: selected.value, reviewer: reviewer.value, note: note.value }); status.value = 'Accepted'; await load(); await loadDetail(); notice.value = `Request accepted. Task ${result.task} created.` }
  catch (e) { actionError.value = e.message || 'The request could not be accepted.' }
  finally { busy.value = false }
}
function formatDate(value) {
  if (!value) return 'Time unavailable'
  const date = new Date(value.replace(' ', 'T'))
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
async function loadReviewers(projectName, draftMode = false) {
  const version = draftMode ? ++draftReviewerVersion : ++reviewerVersion
  const target = draftMode ? draftReviewers : reviewers
  target.value = []; reviewerError.value = ''
  if (!projectName) return
  try { const rows = await call('pulse.api.intake.reviewer_options', { project: projectName }); if (version === (draftMode ? draftReviewerVersion : reviewerVersion)) target.value = rows }
  catch (e) { reviewerError.value = e.message || 'Reviewer choices could not be loaded. Re-select the project to retry.' }
}
async function loadPublicForm() {
  const version = ++formVersion; publicForm.value = null; formError.value = ''
  if (!canManage.value || !project.value) return
  formLoading.value = true
  try { const result = await call('pulse.api.public_intake.get_settings', { project: project.value }); if (version === formVersion) publicForm.value = result }
  catch (e) { if (version === formVersion) formError.value = e.message || 'Public form settings could not be loaded.' }
  finally { if (version === formVersion) formLoading.value = false }
}
async function savePublicForm() {
  if (formBusy.value || !publicForm.value) return
  const name = project.value
  formBusy.value = true; formError.value = ''
  try { const result = await call('pulse.api.public_intake.save_settings', { project: name, enabled: publicForm.value.enabled ? 1 : 0, public_title: publicForm.value.public_title, public_description: publicForm.value.public_description }); if (project.value === name) publicForm.value = result; notice.value = 'Public form settings saved.' }
  catch (e) { formError.value = e.message || 'Public form settings could not be saved.' }
  finally { formBusy.value = false }
}
watch(() => draft.value.project, value => { draft.value.reviewer = ''; loadReviewers(value, true) })
watch(() => route.query.project, () => { project.value = queryProject() })
watch(project, value => { loadPublicForm(); if (value !== queryProject()) router.replace({ query: { ...route.query, project: value || undefined } }) })
watch([project, status], load)
watch(selected, loadDetail)
async function loadProjects() { projectError.value = ''; try { projects.value = await call('frappe.client.get_list', { doctype: 'Project', fields: ['name', 'project_name'], limit_page_length: 0 }) } catch (e) { projectError.value = e.message || 'Projects could not be loaded.' } }
onMounted(async () => { loadProjects(); load(); try { canManage.value = await call('pulse.api.public_intake.can_manage'); loadPublicForm() } catch { canManage.value = false } })
</script>
<style scoped>
.intake-page { flex: 1; height: 100%; min-height: 0; display: flex; flex-direction: column; overflow: hidden; min-width: 0; font-size: 14px; }
.intake-header { flex-shrink: 0; padding: 24px 28px 20px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.intake-header h1 { font-size: 22px; font-weight: 600; margin: 0 0 5px; }
.intake-header p { font-size: 13px; }
.intake-toolbar { flex-shrink: 0; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding-inline: 28px; border-bottom: 1px solid var(--border); }
.status-tabs { display: flex; gap: 20px; min-width: 0; overflow-x: auto; }
.status-tabs button { padding: 13px 0; border-bottom: 2px solid transparent; font-size: 13px; color: var(--muted); white-space: nowrap; }
.status-tabs button[aria-pressed=true] { border-bottom-color: var(--accent); color: var(--text); font-weight: 600; }
.status-tabs button:hover { color: var(--text); }
.project-filter { flex-shrink: 0; max-width: 220px; }
.project-filter .intake-input { margin: 0; font-size: 12px; }
.intake-layout { display: grid; grid-template-columns: minmax(260px, 32%) minmax(0, 1fr); flex: 1; min-height: 0; overflow: hidden; grid-template-rows: minmax(0, 1fr); }
.request-queue { min-height: 0; overflow-y: auto; overscroll-behavior: contain; border-inline-end: 1px solid var(--border); min-width: 0; }
.queue-heading { position: sticky; top: 0; z-index: 1; background: var(--surface); display: flex; justify-content: space-between; padding: 14px 22px; border-bottom: 1px solid var(--border); font-size: 12px; }
.queue-heading h2 { font-weight: 500; }
.request-choice { display: block; width: 100%; text-align: start; padding: 16px 22px; border-bottom: 1px solid var(--border); }
.request-choice:hover { background: color-mix(in srgb, var(--accent) 3%, var(--surface)); }
.request-choice[aria-current=true] { background: color-mix(in srgb, var(--accent) 7%, var(--surface)); }
.request-title { display: block; font-size: 14px; font-weight: 500; line-height: 1.5; overflow-wrap: anywhere; }
.request-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 5px; font-size: 12px; margin-top: 8px; color: var(--muted); }
.request-reviewer { display: block; font-size: 12px; margin-top: 5px; overflow-wrap: anywhere; }
.status-marker { width: 7px; height: 7px; border: 1px solid currentColor; border-radius: 50%; flex-shrink: 0; }
.status-marker[data-status=Incoming] { color: var(--accent); }
.status-marker[data-status=Accepted] { color: var(--success, #27865c); background: currentColor; }
.status-marker[data-status=Rejected] { color: var(--danger, #b94545); }
.status-marker[data-status=Deferred] { color: var(--warning, #977018); }
.request-detail { min-height: 0; overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable; min-width: 0; padding: 28px 36px; }
.detail-context { font-size: 12px; overflow-wrap: anywhere; }
.detail-context span { padding-inline: 8px; }
.detail-header h2 { font-size: 21px; line-height: 1.45; font-weight: 600; margin-top: 12px; overflow-wrap: anywhere; }
.description { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.7; max-width: 72ch; padding-block: 24px; }
.request-form { display: grid; gap: 14px; font-size: 13px; }
.request-form h2, .request-form h3, .request-history h3 { font-weight: 600; font-size: 14px; }
.create-form { flex-shrink: 0; max-height: 42%; overflow-y: auto; overscroll-behavior: contain; padding: 20px 28px 24px; border-block: 1px solid var(--border); max-width: 800px; }
.property-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.property-grid > label { min-width: 0; }
.intake-input { display: block; width: 100%; min-height: 32px; padding: 6px 9px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); margin-top: 6px; font-size: 13px; }
textarea.intake-input { resize: vertical; }
.review-form { padding-block: 20px 24px; border-top: 1px solid var(--border); }
.form-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.request-history { padding-top: 24px; border-top: 1px solid var(--border); }
.request-history h3 { margin-bottom: 8px; }
.history-entry { padding-block: 12px; font-size: 13px; overflow-wrap: anywhere; }
.history-action { font-weight: 500; }
.history-meta { font-size: 12px; margin-top: 5px; }
.accepted-notice { display: grid; gap: 6px; padding-bottom: 24px; font-size: 13px; }
.review-access { padding-bottom: 24px; font-size: 13px; }
.task-link { color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }
.public-settings { flex-shrink: 0; max-height: 35%; overflow-y: auto; overscroll-behavior: contain; border-bottom: 1px solid var(--border); font-size: 13px; }
.public-settings summary { padding: 12px 28px; cursor: pointer; font-weight: 500; }
.public-settings summary span { font-size: 12px; margin-inline-start: 12px; font-weight: 400; }
.settings-content { padding: 0 28px 20px; max-width: 740px; }
.settings-content > p { margin-bottom: 16px; }
.checkbox-label { display: flex; gap: 8px; align-items: center; }
.share-link { overflow-wrap: anywhere; }
.page-message { flex-shrink: 0; max-height: 15%; overflow-y: auto; padding: 14px 28px; font-size: 13px; }
.form-error { color: var(--danger, #b94545); font-size: 13px; }
.queue-empty { padding: 32px 22px; font-size: 13px; }
.queue-empty h3 { font-weight: 500; margin-bottom: 6px; }
.queue-empty p { line-height: 1.6; margin-bottom: 16px; }
.detail-empty { padding-block: 64px; text-align: center; font-size: 13px; }
button:disabled { opacity: .55; cursor: not-allowed; }
button:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 900px) { .intake-toolbar { flex-wrap: wrap; gap: 0; padding-bottom: 10px; } .project-filter { max-width: 100%; } .request-detail { padding: 24px; } }
@media (max-width: 680px) { .intake-header { flex-shrink: 0; padding: 20px 16px; align-items: flex-start; } .intake-header p { max-width: 30ch; } .intake-toolbar { padding-inline: 16px; } .status-tabs { gap: 16px; width: 100%; } .intake-layout { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(80px, 30%) minmax(0, 1fr); } .request-queue { border-inline-end: 0; border-bottom: 1px solid var(--border); max-height: none; overflow-y: auto; } .request-detail { padding: 24px 16px; } .property-grid { grid-template-columns: minmax(0, 1fr); gap: 14px; } .create-form { padding-inline: 16px; } .public-settings summary, .settings-content { padding-inline: 16px; } }
</style>
