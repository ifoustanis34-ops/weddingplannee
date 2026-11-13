<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { formatDate } from '@/composables/useDate'
import { formatAmount } from '@/composables/useMoney'

import type { ReportColumn } from '../billing'

/** A report as a table (§6.5): money right-aligned in tabular figures, totals at the bottom. */
defineProps<{
  columns: ReportColumn[]
  rows: Record<string, unknown>[]
  totals?: Record<string, unknown>
  caption: string
  clickable?: boolean
}>()
const emit = defineEmits<{ row: [row: Record<string, unknown>] }>()
const { t, locale } = useI18n()

/** Document numbers and dates never break across lines. */
const NOWRAP = ['number', 'reference', 'date', 'due', 'month']
const numeric = (column: ReportColumn) => ['money', 'pct', 'number'].includes(column.kind)
function text(raw: unknown, column: ReportColumn): string {
  if (raw === null || raw === undefined || raw === '') return '—'
  // Report cells are strings or numbers (JSON).
  const value = typeof raw === 'number' ? raw : typeof raw === 'string' ? raw : JSON.stringify(raw)
  switch (column.kind) {
    case 'money':
      return formatAmount(Number(value))
    case 'pct': {
      const sign = column.key === 'variation_pct' || column.key === 'variationPct'
      const number = Number(value).toLocaleString(locale.value, { maximumFractionDigits: 1 })
      return `${sign && Number(value) > 0 ? '+' : ''}${number} %`
    }
    case 'number':
      return Number(value).toLocaleString(locale.value)
    case 'date':
      return formatDate(String(value))
    case 'month': {
      const label = new Intl.DateTimeFormat(locale.value, {
        month: 'long',
        year: 'numeric',
      }).format(new Date(`${String(value).slice(0, 7)}-15T12:00:00Z`))
      return label.charAt(0).toUpperCase() + label.slice(1)
    }
    default:
      return String(value)
  }
}
const camel = (key: string) => key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase())
const cell = (row: Record<string, unknown>, column: ReportColumn) =>
  row[column.key] ?? row[camel(column.key)]
const negative = (row: Record<string, unknown>, column: ReportColumn) =>
  numeric(column) && Number(cell(row, column)) < 0
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full min-w-[640px] border-collapse text-[13.5px]">
      <caption class="sr-only">
        {{
          caption
        }}
      </caption>
      <thead>
        <tr class="border-b border-line text-left text-[12px] font-bold text-muted">
          <th
            v-for="column in columns"
            :key="column.key"
            scope="col"
            class="px-3 py-2.5 whitespace-nowrap"
            :class="numeric(column) && 'text-right'"
          >
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="index"
          class="border-b border-line last:border-b-0 hover:bg-surface-2"
          :class="clickable && 'cursor-pointer'"
          @click="emit('row', row)"
        >
          <td
            v-for="column in columns"
            :key="column.key"
            class="px-3 py-2.5"
            :class="[
              numeric(column) && 'num text-right whitespace-nowrap',
              NOWRAP.includes(column.key) && 'whitespace-nowrap',
              negative(row, column) && 'font-semibold text-red',
            ]"
          >
            {{ text(cell(row, column), column) }}
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length" class="px-3 py-6 text-center text-muted">
            {{ t('finance.reports.empty') }}
          </td>
        </tr>
      </tbody>
      <tfoot v-if="totals && rows.length">
        <tr class="border-t-2 border-ink font-bold">
          <td
            v-for="(column, index) in columns"
            :key="column.key"
            class="px-3 py-2.5"
            :class="numeric(column) && 'num text-right whitespace-nowrap'"
          >
            {{
              index === 0
                ? t('finance.reports.total')
                : column.key in totals || camel(column.key) in totals
                  ? text(cell(totals, column), column)
                  : ''
            }}
          </td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>
