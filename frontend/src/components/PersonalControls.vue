<template>
  <div class="flex flex-wrap gap-2 items-center">
    <button class="btn text-xs" :disabled="busy" :aria-pressed="favorite" @click="toggle('Favorite')">{{ favorite ? '★ Favorited' : '☆ Favorite' }}</button>
    <button v-if="doctype === 'Task'" class="btn text-xs" :disabled="busy" :aria-pressed="following" @click="toggle('Follow')">{{ following ? 'Following' : 'Follow task' }}</button>
    <span v-if="error" role="alert" class="text-xs">{{ error }}</span>
  </div>
</template>
<script setup>
import { ref, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({ doctype: { type: String, default: 'Task' }, name: String, recordRecent: { type: Boolean, default: true } })
const favorite = ref(false), following = ref(false), busy = ref(false), error = ref('')
let generation = 0
watch(() => [props.doctype, props.name], async () => {
  const request = ++generation
  const { doctype, name } = props
  favorite.value = following.value = false
  error.value = ''
  busy.value = true
  if (!name) { busy.value = false; return }
  try {
    const kinds = await call('pulse.api.personal.state', { doctype, name })
    if (request !== generation) return
    favorite.value = kinds.includes('Favorite')
    following.value = kinds.includes('Follow')
    if (props.recordRecent) await call('pulse.api.personal.remember', { doctype, name })
  } catch { if (request === generation) error.value = 'Could not load personal controls.' }
  finally { if (request === generation) busy.value = false }
}, { immediate: true })
async function toggle(kind) {
  if (busy.value || !props.name) return
  const request = generation
  busy.value = true; error.value = ''
  const state = kind === 'Favorite' ? favorite : following
  try { await call('pulse.api.personal.remember', { doctype: props.doctype, name: props.name, kind, enabled: state.value ? 0 : 1 }); if (request === generation) state.value = !state.value }
  catch { if (request === generation) error.value = 'Could not save. Try again.' }
  finally { if (request === generation) busy.value = false }
}
</script>
