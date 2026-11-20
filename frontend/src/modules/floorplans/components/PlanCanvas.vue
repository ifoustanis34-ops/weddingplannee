<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  CHAIR,
  chairsOf,
  ELEMENTS,
  metres,
  outerMargin,
  PAPER,
  round,
  seatCount,
} from '../elements'
import type { PlanElement } from '../types'

/**
 * The plan drawn to scale (one SVG unit = one metre): the room with its 1 m grid and its
 * dimensions, then every element. In the editor, an element is selected and dragged with the
 * mouse or the finger (snapped to 5 cm). Also the thumbnail of the list, and the exported image.
 */
const props = withDefaults(
  defineProps<{
    name?: string
    venue?: string
    length: number
    width: number
    elements: PlanElement[]
    selected?: string | null
    editable?: boolean
    /** Thumbnail: no title, no dimensions. */
    compact?: boolean
  }>(),
  { name: '', venue: '', selected: null, editable: false, compact: false },
)
const emit = defineEmits<{
  select: [id: string | null]
  move: [id: string, x: number, y: number]
  moved: []
}>()
const { t } = useI18n()

const svg = ref<SVGSVGElement | null>(null)
defineExpose({ svg })

const L = computed(() => Math.max(1, props.length || 1))
const W = computed(() => Math.max(1, props.width || 1))
const big = computed(() => Math.max(L.value, W.value))
const font = computed(() => Math.max(0.22, Math.min(big.value / 55, 1.4)))
const margin = computed(() => (props.compact ? big.value * 0.03 : Math.max(1, font.value * 3.2)))
const header = computed(() => (props.compact ? 0 : font.value * 3.4))
const viewBox = computed(
  () =>
    `${-margin.value} ${-margin.value - header.value} ${L.value + 2 * margin.value} ${
      W.value + 2 * margin.value + header.value
    }`,
)

// Grid: every metre (every 5 m on large grounds), stronger every 5 m (10 m).
const step = computed(() => (big.value > 60 ? 5 : 1))
const strong = computed(() => step.value * 5)
const gridX = computed(() => lines(L.value))
const gridY = computed(() => lines(W.value))
function lines(size: number): number[] {
  const out: number[] = []
  for (let v = step.value; v < size - 1e-6; v += step.value) out.push(round(v))
  return out
}

const label = (element: PlanElement) =>
  element.label || (element.type === 'chair' ? '' : t(`floorplans.types.${element.type}`))
const textSize = (element: PlanElement) =>
  Math.max(0.16, Math.min(font.value, Math.min(element.w, element.h) * 0.42))
const transform = (element: PlanElement) =>
  `translate(${element.x} ${element.y}) rotate(${element.rotation || 0} ${element.w / 2} ${
    element.h / 2
  })`
const seats = computed(() => seatCount(props.elements))

// --- Dragging --------------------------------------------------------------------------------
let drag: { id: string; dx: number; dy: number; moved: boolean } | null = null

function point(event: PointerEvent): { x: number; y: number } {
  const matrix = svg.value?.getScreenCTM()
  if (!svg.value || !matrix) return { x: 0, y: 0 }
  const p = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse())
  return { x: p.x, y: p.y }
}

function start(event: PointerEvent, element: PlanElement): void {
  if (!props.editable) return
  event.stopPropagation()
  emit('select', element.id)
  const p = point(event)
  drag = { id: element.id, dx: p.x - element.x, dy: p.y - element.y, moved: false }
  svg.value?.setPointerCapture(event.pointerId)
}

function move(event: PointerEvent): void {
  if (!drag) return
  const element = props.elements.find((e) => e.id === drag!.id)
  if (!element) return
  const p = point(event)
  const x = Math.min(Math.max(p.x - drag.dx, -element.w / 2), L.value - element.w / 2)
  const y = Math.min(Math.max(p.y - drag.dy, -element.h / 2), W.value - element.h / 2)
  const snapped = { x: round(x, 0.05), y: round(y, 0.05) }
  if (snapped.x === element.x && snapped.y === element.y) return
  drag.moved = true
  emit('move', element.id, snapped.x, snapped.y)
}

function end(event: PointerEvent): void {
  if (!drag) return
  if (svg.value?.hasPointerCapture(event.pointerId))
    svg.value.releasePointerCapture(event.pointerId)
  if (drag.moved) emit('moved')
  drag = null
}

function background(): void {
  if (props.editable) emit('select', null)
}
</script>

