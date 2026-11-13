<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import type { CalendarItem } from '../api'
import { iso } from '../month'
import CalendarChip from './CalendarChip.vue'
import { type MoveRequest, useDropDay } from './useDropDay'

/** Week (7 columns) or day (one wide column with details), in the order of the day. */
const props = defineProps<{
  days: Date[]
  byDay: Map<string, CalendarItem[]>
  title: string
  busy: boolean
}>()
const emit = defineEmits<{
  open: [item: CalendarItem]
  day: [day: string]
  move: [request: MoveRequest]
}>()
const { t, locale } = useI18n()
const drop = useDropDay((request) => emit('move', request))
const todayIso = iso(new Date())
const single = () => props.days.length === 1
const heading = (day: Date) =>
  new Intl.DateTimeFormat(locale.value, {
    weekday: single() ? 'long' : 'short',
    day: 'numeric',
    month: single() ? 'long' : undefined,
  }).format(day)
</script>

<template>
  <div
    class="grid overflow-hidden rounded-wd-lg border border-line bg-surface"
    :class="single() ? 'grid-cols-1' : 'grid-cols-1 min-[901px]:grid-cols-7'"
    :aria-label="title"
    :aria-busy="busy"
    role="list"
  >
    <section
      v-for="(day, index) in days"
      :key="iso(day)"
      role="listitem"
      :data-day="iso(day)"
      class="flex min-h-[120px] min-w-0 flex-col gap-1.5 border-line p-2 transition-colors min-[901px]:min-h-[420px]"
      :class="[
        index < days.length - 1 && 'border-b min-[901px]:border-r min-[901px]:border-b-0',
        drop.over.value === iso(day) && 'bg-violet-soft',
      ]"
      @dragover="drop.dragover($event, iso(day))"
      @dragleave="drop.dragleave(iso(day))"
      @drop="drop.drop($event, iso(day))"
    >
      <h3 class="mb-1">
        <button
          v-if="!single()"
          type="button"
          class="rounded-[6px] px-1 text-[13px] inline-block font-bold first-letter:uppercase hover:bg-surface-2"
          :class="iso(day) === todayIso ? 'text-violet' : 'text-ink'"
          @click="emit('day', iso(day))"
        >
          {{ heading(day) }}
        </button>
        <span
          v-else
          class="px-1 text-[15px] inline-block font-bold first-letter:uppercase"
          :class="iso(day) === todayIso ? 'text-violet' : 'text-ink'"
          >{{ heading(day) }}</span
        >
      </h3>
      <p v-if="!(byDay.get(iso(day)) ?? []).length" class="px-1 text-[13px] text-muted">
        {{ t('calendar.nothing') }}
      </p>
      <CalendarChip
        v-for="item in byDay.get(iso(day)) ?? []"
        :key="`${item.kind}-${item.id}`"
        :item="item"
        :detailed="single()"
        @open="emit('open', $event)"
      />
    </section>
  </div>
</template>
