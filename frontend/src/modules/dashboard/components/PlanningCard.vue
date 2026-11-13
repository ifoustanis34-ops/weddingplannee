<script setup lang="ts">
import { CalendarHeart, CircleCheck, Hammer, PackageCheck, Truck, Undo2, Wallet } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { formatMoneyShort } from '@/composables/useMoney'
import { WAvatar, WCard } from '@/design'

import type { DashboardSummary, PlanningItem } from '../api'

/**
 * « Planning logistique des 7 prochains jours » (reservations-stock.md §8): one line per day.
 * Weddings wear the ribbon, installments the gold; deliveries, setups and pickups join with
 * reservations (S4), each with its own color (violet, fuchsia, coral).
 */
defineProps<{ days: DashboardSummary['planning'] }>()
const { t } = useI18n()

const ICONS = {
  event: CalendarHeart,
  task: CircleCheck,
  payment: Wallet,
  delivery: Truck,
  setup: Hammer,
  pickup: PackageCheck,
  return: Undo2,
} as const
const dayName = (iso: string, index: number) => {
  if (index === 0) return t('dashboard.planning.today')
  if (index === 1) return t('dashboard.planning.tomorrow')
  const label = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    timeZone: 'UTC',
  }).format(new Date(`${iso}T12:00:00Z`))
  return label.charAt(0).toUpperCase() + label.slice(1)
}
const dayNumber = (iso: string) =>
  new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(
    new Date(`${iso}T12:00:00Z`),
  )
const link = (item: PlanningItem) =>
  item.reservation
    ? { name: 'reservations', query: { reservation: item.reservation } }
    : item.kind === 'payment'
      ? { name: 'finance', query: { contract: item.contract } }
      : { name: 'weddings', query: { mariage: item.wedding } }
/** A busy day never stretches the page: weddings and installments always, 3 tasks at most. */
const TASKS_PER_DAY = 3
function visible(items: PlanningItem[]): { shown: PlanningItem[]; hidden: number } {
  const tasks = items.filter((i) => i.kind === 'task')
  // Timed steps in the order of the day, then the untimed ones (weddings, installments).
  const steps = items
    .filter((i) => i.kind !== 'task')
    .sort((a, b) => (a.time ?? '99:99').localeCompare(b.time ?? '99:99'))
  const shown = [...steps, ...tasks.slice(0, TASKS_PER_DAY)]
  return { shown, hidden: Math.max(0, tasks.length - TASKS_PER_DAY) }
}
/** §4.3 colors: events ribbon, deliveries violet, setups fuchsia, pickups and returns coral. */
const TONES: Record<PlanningItem['kind'], string> = {
  event: 'bg-ribbon text-white',
  delivery: 'bg-violet-soft text-ink',
  setup: 'bg-fuchsia-soft text-ink',
  pickup: 'bg-coral-soft text-ink',
  return: 'bg-coral-soft text-ink',
  payment: 'bg-gold-soft text-ink',
  task: 'bg-surface-2 text-ink',
}
const ICON_TONES: Partial<Record<PlanningItem['kind'], string>> = {
  delivery: 'text-violet',
  setup: 'text-fuchsia',
  pickup: 'text-coral',
  return: 'text-coral',
  payment: 'text-gold',
}
const tone = (item: PlanningItem) => TONES[item.kind]
</script>

<template>
  <WCard
    :title="t('dashboard.planning.title')"
    :subtitle="t('dashboard.planning.subtitle')"
    class="h-full"
  >
    <ol class="flex flex-col">
      <li
        v-for="(day, index) in days"
        :key="day.date"
        class="flex gap-3 border-line py-2.5 not-last:border-b"
      >
        <div class="w-[78px] shrink-0 pt-1">
          <p class="text-[13px] font-bold" :class="index === 0 ? 'text-violet' : 'text-ink'">
            {{ dayName(day.date, index) }}
          </p>
          <p class="text-[12px] font-semibold text-muted">{{ dayNumber(day.date) }}</p>
        </div>
        <p v-if="!day.items.length" class="pt-1 text-[13px] text-muted">
          {{ t('dashboard.planning.nothing') }}
        </p>
        <ul v-else class="flex min-w-0 flex-1 flex-col gap-1.5">
          <li v-for="item in visible(day.items).shown" :key="item.id">
            <RouterLink
              :to="link(item)"
              class="flex items-center gap-2.5 rounded-[10px] px-2.5 py-2 transition-opacity hover:opacity-90"
              :class="tone(item)"
            >
              <component
                :is="ICONS[item.kind]"
                class="size-4 shrink-0"
                :class="ICON_TONES[item.kind]"
                aria-hidden="true"
              />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[13.5px] font-bold">
                  <span class="sr-only">{{ t(`dashboard.planning.kinds.${item.kind}`) }} : </span
                  ><template v-if="item.time">{{ item.time }} · </template>{{ item.title }}
                </span>
                <span
                  v-if="item.subtitle"
                  class="block truncate text-[12px]"
                  :class="item.kind === 'event' ? 'text-white/85' : 'text-muted'"
                  >{{ item.subtitle }}</span
                >
              </span>
              <span v-if="item.amount" class="num shrink-0 text-[13px] font-bold">{{
                formatMoneyShort(item.amount)
              }}</span>
              <span
                v-if="item.team.length"
                class="flex shrink-0 -space-x-1.5"
                :title="item.team.join(', ')"
              >
                <WAvatar
                  v-for="name in item.team.slice(0, 3)"
                  :key="name"
                  :name="name"
                  :size="24"
                  class="ring-2 ring-surface"
                />
                <span class="sr-only">{{ item.team.join(', ') }}</span>
              </span>
            </RouterLink>
          </li>
          <li v-if="visible(day.items).hidden">
            <RouterLink
              :to="{ name: 'calendar' }"
              class="inline-block px-2.5 text-[12.5px] font-bold text-violet hover:underline"
              >{{
                t(
                  'dashboard.planning.moreTasks',
                  { count: visible(day.items).hidden },
                  visible(day.items).hidden,
                )
              }}</RouterLink
            >
          </li>
        </ul>
      </li>
    </ol>
  </WCard>
</template>
