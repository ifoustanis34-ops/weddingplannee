<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { CalendarItem, CalendarKind } from '../api'
import { ICON_TINT, KIND_STYLE } from '../kinds'
import { iso } from '../month'

/**
 * « Planning logistique » (§4.3): one line per day with the deliveries, setups and pickups,
 * the team and the vehicle — what the warehouse prepares and who drives where.
 */
const props = defineProps<{ days: Date[]; byDay: Map<string, CalendarItem[]> }>()
const emit = defineEmits<{ open: [item: CalendarItem] }>()
const { t, locale } = useI18n()

const COLUMNS: { key: string; kinds: CalendarKind[] }[] = [
  { key: 'delivery', kinds: ['delivery'] },
  { key: 'setup', kinds: ['setup'] },
  { key: 'event', kinds: ['event'] },
  { key: 'pickup', kinds: ['teardown', 'pickup', 'return'] },
]
const todayIso = iso(new Date())
const rows = computed(() =>
  props.days.map((day) => {
    const items = props.byDay.get(iso(day)) ?? []
    return {
      day,
      columns: COLUMNS.map((column) => ({
        ...column,
        items: items.filter((i) => column.kinds.includes(i.kind) && i.reservation),
      })),
      empty: !items.some((i) => i.reservation && i.kind !== 'payment'),
    }
  }),
)
const dayLabel = (day: Date) =>
  new Intl.DateTimeFormat(locale.value, { weekday: 'short', day: 'numeric', month: 'short' })
    .format(day)
    .replace('.', '')
</script>

<template>
  <div class="overflow-hidden rounded-wd-lg border border-line bg-surface">
    <div
      class="hidden grid-cols-[110px_repeat(4,minmax(0,1fr))] border-b border-line bg-surface-2 text-[12px] font-bold text-muted min-[1101px]:grid"
      aria-hidden="true"
    >
      <span class="px-3 py-2">{{ t('calendar.logistics.day') }}</span>
      <span v-for="column in COLUMNS" :key="column.key" class="px-3 py-2">{{
        t(`calendar.logistics.columns.${column.key}`)
      }}</span>
    </div>
    <section
      v-for="row in rows"
      :key="iso(row.day)"
      class="grid grid-cols-1 border-line not-last:border-b min-[1101px]:grid-cols-[110px_repeat(4,minmax(0,1fr))]"
      :class="row.empty && 'text-muted'"
    >
      <h3
        class="px-3 py-2.5 text-[13px] font-bold first-letter:uppercase"
        :class="iso(row.day) === todayIso ? 'text-violet' : row.empty ? 'text-muted' : 'text-ink'"
      >
        {{ dayLabel(row.day) }}
        <span v-if="row.empty" class="block text-[12px] font-semibold text-muted normal-case">{{
          t('calendar.nothing')
        }}</span>
      </h3>
      <template v-if="!row.empty">
        <div
          v-for="column in row.columns"
          :key="column.key"
          class="flex min-w-0 flex-col gap-1.5 px-3 pb-2.5 min-[1101px]:py-2.5"
          :class="!column.items.length && 'hidden min-[1101px]:flex'"
        >
          <p class="text-[11.5px] font-bold text-muted min-[1101px]:hidden">
            {{ t(`calendar.logistics.columns.${column.key}`) }}
          </p>
          <button
            v-for="item in column.items"
            :key="item.id"
            type="button"
            class="flex min-w-0 items-start gap-2 rounded-[8px] px-2 py-1.5 text-left hover:brightness-[0.97]"
            :class="KIND_STYLE[item.kind].chip"
            @click="emit('open', item)"
          >
            <component
              :is="KIND_STYLE[item.kind].icon"
              class="mt-0.5 size-3.5 shrink-0"
              :class="ICON_TINT[item.kind]"
              aria-hidden="true"
            />
            <span class="min-w-0 text-[12.5px]">
              <span class="block truncate font-bold"
                ><template v-if="item.time">{{ item.time }} · </template>{{ item.title }}</span
              >
              <span
                class="block truncate"
                :class="item.kind === 'event' ? 'text-white/85' : 'text-ink-2'"
                >{{ item.subtitle }}</span
              >
              <span
                v-if="item.kind !== 'event'"
                class="block truncate"
                :class="
                  item.vehicle || item.team.length || item.owner ? 'text-ink-2' : 'text-coral'
                "
                >{{
                  [item.team.length ? item.team.join(', ') : item.owner, item.vehicle]
                    .filter(Boolean)
                    .join(' · ') || t('calendar.logistics.unassigned')
                }}</span
              >
            </span>
          </button>
        </div>
      </template>
    </section>
  </div>
</template>