<template>
  <svg
    ref="svg"
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="viewBox"
    preserveAspectRatio="xMidYMid meet"
    font-family="Montserrat, Arial, sans-serif"
    class="block h-auto w-full select-none"
    :class="editable ? 'touch-none' : ''"
    role="img"
    :aria-label="t('floorplans.canvasLabel', { length: metres(L), width: metres(W) })"
    @pointerdown="background"
    @pointermove="move"
    @pointerup="end"
    @pointercancel="end"
  >
    <rect
      :x="-margin"
      :y="-margin - header"
      :width="L + 2 * margin"
      :height="W + 2 * margin + header"
      :fill="PAPER.sheet"
    />

    <!-- Title: name, venue, size, places -->
    <g v-if="!compact" :fill="PAPER.ink">
      <text :x="0" :y="-margin - header + font * 1.5" :font-size="font * 1.15" font-weight="700">
        {{ name }}
      </text>
      <text :x="0" :y="-margin - header + font * 2.9" :font-size="font * 0.8" :fill="PAPER.muted">
        {{
          [
            venue,
            t('floorplans.size', { length: metres(L), width: metres(W) }),
            t('floorplans.seats', { count: seats }, seats),
          ]
            .filter(Boolean)
            .join(' · ')
        }}
      </text>
    </g>

    <!-- Room and grid -->
    <rect :width="L" :height="W" :fill="PAPER.room" />
    <line
      v-for="x in gridX"
      :key="`x${x}`"
      :x1="x"
      :x2="x"
      :y2="W"
      :stroke="x % strong === 0 ? PAPER.gridStrong : PAPER.grid"
      stroke-width="1"
      vector-effect="non-scaling-stroke"
    />
    <line
      v-for="y in gridY"
      :key="`y${y}`"
      :y1="y"
      :y2="y"
      :x2="L"
      :stroke="y % strong === 0 ? PAPER.gridStrong : PAPER.grid"
      stroke-width="1"
      vector-effect="non-scaling-stroke"
    />
    <rect
      :width="L"
      :height="W"
      fill="none"
      :stroke="PAPER.wall"
      :stroke-width="compact ? 1.5 : 3"
      vector-effect="non-scaling-stroke"
    />

    <!-- Dimensions -->
    <g v-if="!compact" :fill="PAPER.muted" :font-size="font * 0.85" font-weight="600">
      <line
        :x1="0"
        :x2="L"
        :y1="-margin / 2"
        :y2="-margin / 2"
        :stroke="PAPER.muted"
        stroke-width="1"
        vector-effect="non-scaling-stroke"
      />
      <text :x="L / 2" :y="-margin / 2 - font * 0.35" text-anchor="middle">{{ metres(L) }}</text>
      <line
        :x1="-margin / 2"
        :x2="-margin / 2"
        :y1="0"
        :y2="W"
        :stroke="PAPER.muted"
        stroke-width="1"
        vector-effect="non-scaling-stroke"
      />
      <text
        :transform="`translate(${-margin / 2 - font * 0.35} ${W / 2}) rotate(-90)`"
        text-anchor="middle"
      >
        {{ metres(W) }}
      </text>
    </g>

    <!-- Elements -->
    <g
      v-for="element in elements"
      :key="element.id"
      :transform="transform(element)"
      :class="editable ? 'cursor-move' : ''"
      @pointerdown="start($event, element)"
    >
      <!-- Chairs of tables and rows -->
      <rect
        v-for="(chair, i) in chairsOf(element)"
        :key="i"
        :x="chair.x - CHAIR / 2"
        :y="chair.y - CHAIR / 2"
        :width="CHAIR"
        :height="CHAIR"
        :rx="CHAIR * 0.2"
        :transform="`rotate(${chair.rotation} ${chair.x} ${chair.y})`"
        :fill="PAPER.chairFill"
        :stroke="PAPER.chair"
        stroke-width="1"
        vector-effect="non-scaling-stroke"
      />
      <circle
        v-if="element.type === 'round_table'"
        :cx="element.w / 2"
        :cy="element.h / 2"
        :r="Math.min(element.w, element.h) / 2"
        :fill="ELEMENTS.round_table.fill"
        :stroke="ELEMENTS.round_table.stroke"
        stroke-width="1.5"
        vector-effect="non-scaling-stroke"
      />
      <g v-else-if="element.type === 'chair'">
        <rect
          :width="element.w"
          :height="element.h"
          :rx="Math.min(element.w, element.h) * 0.2"
          :fill="PAPER.chairFill"
          :stroke="PAPER.chair"
          stroke-width="1"
          vector-effect="non-scaling-stroke"
        />
        <line
          :x1="element.w * 0.15"
          :x2="element.w * 0.85"
          :y1="element.h * 0.18"
          :y2="element.h * 0.18"
          :stroke="PAPER.chair"
          stroke-width="2"
          vector-effect="non-scaling-stroke"
        />
      </g>
      <rect
        v-else-if="element.type !== 'text' && element.type !== 'chair_row'"
        :width="element.w"
        :height="element.h"
        :rx="element.type === 'pillar' ? 0 : Math.min(element.w, element.h) * 0.08"
        :fill="ELEMENTS[element.type].fill"
        :stroke="ELEMENTS[element.type].stroke"
        stroke-width="1.5"
        vector-effect="non-scaling-stroke"
        :stroke-dasharray="element.type === 'dance_floor' ? '6 4' : undefined"
      />
      <!-- Invisible hit area for the row and the text -->
      <rect
        v-if="element.type === 'chair_row' || element.type === 'text'"
        :width="element.w"
        :height="element.h"
        fill="transparent"
      />
      <text
        v-if="label(element) && element.type !== 'pillar'"
        :x="element.w / 2"
        :y="element.type === 'chair_row' ? element.h + textSize(element) * 1.1 : element.h / 2"
        :font-size="element.type === 'text' ? font * 1.1 : textSize(element)"
        :font-weight="element.type === 'text' ? 700 : 600"
        :fill="PAPER.ink"
        text-anchor="middle"
        dominant-baseline="central"
        pointer-events="none"
      >
        {{ label(element) }}
      </text>
      <rect
        v-if="editable && element.id === selected"
        :x="-outerMargin(element) - 0.1"
        :y="-outerMargin(element) - 0.1"
        :width="element.w + 2 * outerMargin(element) + 0.2"
        :height="element.h + 2 * outerMargin(element) + 0.2"
        fill="none"
        :stroke="PAPER.selected"
        stroke-width="2"
        stroke-dasharray="5 3"
        vector-effect="non-scaling-stroke"
        pointer-events="none"
      />
    </g>
  </svg>
</template>
