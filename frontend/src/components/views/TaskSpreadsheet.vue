<template>
  <div class="sheet-scroll" :class="{grouped}">
    <div class="sheet-body"><table>
      <caption class="sr-only">Editable tasks</caption>
      <thead><tr>
        <th class="identity" :aria-sort="sortState('subject')"><button @click="$emit('sort', 'subject')">Task <span>{{ sortMark('subject') }}</span></button></th>
        <th v-for="key in propertyColumns" :key="key" :aria-sort="sortState(key)"><span v-if="key === 'modules'">{{ labels[key] }}</span><button v-else @click="$emit('sort', key)">{{ labels[key] || key }} <span>{{ sortMark(key) }}</span></button></th>
      </tr></thead>
      <tbody><tr v-for="task in tasks" :key="task.name" :aria-busy="pending.has(task.name)">
        <td class="identity"><div class="task-identity"><button class="task-key" :aria-label="`Open ${task.subject}`" @click="$emit('open', task.name)">{{ task.issue_key || task.name }}</button><input :value="task.subject" :aria-label="`Title for ${task.subject}`" :disabled="locked(task)" @change="edit(task, 'subject', $event.target.value)" /><button class="open-task" :aria-label="`Open details for ${task.subject}`" @click="$emit('open', task.name)">↗</button></div></td>
        <td v-for="key in propertyColumns" :key="key">
          <span v-if="['creation', 'modified'].includes(key)" class="metadata" :title="task[key] || ''">{{ formatDate(task[key]) }}</span>
          <span v-else-if="key === 'modules'" class="metadata" :title="(task.modules || []).map(module => module.title).join(', ')">{{ (task.modules || []).map(module => module.title).join(', ') || '—' }}</span>
          <span v-else-if="key === 'owner'" class="metadata creator" :title="task.owner">{{ task.owner || '—' }}</span>
          <a v-else-if="key === 'name'" class="record-link" :href="`/app/task/${encodeURIComponent(task.name)}`" target="_blank" rel="noopener">Open record ↗</a>
          <div v-else-if="key === 'workflow_state'" class="property-value"><span class="status-dot" :style="{ backgroundColor: statusColor(task) }" /><select :value="task[key]" :aria-label="`Status for ${task.subject}`" :disabled="locked(task)" @change="edit(task,key,$event.target.value)"><option v-for="option in optionsFor(task,key)" :key="option" :value="option">{{ option }}</option></select></div>
          <div v-else-if="key === 'priority'" class="property-value"><PriorityDot :value="task.priority" /><select :value="task[key]" :aria-label="`Priority for ${task.subject}`" :disabled="locked(task)" @change="edit(task,key,$event.target.value)"><option v-for="option in optionsFor(task,key)" :key="option" :value="option">{{ option }}</option></select></div>
          <select v-else-if="key === 'type'" :value="task[key]" :aria-label="`Type for ${task.subject}`" :disabled="locked(task)" @change="edit(task,key,$event.target.value)"><option v-for="option in optionsFor(task,key)" :key="option" :value="option">{{ option }}</option></select>
          <button v-else-if="['assignees','labels'].includes(key)" class="multi-value" :aria-label="`${labels[key]} for ${task.subject}`" :disabled="locked(task)" aria-haspopup="dialog" :aria-expanded="picker?.task.name === task.name && picker.key === key" @click="openPicker($event,task,key)"><template v-if="task[key]?.length"><span v-for="value in task[key].slice(0,2)" :key="value" class="value-chip"><span v-if="key === 'labels'" class="status-dot" :style="{backgroundColor: labelInfo(task,value)?.color || 'var(--muted)'}" /><span v-else class="assignee-initial">{{ userName(value).slice(0,1).toUpperCase() }}</span><span class="chip-text">{{ key === 'labels' ? labelInfo(task,value)?.label_name || value : userName(value) }}</span></span><span v-if="task[key].length > 2" class="more-values">+{{ task[key].length - 2 }}</span></template><span v-else class="placeholder">{{ key === 'assignees' ? 'Unassigned' : 'Add labels' }}</span></button>
          <input v-else :value="key.includes('date') ? dateValue(task[key]) : task[key]" :aria-label="`${labels[key]} for ${task.subject}`" :type="key.includes('date') ? 'date' : ['expected_time','pulse_story_points'].includes(key) ? 'number' : 'text'" :min="['expected_time','pulse_story_points'].includes(key) ? 0 : undefined" :disabled="locked(task)" @change="edit(task,key,$event.target.value)" />
        </td>
      </tr></tbody>
    </table></div>
    <div v-if="!grouped" class="create-footer"><InlineTaskCreate v-if="creating" variant="table" :create-task="createTask" :project="project" :projects="projects" @cancel="creating = false" /><button v-else class="add-task-row" @click="creating = true">+ Add work item</button></div>
    <Teleport to="body"><div v-if="picker" class="property-overlay" @click.self="closePicker"><section ref="pickerElement" class="property-picker" role="dialog" :aria-label="`Edit ${labels[picker.key]}`" :style="pickerPosition" @keydown="pickerKeydown"><header><strong>{{ labels[picker.key] }}</strong><button aria-label="Close property picker" @click="closePicker">×</button></header><input ref="searchElement" v-model="query" type="search" :placeholder="`Search ${labels[picker.key].toLowerCase()}`" :aria-label="`Search ${labels[picker.key].toLowerCase()}`" /><p v-if="pickerLoading" role="status">Loading people…</p><p v-if="pickerError" role="alert">{{ pickerError }} <button @click="loadPeople">Retry</button></p><div class="property-choices"><label v-for="option in filteredOptions" :key="option.value"><input v-model="draft" type="checkbox" :value="option.value" /><span v-if="option.color" class="status-dot" :style="{backgroundColor:option.color}" /><span>{{ option.label }}<small v-if="picker.key === 'assignees' && option.label !== option.value">{{ option.value }}</small></span></label><p v-if="!pickerLoading && !filteredOptions.length">{{ picker.key === 'labels' ? 'No matching labels. Add labels in project task settings.' : 'No matching people.' }}</p></div><footer><span>{{ draft.length }} selected</span><button @click="closePicker">Cancel</button><button class="apply-choice" :disabled="pickerLoading || Boolean(pickerError)" @click="applyPicker">Apply</button></footer></section></div></Teleport>
  </div>
