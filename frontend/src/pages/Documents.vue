<template>
  <main class="documents">
    <form class="pages-toolbar" @submit.prevent="load">
      <h1>Pages</h1>
      <label v-if="!route.query.project" class="project-filter"><span class="sr-only">Project</span><select v-model="project" @change="changeProject"><option value="">All projects</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option></select></label>
      <label class="page-search"><span class="sr-only">Search pages</span><input v-model="query" type="search" placeholder="Search pages…" /></label>
      <button class="btn-ghost search-submit">Search</button>
      <button type="button" class="btn-primary" @click="newPage">New page</button>
    </form>
    <p v-if="error" class="page-alert" role="alert">{{ error }} <button class="btn-ghost" @click="load">Retry</button></p>
    <div class="doc-layout">
      <nav class="page-library" aria-label="Project pages">
        <div class="library-heading"><span>All pages</span><span>{{ pages.length }}</span></div>
        <p v-if="loading" class="library-empty" role="status">Loading pages…</p>
        <button v-for="row in pages" :key="row.name" class="page-row" :title="`${row.title} · ${projectLabel(row.project)}`" :aria-current="page?.name === row.name ? 'page' : undefined" @click="open(row.name)">
          <FeatherIcon name="file-text" class="page-file" aria-hidden="true" /><span class="page-row-copy">{{ row.title }}</span>
        </button>
        <p v-if="!loading && !pages.length" class="library-empty">No pages found.<br />Create a page or change your search.</p>
      </nav>
      <article v-if="page" :key="page.name || 'new-page'" class="doc-body">
        <p v-if="actionError" class="page-alert" role="alert">{{ actionError }}</p>
        <p v-if="notice" class="page-notice" role="status">{{ notice }}</p>
        <template v-if="editing">
          <div class="editor-heading"><span class="page-context">{{ page.name ? 'Editing page' : 'New page' }}</span><div class="doc-actions"><button class="btn-ghost" :disabled="busy" @click="cancel">{{ page.name ? 'Close' : 'Cancel' }}</button><button class="btn-primary" :disabled="busy || !draft.title || !draft.project" @click="save">{{ busy ? 'Saving…' : page.name ? 'Save details' : 'Create page' }}</button></div></div>
          <label class="title-field"><span class="sr-only">Page title</span><input v-model.trim="draft.title" placeholder="Untitled page" maxlength="140" required /></label>
          <div v-if="!page.name" class="new-page-options">
            <label>Project<select v-model="draft.project" @change="options"><option value="">Select project</option><option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option></select></label>
            <label>Template<select v-model="template" @change="applyTemplate"><option value="">Blank page</option><option value="brief">Project brief</option><option value="meeting">Meeting notes</option><option value="specification">Specification</option></select></label>
          </div>
          <CollaborativeEditor v-if="page.name" ref="collaborativeEditor" :key="page.name" :name="page.name" :content="page.content" :mentions="mentions" @synced="page.modified = $event" />
          <TextEditor v-else :key="editorKey" :content="draft.content" :fixed-menu="true" :mentions="mentionOptions" :upload-args="{ doctype: 'Pulse Document', docname: page.name, is_private: 1 }" placeholder="Write your page. Type @ to mention a teammate." editor-class="prose prose-sm doc-editor" @change="draft.content = $event" />
          <details class="page-panel"><summary>Linked tasks <span>{{ draft.tasks.length }}</span></summary><div class="panel-content"><label>Choose tasks<select v-model="draft.tasks" multiple size="4"><option v-for="task in taskOptions" :key="task.name" :value="task.name">{{ task.subject }} ({{ task.name }})</option></select></label><small>Use Ctrl or Command to select several tasks.</small></div></details>
        </template>
        <template v-else>
          <header class="reader-heading">
            <h2>{{ page.title }}</h2>
            <div class="reader-actions">
              <details class="page-details" @keydown.esc="$event.currentTarget.open = false"><summary>Details</summary><div class="metadata-popover"><dl><dt>Project</dt><dd>{{ projectLabel(page.project) }}</dd><dt>Updated</dt><dd>{{ page.modified?.slice(0,10) }}</dd><dt>Updated by</dt><dd>{{ page.modified_by }}</dd></dl><PersonalControls doctype="Pulse Document" :name="page.name" /></div></details>
              <button v-if="page.can_write" class="btn-ghost" @click="edit">Edit page</button>
            </div>
          </header>
          <TextEditor :key="page.modified" :content="page.content" :mentions="mentionOptions" :editable="false" editor-class="prose prose-sm doc-reader" />
          <div class="page-tools">
            <details class="page-panel"><summary>Linked tasks <span>{{ page.tasks?.length || 0 }}</span></summary><div class="panel-content"><a v-for="task in page.tasks" :key="task.name" class="task-link" :href="`/app/task/${encodeURIComponent(task.name)}`"><span>{{ task.subject }}</span><small>{{ task.name }}</small></a><p v-if="!page.tasks?.length" class="text-muted">No linked tasks. Edit this page to connect it to your work.</p></div></details>
            <details class="page-panel"><summary>Comments <span>{{ page.comments?.length || 0 }}</span></summary><div class="panel-content"><ol class="comment-list"><li v-for="item in page.comments" :key="item.name"><small>{{ item.owner }} · {{ item.creation }}</small><TextEditor :content="item.content" :mentions="mentionOptions" :editable="false" editor-class="prose prose-sm" /></li></ol><TextEditor :key="commentKey" :content="comment" :mentions="mentionOptions" placeholder="Add a comment or @mention a teammate" editor-class="prose prose-sm doc-comment" @change="comment = $event" /><div class="comment-actions"><button class="btn-ghost" :disabled="busy || !plain(comment).trim()" @click="postComment">Post comment</button></div></div></details>
            <details class="page-panel" @toggle="loadHistory"><summary>Revision history</summary><div class="panel-content"><p v-if="historyError" role="alert">{{ historyError }}</p><ol class="revision-list"><li v-for="revision in history" :key="revision.name"><small>{{ revision.creation }} · {{ revision.owner }}</small><details><summary>View changes</summary><div v-for="(change,index) in changes(revision)" :key="index"><strong>{{ change[0] }}</strong><p class="revision-value">Previous: {{ plain(change[1]) }}</p><p class="revision-value">Updated: {{ plain(change[2]) }}</p></div></details></li></ol><p v-if="!history.length" class="text-muted">No saved revisions yet.</p></div></details>
          </div>
        </template>
      </article>
      <div v-else class="pages-empty"><FeatherIcon name="file-text" class="empty-page-icon" aria-hidden="true" /><h2>Select a page</h2><p>Choose from the list or create a new page.</p></div>
    </div>
  </main>
