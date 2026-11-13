<script setup lang="ts">
import { computed, ref } from 'vue'

import { ringSegments } from '../charts'

/**
 * Ring with a 2px surface gap between segments (dataviz: never a border). Hovering or focusing
 * a segment shows it in the center; the legend next to it always carries every value.
 */
const props = withDefaults(
  defineProps<{
    items: { key: string; label: string; value: number; color: string; display: string }[]
    /** Shown in the center when nothing is hovered. */
    centerValue: string
    centerLabel: string
    label: string
    size?: number
  }>(),
  { size: 148 },
)

const RADIUS = 54
const STROKE = 16
const active = ref<string | null>(null)
const segments = computed(() =>
  ringSegments(
    props.items.map((i) => i.value),
    RADIUS,
  ).map((segment) => ({ ...segment, item: props.items[segment.index]! })),
)
const focused = computed(() => props.items.find((i) => i.key === active.value) ?? null)
</script>

<template>
  <div class="relative shrink-0" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg viewBox="0 0 140 140" class="size-full -rotate-90" role="img" :aria-label="label">
      <circle
        cx="70"
        cy="70"
        :r="RADIUS"
        fill="none"
        stroke="var(--surface-2)"
        :stroke-width="STROKE"
      />
      <circle
        v-for="segment in segments"
        :key="segment.item.key"
        cx="70"
        cy="70"
        :r="RADIUS"
        fill="none"
        :stroke="segment.item.color"
        :stroke-width="active === segment.item.key ? STROKE + 4 : STROKE"
        :stroke-dasharray="segment.dash"
        :stroke-dashoffset="segment.offset"
        class="cursor-default transition-[stroke-width] duration-150 outline-none"
        :class="active && active !== segment.item.key && 'opacity-45'"
        tabindex="0"
        :aria-label="`${segment.item.label} : ${segment.item.display}`"
        @mouseenter="active = segment.item.key"
        @mouseleave="active = null"
        @focus="active = segment.item.key"
        @blur="active = null"
      />
    </svg>
    <div
      class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-5 text-center"
      aria-hidden="true"
    >
      <span class="font-display text-[19px] leading-tight font-semibold">{{
        focused ? focused.display : centerValue
      }}</span>
      <span class="mt-0.5 line-clamp-2 text-[11.5px] leading-tight font-semibold text-muted">{{
        focused ? focused.label : centerLabel
      }}</span>
    </div>
  </div>
</template>
