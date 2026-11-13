<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatMoneyShort } from '@/composables/useMoney'
import { WCard } from '@/design'

import type { DashboardSummary } from '../api'
import RingChart from './RingChart.vue'

/**
 * « Dépenses par catégorie »: ring and legend with amounts. The server gives each of the five
 * main categories of the year a fixed slot, so a category keeps its color from one period to
 * the next (never colored by rank); the rest is « Autres ».
 */
const props = defineProps<{ rows: NonNullable<DashboardSummary['expensesByCategory']> }>()
const { t } = useI18n()

const color = (slot: number) => (slot ? `var(--chart-${slot})` : 'var(--chart-other)')
const total = computed(() => props.rows.reduce((sum, row) => sum + row.amount, 0))
const items = computed(() =>
  props.rows.map((row) => ({
    key: row.id ?? 'others',
    label: row.name ?? t('dashboard.expensesRing.others'),
    value: row.amount,
    color: color(row.slot),
    display: formatMoneyShort(row.amount),
  })),
)
</script>

<template>
  <WCard
    :title="t('dashboard.expensesRing.title')"
    :subtitle="t('dashboard.expensesRing.subtitle')"
    class="h-full"
  >
    <p v-if="!total" class="text-muted">{{ t('dashboard.expensesRing.empty') }}</p>
    <div v-else class="flex flex-col items-center gap-4">
      <RingChart
        :items="items"
        :center-value="formatMoneyShort(total)"
        :center-label="t('dashboard.expensesRing.total')"
        :label="items.map((i) => `${i.label} ${i.display}`).join(', ')"
      />
      <ul class="flex w-full flex-col gap-1.5 text-[13px]">
        <li v-for="item in items" :key="item.key" class="flex items-center gap-2">
          <span class="size-2.5 shrink-0 rounded-[3px]" :style="{ background: item.color }" />
          <span class="min-w-0 flex-1 truncate font-semibold text-ink-2">{{ item.label }}</span>
          <span class="num font-bold">{{ item.display }}</span>
        </li>
      </ul>
    </div>
  </WCard>
</template>
