<template>
  <section class="inbox-page">
    <header class="page-header"><div><h1 class="page-title">Inbox</h1><p class="page-description">Assignments, mentions, and updates to the work you follow.</p></div><span class="connection" :title="connected ? 'Live updates connected' : 'Checking every 30 seconds'"><span :class="{ online: connected }" />{{ connected ? 'Live' : 'Syncing' }}</span></header>
    <div class="inbox-toolbar" aria-label="Notification filter"><button :class="{ selected: !unread }" @click="unread = false; load()">All updates</button><button :class="{ selected: unread }" @click="unread = true; load()">Unread</button></div>
    <p v-if="error" role="alert" class="notice">{{ error }} <button class="underline" @click="load">Try again</button></p>
    <p v-if="loading" role="status" class="empty">Loading updates…</p>
    <div v-else-if="!rows.length && !error" class="empty"><InboxIcon class="empty-icon" /><h2>{{ unread ? 'You’re all caught up' : 'A little quiet here' }}</h2><p>{{ unread ? 'New updates will appear here as your team makes progress.' : 'Your assignments, mentions, and followed task updates will appear here.' }}</p></div>
    <ul class="notification-list"><li v-for="row in rows" :key="row.name" :class="{ unread: !row.is_read }">
      <span class="read-indicator" :class="{ fresh: !row.is_read }" aria-hidden="true" />
      <div class="notification-body"><button class="notification-title" :class="{ 'font-semibold': !row.is_read }" @click="open(row)">{{ row.message }}</button><p>{{ row.notification_type }} <span aria-hidden="true">·</span> {{ formatDate(row.creation) }}</p></div>
      <button class="read-action" :disabled="!!saving" @click="mark(row)">{{ row.is_read ? 'Mark unread' : 'Mark read' }}</button>
    </li></ul>
  </section>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { call } from 'frappe-ui'
import { io } from 'socket.io-client'
import InboxIcon from '~icons/lucide/inbox'
import { useRouter } from 'vue-router'
const rows=ref([]), unread=ref(false), loading=ref(false), error=ref(''), saving=ref(''), router=useRouter()
const connected = ref(false)
let socket, poll
let generation = 0
function formatDate(value) { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) }
async function load() { const request = ++generation; loading.value=true; error.value=''; try { const result=await call('pulse.api.personal.inbox',{unread_only:unread.value?1:0}); if(request === generation) rows.value=result } catch { if(request === generation) error.value='Notifications could not load.' } finally { if(request === generation) loading.value=false } }
async function mark(row, read) { if (saving.value) return false; saving.value=row.name; try { await call('pulse.api.personal.mark_read',{name:row.name,is_read:read ?? (row.is_read?0:1)}); await load(); return true } catch { error.value='Could not update this notification. Try again.'; return false } finally { saving.value='' } }
async function open(row) { if(await mark(row,1)) router.push(row.url) }
onMounted(() => {
  load()
  const site = window.sitename || location.hostname
  socket = io(`${location.protocol}//${location.hostname}:${window.socketio_port || 9000}/${site}`, {
    withCredentials: true, transports: ['polling', 'websocket'],
    transportOptions: { polling: { extraHeaders: { 'X-Frappe-Site-Name': site } } },
  })
  socket.on('connect', () => { connected.value = true; load() })
  socket.on('disconnect', () => { connected.value = false })
  socket.on('connect_error', () => { connected.value = false })
  socket.on('pulse_notification', load)
  poll = setInterval(() => { if (!document.hidden && !loading.value && !saving.value) load() }, 30000)
})
onBeforeUnmount(() => { ++generation; socket?.disconnect(); clearInterval(poll) })
</script>

<style scoped>
.inbox-page { max-width: 1000px; margin: 0 auto; padding: 28px 32px; }
.connection { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); }
.connection span { width: 6px; height: 6px; background: var(--faint); border-radius: 50%; }.connection .online { background: var(--term-green); }
.inbox-toolbar { display: flex; gap: 22px; border-bottom: 1px solid var(--border); }
.inbox-toolbar button { padding: 10px 0; font-size: 13px; color: var(--muted); border-bottom: 2px solid transparent; }
.inbox-toolbar .selected { color: var(--text); border-bottom-color: var(--text); font-weight: 500; }
.notice { margin-top: 16px; color: var(--danger); }
.empty { padding: 72px 20px; text-align: center; color: var(--muted); }.empty h2 { margin-top: 16px; color: var(--text); font-size: 16px; }.empty p { max-width: 380px; margin: 8px auto 0; font-size: 13px; }.empty-icon { width: 28px; height: 28px; margin: auto; }
.notification-list li { display: flex; gap: 12px; align-items: flex-start; padding: 18px 12px; border-bottom: 1px solid var(--border-soft); }.notification-list li:hover { background: var(--surface-2); }.notification-body { flex: 1; min-width: 0; }.notification-title { text-align: left; font-size: 13px; line-height: 1.6; }.notification-title:hover { text-decoration: underline; }.notification-body p { font-size: 12px; color: var(--muted); margin-top: 4px; }.notification-body p span { margin: 0 5px; }.read-indicator { width: 6px; height: 6px; flex-shrink: 0; border-radius: 50%; margin-top: 7px; }.read-indicator.fresh { background: var(--accent); }.read-action { font-size: 12px; color: var(--muted); white-space: nowrap; padding: 3px 6px; border-radius: 4px; }.read-action:hover { color: var(--text); background: var(--hover); }
@media (max-width:767px) { .inbox-page { padding: 20px 16px; }.notification-list li { flex-wrap: wrap; }.read-action { margin-left: 18px; }.connection { display: none; } }
</style>
