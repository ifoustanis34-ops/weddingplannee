<script setup lang="ts">
import { CalendarCheck, Plus, Search } from '@lucide/vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import DownloadMenu from '@/components/DownloadMenu.vue'
import { formatDate } from '@/composables/useDate'
import { useMembers } from '@/composables/useMembers'
import { formatAmount, formatMoneyShort } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useSessionStore } from '@/stores/session'
import {
  type TableColumn,
  WBadge,
  WButton,
  WCard,
  WEmptyState,
  WInput,
  WSelect,
  WTable,
  WTabs,
  WTile,
} from '@/design'

import { type ReservationFilters, useReservationStats, useReservations } from '../api'
import ReservationDrawer from '../components/ReservationDrawer.vue'
import ReservationWizard from '../components/ReservationWizard.vue'
import { STATUS_TONES, TABS } from '../constants'
import type { Reservation, ReservationRow } from '../types'

/** « Réservations » (reservations-stock.md §4.2). */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { can } = usePermissions()
const session = useSessionStore()
const seesMoney = computed(() => can('viewFinance'))
const canCreate = computed(() => session.role === 'owner' || session.role === 'planner')

type Tab = (typeof TABS)[number]
const tab = computed<Tab>({
  get: () =>
    (TABS as readonly string[]).includes(String(route.query.onglet))
      ? (route.query.onglet as Tab)
      : 'all',
  set: (value) =>
    void router.replace({ query: { ...route.query, onglet: value === 'all' ? undefined : value } }),
})
const search = ref('')
const debounced = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
watch(search, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debounced.value = value.trim()), 250)
})
onBeforeUnmount(() => clearTimeout(timer))
const kind = ref('')
const owner = ref('')
const from = ref('')
const to = ref('')
const filters = computed<ReservationFilters>(() => ({
  tab: tab.value,
  search: debounced.value,
  kind: kind.value,
  owner: owner.value,
  from: from.value && to.value ? from.value : '',
  to: from.value && to.value ? to.value : '',
}))
const reservations = useReservations(filters)
const stats = useReservationStats()
const members = useMembers()

const tabs = computed(() => TABS.map((key) => ({ key, label: t(`reservations.tabs.${key}`) })))
const kindOptions = computed(() => [
  { value: '', label: t('reservations.allKinds') },
  ...(['rental', 'sale', 'service', 'mixed'] as const).map((value) => ({
    value,
    label: t(`reservations.kinds.${value}`),
  })),
])
const ownerOptions = computed(() => [
  { value: '', label: t('reservations.allOwners') },
  ...(members.data.value ?? [])
    .filter((m) => m.isActive)
    .map((m) => ({ value: m.userId, label: m.fullName })),
])
const columns = computed<TableColumn[]>(() => [
  { key: 'number', label: t('reservations.columns.number') },
  { key: 'clientName', label: t('reservations.columns.client') },
  { key: 'title', label: t('reservations.columns.event') },
  { key: 'eventStart', label: t('reservations.columns.date') },
  { key: 'status', label: t('reservations.columns.status') },
  ...(seesMoney.value
    ? [
        { key: 'total', label: t('reservations.columns.total'), align: 'right' as const },
        { key: 'paid', label: t('reservations.columns.paid'), align: 'right' as const },
        { key: 'balance', label: t('reservations.columns.balance'), align: 'right' as const },
      ]
    : []),
  { key: 'next', label: t('reservations.columns.next') },
])
const row = (value: unknown) => value as ReservationRow
const nextLabel = (r: ReservationRow) =>
  r.nextStep
    ? t(`reservations.next.${r.nextStep.key}`, {
        date: r.nextStep.at ? formatDate(r.nextStep.at) : '',
      })
    : '—'

// Sheet and wizard, addressable (?reservation=<id>, ?nouvelle=1).
const openId = computed(() =>
  typeof route.query.reservation === 'string' ? route.query.reservation : null,
)
const openReservation = (id: string) =>
  void router.replace({ query: { ...route.query, reservation: id } })
const closeReservation = () =>
  void router.replace({ query: { ...route.query, reservation: undefined } })
const wizardOpen = ref(false)
watch(
  () => route.query.nouvelle,
  (value) => {
    if (value && canCreate.value) {
      wizardOpen.value = true
      void router.replace({ query: { ...route.query, nouvelle: undefined } })
    }
  },
  { immediate: true },
)
const onSaved = (reservation: Reservation) => openReservation(reservation.id)

