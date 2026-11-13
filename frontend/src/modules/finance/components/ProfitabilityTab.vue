<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { WCard, WChips, WEmptyState } from '@/design'
import type { PeriodRequest } from '@/modules/dashboard/api'

import { type ProfitabilityBy, type ReportColumn, useProfitability } from '../billing'
import ReportTable from './ReportTable.vue'

/** « Rentabilité » (§6.4): by event, by service, by stock item. */
const props = defineProps<{ period: PeriodRequest }>()
const { t } = useI18n()
const router = useRouter()
const by = ref<ProfitabilityBy>('event')
const data = useProfitability<Record<string, unknown>>(by, () => props.period)
const options = computed(() =>
  (['event', 'service', 'item'] as const).map((value) => ({
    value,
    label: t(`finance.profitability.by.${value}`),
  })),
)
const col = (key: string, kind: ReportColumn['kind']): ReportColumn => ({
  key,
  kind,
  label: t(`finance.profitability.columns.${key}`),
})
const columns = computed<ReportColumn[]>(() => {
  if (by.value === 'event')
    return [
      col('date', 'date'),
      col('number', 'text'),
      col('title', 'text'),
      col('client', 'text'),
      col('revenue', 'money'),
      col('costs', 'money'),
      col('margin', 'money'),
      col('marginPct', 'pct'),
    ]
  if (by.value === 'service')
    return [
      col('name', 'text'),
      col('sales', 'number'),
      col('revenue', 'money'),
      col('marginAvg', 'pct'),
    ]
  return [
    col('reference', 'text'),
    col('name', 'text'),
    col('revenue', 'money'),
    col('rentedDays', 'number'),
    col('utilisationPct', 'pct'),
    col('purchaseCost', 'money'),
    col('paybackPct', 'pct'),
  ]
})
const totals = computed(() => {
  const rows = data.data.value ?? []
  if (by.value !== 'event' || !rows.length) return undefined
  const sum = (key: string) => rows.reduce((total, row) => total + Number(row[key] ?? 0), 0)
  const revenue = sum('revenue')
  const margin = sum('margin')
  return {
    revenue,
    costs: sum('costs'),
    margin,
    marginPct: revenue ? Math.round((margin * 1000) / revenue) / 10 : null,
  }
})
function open(row: Record<string, unknown>): void {
  if (by.value === 'event' && row.kind === 'reservation')
    void router.push({ name: 'reservations', query: { reservation: String(row.id) } })
  else if (by.value === 'event')
    void router.push({ name: 'finance', query: { contract: String(row.id), onglet: 'contrats' } })
  else if (by.value === 'item')
    void router.push({ name: 'stock', query: { article: String(row.id) } })
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <WChips v-model="by" :options="options" :label="t('finance.profitability.label')" />
    <WCard>
      <WEmptyState
        v-if="data.isError.value"
        :title="t('finance.profitability.loadError')"
        :description="toApiError(data.error.value).message"
      />
      <div v-else-if="data.isPending.value" class="skeleton h-48" />
      <ReportTable
        v-else
        :columns="columns"
        :rows="data.data.value ?? []"
        :totals="totals"
        :caption="t(`finance.profitability.by.${by}`)"
        :clickable="by !== 'service'"
        @row="open"
      />
      <p class="mt-3 text-[12.5px] text-muted">{{ t(`finance.profitability.notes.${by}`) }}</p>
    </WCard>
  </div>
</template>
