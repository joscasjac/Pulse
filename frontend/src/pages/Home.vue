<!-- THESIS: A personal starting point centered on work. OWN-WORLD: Plane-inspired neutral lists and compact controls. STORY: Resume a task or enter a project. FIRST VIEWPORT: Left-aligned greeting, assigned work, then recent items. FORM: User-selected operational workspace. -->
<template>
  <div class="home-page">
    <header class="home-header">
      <div><p class="home-date">{{ dateStr }}</p><h1>{{ greeting }}, {{ firstName }}</h1><p class="home-subtitle">Pick up where you left off.</p></div>
    </header>
    <div v-if="error" class="home-error" role="alert">{{ error }} <button class="btn-ghost" @click="reload">Try again</button></div>
    <div v-if="loading" class="home-loading" role="status">Loading your workspace…</div>
    <template v-else>
      <section class="home-section" aria-labelledby="assigned-heading">
        <div class="section-heading"><h2 id="assigned-heading">Assigned to you <span class="count">{{ tasks.length }}</span></h2><router-link to="/my-work">View all →</router-link></div>
        <div class="home-list">
          <button v-for="task in tasks.slice(0, 6)" :key="task.name" class="task-row" @click="openId = task.name">
            <span class="task-state" :class="{ working: task.status === 'Working' }" aria-hidden="true"></span>
            <span class="task-main"><span class="task-subject">{{ task.subject }}</span><span class="task-context">{{ task.issue_key || task.name }}<template v-if="task.project"> · {{ projectNames[task.project] || task.project }}</template></span></span>
            <span class="task-status">{{ task.workflow_state || task.status }}</span><span v-if="task.exp_end_date" class="task-date" :class="{ overdue: task.exp_end_date < today }">{{ formatDate(task.exp_end_date) }}</span>
          </button>
          <div v-if="!tasks.length" class="home-empty"><strong>No open tasks assigned to you</strong><p>Browse your projects to find work, or create a task to get started.</p><router-link to="/projects">Browse projects →</router-link></div>
        </div>
      </section>
      <div class="home-columns">
        <section class="home-section" aria-labelledby="projects-heading">
          <div class="section-heading"><h2 id="projects-heading">Your projects</h2><router-link to="/projects">Browse all →</router-link></div>
          <div class="home-list"><router-link v-for="project in projects.slice(0, 5)" :key="project.name" :to="{ path: '/board', query: { project: project.name } }" class="project-row"><span class="project-symbol" aria-hidden="true">{{ (project.project_name || project.name).slice(0, 1).toUpperCase() }}</span><span class="project-title">{{ project.project_name || project.name }}</span><span class="task-status">{{ project.status }}</span></router-link><div v-if="!projects.length" class="home-empty"><strong>No projects yet</strong><p>Projects you can access will appear here.</p><router-link to="/projects">Open projects →</router-link></div></div>
        </section>
        <section class="home-section" aria-labelledby="recent-heading">
          <div class="section-heading"><h2 id="recent-heading">Recently opened</h2></div>
          <div class="home-list"><router-link v-for="item in recents.slice(0, 5)" :key="item.reference_doctype + item.reference_name" :to="item.url" class="recent-row"><span class="task-main"><span class="task-subject">{{ item.title || item.reference_name }}</span><span class="task-context">{{ item.reference_doctype === 'Pulse Document' ? 'Page' : item.reference_doctype }}</span></span><span aria-hidden="true" class="recent-arrow">↗</span></router-link><div v-if="!recents.length" class="home-empty"><strong>Your recent work, one click away</strong><p>Open a task, project, or page and you can return to it here.</p></div></div>
        </section>
      </div>
    </template>
    <TaskDrawer :task-id="openId" @close="openId = null" @changed="reload" @open="openId = $event" />
  </div>
