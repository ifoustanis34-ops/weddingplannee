<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { formatMoneyShort } from '@/composables/useMoney'
import { WDateBlock } from '@/design'

import type { CalendarItem } from '../api'
import { ICON_TINT, KIND_STYLE } from '../kinds'
import { iso } from '../month'

/** « Liste »: the period day by day, one line per item, details visible. */
defineProps<{ days: Date[]; byDay: Map<string, CalendarItem[]> }>()
const emit = defineEmits<{ open: [item: CalendarItem] }>()
const { t } = useI18n()
</script>

<template>
  <div class="rounded-wd-lg border border-line bg-surface">
    <template v-for="day in days" :key="iso(day)">
      <section
        v-if="(byDay.get(iso(day)) ?? []).length"
        class="flex gap-4 border-line px-4 py-3 not-last:border-b"
      >
        <WDateBlock :date="iso(day)" weekday class="shrink-0" />
        <ul class="flex min-w-0 flex-1 flex-col divide-y divide-line">
          <li v-for="item in byDay.get(iso(day))" :key="`${item.kind}-${item.id}`">
            <button
              type="button"
              class="flex w-full items-center gap-3 rounded-wd py-2 text-left hover:bg-surface-2"
              @click="emit('open', item)"
            >
              <span
                class="flex size-8 shrink-0 items-center justify-center rounded-full"
                :class="KIND_STYLE[item.kind].chip"
              >
                <component
                  :is="KIND_STYLE[item.kind].icon"
                  class="size-4"
                  :class="ICON_TINT[item.kind]"
                  aria-hidden="true"
                />
              </span>
              <span class="num w-12 shrink-0 text-[13px] font-semibold text-ink-2">{{
                item.time ?? ''
              }}</span>
              <span class="min-w-0 flex-1">
                <span class="block truncate font-semibold">
                  <span class="text-muted">{{ t(`calendar.kinds.${item.kind}`) }} · </span
                  >{{ item.title }}
                </span>
                <span class="block truncate text-[12.5px] text-muted">{{
                  [item.subtitle, item.owner, item.vehicle].filter(Boolean).join(' · ')
                }}</span>
              </span>
              <span v-if="item.amount !== null" class="num shrink-0 font-semibold">{{
                formatMoneyShort(item.amount)
              }}</span>
            </button>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
