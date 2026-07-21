import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('@/pages/Home.vue') },
  { path: '/dashboard', name: 'Dashboard', component: () => import('@/pages/Dashboard.vue') },
  { path: '/dashboard/custom', name: 'CustomDashboard', component: () => import('@/pages/CustomDashboard.vue') },
  { path: '/analytics', name: 'Analytics', component: () => import('@/pages/Analytics.vue') },
  { path: '/reports', name: 'Reports', component: () => import('@/pages/Reports.vue') },
  { path: '/todo', name: 'ToDo', component: () => import('@/pages/ToDo.vue') },
  { path: '/my-work', name: 'MyWork', component: () => import('@/pages/MyWork.vue') },
  { path: '/board', name: 'Board', component: () => import('@/pages/Board.vue') },
  { path: '/backlog', name: 'Backlog', component: () => import('@/pages/Backlog.vue') },
  { path: '/sprints', name: 'Sprints', component: () => import('@/pages/Sprints.vue') },
  { path: '/recurring', name: 'Recurring', component: () => import('@/pages/Recurring.vue') },
  { path: '/projects', name: 'Projects', component: () => import('@/pages/Projects.vue') },
  { path: '/epics', name: 'Epics', component: () => import('@/pages/Epics.vue') },
  { path: '/releases', name: 'Releases', component: () => import('@/pages/Releases.vue') },
  { path: '/audit', name: 'Audit', component: () => import('@/pages/AuditLog.vue') },
  { path: '/m/:mod', name: 'Module', component: () => import('@/pages/Module.vue') },
]

const router = createRouter({
  history: createWebHistory('/pulse'),
  routes,
})

export default router
