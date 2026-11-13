<script setup lang="ts">
import { TriangleAlert } from '@lucide/vue'

/** Alert banner (complement §4): coral background, icon in a white square, action on the right. */
defineProps<{ title: string; text?: string }>()
</script>

<template>
  <div
    class="flex flex-col gap-3 rounded-[14px] bg-coral-soft px-4 py-3.5 sm:flex-row sm:items-center"
    role="status"
  >
    <span class="flex size-[38px] shrink-0 items-center justify-center rounded-[10px] bg-surface">
      <TriangleAlert class="size-[18px] text-coral" aria-hidden="true" />
    </span>
    <div class="min-w-0 flex-1">
      <p class="font-bold text-ink">{{ title }}</p>
      <p v-if="text" class="text-[13.5px] text-ink-2">{{ text }}</p>
    </div>
    <div v-if="$slots.default" class="shrink-0"><slot /></div>
  </div>
</template>
