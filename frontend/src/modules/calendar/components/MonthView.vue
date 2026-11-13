<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { CalendarItem } from '../api'
import { iso } from '../month'
import { KIND_STYLE } from '../kinds'
import CalendarChip from './CalendarChip.vue'
import { type MoveRequest, useDropDay } from './useDropDay'

/** Month grid from Monday: 3 items a day, then « +n » opens the day (complement §11). */
const props = defineProps<{
  days: Date[]
  month: number
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

const weekdays = computed(() =>
  Array.from({ length: 7 }, (_, i) =>
    new Intl.DateTimeFormat(locale.value, { weekday: 'short' })
      .format(new Date(2026, 9, 19 + i)) // 19 Oct 2026 is a Monday
      .replace('.', ''),
  ),
)
const todayIso = iso(new Date())
const items = (day: Date) => props.byDay.get(iso(day)) ?? []
</script>

<template>
  <div
    class="overflow-hidden rounded-wd-lg border border-line bg-surface"
    role="grid"
    :aria-label="title"
    :aria-busy="busy"
  >
    <div class="grid grid-cols-7 border-b border-line" role="row">
      <span
        v-for="day in weekdays"
        :key="day"
        role="columnheader"
        class="px-2 py-2 text-center text-[12px] font-bold text-muted capitalize"
        >{{ day }}</span
      >
    </div>
    <div class="grid grid-cols-7">
      <div
        v-for="(day, index) in days"
        :key="iso(day)"
        role="gridcell"
        :data-day="iso(day)"
        class="flex min-h-[58px] min-w-0 flex-col gap-1 border-line p-1.5 transition-colors min-[701px]:min-h-[112px]"
        :class="[
          day.getMonth() !== month && 'bg-surface-2 text-muted',
          index % 7 !== 6 && 'border-r',
          index < 35 && 'border-b',
          drop.over.value === iso(day) && 'bg-violet-soft',
        ]"
        @dragover="drop.dragover($event, iso(day))"
        @dragleave="drop.dragleave(iso(day))"
        @drop="drop.drop($event, iso(day))"
      >
        <button
          type="button"
          class="num flex size-6 items-center justify-center self-center rounded-full text-[12.5px] font-semibold hover:bg-surface-2 min-[701px]:self-start"
          :class="iso(day) === todayIso && 'bg-violet text-violet-ink hover:bg-violet'"
          :aria-label="t('calendar.openDay', { date: day.toLocaleDateString(locale) })"
          @click="emit('day', iso(day))"
        >
          {{ day.getDate() }}
        </button>
        <div class="hidden flex-col gap-1 min-[701px]:flex">
          <CalendarChip
            v-for="item in items(day).slice(0, 3)"
            :key="`${item.kind}-${item.id}`"
            :item="item"
            @open="emit('open', $event)"
          />
          <button
            v-if="items(day).length > 3"
            type="button"
            class="px-1.5 text-left text-[11.5px] font-bold text-violet hover:underline"
            @click="emit('day', iso(day))"
          >
            {{ t('calendar.more', { count: items(day).length - 3 }) }}
          </button>
        </div>
        <!-- Mobile: dots, the day opens on tap -->
        <button
          v-if="items(day).length"
          type="button"
          class="flex justify-center gap-1 min-[701px]:hidden"
          :aria-label="t('calendar.dayItems', { count: items(day).length }, items(day).length)"
          @click="emit('day', iso(day))"
        >
          <span
            v-for="item in items(day).slice(0, 3)"
            :key="`dot-${item.kind}-${item.id}`"
            class="size-[7px] rounded-full"
            :class="KIND_STYLE[item.kind].dot"
          />
        </button>
      </div>
    </div>
  </div>
</template>
