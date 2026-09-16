<template>
  <fieldset class="filter-group" :class="{ nested: depth > 0 }"><legend>Match <select v-model="model.op" aria-label="Filter combination"><option value="and">all (AND)</option><option value="or">any (OR)</option></select> rules</legend><p v-if="!model.rules.length" class="filter-empty">All tasks are included. Add a rule to narrow this view.</p>
    <div v-for="(rule, i) in model.rules" :key="i" class="filter-rule">
      <FilterGroup v-if="rule.rules" v-model="model.rules[i]" :depth="depth + 1" />
      <template v-else><select v-model="rule.field" @change="rule.op = 'eq'; rule.value = ''" aria-label="Filter field"><option v-for="(label, key) in fields" :key="key" :value="key">{{ label }}</option></select><select v-model="rule.op" aria-label="Filter operator"><option value="eq">is</option><option value="ne">is not</option><option value="contains">contains</option><option v-if="isOrdered(rule.field)" value="before">less than / before</option><option v-if="isOrdered(rule.field)" value="after">greater than / after</option><option value="empty">is empty</option><option v-if="rule.field.includes('date')" value="overdue">is overdue</option></select><input v-if="!['empty', 'overdue'].includes(rule.op)" :type="rule.field.includes('date') ? 'date' : ['expected_time', 'pulse_story_points'].includes(rule.field) ? 'number' : 'text'" v-model="rule.value" placeholder="Enter a value" aria-label="Filter value" /></template>
      <button type="button" class="btn-ghost remove-rule" :aria-label="rule.rules ? 'Remove filter group' : 'Remove filter rule'" @click="model.rules.splice(i, 1)">Remove</button>
    </div>
    <button type="button" class="btn-ghost" :disabled="model.rules.length >= 30" @click="model.rules.push({ field: 'subject', op: 'contains', value: '' })">Add rule</button><button v-if="depth < 6" type="button" class="btn-ghost" :disabled="model.rules.length >= 30" @click="model.rules.push({ op: 'or', rules: [] })">Add group</button>
  </fieldset>
</template>
<script setup>
const model = defineModel({ required: true })
defineProps({ depth: { type: Number, default: 0 } })
const isOrdered = field => field.includes('date') || ['expected_time', 'pulse_story_points'].includes(field)
const fields = { subject: 'Title', project: 'Project', workflow_state: 'Status', priority: 'Priority', type: 'Type', assignees: 'Assignee', labels: 'Label', exp_start_date: 'Start date', exp_end_date: 'Due date', expected_time: 'Estimated hours', pulse_story_points: 'Points' }
</script>
<style scoped>
.filter-group { min-width: 0; padding: 0; }
.filter-group.nested { border: 1px solid var(--border); border-radius: 5px; padding: 12px; }
legend { display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: 13px; }
.filter-rule { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 10px 0; }
.filter-rule > .filter-group { flex: 1; }
.filter-empty { color: var(--muted); font-size: 13px; padding: 14px 0 8px; }
input, select { background: var(--surface); border: 1px solid var(--border); border-radius: 5px; padding: 6px 8px; max-width: 100%; min-height: 32px; font-size: 13px; }
input { flex: 1; min-width: 120px; }
input:focus-visible, select:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.remove-rule { color: var(--muted); }
@media (max-width: 640px) { .filter-group.nested { padding: 8px; } .filter-rule > select { flex: 1; min-width: 100px; } }
</style>
