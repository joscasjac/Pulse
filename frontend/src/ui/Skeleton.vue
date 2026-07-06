<template>
  <span class="sk" :style="{ width, height, borderRadius: radius }" aria-hidden="true" />
</template>

<script setup>
defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '14px' },
  radius: { type: String, default: '6px' },
})
</script>

<style scoped>
.sk {
  display: inline-block;
  background: linear-gradient(90deg, var(--surface-2) 25%, var(--hover) 37%, var(--surface-2) 63%);
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}
@keyframes shimmer { 0% { background-position: 100% 0; } 100% { background-position: 0 0; } }
@media (prefers-reduced-motion: reduce) { .sk { animation: none; } }
</style>
