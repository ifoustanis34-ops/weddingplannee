<script setup lang="ts">
import { computed } from 'vue'

/** `ribbon` is reserved for wedding progress and cash-in curves (CLAUDE.md §6). */
const props = withDefaults(
  defineProps<{
    value: number
    label: string
    ribbon?: boolean
    showValue?: boolean
    /** Green once complete (contract fully paid, complement §12). */
    greenWhenFull?: boolean
  }>(),
  { ribbon: false, showValue: false, greenWhenFull: false },
)
const clamped = computed(() => Math.min(100, Math.max(0, Math.round(props.value))))
</script>

<template>
  <div class="flex items-center gap-3">
    <div
      class="h-1.5 flex-1 overflow-hidden rounded-[6px] bg-surface-2"
      role="progressbar"
      :aria-label="label"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="clamped"
    >
      <div
        class="h-full rounded-[6px] transition-[width] duration-500"
        :class="ribbon ? 'bg-ribbon' : greenWhenFull && clamped >= 100 ? 'bg-green' : 'bg-violet'"
        :style="{ width: `${clamped}%` }"
      />
    </div>
    <span v-if="showValue" class="tabular w-10 text-right text-[13px] font-bold text-ink-2">
      {{ clamped }} %
    </span>
  </div>
</template>
