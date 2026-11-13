<script setup lang="ts">
import { computed } from 'vue'

/**
 * Avatar (complement §4): round with the ribbon gradient for people,
 * rounded square on the hero colour for an organisation.
 */
const props = withDefaults(
  defineProps<{ name: string; kind?: 'person' | 'organization'; size?: number }>(),
  { kind: 'person', size: 34 },
)

const initials = computed(() => {
  const words = props.name
    .replace(/[&+]/g, ' ')
    .split(/\s+/)
    .filter((word) => /\p{L}/u.test(word))
  const letters = words.length > 1 ? [words[0], words[words.length - 1]] : words
  return letters
    .map((word) => word?.match(/\p{L}/u)?.[0] ?? '')
    .join('')
    .toUpperCase()
})
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center justify-center select-none"
    :class="
      kind === 'person'
        ? 'rounded-full bg-ribbon text-[12.5px] font-extrabold text-white'
        : 'rounded-[9px] bg-hero font-display text-[13px] font-semibold text-hero-ink'
    "
    :style="{ width: `${size}px`, height: `${size}px` }"
    aria-hidden="true"
    >{{ initials }}</span
  >
</template>