</template>
<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { call, TextEditor, FeatherIcon } from 'frappe-ui'
import CollaborativeEditor from '../components/documents/CollaborativeEditor.vue'
import PersonalControls from '../components/PersonalControls.vue'
const collaborativeEditor = ref(null)
const route = useRoute(), router = useRouter()
const pages=ref([]), projects=ref([]), project=ref(typeof route.query.project === 'string' ? route.query.project : ''), query=ref(''), page=ref(null), loading=ref(false), busy=ref(false), error=ref(''), actionError=ref(''), notice=ref(''), editing=ref(false)
const draft=ref({title:'', project:'', content:'', tasks:[]}), template=ref(''), templateContents=ref({}), mentions=ref([]), taskOptions=ref([]), editorKey=ref(0), comment=ref(''), commentKey=ref(0), history=ref([]), historyError=ref('')
const mentionOptions={mentions:()=>mentions.value}
const api=(method,args={})=>call(`pulse.api.documents.${method}`,args)
let request=0, listRequest=0, optionsRequest=0, historyRequest=0
function projectLabel(name){return projects.value.find(p=>p.name===name)?.project_name||name}
async function changeProject(){const next={...route.query};if(project.value)next.project=project.value;else delete next.project;if(page.value?.project && project.value && page.value.project!==project.value)delete next.name;await router.replace({query:next});project.value=typeof route.query.project==='string'?route.query.project:''}