</template>
<script setup>
import { computed, ref, nextTick, onBeforeUnmount } from 'vue'
import { call } from 'frappe-ui'
import PriorityDot from '@/ui/PriorityDot.vue'
import InlineTaskCreate from './InlineTaskCreate.vue'
const creating = ref(false)
const props = defineProps({ grouped:Boolean, createTask:{type:Function,required:true}, project:{type:String,default:null}, projects:{type:Array,default:()=>[]}, tasks: { type: Array, default: () => [] }, columns: { type: Array, default: () => [] }, labels: { type: Object, default: () => ({}) }, pending: { type: Set, default: () => new Set() }, projectConfigs: { type: Object, default: () => ({}) }, orderBy: String, orderDirection: String })
const emit = defineEmits(['edit', 'open', 'sort'])
const propertyColumns = computed(() => props.columns.filter(key => key !== 'subject'))
const dateValue = value => value ? String(value).slice(0,10) : ''
const formatDate = value => value ? new Date(dateValue(value) + 'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}) : '—'
const locked = task => !task.can_write || props.pending.has(task.name)
function edit(task,key,value) { emit('edit',task,key,value) }
function optionsFor(task,key) { const cfg=props.projectConfigs[task.project]; const values=key==='priority'?['Low','Medium','High','Urgent']:key==='workflow_state'?(cfg?.statuses||[]).map(s=>s.label):cfg?.task_types||[]; return [...new Set([task[key]||'',...values])] }
function statusColor(task) { return props.projectConfigs[task.project]?.statuses?.find(status=>status.label===task.workflow_state)?.color || 'var(--muted)' }
const picker = ref(null), draft = ref([]), query = ref(''), pickerLoading = ref(false), pickerError = ref(''), people = ref([]), userNames = ref({}), pickerPosition = ref({}), pickerElement = ref(null), searchElement = ref(null)
let trigger = null, requestVersion = 0
function labelInfo(task,value) { return props.projectConfigs[task.project]?.labels?.find(label=>label.name===value) }
function userName(value) { return userNames.value[value] || value }
const pickerOptions = computed(() => {
  if (!picker.value) return []
  const { task,key }=picker.value
  const options=key==='labels'?(props.projectConfigs[task.project]?.labels || []).map(label=>({value:label.name,label:label.label_name,color:label.color})):people.value.map(user=>({value:user.name,label:user.full_name || user.name}))
  for(const value of task[key] || []) if(!options.some(option=>option.value===value)) options.push({value,label:key==='assignees'?userName(value):value})
  return options
})
const filteredOptions=computed(()=>pickerOptions.value.filter(option=>`${option.label} ${option.value}`.toLowerCase().includes(query.value.trim().toLowerCase())))
async function loadPeople() {
  const token=++requestVersion; pickerLoading.value=true; pickerError.value=''
  try { const users=await call('pulse.api.spa.get_assignable_users',{project:picker.value?.task.project || null}); if(token!==requestVersion)return; people.value=users; userNames.value={...userNames.value,...Object.fromEntries(users.map(user=>[user.name,user.full_name || user.name]))} }
  catch(e) { if(token===requestVersion)pickerError.value=e.message || 'People could not be loaded.' }
  finally { if(token===requestVersion)pickerLoading.value=false }
}
async function openPicker(event,task,key) {
  trigger=event.currentTarget; const bounds=trigger.getBoundingClientRect(); const width=Math.min(300,window.innerWidth-24)
  pickerPosition.value={left:`${Math.max(12,Math.min(bounds.left,window.innerWidth-width-12))}px`,top:`${Math.max(12,Math.min(bounds.bottom+4,window.innerHeight-360))}px`,width:`${width}px`}
  picker.value={task,key}; draft.value=[...(task[key] || [])]; query.value=''; people.value=[]; pickerError.value=''; pickerLoading.value=false
  if(key==='assignees')loadPeople()
  await nextTick();searchElement.value?.focus()
}
function closePicker(){++requestVersion;picker.value=null;pickerLoading.value=false;trigger?.focus()}
function applyPicker(){if(!picker.value)return; const {task,key}=picker.value;edit(task,key,[...draft.value]);closePicker()}
function pickerKeydown(event){if(event.key==='Escape'){event.preventDefault();closePicker()}else if(event.key==='Tab'){const nodes=pickerElement.value?.querySelectorAll('button:not(:disabled),input:not(:disabled)');if(!nodes?.length)return;const first=nodes[0],last=nodes[nodes.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}}
onBeforeUnmount(()=>{++requestVersion})
function sortState(key) { return props.orderBy===key?(props.orderDirection==='desc'?'descending':'ascending'):'none' }
function sortMark(key) { return props.orderBy===key?(props.orderDirection==='desc'?'↓':'↑'):'' }
</script>
<style scoped>
.create-footer { flex-shrink:0;width:100%;border-top:1px solid var(--border);background:var(--surface); }
.add-task-row { text-align:left;width:100%;padding:10px 14px;min-height:38px;color:var(--muted);font-size:12px; }
.add-task-row:hover { color:var(--text); }
.sheet-scroll { flex: 1; display:flex;flex-direction:column;min-height:0;overflow:hidden;min-width:0;height:100%;max-height:100%; }
.sheet-scroll.grouped { display:block;height:auto;max-height:none;overflow:visible; }
.sheet-scroll.grouped .sheet-body { overflow:visible; }
.sheet-body { flex:1;min-height:0;min-width:0;overflow:auto; }
table { width: 100%; border-collapse: separate; border-spacing: 0; text-align: left; font-size: 12px; }
th { position: sticky; top: 0; z-index: 2; background: var(--surface-2); color: var(--muted); font-weight: 500; height: 36px; border-bottom: 1px solid var(--border); }
th button { display: flex; justify-content: space-between; align-items: center; width: 100%; min-width: 130px; padding: 8px 12px; white-space: nowrap; text-align: left; }
th button:hover { color: var(--text); }
td { height: 42px; padding: 3px 8px; border-bottom: 1px solid var(--border); background: var(--surface); }
.identity { position: sticky; left: 0; min-width: 392px; max-width: 520px; border-right: 1px solid var(--border); z-index: 1; }
th.identity { z-index: 3; }
.task-identity { display: flex; align-items: center; gap: 8px; }
.task-key { color: var(--muted); font-size: 11px; flex-shrink: 0; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-key:hover, .record-link:hover { color: var(--accent); }
.task-identity input { min-width: 160px; width: 100%; color: var(--text); font-size: 13px; }
.open-task { color: var(--muted); flex-shrink: 0; opacity: 0; padding: 4px; }
tr:hover .open-task, tr:focus-within .open-task { opacity: 1; }
input, select { border: 1px solid transparent; border-radius: 4px; background: transparent; padding: 5px 4px; width: 100%; min-width: 120px; height: 30px; color: var(--text); font: inherit; }
input:focus, select:focus { border-color: var(--accent); background: var(--surface); outline: 0; }
input::placeholder { color: var(--muted); }
.property-value { display: flex; gap: 5px; align-items: center; }
.property-value select, .property-value input { min-width: 110px; }
.status-dot { height: 8px; width: 8px; border-radius: 50%; flex-shrink: 0; }
.priority-symbol { width: 13px; font-size: 14px; color: var(--muted); text-align: center; }
.priority-urgent, .priority-critical { color: var(--danger); }
.assignee-initial { display: grid; place-items: center; width: 20px; height: 20px; flex-shrink: 0; border-radius: 50%; background: var(--surface-2); color: var(--text); font-size: 10px; }
.multi-value { display: flex; align-items: center; gap: 4px; min-width: 150px; min-height: 30px; width: 100%; text-align: left; padding: 3px; border-radius: 4px; }
.multi-value:hover { background: var(--surface-2); }
.value-chip { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--border); border-radius: 4px; padding: 2px 5px; max-width: 140px; font-size: 11px; }
.chip-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.placeholder,.more-values { color: var(--muted); font-size: 12px; }
.property-overlay { position: fixed; inset: 0; z-index: 100; }
.property-picker { position: fixed; background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 8px; max-height: min(350px,calc(100dvh - 24px)); display: flex; flex-direction: column; font-size: 12px; }
.property-picker header { display: flex; align-items: center; justify-content: space-between; padding: 3px 3px 8px; }
.property-picker header button { width: 24px; height: 24px; font-size: 18px; }
.property-picker input[type="search"] { border-color: var(--border); flex-shrink: 0; }
.property-choices { overflow: auto; min-height: 0; padding-block: 5px; }
.property-choices label { display: flex; align-items: center; gap: 8px; padding: 7px 5px; border-radius: 4px; cursor: pointer; }
.property-choices label:hover { background: var(--hover); }
.property-choices input[type="checkbox"] { width: 14px; height: 14px; min-width: 14px; padding: 0; accent-color: var(--accent); }
.property-choices small { display: block; font-size: 10px; color: var(--muted); }
.property-picker p { padding: 10px 5px; color: var(--muted); }
.property-picker footer { display: flex; align-items: center; gap: 8px; border-top: 1px solid var(--border); padding-top: 8px; }
.property-picker footer span { margin-right: auto; color: var(--muted); }
.property-picker footer button { padding: 5px 8px; border-radius: 4px; }
.apply-choice { background: var(--accent); color: var(--on-accent); }
.metadata, .record-link { display: block; min-width: 120px; padding: 5px 4px; color: var(--muted); white-space: nowrap; }
.creator { max-width: 220px; overflow: hidden; text-overflow: ellipsis; }
tr:hover td { background: var(--hover); }
button:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media(max-width:640px) { .identity { min-width: 280px; max-width: 300px; } .open-task { opacity: 1; } }
</style>
