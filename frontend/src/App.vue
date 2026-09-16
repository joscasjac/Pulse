<template>
  <div class="pulse-shell bg-app text-app">
    <a href="#main-content" class="skip-link">Skip to content</a>
    <button v-if="mobileOpen" class="nav-backdrop" aria-label="Close navigation" @click="mobileOpen = false" />
    <aside ref="sidebar" id="primary-navigation" :inert="isMobile && !mobileOpen" :class="['pulse-sidebar', { 'is-open': mobileOpen }]">
      <router-link to="/" class="workspace-brand"><span class="brand-mark">P</span><span>Pulse</span><span class="workspace-caption">Workspace</span></router-link>
      <button class="search-trigger" @click="searchOpen = true"><Search class="nav-icon" /><span>Search anything</span><kbd>⌘ K</kbd></button>
      <nav class="sidebar-scroll" aria-label="Main navigation">
        <div class="nav-group">
          <router-link v-for="item in personalNav" :key="item.to" :to="item.to" class="nav-item" :class="{ active: route.path === item.to }"><component :is="item.icon" class="nav-icon" /><span>{{ item.label }}</span></router-link>
        </div>
        <div class="nav-group">
          <h2 class="nav-heading">Workspace</h2>
          <router-link v-for="item in workspaceNav" :key="item.to" :to="item.to" class="nav-item" :class="{ active: !projectId && route.path === item.to }"><component :is="item.icon" class="nav-icon" /><span>{{ item.label }}</span></router-link>
        </div>
        <div class="nav-group">
          <div class="nav-heading-row"><h2 class="nav-heading">Your projects</h2><router-link to="/projects" aria-label="Browse projects" class="icon-button"><Plus class="nav-icon" /></router-link></div>
          <p v-if="projectsLoading" class="nav-message" role="status">Loading projects…</p>
          <p v-else-if="projectsError" class="nav-message" role="alert">Projects couldn't load. <button class="retry-link" @click="loadProjects">Retry</button></p>
          <p v-else-if="!projects.length" class="nav-message">Your projects will appear here.</p>
          <template v-for="project in sidebarProjects" :key="project.name">
            <router-link :to="{ path: '/board', query: { project: project.name } }" class="nav-item project-link" :class="{ 'project-selected': projectId === project.name }"><span class="project-mark">{{ (project.pulse_project_key || project.project_name || 'P').slice(0, 2) }}</span><span class="truncate">{{ project.project_name || project.name }}</span><ChevronDown v-if="projectId === project.name" class="nav-icon project-chevron" /></router-link>
            <div v-if="projectId === project.name" class="project-navigation">
              <router-link v-for="item in projectNav" :key="item.to" :to="projectRoute(item.to)" class="nav-item" :class="{ active: route.path === item.to }"><component :is="item.icon" class="nav-icon" /><span>{{ item.label }}</span></router-link>
            </div>
          </template>
          <router-link to="/projects" class="nav-item view-all-projects">View all projects</router-link>
        </div>
        <details class="more-navigation" :open="isAdvanced">
          <summary class="nav-item"><MoreHorizontal class="nav-icon" /><span>More</span><ChevronDown class="nav-icon project-chevron" /></summary>
          <div v-for="group in advancedNav" :key="group.label" class="advanced-group"><h2 class="nav-heading">{{ group.label }}</h2><router-link v-for="item in group.items" :key="item.to" :to="item.to" class="nav-item" :class="{ active: route.path === item.to }">{{ item.label }}</router-link></div>
        </details>
      </nav>
      <footer class="sidebar-footer"><Avatar :name="user" :size="24" /><span class="user-name">{{ shortUser || 'Your workspace' }}</span><a href="/app/pulse-settings" aria-label="Workspace settings" title="Settings" class="icon-button"><Settings class="nav-icon" /></a><button @click="toggleTheme" class="icon-button" :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"><Sun v-if="theme === 'dark'" class="nav-icon" /><Moon v-else class="nav-icon" /></button></footer>
    </aside>
    <div class="workspace-content" :inert="isMobile && mobileOpen">
      <header class="context-bar">
        <button class="icon-button mobile-menu" aria-label="Open navigation" aria-controls="primary-navigation" :aria-expanded="mobileOpen" @click="mobileOpen = true"><Menu class="nav-icon" /></button>
        <div v-if="route.path === '/board'" id="task-toolbar-host" class="task-toolbar-host" />
        <nav v-else class="breadcrumbs" aria-label="Breadcrumb"><router-link :to="projectId ? '/projects' : '/'">{{ projectId ? 'Projects' : 'Workspace' }}</router-link><ChevronRight class="breadcrumb-separator" /><span v-if="projectId" class="breadcrumb-project">{{ projectName }}</span><ChevronRight v-if="projectId" class="breadcrumb-separator" /><span class="current-page">{{ pageTitle }}</span></nav>
        <div v-if="route.path !== '/board'" class="context-actions"><button class="icon-button mobile-search" aria-label="Search workspace" @click="searchOpen = true"><Search class="nav-icon" /></button><button v-if="['/', '/my-work'].includes(route.path)" class="create-button" :class="{ secondary: !['/', '/board', '/my-work'].includes(route.path) }" @click="createTask"><Plus class="nav-icon" /><span>New task</span></button></div>
      </header>
      <nav v-if="projectId && route.path !== '/board'" class="project-tabs" aria-label="Project navigation"><router-link v-for="item in projectNav" :key="item.to" :to="projectRoute(item.to)" :class="{ selected: route.path === item.to }">{{ item.label }}</router-link></nav>
      <main id="main-content" tabindex="-1" class="workspace-page" :class="{ 'pane-workspace': ['/board', '/views', '/sprints', '/sprint-planner', '/modules', '/intake', '/documents'].includes(route.path) }">
        <div v-if="pageError" class="page-recovery" role="alert"><h1>This page couldn't load</h1><p>Reload the page to try again.</p><button class="btn" @click="retryPage">Reload page</button></div>
        <router-view v-else />
      </main>
    </div>
    <CommandPalette :open="searchOpen" @close="searchOpen = false" />
    <CreateIssueModal /><EntityForm /><Toaster />
  </div>
