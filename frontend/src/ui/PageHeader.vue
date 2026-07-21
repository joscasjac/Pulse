<template>
  <div class="flex items-start justify-between gap-4 flex-wrap mb-5">
    <div class="min-w-0">
      <h1 class="text-2xl font-bold">{{ title }}</h1>
      <p v-if="subtitle" class="text-sm text-muted mt-0.5">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="flex items-center gap-2 shrink-0">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>