</template>
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { call } from 'frappe-ui'
import TaskDrawer from '@/components/TaskDrawer.vue'
import { createState } from '@/ui/create'
const firstName = ref('there'), tasks = ref([]), projects = ref([]), recents = ref([]), openId = ref(null), loading = ref(true), error = ref('')
const now = new Date()
const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
const greeting = computed(() => now.getHours() < 12 ? 'Good morning' : now.getHours() < 18 ? 'Good afternoon' : 'Good evening')
const dateStr = now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
const projectNames = computed(() => Object.fromEntries(projects.value.map(p => [p.name, p.project_name])))
function formatDate(date) { return new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }
async function reload() {
  loading.value = true; error.value = ''
  try {
    const me = await call('frappe.auth.get_logged_user')
    const results = await Promise.allSettled([
      call('frappe.client.get_value', { doctype: 'User', filters: me, fieldname: 'first_name' }),
      call('frappe.client.get_list', { doctype: 'Task', fields: ['name', 'issue_key', 'subject', 'status', 'workflow_state', 'project', 'exp_end_date', '_assign'], filters: [['pulse_archived', '=', 0], ['status', 'not in', ['Completed', 'Cancelled']], ['_assign', 'like', `%${me}%`]], order_by: 'exp_end_date asc, modified desc', limit_page_length: 0 }),
      call('frappe.client.get_list', { doctype: 'Project', fields: ['name', 'project_name', 'status'], order_by: 'modified desc', limit_page_length: 0 }),
      call('pulse.api.personal.items'),
    ])
    firstName.value = results[0].status === 'fulfilled' ? results[0].value?.first_name || me.split('@')[0] : me.split('@')[0]
    tasks.value = results[1].status === 'fulfilled' ? (results[1].value || []).filter(t => { try { return JSON.parse(t._assign || '[]').includes(me) } catch { return false } }) : []
    projects.value = results[2].status === 'fulfilled' ? results[2].value || [] : []
    recents.value = results[3].status === 'fulfilled' ? (results[3].value || []).filter(i => i.kind === 'Recent') : []
    if (results.some(r => r.status === 'rejected')) error.value = 'Some workspace items could not be loaded. Try again to refresh them.'
  } catch { error.value = 'Your workspace could not be loaded. Please try again.' }
  finally { loading.value = false }
}
watch(() => createState.created, reload)
onMounted(reload)
</script>
<style scoped>
.home-page { max-width: 1120px; margin: 0 auto; padding: 40px 40px 64px; }
.home-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 38px; }
.home-date { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
h1 { font-size: 24px; font-weight: 600; line-height: 1.3; }
.home-subtitle { color: var(--muted); margin-top: 7px; font-size: 14px; }
.home-section { min-width: 0; margin-bottom: 32px; }
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; }
.section-heading h2 { font-size: 14px; font-weight: 600; display: flex; gap: 8px; align-items: center; }
.section-heading a, .home-empty a { font-size: 12px; color: var(--accent); }
.count { color: var(--muted); background: var(--surface-2); border-radius: 4px; padding: 1px 6px; font-size: 11px; font-weight: 400; }
.home-list { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.task-row, .project-row, .recent-row { display: flex; width: 100%; align-items: center; gap: 12px; text-align: left; min-height: 62px; padding: 12px 16px; }
.task-row + .task-row, .project-row + .project-row, .recent-row + .recent-row { border-top: 1px solid var(--border-soft); }
.task-row:hover, .project-row:hover, .recent-row:hover { background: var(--hover); }
.task-state { width: 14px; height: 14px; border: 1.5px solid var(--muted); border-radius: 50%; flex-shrink: 0; }
.task-state.working { border-color: var(--accent); background: var(--accent); box-shadow: inset 0 0 0 3px var(--surface); }
.task-main { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 0; }
.task-subject, .project-title { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-context { font-size: 11px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-status, .task-date { font-size: 12px; color: var(--muted); white-space: nowrap; }
.task-date.overdue { color: var(--danger); }
.home-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
.project-symbol { width: 28px; height: 28px; display: grid; place-items: center; background: var(--surface-2); border: 1px solid var(--border); border-radius: 6px; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.project-title { flex: 1; }
.recent-arrow { color: var(--muted); }
.home-empty { padding: 28px 20px; font-size: 13px; }
.home-empty strong { font-weight: 500; }.home-empty p { color: var(--muted); margin: 7px 0 12px; line-height: 1.6; }
.home-error { font-size: 13px; color: var(--danger); padding: 12px; border: 1px solid var(--border); margin-bottom: 20px; border-radius: 6px; }
.home-loading { color: var(--muted); padding: 40px 0; font-size: 14px; }
@media (max-width: 768px) { .home-page { padding: 24px 16px; }.home-columns { grid-template-columns: 1fr; gap: 0; }.home-header { align-items: flex-start; }.home-header .btn-primary { white-space: nowrap; }h1 { font-size: 20px; }.task-row .task-status { display: none; } }
</style>
