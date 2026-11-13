<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatMoneyShort } from '@/composables/useMoney'
import { WButton, WCard, WEmptyState, WTile } from '@/design'
import type { MonthRow, PeriodRequest } from '@/modules/dashboard/api'
import MoneyChartCard from '@/modules/dashboard/components/MoneyChartCard.vue'

import { useTreasury } from '../billing'

/** « Trésorerie » (§6.2): cash in, to come, out, balance of the period and the 12-month curve. */
const props = defineProps<{ period: PeriodRequest }>()
const { t, locale } = useI18n()
const treasury = useTreasury(() => props.period)
const data = computed(() => treasury.data.value)

const variation = (current: number, previous: number) => {
  if (!previous) return null
  const pct = Math.round(((current - previous) * 1000) / Math.abs(previous)) / 10
  return `${pct > 0 ? '+' : ''}${pct.toLocaleString(locale.value)} % ${t('finance.treasury.vsPrevious')}`
}
const monthly = computed<MonthRow[]>(() =>
  (data.value?.monthly ?? []).map((row) => ({
    month: row.month,
    label: new Intl.DateTimeFormat(locale.value, { month: 'short' })
      .format(new Date(`${row.month.slice(0, 7)}-15T12:00:00Z`))
      .replace('.', ''),
    revenue: row.cashIn,
    income: row.cashIn,
    expenses: row.cashOut,
    profit: row.net,
  })),
)
const maxCategory = computed(() =>
  Math.max(1, ...(data.value?.revenueByCategory ?? []).map((row) => row.amount)),
)
const maxExpense = computed(() =>
  Math.max(1, ...(data.value?.expensesByCategory ?? []).map((row) => row.amount)),
)
</script>

<template>
  <WEmptyState
    v-if="treasury.isError.value"
    :title="t('finance.treasury.loadError')"
    :description="toApiError(treasury.error.value).message"
  >
    <WButton variant="secondary" @click="treasury.refetch()">{{ t('common.retry') }}</WButton>
  </WEmptyState>
  <div v-else-if="!data" class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
    <div v-for="n in 4" :key="n" class="skeleton h-[96px] rounded-wd-lg" />
  </div>
  <div v-else class="flex flex-col gap-[18px]">
    <div class="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
      <WTile :label="t('finance.treasury.collected')" :value="formatMoneyShort(data.collected)">{{
        variation(data.collected, data.previous.collected)
      }}</WTile>
      <WTile :label="t('finance.treasury.toCollect')" :value="formatMoneyShort(data.toCollect)">
        <template v-if="data.invoicesOverdue.count">{{
          t(
            'finance.treasury.overdue',
            {
              count: data.invoicesOverdue.count,
              amount: formatMoneyShort(data.invoicesOverdue.amount),
            },
            data.invoicesOverdue.count,
          )
        }}</template>
      </WTile>
      <WTile :label="t('finance.treasury.spent')" :value="formatMoneyShort(data.spent)">{{
        variation(data.spent, data.previous.spent)
      }}</WTile>
      <WTile :label="t('finance.treasury.balance')" :value="formatMoneyShort(data.balance)">{{
        variation(data.balance, data.previous.balance)
      }}</WTile>
    </div>
    <MoneyChartCard :monthly="monthly" />
    <div class="grid gap-[18px] lg:grid-cols-2">
      <WCard :title="t('finance.treasury.byCategory')" :subtitle="t('finance.treasury.periodHint')">
        <ul class="flex flex-col gap-3">
          <li v-for="row in data.revenueByCategory" :key="row.category">
            <div class="mb-1 flex justify-between text-[13.5px]">
              <span class="font-semibold">{{ row.label }}</span>
              <span class="num font-semibold">{{ formatMoneyShort(row.amount) }}</span>
            </div>
            <div class="h-2 rounded-full bg-surface-2">
              <div
                class="h-2 rounded-full bg-chart-income"
                :style="{ width: `${(row.amount / maxCategory) * 100}%` }"
              />
            </div>
          </li>
        </ul>
      </WCard>
      <WCard :title="t('finance.treasury.expenses')" :subtitle="t('finance.treasury.periodHint')">
        <p v-if="!data.expensesByCategory.length" class="text-muted">
          {{ t('finance.treasury.noExpense') }}
        </p>
        <ul v-else class="flex flex-col gap-3">
          <li v-for="row in data.expensesByCategory" :key="row.category">
            <div class="mb-1 flex justify-between text-[13.5px]">
              <span class="font-semibold">{{ row.category }}</span>
              <span class="num font-semibold">{{ formatMoneyShort(row.amount) }}</span>
            </div>
            <div class="h-2 rounded-full bg-surface-2">
              <div
                class="h-2 rounded-full bg-chart-expense"
                :style="{ width: `${(row.amount / maxExpense) * 100}%` }"
              />
            </div>
          </li>
        </ul>
      </WCard>
    </div>
  </div>
</template>
