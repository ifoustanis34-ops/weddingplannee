<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import DownloadMenu from '@/components/DownloadMenu.vue'
import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { useMembers } from '@/composables/useMembers'
import { useToast } from '@/composables/useToast'
import { WButton, WChips, WEmptyState, WSelect } from '@/design'
import ReservationDrawer from '@/modules/reservations/components/ReservationDrawer.vue'
import { STATUS_TONES } from '@/modules/reservations/constants'
import type { ReservationStatus } from '@/modules/reservations/types'

import { type CalendarItem, type CalendarKind, useCalendar, useMoveReservation } from '../api'
import DaysView from '../components/DaysView.vue'
import ListView from '../components/ListView.vue'
import LogisticsView from '../components/LogisticsView.vue'
import MonthView from '../components/MonthView.vue'
import type { MoveRequest } from '../components/useDropDay'
import { KIND_GROUPS, KIND_STYLE } from '../kinds'
import {
  type CalendarView,
  groupByDay,
  iso,
  parseDay,
  shiftAnchor,
  VIEWS,
  viewDays,
} from '../month'

/**
 * « Calendrier » (reservations-stock.md §4.3): month, week, day, list and logistic planning
 * over one feed. Addressable: `?vue=&jour=` and the reservation sheet `?reservation=<id>`.
 */
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const members = useMembers()

const view = computed<CalendarView>({
  get: () =>
    (VIEWS as readonly string[]).includes(String(route.query.vue))
      ? (route.query.vue as CalendarView)
      : 'mois',
  set: (value) => void router.replace({ query: { ...route.query, vue: value } }),
})
const anchor = computed(() => parseDay(route.query.jour))
const days = computed(() => viewDays(view.value, anchor.value))
function goTo(day: Date | null, next?: CalendarView): void {
  void router.replace({
    query: {
      ...route.query,
      jour: day ? iso(day) : undefined,
      ...(next ? { vue: next } : {}),
    },
  })
}
const openDay = (day: string) => goTo(parseDay(day), 'jour')