// « Télécharger » with the screen's filters (PDF, CSV, Excel).
const exportParams = computed(() =>
  Object.fromEntries(
    Object.entries(filters.value)
      .filter(([, v]) => v && v !== 'all')
      .map(([k, v]) => [k, String(v)]),
  ),
)
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('reservations.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('reservations.subtitle') }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <DownloadMenu url="/exports/reservations" filename="reservations" :params="exportParams" />
        <WButton v-if="canCreate" @click="wizardOpen = true">
          <Plus class="size-[18px]" aria-hidden="true" />{{ t('reservations.add') }}
        </WButton>
      </div>
    </header>

    <div v-if="stats.data.value" class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
      <WTile
        :label="t('reservations.tiles.confirmedMonth')"
        :value="String(stats.data.value.confirmedMonth)"
      />
      <WTile
        :label="t('reservations.tiles.awaitingDeposit')"
        :value="String(stats.data.value.awaitingDeposit)"
      >
        <template v-if="stats.data.value.awaitingDepositAmount !== null">{{
          t('reservations.tiles.awaitingDepositHint', {
            amount: formatMoneyShort(stats.data.value.awaitingDepositAmount),
          })
        }}</template>
      </WTile>
      <WTile
        :label="t('reservations.tiles.toDeliver')"
        :value="String(stats.data.value.toDeliverWeek)"
      />
      <WTile
        v-if="stats.data.value.balanceDue !== null"
        :label="t('reservations.tiles.balanceDue')"
        :value="formatMoneyShort(stats.data.value.balanceDue)"
      />
    </div>
    <div v-else class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
      <div v-for="n in 4" :key="n" class="skeleton h-[92px] rounded-wd-lg" />
    </div>

    <WTabs v-model="tab" :tabs="tabs" :label="t('reservations.title')">
      <div class="mb-4 flex flex-wrap items-end gap-3">
        <WInput
          v-model="search"
          class="min-w-[220px] flex-1"
          type="search"
          :label="t('reservations.search')"
          :placeholder="t('reservations.searchPlaceholder')"
          hide-label
        >
          <template #prefix><Search class="size-[18px] text-muted" aria-hidden="true" /></template>
        </WInput>
        <WSelect
          v-model="kind"
          class="w-[170px]"
          :label="t('reservations.wizard.kind')"
          :options="kindOptions"
          hide-label
        />
        <WSelect
          v-model="owner"
          class="w-[220px]"
          :label="t('reservations.wizard.owner')"
          :options="ownerOptions"
          hide-label
        />
        <WInput
          v-model="from"
          type="date"
          class="w-[160px]"
          :label="t('reservations.from')"
          hide-label
        />
        <WInput
          v-model="to"
          type="date"
          class="w-[160px]"
          :label="t('reservations.to')"
          hide-label
        />
      </div>

      <WCard>
        <WEmptyState
          v-if="reservations.isError.value"
          :title="t('reservations.loadError')"
          :description="toApiError(reservations.error.value).message"
        >
          <WButton variant="secondary" @click="reservations.refetch()">{{
            t('common.retry')
          }}</WButton>
        </WEmptyState>
        <WTable
          v-else
          :columns="columns"
          :rows="(reservations.data.value ?? []) as unknown as Record<string, unknown>[]"
          row-key="id"
          :caption="t('reservations.title')"
          :loading="reservations.isPending.value"
          clickable-rows
          @row-click="(r) => openReservation(row(r).id)"
        >
          <template #empty>
            <WEmptyState
              :icon="CalendarCheck"
              :title="
                debounced || kind || owner
                  ? t('reservations.noResults')
                  : t('reservations.emptyTitle')
              "
              :description="debounced || kind || owner ? undefined : t('reservations.emptyText')"
            >
              <WButton v-if="canCreate && !debounced" @click="wizardOpen = true">
                <Plus class="size-[18px]" aria-hidden="true" />{{ t('reservations.add') }}
              </WButton>
            </WEmptyState>
          </template>
          <template #cell-number="{ row: r }"
            ><span class="num font-bold whitespace-nowrap">{{ row(r).number }}</span></template
          >
          <template #cell-title="{ row: r }">
            <span class="block font-semibold">{{ row(r).title }}</span>
            <span class="text-[12px] text-muted"
              >{{ t(`reservations.kinds.${row(r).kind}`)
              }}<template v-if="row(r).venue"> · {{ row(r).venue }}</template></span
            >
          </template>
          <template #cell-eventStart="{ row: r }">{{ formatDate(row(r).eventStart) }}</template>
          <template #cell-status="{ row: r }">
            <WBadge :tone="STATUS_TONES[row(r).status]">{{
              t(`reservations.statuses.${row(r).status}`)
            }}</WBadge>
          </template>
          <template #cell-total="{ row: r }"
            ><span class="num">{{ formatAmount(row(r).total ?? 0) }}</span></template
          >
          <template #cell-paid="{ row: r }"
            ><span class="num">{{ formatAmount(row(r).paid ?? 0) }}</span></template
          >
          <template #cell-balance="{ row: r }">
            <span class="num" :class="(row(r).balance ?? 0) > 0 && 'font-bold text-coral'">{{
              formatAmount(row(r).balance ?? 0)
            }}</span>
          </template>
          <template #cell-next="{ row: r }"
            ><span class="text-[13px] text-ink-2">{{ nextLabel(row(r)) }}</span></template
          >
        </WTable>
      </WCard>
    </WTabs>

    <ReservationDrawer :reservation-id="openId" @close="closeReservation" />
    <ReservationWizard v-model:open="wizardOpen" @saved="onSaved" />
  </div>
</template>