</template>
<script setup>
import { ref, computed, onMounted, onBeforeUnmount, onErrorCaptured, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { call } from 'frappe-ui'
import { theme, toggleTheme } from './theme'
import { openCreate, createState } from './ui/create'
import { entityState } from './ui/entity'
import { MODULES } from './modules'
import Avatar from './ui/Avatar.vue'
import Toaster from './ui/Toaster.vue'
import CommandPalette from './components/CommandPalette.vue'
import CreateIssueModal from './components/CreateIssueModal.vue'
import EntityForm from './components/EntityForm.vue'
import Plus from '~icons/lucide/plus'
import House from '~icons/lucide/house'
import SquareCheckBig from '~icons/lucide/square-check-big'
import SquareKanban from '~icons/lucide/square-kanban'
import Inbox from '~icons/lucide/inbox'
import Folder from '~icons/lucide/folder'
import FileText from '~icons/lucide/file-text'
import Settings from '~icons/lucide/settings'
import Sun from '~icons/lucide/sun'
import Moon from '~icons/lucide/moon'
import Search from '~icons/lucide/search'
import Menu from '~icons/lucide/menu'
import MoreHorizontal from '~icons/lucide/ellipsis'
import ChevronDown from '~icons/lucide/chevron-down'
import ChevronRight from '~icons/lucide/chevron-right'

const route = useRoute()
const media = window.matchMedia('(max-width: 767px)')
const isMobile = ref(media.matches), mobileOpen = ref(false), searchOpen = ref(false), pageError = ref(false)
const user = ref(''), projects = ref([]), projectsLoading = ref(true), projectsError = ref(false)
const shortUser = computed(() => (user.value || '').split('@')[0])
const projectId = computed(() => typeof route.query.project === 'string' ? route.query.project : '')
const projectName = computed(() => projects.value.find(p => p.name === projectId.value)?.project_name || projectId.value)
const personalProjects = ref([]), sidebar = ref(null)
const sidebarProjects = computed(() => {
  const preferred = personalProjects.value.filter(row => row.reference_doctype === 'Project')
  const order = new Map(preferred.map((row, index) => [row.reference_name, index]))
  const favorites = new Set(preferred.filter(row => row.kind === 'Favorite').map(row => row.reference_name))
  return [...projects.value].sort((a, b) => Number(favorites.has(b.name)) - Number(favorites.has(a.name))
    || (order.get(a.name) ?? 9999) - (order.get(b.name) ?? 9999)).slice(0, 6)
})
let previousFocus
watch(mobileOpen, async open => {
  if (!isMobile.value) return
  if (open) { previousFocus = document.activeElement; await nextTick(); sidebar.value?.querySelector('a, button')?.focus() }
  else { await nextTick(); previousFocus?.focus() }
})
watch(() => entityState.saved, loadProjects)

const personalNav = [{ to: '/', label: 'Home', icon: House }, { to: '/inbox', label: 'Inbox', icon: Inbox }, { to: '/my-work', label: 'My work', icon: SquareCheckBig }]
const workspaceNav = [{ to: '/projects', label: 'Projects', icon: Folder }, { to: '/views', label: 'Views', icon: SquareKanban }, { to: '/documents', label: 'Pages', icon: FileText }]
const projectNav = [{ to: '/board', label: 'Tasks', icon: SquareKanban }, { to: '/modules', label: 'Modules', icon: Folder }, { to: '/documents', label: 'Pages', icon: FileText }]
const advancedNav = [
  { label: 'Work & planning', items: [{ to: '/board', label: 'All tasks' }, { to: '/todo', label: 'To do' }, { to: '/backlog', label: 'Backlog' }, { to: '/modules', label: 'All modules' }, { to: '/recurring', label: 'Recurring tasks' }, { to: '/epics', label: 'Epics' }, { to: '/releases', label: 'Releases' }] },
  { label: 'Insights', items: [{ to: '/dashboard', label: 'Dashboard' }, { to: '/dashboard/custom', label: 'Custom dashboards' }, { to: '/analytics', label: 'Analytics' }, { to: '/reports', label: 'Reports' }, { to: '/audit', label: 'Audit log' }] },
  { label: 'Workspace tools', items: Object.entries(MODULES).filter(([key]) => key !== 'timesheets').map(([key, mod]) => ({ to: `/m/${key}`, label: mod.title })) },
]
const allItems = [...personalNav, ...workspaceNav, ...projectNav, ...advancedNav.flatMap(group => group.items)]
const pageTitle = computed(() => allItems.find(item => item.to === route.path)?.label || 'Workspace')
const isAdvanced = computed(() => !projectId.value && advancedNav.some(group => group.items.some(item => item.to === route.path)))
function projectRoute(path) { return { path, query: { project: projectId.value } } }
function createTask() { mobileOpen.value = false; openCreate(projectId.value ? { project: projectId.value } : {}) }
function resize(event) { isMobile.value = event.matches }
watch(() => route.fullPath, () => { mobileOpen.value = false; pageError.value = false; if (projectId.value && !projects.value.some(p => p.name === projectId.value)) loadProjects() })
watch(projectId, project => { if (project) call('pulse.api.personal.remember', { doctype: 'Project', name: project }).catch(() => {}) }, { immediate: true })
onErrorCaptured(() => { pageError.value = true; return false })
function retryPage() { window.location.reload() }
function shortcuts(event) {
  if (isMobile.value && mobileOpen.value && !document.querySelector('dialog[open], [role=dialog]') && event.key === 'Tab') {
    const focusable = [...sidebar.value.querySelectorAll('a, button, summary, [tabindex="0"]')].filter(el => el.getClientRects().length && !el.disabled)
    const first = focusable[0], last = focusable.at(-1)
    if (event.shiftKey && (document.activeElement === first || !sidebar.value.contains(document.activeElement))) { event.preventDefault(); last?.focus() }
    else if (!event.shiftKey && (document.activeElement === last || !sidebar.value.contains(document.activeElement))) { event.preventDefault(); first?.focus() }
  }
  if (event.isComposing || event.repeat) return
  const editing = event.target?.closest('input, textarea, select, [contenteditable=true]')
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); searchOpen.value = !searchOpen.value }
  else if (!editing && !event.ctrlKey && !event.metaKey && !event.altKey && !createState.open && !document.querySelector('dialog[open], [role=dialog]') && event.key.toLowerCase() === 'n') { event.preventDefault(); createTask() }
  else if (event.key === 'Escape') mobileOpen.value = false
}
async function loadProjects() {
  projectsLoading.value = true; projectsError.value = false
  try { projects.value = await call('frappe.client.get_list', { doctype: 'Project', fields: ['name', 'project_name', 'pulse_project_key', 'modified'], order_by: 'modified desc', limit_page_length: 0 }) }
  catch { projectsError.value = true }
  finally { projectsLoading.value = false }
  personalProjects.value = await call('pulse.api.personal.items').catch(() => [])
}
onMounted(() => {
  media.addEventListener('change', resize); window.addEventListener('keydown', shortcuts); window.addEventListener('pulse-projects-changed', loadProjects)
  call('frappe.auth.get_logged_user').then(value => { user.value = value }).catch(() => {})
  loadProjects()
})
onBeforeUnmount(() => { media.removeEventListener('change', resize); window.removeEventListener('keydown', shortcuts); window.removeEventListener('pulse-projects-changed', loadProjects) })
</script>
<style scoped>
.pulse-shell { display:flex; height:100%; font-size:14px; overflow:hidden; }
.pulse-sidebar { width:224px; flex-shrink:0; display:flex; flex-direction:column; border-right:1px solid var(--border); background:var(--sidebar, var(--surface-2)); }
.workspace-brand { display:flex; align-items:center; gap:9px; min-height:56px; padding:0 16px; color:var(--text); font-size:15px; font-weight:600; }
.brand-mark { display:grid; place-items:center; width:25px; height:25px; background:var(--text); color:var(--bg); border-radius:6px; font-size:14px; }
.workspace-caption { margin-left:auto; font-size:10px; font-weight:400; color:var(--muted); }
.search-trigger { margin:0 12px 16px; display:flex; align-items:center; gap:8px; height:32px; padding:0 8px; border:1px solid var(--border); border-radius:6px; text-align:left; color:var(--muted); background:var(--surface); font-size:12px; }
.search-trigger kbd { margin-left:auto; font-size:10px; white-space:nowrap; }
.sidebar-scroll { flex:1; min-height:0; overflow:auto; padding:0 10px 16px; }
.nav-group + .nav-group { margin-top:22px; }
.nav-item { display:flex; align-items:center; gap:9px; min-height:32px; padding:6px 9px; border-radius:5px; color:var(--muted); font-size:13px; cursor:pointer; }
.nav-item:hover, .icon-button:hover { background:var(--surface-2); color:var(--text); }
.nav-item.active { color:var(--text); background:var(--surface-3, var(--surface-2)); font-weight:500; }
.nav-item.active .nav-icon { color:var(--accent); }
.nav-icon { width:15px; height:15px; flex-shrink:0; }
.nav-heading { font-size:11px; font-weight:500; color:var(--muted); padding:0 9px; margin:0 0 6px; }
.nav-heading-row { display:flex; align-items:center; justify-content:space-between; padding-right:4px; }
.nav-heading-row .nav-heading { margin:0; }
.project-mark { display:grid; place-items:center; width:18px; height:18px; border:1px solid var(--border); border-radius:4px; font-size:9px; font-weight:600; color:var(--muted); background:var(--surface); }
.project-selected { color:var(--text); font-weight:500; }
.project-chevron { margin-left:auto; width:12px; }
.project-navigation { margin:2px 0 7px 17px; padding-left:7px; border-left:1px solid var(--border); }
.more-navigation { margin-top:22px; }
.more-navigation summary { list-style:none; }
.more-navigation summary::-webkit-details-marker { display:none; }
.advanced-group { margin:12px 0 12px 13px; }
.advanced-group .nav-item { min-height:29px; font-size:12px; }
.nav-message { padding:6px 9px; color:var(--muted); font-size:12px; }
.retry-link { text-decoration:underline; }
.sidebar-footer { display:flex; align-items:center; gap:7px; padding:12px; border-top:1px solid var(--border); }
.user-name { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; font-size:12px; }
.icon-button { display:grid; place-items:center; width:28px; height:28px; border-radius:5px; color:var(--muted); flex-shrink:0; }
.workspace-content { display:flex; flex-direction:column; flex:1; min-width:0; min-height:0; overflow:hidden; }
.context-bar { height:48px; flex-shrink:0; display:flex; align-items:center; gap:10px; padding:0 24px; border-bottom:1px solid var(--border); background:var(--surface); }
.task-toolbar-host { flex:1; min-width:0; }
.breadcrumbs { display:flex; align-items:center; gap:9px; min-width:0; font-size:12px; color:var(--muted); }
.breadcrumbs a { flex-shrink:0; }
.breadcrumbs a:hover { color:var(--text); }
.breadcrumb-project, .current-page { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.breadcrumb-project { max-width:240px; }
.current-page { color:var(--text); }
.breadcrumb-separator { width:12px; height:12px; flex-shrink:0; color:var(--muted); }
.context-actions { display:flex; align-items:center; gap:8px; margin-left:auto; flex-shrink:0; }
.create-button { display:flex; align-items:center; justify-content:center; gap:6px; height:30px; padding:0 10px; border-radius:6px; background:var(--accent); color:var(--on-accent); font-size:12px; font-weight:500; }
.create-button.secondary { background:var(--surface); border:1px solid var(--border); color:var(--text); }
.view-all-projects { margin-top:4px; font-size:12px; color:var(--muted); }
.create-button:hover { filter:brightness(.95); }
.project-tabs { display:flex; gap:24px; flex-shrink:0; padding:0 24px; min-height:42px; border-bottom:1px solid var(--border); background:var(--surface); overflow-x:auto; }
.project-tabs a { display:flex; align-items:center; padding:0 2px; font-size:13px; color:var(--muted); border-bottom:2px solid transparent; }
.project-tabs a.selected { color:var(--text); border-bottom-color:var(--accent); font-weight:500; }
.workspace-page { flex:1; min-height:0; overflow:auto; min-width:0; }
.workspace-page.pane-workspace { display:flex; flex-direction:column; overflow:hidden; }
.pane-workspace > :deep(*) { min-height:0; min-width:0; }
.page-recovery { padding:32px; }
.page-recovery h1 { font-size:20px; font-weight:600; }
.page-recovery p { margin:8px 0 16px; color:var(--muted); }
.mobile-menu, .mobile-search, .nav-backdrop { display:none; }
.skip-link { position:fixed; top:8px; left:8px; z-index:100; padding:12px; background:var(--surface); transform:translateY(-150%); }
.skip-link:focus { transform:translateY(0); }
@media (max-width:767px) {
  .pulse-sidebar { position:fixed; inset:0 auto 0 0; z-index:40; transform:translateX(-100%); transition:transform 160ms ease; }
  .pulse-sidebar.is-open { transform:translateX(0); }
  .nav-backdrop { display:block; position:fixed; inset:0; z-index:30; background:#0006; }
  .mobile-menu, .mobile-search { display:grid; }
  .context-bar { padding:0 12px; gap:6px; }
  .breadcrumbs { gap:5px; }
  .breadcrumbs > a, .breadcrumbs > .breadcrumb-separator:first-of-type { display:none; }
  .breadcrumb-project { max-width:100px; }
  .project-tabs { padding:0 16px; gap:24px; }
}
@media (prefers-reduced-motion:reduce) { .pulse-sidebar { transition:none; } }
</style>
