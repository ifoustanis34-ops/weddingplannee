<script setup lang="ts">
import { computed, useId } from 'vue'

import {
  areaChartGeometry,
  CHART_BOTTOM,
  CHART_HEIGHT,
  CHART_PAD_X,
  CHART_WIDTH,
} from './areaChart'

/**
 * Cash-in curve of the dashboard (complement §7): hand-made SVG, ribbon stroke, last value labelled.
 * The ribbon gradient is reserved for this curve and a few other places (CLAUDE.md §6).
 */
const props = withDefaults(
  defineProps<{
    points: { label: string; value: number }[]
    /** Accessible summary, e.g. « mai : 3 200 000 FCFA, juin : … ». */
    label: string
    formatTick?: (value: number) => string
    formatValue?: (value: number) => string
  }>(),
  {
    formatTick: (value: number) => String(value),
    formatValue: (value: number) => String(value),
  },
)

const id = useId()
// Sora has no narrow no-break space glyph: in SVG text it collapses (« 800000 »).
const svgText = (text: string) => text.replace(/[\u202f\u00a0]/g, ' ')
const geometry = computed(() => areaChartGeometry(props.points.map((p) => p.value)))
const last = computed(() => geometry.value.points[geometry.value.points.length - 1])
/** The value label stays inside the chart, even when the last point is close to an edge. */
const labelX = computed(() =>
  last.value ? Math.min(Math.max(last.value.x - 36, 0), CHART_WIDTH - 72) : 0,
)
</script>

<template>
  <svg
    :viewBox="`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`"
    class="block h-auto w-full overflow-visible"
    role="img"
    :aria-label="label"
  >
    <defs>
      <linearGradient :id="`${id}-stroke`" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#4A22B5" />
        <stop offset="0.42" stop-color="#8E2BA8" />
        <stop offset="0.7" stop-color="#E03E7D" />
        <stop offset="1" stop-color="#F68A45" />
      </linearGradient>
      <linearGradient :id="`${id}-area`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#8E2BA8" stop-opacity="0.28" />
        <stop offset="1" stop-color="#8E2BA8" stop-opacity="0" />
      </linearGradient>
    </defs>

    <g class="text-[11.5px] font-semibold" aria-hidden="true">
      <template v-for="tick in geometry.ticks" :key="tick.value">
        <line
          :x1="CHART_PAD_X"
          :x2="CHART_WIDTH - CHART_PAD_X"
          :y1="tick.y"
          :y2="tick.y"
          stroke="var(--line)"
          stroke-width="1"
          :stroke-dasharray="tick.value === 0 ? undefined : '3 5'"
        />
        <text :x="CHART_PAD_X - 10" :y="tick.y + 4" text-anchor="end" fill="var(--muted)">
          {{ svgText(formatTick(tick.value)) }}
        </text>
      </template>
      <text
        v-for="(point, index) in geometry.points"
        :key="`m-${index}`"
        :x="point.x"
        :y="CHART_BOTTOM + 22"
        text-anchor="middle"
        fill="var(--muted)"
      >
        {{ points[index]?.label }}
      </text>
    </g>

    <path v-if="geometry.area" :d="geometry.area" :fill="`url(#${id}-area)`" />
    <path
      v-if="geometry.line"
      :d="geometry.line"
      fill="none"
      :stroke="`url(#${id}-stroke)`"
      stroke-width="3.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <circle
      v-for="(point, index) in geometry.points.slice(0, -1)"
      :key="`p-${index}`"
      :cx="point.x"
      :cy="point.y"
      r="3.5"
      fill="var(--surface)"
      stroke="#A12FA4"
      stroke-width="2"
    />
    <g v-if="last" data-testid="area-chart-last">
      <circle :cx="last.x" :cy="last.y" r="6" fill="#E5407B" />
      <rect :x="labelX" :y="last.y - 40" width="72" height="28" rx="8" fill="var(--hero)" />
      <text
        :x="labelX + 36"
        :y="last.y - 21.5"
        text-anchor="middle"
        fill="var(--hero-ink)"
        class="font-display text-[12.5px] font-semibold"
      >
        {{ svgText(formatValue(last.value)) }}
      </text>
    </g>
  </svg>
</template>
