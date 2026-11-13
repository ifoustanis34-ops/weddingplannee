<script setup lang="ts">
import { Info } from '@lucide/vue'
</script>

<template>
  <!-- Informational note (complement §4). -->
  <p class="flex items-start gap-2.5 rounded-wd bg-surface-2 px-3.5 py-3 text-[13.5px] text-ink-2">
    <Info class="mt-px size-[18px] shrink-0 text-violet" aria-hidden="true" />
    <span><slot /></span>
  </p>
</template>