// Filters: member, reservation status, kinds (the legend toggles them).
const member = ref('')
const status = ref('')
const hidden = ref(new Set<string>())
const kinds = computed<CalendarKind[]>(() =>
  KIND_GROUPS.filter((g) => !hidden.value.has(g.key)).flatMap((g) => g.kinds),
)
function toggle(key: string): void {
  const next = new Set(hidden.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  hidden.value = next
}
const filters = computed(() => ({
  from: iso(days.value[0]!),
  to: iso(days.value[days.value.length - 1]!),
  member: member.value,
  kinds: kinds.value,
  status: status.value,
}))
const calendar = useCalendar(filters)
const byDay = computed(() => groupByDay(calendar.data.value ?? [], days.value))
const nothing = computed(
  () => !calendar.isPending.value && !(calendar.data.value ?? []).length && kinds.value.length,
)

const title = computed(() => {
  const first = days.value[0]!
  const last = days.value[days.value.length - 1]!
  const format = (options: Intl.DateTimeFormatOptions, date: Date) =>
    new Intl.DateTimeFormat(locale.value, options).format(date)
  let text: string
  if (view.value === 'mois' || view.value === 'liste')
    text = format({ month: 'long', year: 'numeric' }, anchor.value)
  else if (view.value === 'jour')
    text = format({ weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }, first)
  else
    text = t('calendar.range', {
      from: format({ day: 'numeric', month: 'short' }, first),
      to: format({ day: 'numeric', month: 'short', year: 'numeric' }, last),
    })
  return text.charAt(0).toUpperCase() + text.slice(1)
})
const viewOptions = computed(() =>
  VIEWS.map((value) => ({ value, label: t(`calendar.views.${value}`) })),
)
const memberOptions = computed(() => [
  { value: '', label: t('calendar.everyone') },
  ...(members.data.value ?? [])
    .filter((m) => m.isActive)
    .map((m) => ({ value: m.userId, label: m.fullName })),
])
const statusOptions = computed(() => [
  { value: '', label: t('calendar.allStatuses') },
  ...(Object.keys(STATUS_TONES) as ReservationStatus[]).map((value) => ({
    value,
    label: t(`reservations.statuses.${value}`),
  })),
])

// Opening an item: the reservation sheet stays on the calendar.
const openId = computed(() =>
  typeof route.query.reservation === 'string' ? route.query.reservation : null,
)
function openItem(item: CalendarItem): void {
  if (item.reservation) {
    void router.replace({ query: { ...route.query, reservation: item.reservation } })
  } else if (item.kind === 'payment' && item.contract) {
    void router.push({ name: 'finance', query: { contract: item.contract } })
  } else if (item.kind === 'maintenance' && item.item) {
    void router.push({ name: 'stock', query: { article: item.item } })
  } else if (item.wedding) {
    void router.push({ name: 'weddings', query: { mariage: item.wedding } })
  }
}
const closeReservation = () =>
  void router.replace({ query: { ...route.query, reservation: undefined } })

// Drag to another day (§4.3): the server checks the equipment again.
const move = useMoveReservation()
async function onMove(request: MoveRequest): Promise<void> {
  try {
    const moved = await move.mutateAsync({ id: request.reservation, days: request.days })
    toast.success(t('calendar.moved', { number: moved.number, date: formatDate(moved.eventStart) }))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <div class="flex flex-col gap-[18px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('calendar.title') }}</h1>
        <p class="mt-1 max-w-[70ch] text-muted">{{ t('calendar.subtitle') }}</p>
      </div>
      <DownloadMenu
        url="/exports/calendar"
        filename="calendrier"
        :params="{
          from: filters.from,
          to: filters.to,
          member: filters.member || undefined,
          kinds: filters.kinds.join(','),
          statuses: filters.status || undefined,
        }"
      />
      <div class="flex flex-wrap items-center gap-2">
        <WButton variant="secondary" @click="goTo(null)">{{ t('calendar.today') }}</WButton>
        <WButton
          variant="secondary"
          icon
          :aria-label="t('calendar.previous')"
          @click="goTo(shiftAnchor(view, anchor, -1))"
          ><ChevronLeft class="size-[18px]" aria-hidden="true"
        /></WButton>
        <WButton
          variant="secondary"
          icon
          :aria-label="t('calendar.next')"
          @click="goTo(shiftAnchor(view, anchor, 1))"
          ><ChevronRight class="size-[18px]" aria-hidden="true"
        /></WButton>
      </div>
    </header>

    <div class="flex flex-wrap items-center gap-3">
      <WChips v-model="view" :options="viewOptions" :label="t('calendar.view')" />
      <div class="ml-auto flex flex-wrap gap-2">
        <WSelect
          v-model="member"
          class="w-[200px]"
          hide-label
          :label="t('calendar.member')"
          :options="memberOptions"
        />
        <WSelect
          v-model="status"
          class="w-[200px]"
          hide-label
          :label="t('calendar.status')"
          :options="statusOptions"
        />
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-x-5 gap-y-2">
      <h2 class="text-[20px]" aria-live="polite">{{ title }}</h2>
      <ul
        class="flex flex-wrap gap-1.5 text-[12.5px] font-semibold"
        :aria-label="t('calendar.legendLabel')"
      >
        <li v-for="group in KIND_GROUPS" :key="group.key">
          <button
            type="button"
            class="flex h-7 items-center gap-1.5 rounded-full border px-2.5 transition-opacity"
            :class="
              hidden.has(group.key)
                ? 'border-line text-muted line-through opacity-60'
                : 'border-line-2 text-ink-2 hover:bg-surface-2'
            "
            :aria-pressed="!hidden.has(group.key)"
            @click="toggle(group.key)"
          >
            <span
              class="h-2.5 w-4 rounded-full"
              :class="group.key === 'event' ? 'bg-ribbon' : KIND_STYLE[group.kinds[0]!].dot"
              aria-hidden="true"
            />{{ t(`calendar.legend.${group.key}`) }}
          </button>
        </li>
      </ul>
    </div>

    <WEmptyState
      v-if="calendar.isError.value"
      :title="t('calendar.loadError')"
      :description="toApiError(calendar.error.value).message"
    >
      <WButton variant="secondary" @click="calendar.refetch()">{{ t('common.retry') }}</WButton>
    </WEmptyState>
    <template v-else>
      <div
        v-if="calendar.isPending.value && kinds.length"
        class="skeleton h-[420px] rounded-wd-lg"
      />
      <MonthView
        v-else-if="view === 'mois'"
        :days="days"
        :month="anchor.getMonth()"
        :by-day="byDay"
        :title="title"
        :busy="calendar.isFetching.value"
        @open="openItem"
        @day="openDay"
        @move="onMove"
      />
      <DaysView
        v-else-if="view === 'semaine' || view === 'jour'"
        :days="days"
        :by-day="byDay"
        :title="title"
        :busy="calendar.isFetching.value"
        @open="openItem"
        @day="openDay"
        @move="onMove"
      />
      <template v-else-if="view === 'liste'">
        <WEmptyState v-if="nothing" :title="t('calendar.empty')" />
        <ListView v-else :days="days" :by-day="byDay" @open="openItem" />
      </template>
      <LogisticsView v-else :days="days" :by-day="byDay" @open="openItem" />
      <p class="text-[12.5px] text-muted">{{ t('calendar.dragHelp') }}</p>
    </template>

    <ReservationDrawer :reservation-id="openId" @close="closeReservation" />
  </div>
</template>
