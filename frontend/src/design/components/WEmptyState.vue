<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ title: string; description?: string; icon?: Component }>()
</script>

<template>
  <div
    class="flex flex-col items-center rounded-wd border border-dashed border-line-2 p-7 text-center"
  >
    <div
      v-if="icon"
      class="mb-4 flex size-12 items-center justify-center rounded-wd bg-violet-soft text-violet"
    >
      <component :is="icon" class="size-6" aria-hidden="true" />
    </div>
    <h3 class="text-[15px] font-semibold text-ink-2">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-[46ch] text-muted">{{ description }}</p>
    <div v-if="$slots.default" class="mt-5 flex flex-wrap justify-center gap-2"><slot /></div>
  </div>
</template>
