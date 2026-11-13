<script setup lang="ts">
import { CalendarCheck, CalendarClock, CircleCheck } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { toZonedInput } from '@/composables/useDate'
import { WEmptyState } from '@/design'

import { useMissions } from '../api'
import MissionCard from '../components/MissionCard.vue'
import { groupMissions } from '../missions'

/**
 * « Mes missions » (reservations-stock.md §7, reorganized 13/11/2026), made for the phone: what is
 * on today first, then tomorrow, this week, later; the missions done over the last 14 days at the
 * end. Each card keeps its main action (arrival, departure) in reach.
 */
const { t } = useI18n()
const missions = useMissions()
const today = computed(() => toZonedInput(new Date().toISOString()).slice(0, 10))
const groups = computed(() =>
  groupMissions(missions.data.value?.missions ?? [], today.value, (instant) =>
    toZonedInput(instant).slice(0, 10),
  ),
)
const count = (key: string) => groups.value.find((g) => g.key === key)?.items.length ?? 0
const summary = computed(() => [
  { key: 'today', icon: CalendarCheck, value: count('today'), tone: 'text-violet bg-violet-soft' },
  {
    key: 'coming',
    icon: CalendarClock,
    value: count('tomorrow') + count('week') + count('later'),
    tone: 'text-gold bg-gold-soft',
  },
  { key: 'done', icon: CircleCheck, value: count('done'), tone: 'text-green bg-green-soft' },
])
</script>

<template>
  <div class="mx-auto flex w-full max-w-[760px] flex-col gap-5">
    <header>
      <h1>{{ t('staff.missions.title') }}</h1>
      <p class="mt-1 text-muted">{{ t('staff.missions.subtitle') }}</p>
    </header>

    <WEmptyState
      v-if="missions.isError.value"
      :title="t('staff.missions.loadError')"
      :description="toApiError(missions.error.value).message"
    />
    <template v-else-if="missions.isPending.value">
      <div class="skeleton h-20 rounded-wd-lg" />
      <div class="skeleton h-44 rounded-wd-lg" />
    </template>
    <WEmptyState
      v-else-if="!missions.data.value?.staff"
      :title="t('staff.missions.noProfile')"
      :description="t('staff.missions.noProfileText')"
    />
    <template v-else>
      <ul class="grid grid-cols-3 gap-2.5">
        <li
          v-for="item in summary"
          :key="item.key"
          class="flex flex-col gap-2 rounded-wd-lg border border-line bg-surface p-3 sm:flex-row sm:items-center"
        >
          <span class="flex size-9 items-center justify-center rounded-[10px]" :class="item.tone">
            <component :is="item.icon" class="size-[18px]" aria-hidden="true" />
          </span>
          <span>
            <span class="num block font-display text-[20px] leading-none font-semibold">{{
              item.value
            }}</span>
            <span class="text-[12px] text-muted">{{
              t(`staff.missions.summary.${item.key}`)
            }}</span>
          </span>
        </li>
      </ul>

      <WEmptyState v-if="!groups.length" :icon="CalendarCheck" :title="t('staff.missions.none')" />
      <section
        v-for="group in groups"
        :key="group.key"
        class="flex flex-col gap-3"
        :aria-labelledby="`missions-${group.key}`"
      >
        <h2 :id="`missions-${group.key}`" class="flex items-center gap-2 text-[15px] font-bold">
          {{ t(`staff.missions.groups.${group.key}`) }}
          <span class="num rounded-full bg-surface-2 px-2 text-[12px] text-ink-2">{{
            group.items.length
          }}</span>
        </h2>
        <MissionCard
          v-for="mission in group.items"
          :key="mission.id"
          :mission="mission"
          :open="group.key === 'today'"
        />
      </section>
    </template>
  </div>
</template>
