<script setup lang="ts">
import { GripVertical } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatMoneyShort } from '@/composables/useMoney'

import type { CalendarItem } from '../api'
import { DRAG_TYPE, ICON_TINT, KIND_STYLE } from '../kinds'

/**
 * One calendar item: kind color and icon, time, client. A movable reservation can be dragged
 * onto another day (§4.3); the keyboard path is its sheet (« Modifier » the dates).
 */
const props = defineProps<{ item: CalendarItem; detailed?: boolean }>()
const emit = defineEmits<{ open: [item: CalendarItem] }>()
const { t } = useI18n()

const style = computed(() => KIND_STYLE[props.item.kind])
const draft = computed(() => props.item.status === 'draft' || props.item.status === 'quote_sent')
const text = computed(() =>
  props.item.kind === 'payment' && props.item.amount !== null
    ? `${formatMoneyShort(props.item.amount)} · ${props.item.title}`
    : props.item.title,
)

function onDragStart(event: DragEvent): void {
  if (!props.item.movable || !props.item.reservation || !event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData(
    DRAG_TYPE,
    JSON.stringify({ reservation: props.item.reservation, date: props.item.date }),
  )
  event.dataTransfer.setData('text/plain', props.item.title)
}
</script>

<template>
  <button
    type="button"
    class="group flex w-full min-w-0 items-center gap-1.5 rounded-[7px] text-left transition-[filter] hover:brightness-[0.97]"
    :class="[
      style.chip,
      detailed ? 'px-3 py-2.5' : 'px-1.5 py-1 text-[11.5px]',
      draft && 'opacity-75',
      item.movable && 'cursor-grab active:cursor-grabbing',
    ]"
    :draggable="item.movable && Boolean(item.reservation)"
    :title="item.movable ? t('calendar.dragHint') : undefined"
    @dragstart="onDragStart"
    @click="emit('open', item)"
  >
    <component
      :is="style.icon"
      class="shrink-0"
      :class="[detailed ? 'size-4' : 'size-3.5', ICON_TINT[item.kind]]"
      aria-hidden="true"
    />
    <span class="min-w-0 flex-1">
      <span class="block truncate font-bold" :class="detailed && 'text-[13.5px]'">
        <span class="sr-only">{{ t(`calendar.kinds.${item.kind}`) }} : </span>
        <template v-if="item.time">{{ item.time }} · </template>{{ text }}
        <span v-if="draft" class="sr-only"> ({{ t(`reservations.statuses.${item.status}`) }})</span>
      </span>
      <template v-if="detailed">
        <span
          v-if="item.subtitle"
          class="block truncate text-[12px]"
          :class="item.kind === 'event' ? 'text-white/85' : 'text-muted'"
          >{{ item.subtitle }}</span
        >
        <span
          v-if="item.vehicle || item.owner || item.team.length"
          class="block truncate text-[12px]"
          :class="item.kind === 'event' ? 'text-white/85' : 'text-ink-2'"
          >{{
            [item.team.length ? item.team.join(', ') : item.owner, item.vehicle]
              .filter(Boolean)
              .join(' · ')
          }}</span
        >
      </template>
    </span>
    <GripVertical
      v-if="item.movable && detailed"
      class="size-4 shrink-0 opacity-50"
      aria-hidden="true"
    />
  </button>
</template>