async function load(){const current=++listRequest;loading.value=true;error.value='';try{const result=await api('list_pages',{project:project.value||null,query:query.value||null});if(current===listRequest)pages.value=result}catch(e){if(current===listRequest)error.value=e.message||'Pages could not be loaded.'}finally{if(current===listRequest)loading.value=false}}
async function options(){
  const current=++optionsRequest, selectedProject=draft.value.project
  mentions.value=[];taskOptions.value=[]
  if(!selectedProject)return
  try{const data=await api('editor_options',{project:selectedProject});if(current!==optionsRequest || selectedProject!==draft.value.project)return;mentions.value=data.mentions||[];taskOptions.value=data.tasks||[]}
  catch(e){if(current===optionsRequest)actionError.value=e.message}
}
async function discard(){if(!editing.value)return true;if(page.value?.name){try{await collaborativeEditor.value?.flush()}catch(e){actionError.value=e.message;return false}if(draft.value.title===page.value.title && JSON.stringify([...draft.value.tasks].sort())===JSON.stringify((page.value.task_links||[]).map(row=>row.task).sort()))return true}return window.confirm(page.value?.name ? 'Leave editing? Shared body changes are already saved. Unsaved title and task changes will be discarded.' : 'Discard your unsaved page changes?')}
async function open(name){if(!await discard())return;const version=++request;actionError.value='';try{const result=await api('get_page',{name});if(version!==request)return;page.value=result;editing.value=false;draft.value.project=result.project;await options();if(version!==request)return;history.value=[];comment.value='';commentKey.value++}catch(e){actionError.value=e.message;error.value=e.message}}
async function newPage(){if(!await discard())return;request++;historyRequest++;history.value=[];historyError.value='';comment.value='';commentKey.value++;page.value={};draft.value={title:'',project:project.value,content:'',tasks:[]};template.value='';editing.value=true;editorKey.value++;actionError.value='';notice.value='';options()}
function edit(){draft.value={title:page.value.title,project:page.value.project,content:page.value.content||'',tasks:(page.value.task_links||[]).map(t=>t.task)};editing.value=true;editorKey.value++;notice.value=''}
async function cancel(){
  if(!await discard())return
  if(!page.value.name){page.value=null;editing.value=false;return}
  busy.value=true;actionError.value=''
  const name=page.value.name, version=++request
  try{
    // Mount the reader only after the canonical autosaved content is available.
    // Its key may already match the last sync timestamp, so switching modes
    // before this fetch can render the old body under the current revision key.
    const latest=await api('get_page',{name})
    if(version!==request)return
    page.value=latest;history.value=[];historyError.value='';editing.value=false
  }catch(e){actionError.value=e.message||'The saved page could not be refreshed. Keep the editor open and try Close again.'}
  finally{busy.value=false}
}
function applyTemplate(){draft.value.content=templateContents.value[template.value]||'';editorKey.value++}
async function save(){busy.value=true;actionError.value='';try{await collaborativeEditor.value?.flush();page.value=await api('save_page',{...draft.value,name:page.value.name||null,modified:page.value.modified||null,base_details:page.value.name?{title:page.value.title,tasks:(page.value.task_links||[]).map(row=>row.task)}:null});editing.value=false;notice.value='Page saved.';await load()}catch(e){actionError.value=e.message||'The page could not be saved. Your draft is still here.'}finally{busy.value=false}}
async function postComment(){busy.value=true;actionError.value='';try{page.value=await api('add_comment',{name:page.value.name,content:comment.value});comment.value='';commentKey.value++}catch(e){actionError.value=e.message}finally{busy.value=false}}
async function loadHistory(event){
  // A disclosure can emit toggle while its previous page is being unmounted.
  // Nested revision disclosures must not start another page-history request.
  if(event.target!==event.currentTarget || !event.currentTarget.open || editing.value || !page.value?.name)return
  const name=page.value.name, current=++historyRequest
  historyError.value=''
  try{const result=await api('revisions',{name});if(current===historyRequest && page.value?.name===name && !editing.value)history.value=result}
  catch(e){if(current===historyRequest && page.value?.name===name)historyError.value=e.message}
}
function changes(revision){try{return JSON.parse(revision.data).changed||[]}catch{return []}}
function plain(value){const element=document.createElement('div');element.innerHTML=String(value||'');return element.textContent||''}
watch(()=>route.query.name, name=>{if(name && name!==page.value?.name)open(name)})
watch(()=>route.query.project, async value=>{project.value=typeof value==='string'?value:'';if(editing.value || (page.value && project.value && page.value.project!==project.value)){request++;page.value=null;editing.value=false}await load()})
onBeforeRouteUpdate((to,from)=>to.query.project!==from.query.project?discard():true)
onBeforeRouteLeave(()=>discard())
onMounted(async()=>{try{[projects.value,templateContents.value]=await Promise.all([call('frappe.client.get_list',{doctype:'Project',fields:['name','project_name'],limit_page_length:0}),api('templates')]);await load();if(route.query.name)await open(route.query.name)}catch(e){error.value=e.message}})
</script>
<style scoped>
.documents{flex:1;height:100%;min-height:0;display:flex;flex-direction:column;overflow:hidden;color:var(--text);background:var(--surface)}
.pages-toolbar{flex-shrink:0;display:flex;align-items:center;gap:8px;min-height:44px;padding:6px 16px;border-bottom:1px solid var(--border)}
.pages-toolbar h1{font-size:14px;line-height:20px;font-weight:600;margin:0 6px 0 0;flex-shrink:0}
.project-filter{width:160px;min-width:100px}.page-search{width:190px;margin-inline-start:auto;min-width:100px}
input,select{display:block;width:100%;height:28px;padding:3px 7px;border:1px solid var(--border);border-radius:4px;background:var(--surface);color:var(--text);font-size:12px}
.pages-toolbar :is(button,select){white-space:nowrap}.documents :is(.btn-primary,.btn-ghost){min-height:28px;padding:3px 9px;font-size:12px;border-radius:4px}
.doc-layout{display:grid;grid-template-columns:200px minmax(0,1fr);flex:1;min-height:0;overflow:hidden;grid-template-rows:minmax(0,1fr)}
.page-library{min-height:0;overflow-y:auto;overscroll-behavior:contain;border-inline-end:1px solid var(--border);padding:8px 6px;background:var(--surface)}
.library-heading{position:sticky;top:-8px;z-index:1;background:var(--surface);display:flex;justify-content:space-between;align-items:center;height:26px;padding:0 8px;color:var(--muted);font-size:11px}
.page-row{display:flex;align-items:center;gap:7px;width:100%;height:30px;padding:4px 8px;text-align:start;border-radius:3px;color:var(--muted)}
.page-row:hover,.page-row[aria-current]{background:var(--hover);color:var(--text)}
.page-file{width:14px;height:14px;flex-shrink:0}.page-row-copy{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}
.library-empty{padding:10px 8px;color:var(--muted);font-size:12px;line-height:1.6}
.doc-body{min-height:0;overflow-y:auto;overscroll-behavior:contain;scrollbar-gutter:stable;width:100%;height:100%;max-width:none;padding:24px;margin:0;min-width:0;box-sizing:border-box}
.reader-heading,.editor-heading,.doc-actions,.reader-actions{display:flex;align-items:center;gap:8px}
.reader-heading{justify-content:space-between;align-items:flex-start;margin-bottom:20px}
.reader-heading h2{min-width:0;font-size:22px;font-weight:600;line-height:1.35;letter-spacing:-.02em;overflow-wrap:anywhere;margin:0}
.reader-actions{flex-shrink:0;position:relative}.page-details>summary{list-style:none;cursor:pointer;padding:5px 7px;font-size:12px;color:var(--muted);white-space:nowrap}.page-details>summary::-webkit-details-marker{display:none}.page-details>summary:hover{background:var(--hover);border-radius:4px}.metadata-popover{position:absolute;inset-inline-end:0;top:34px;z-index:20;width:270px;max-width:calc(100vw - 32px);padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:6px;font-size:12px}.metadata-popover dl{display:grid;grid-template-columns:70px minmax(0,1fr);gap:8px;margin-bottom:12px}.metadata-popover dt{color:var(--muted)}.metadata-popover dd{overflow-wrap:anywhere}
.editor-heading{justify-content:space-between;margin-bottom:12px}.page-context{font-size:12px;color:var(--muted);margin:0}.title-field input{font-size:22px;font-weight:600;border:0;border-radius:0;padding:2px 0;height:34px;margin-bottom:12px}
.new-page-options{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}.new-page-options label{flex:1 1 160px;font-size:11px;color:var(--muted)}.new-page-options select{margin-top:4px}
.doc-body :deep(.prose){width:100%;max-width:none;margin-inline:0}.doc-body :deep(.doc-editor){min-height:240px;padding:8px 0;max-width:none}.doc-body :deep(.doc-reader){min-height:64px;max-width:none;font-size:14px;line-height:1.7}.doc-body :deep(.doc-comment){padding:10px;min-height:72px;border:1px solid var(--border);border-radius:4px}.doc-body :deep(.sync-state){font-size:11px;padding:4px 0}.doc-body :deep(img){max-width:100%;height:auto}.doc-body :deep(pre){overflow:auto}
.page-tools{margin-top:24px}.page-panel{border-top:1px solid var(--border)}.page-panel>summary{padding:9px 0;font-size:12px;font-weight:500;cursor:pointer}.page-panel>summary span{color:var(--muted);font-weight:400;margin-inline-start:5px}.panel-content{padding:4px 0 14px;font-size:13px}.panel-content label{display:block;font-size:12px}.panel-content select{margin-top:6px;height:auto}.task-link{display:flex;justify-content:space-between;gap:12px;align-items:baseline;padding:7px 0}.task-link:hover span{text-decoration:underline}small{display:block;color:var(--muted);font-size:11px}.panel-content>small{margin-top:6px}.comment-list li,.revision-list li{padding:0 0 12px}.comment-list small,.revision-list small{margin-bottom:6px}.comment-actions{display:flex;justify-content:flex-end;margin-top:6px}.revision-list summary{cursor:pointer;font-size:12px;padding:5px 0}.revision-value{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}
.pages-empty{overflow-y:auto;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;text-align:center;padding:32px 16px;min-height:0}.empty-page-icon{width:24px;height:24px;color:var(--muted)}.pages-empty h2{font-size:14px;font-weight:500;margin:0}.pages-empty p{max-width:36ch;color:var(--muted);font-size:12px;line-height:1.6}
.page-alert,.page-notice{padding:8px 0;font-size:12px}.documents>.page-alert{padding-inline:16px;flex-shrink:0;max-height:20%;overflow:auto}button:disabled{opacity:.55;cursor:not-allowed}:is(button,input,select,summary):focus-visible{outline:2px solid var(--accent);outline-offset:2px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:900px){.doc-layout{grid-template-columns:176px minmax(0,1fr)}.doc-body{padding:24px}.project-filter{width:136px}.page-search{width:150px}.pages-toolbar{padding-inline:12px;gap:6px}}
@media(max-width:640px){.pages-toolbar{flex-wrap:wrap;padding:6px 10px}.pages-toolbar h1{margin-inline-end:0}.project-filter{flex:1;max-width:180px}.page-search{order:4;width:auto;flex:1 1 calc(100% - 64px);margin-inline-start:0}.search-submit{order:5}.pages-toolbar>.btn-primary{margin-inline-start:auto}.doc-layout{grid-template-columns:1fr;grid-template-rows:minmax(70px,24%) minmax(0,1fr)}.page-library{min-height:0;overflow-y:auto;overscroll-behavior:contain;border-inline-end:0;border-bottom:1px solid var(--border);max-height:none;overflow:auto}.doc-body{padding:16px}.reader-heading{gap:12px;flex-wrap:wrap;margin-bottom:16px}.reader-heading h2,.title-field input{font-size:20px}.reader-actions{margin-inline-start:auto}.task-link{flex-direction:column;gap:3px}.editor-heading{flex-wrap:wrap}}
</style>
