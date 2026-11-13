<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { WCard } from '@/design'

import type { DashboardSummary } from '../api'
import RingChart from './RingChart.vue'

/**
 * « Réservations » ring (reservations-stock.md §8): confirmed / pending / cancelled, each number
 * opens the filtered list. Until reservations exist (step S4) it counts signed contracts, quotes
 * awaiting an answer and refused quotes or cancelled contracts.
 */
const props = defineProps<{ orders: DashboardSummary['orders'] }>()
const { t } = useI18n()

const rows = computed(() => [
  {
    key: 'confirmed',
    value: props.orders.confirmed,
    color: 'var(--green)',
    to: { name: 'reservations', query: { onglet: 'confirmed' } },
  },
  {
    key: 'pending',
    value: props.orders.pending,
    color: 'var(--gold)',
    to: { name: 'reservations', query: { onglet: 'awaiting_deposit' } },
  },
  {
    key: 'cancelled',
    value: props.orders.cancelled,
    color: 'var(--chart-other)',
    to: { name: 'reservations', query: { onglet: 'cancelled' } },
  },
])
const total = computed(() => rows.value.reduce((sum, row) => sum + row.value, 0))
const items = computed(() =>
  rows.value.map((row) => ({
    key: row.key,
    label: t(`dashboard.orders.${row.key}`),
    value: row.value,
    color: row.color,
    display: String(row.value),
  })),
)
</script>

<template>
  <WCard
    :title="t('dashboard.orders.title')"
    :subtitle="t('dashboard.orders.subtitle')"
    class="h-full"
  >
    <p v-if="!total" class="text-muted">{{ t('dashboard.orders.empty') }}</p>
    <div v-else class="flex items-center gap-5">
      <RingChart
        :items="items"
        :center-value="String(total)"
        :center-label="t('dashboard.orders.total')"
        :label="t('dashboard.orders.aria', orders)"
        :size="132"
      />
      <ul class="flex min-w-0 flex-1 flex-col gap-1.5">
        <li v-for="row in rows" :key="row.key">
          <RouterLink
            :to="row.to"
            class="-mx-2 flex items-center gap-2.5 rounded-wd px-2 py-1.5 hover:bg-surface-2"
          >
            <span class="size-2.5 shrink-0 rounded-full" :style="{ background: row.color }" />
            <span class="min-w-0 flex-1 truncate font-semibold text-ink-2">{{
              t(`dashboard.orders.${row.key}`)
            }}</span>
            <span class="num font-display text-[17px] font-semibold">{{ row.value }}</span>
          </RouterLink>
        </li>
      </ul>
    </div>
  </WCard>
</template>
