<template>
  <form ref="formElement" class="inline-create" :class="`variant-${variant}`" @submit.prevent="submit" @keydown.esc.stop.prevent="cancel">
    <label v-if="!project" class="project-choice"><span class="sr-only">Project for new task</span><select v-model="selectedProject" required :disabled="pending" aria-label="Project for new task"><option value="" disabled>Choose project</option><option v-for="item in projects" :key="item.name" :value="item.name">{{ item.project_name || item.name }}</option></select></label>
    <div class="title-line"><span v-if="projectKey" class="task-prefix">{{ projectKey }}</span><input ref="titleInput" v-model="subject" :disabled="pending" aria-label="New task title" placeholder="Work item title" autocomplete="off" maxlength="140" required /><button type="submit" :disabled="pending || !subject.trim() || !(project || selectedProject)" :aria-label="pending ? 'Creating task' : 'Create task'">{{ pending ? '…' : '↵' }}</button><button type="button" aria-label="Cancel task creation" :disabled="pending" @click="cancel">×</button></div>
    <p v-if="error" role="alert" class="inline-error">{{ error }}</p><p v-else-if="variant === 'table'" class="inline-hint">Press Enter to create another work item · Esc to cancel</p>
  </form>
</template>
<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { call } from 'frappe-ui'
const props=defineProps({ variant:{type:String,default:'calendar'}, createTask:{type:Function,required:true}, project:{type:String,default:null}, projects:{type:Array,default:()=>[]}, date:{type:String,default:null}, autofocus:{type:Boolean,default:true} })
const emit=defineEmits(['cancel','created'])
const resolvedKey=ref(''),formElement=ref(null)
const projectKey=computed(()=>props.projects.find(item=>item.name===(props.project || selectedProject.value))?.pulse_project_key || resolvedKey.value)
const subject=ref(''),selectedProject=ref(''),pending=ref(false),error=ref(''),titleInput=ref(null)
watch(()=>props.project || selectedProject.value,async project=>{resolvedKey.value='';if(!project || props.projects.some(item=>item.name===project && item.pulse_project_key))return;try{const value=await call('frappe.client.get_value',{doctype:'Project',filters:{name:project},fieldname:'pulse_project_key'});if(project===(props.project || selectedProject.value))resolvedKey.value=value?.pulse_project_key || ''}catch{/* Creation errors remain visible in the form. */}},{immediate:true})
function cancel(){if(!pending.value)emit('cancel')}
async function submit(){if(pending.value || !subject.value.trim())return; const project=props.project || selectedProject.value;if(!project){error.value='Choose a project first.';return}pending.value=true;error.value='';try{const result=await props.createTask({subject:subject.value.trim(),project,date:props.date});subject.value='';emit('created',result)}catch(e){error.value=e?.messages?.[0] || e.message || 'Task could not be created. Your title is kept; try again.'}finally{pending.value=false;await nextTick();titleInput.value?.focus()}}
function dismissOutside(event){if(formElement.value && !formElement.value.contains(event.target))cancel()}
onMounted(()=>{document.addEventListener('pointerdown',dismissOutside,true);if(props.autofocus)titleInput.value?.focus()})
onBeforeUnmount(()=>document.removeEventListener('pointerdown',dismissOutside,true))
</script>
<style scoped>
.inline-create { min-width:0; border:1px solid var(--border); background:var(--surface); padding:5px 6px; border-radius:4px; }
.title-line { display:flex;align-items:center;gap:4px; }
.title-line input { flex:1;min-width:0;width:100%;border:0;background:transparent;color:var(--text);font-size:12px;padding:5px 2px;outline:none; }
.title-line button { width:22px;height:26px;flex-shrink:0;color:var(--muted);font-size:15px;border-radius:3px; }
.title-line button:hover { color:var(--text);background:var(--hover); }
.title-line button:disabled { opacity:.5; }
.task-prefix { color:var(--muted);font-size:11px;white-space:nowrap;flex-shrink:0; }
.inline-hint { color:var(--muted);font-size:11px;font-style:italic;margin:0;padding:7px 12px;background:var(--surface-2);border-top:1px solid var(--border); }
.variant-table { border:0;border-radius:0;padding:0;width:100%; }
.variant-table .title-line { min-height:42px;padding:6px 12px; }
.variant-table .title-line input { font-size:13px; }
.variant-table .project-choice { display:block;padding:6px 12px 0; }
.inline-error { font-size:11px;color:var(--danger);margin-top:4px; }
.project-choice select { width:100%;border:1px solid var(--border);border-radius:4px;padding:4px;margin-bottom:4px;background:var(--surface);color:var(--text);font-size:11px; }
button:focus-visible,select:focus-visible { outline:2px solid var(--accent);outline-offset:2px; }
</style>
