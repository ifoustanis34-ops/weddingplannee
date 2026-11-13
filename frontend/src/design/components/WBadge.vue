<script setup lang="ts">
import { computed } from 'vue'

import type { BadgeTone } from './badgeTones'

const props = withDefaults(defineProps<{ tone?: BadgeTone; dot?: boolean }>(), {
  tone: 'violet',
  dot: true,
})

const resolvedTone = computed<BadgeTone>(() => props.tone)

const TONES: Record<BadgeTone, string> = {
  violet: 'bg-violet-soft text-violet',
  gold: 'bg-gold-soft text-gold',
  fuchsia: 'bg-fuchsia-soft text-fuchsia',
  coral: 'bg-coral-soft text-coral',
  green: 'bg-green-soft text-green',
  red: 'bg-red-soft text-red',
  grey: 'bg-grey-soft text-muted',
}
</script>

<template>
  <span
    class="inline-flex h-6 items-center gap-1.5 rounded-full px-[9px] text-[12px] font-bold whitespace-nowrap"
    :class="TONES[resolvedTone]"
  >
    <span v-if="dot" class="size-1.5 rounded-full bg-current" aria-hidden="true" />
    <slot />
  </span>
</template>
