<template>
  <section class="external-work"><header><h1>Shared work</h1><p class="text-muted">Tasks explicitly shared with your account.</p></header>
    <p v-if="error" role="alert">{{ error }} <button class="btn-ghost" @click="load">Retry</button></p><p v-if="loading">Loading shared work…</p>
    <p v-else-if="!tasks.length" class="text-muted">No tasks have been shared with you.</p>
    <div class="shared-layout"><nav aria-label="Shared tasks"><button v-for="task in tasks" :key="task.name" :aria-current="selected?.name === task.name ? 'page' : undefined" @click="open(task)"><small>{{ task.issue_key || task.name }}</small><span>{{ task.subject }}</span><small>{{ task.status }}</small></button></nav>
      <article v-if="selected"><p class="text-muted">{{ selected.issue_key || selected.name }}</p><h2>{{ selected.subject }}</h2><dl><dt>Status</dt><dd>{{ selected.status }}</dd><dt>Start</dt><dd>{{ selected.start_date || 'Not scheduled' }}</dd><dt>Due</dt><dd>{{ selected.due_date || 'Not scheduled' }}</dd></dl>
        <h3>Shared discussion</h3><p class="text-muted">Comments here are visible to everyone this task is shared with.</p><ul><li v-for="comment in comments" :key="comment.name"><p>{{ comment.content }}</p><small class="text-muted">{{ comment.creation }}</small></li></ul>
        <form @submit.prevent="send"><label>Your comment<textarea v-model="content" class="field" required maxlength="5000" rows="4" /></label><button class="btn-primary" :disabled="busy || !content.trim()">{{ busy ? 'Posting…' : 'Post comment' }}</button></form>
      </article></div>
  </section>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'
const tasks=ref([]), selected=ref(null), comments=ref([]), content=ref(''), loading=ref(true), busy=ref(false), error=ref('')
let version=0
function message(e){return e.messages?.join(' ') || 'Unable to load shared work. Please retry.'}
async function load(){loading.value=true;error.value='';try{tasks.value=await call('pulse.api.external.shared_tasks');if(selected.value&&!tasks.value.some(t=>t.name===selected.value.name)){selected.value=null;comments.value=[]}}catch(e){error.value=message(e);tasks.value=[];selected.value=null}finally{loading.value=false}}
async function open(task){const token=++version;error.value='';selected.value=null;comments.value=[];content.value='';try{const data=await call('pulse.api.external.task',{task:task.name});if(token===version){selected.value=data.task;comments.value=data.comments}}catch(e){error.value=message(e)}}
async function send(){const name=selected.value.name;busy.value=true;error.value='';try{await call('pulse.api.external.comment',{task:name,content:content.value});if(selected.value?.name===name)await open(selected.value)}catch(e){error.value=message(e)}finally{busy.value=false}}
onMounted(load)
</script>
<style scoped>
.external-work{padding:28px;max-width:1400px;margin:auto}.external-work h1{font-size:22px;font-weight:600}.shared-layout{display:grid;grid-template-columns:280px minmax(0,1fr);gap:32px;margin-top:24px}.shared-layout nav{display:grid;align-content:start}.shared-layout nav button{display:grid;gap:5px;text-align:left;padding:14px;border-bottom:1px solid var(--border-color,#e6e8ec)}.shared-layout nav button[aria-current]{background:var(--surface-hover,#f7f8fa)}article h2{font-size:20px;font-weight:600}dl{display:grid;grid-template-columns:80px 1fr;gap:8px;margin:20px 0}h3{font-size:16px;font-weight:600;margin-top:24px}li{padding:12px 0;border-bottom:1px solid var(--border-color,#e6e8ec)}li p{white-space:pre-wrap}form{margin-top:20px;display:grid;gap:12px}label{display:grid;gap:8px}form button{justify-self:start}@media(max-width:700px){.shared-layout{grid-template-columns:1fr}.external-work{padding:16px}}
</style>
