<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatAmount, formatMoneyShort } from '@/composables/useMoney'
import { WCard } from '@/design'

import type { MonthRow } from '../api'
import { BARS_BOTTOM, BARS_HEIGHT, BARS_LEFT, BARS_WIDTH, barsGeometry } from '../charts'

/**
 * « Recettes et dépenses » (reservations-stock.md §8): monthly bars (income violet, expenses
 * coral) and the profit line in gold, on one FCFA axis, over 6 or 12 months. Hover or focus a
 * month for the dark tooltip; every value is also in the table view. Roles without margins get
 * the income bars only.
 */
const props = defineProps<{ monthly: MonthRow[] }>()
const { t } = useI18n()

const span = ref<6 | 12>(6)
const asTable = ref(false)
const rows = computed(() => props.monthly.slice(-span.value))
const withExpenses = computed(() => rows.value.some((r) => r.expenses !== null))
const geometry = computed(() => barsGeometry(rows.value))
const hovered = ref<number | null>(null)
const tip = computed(() => (hovered.value === null ? null : rows.value[hovered.value]))
const tipColumn = computed(() =>
  hovered.value === null ? null : geometry.value.columns[hovered.value],
)
const lastProfit = computed(() => {
  const columns = geometry.value.columns.filter((c) => c.profit)
  return columns.length ? columns[columns.length - 1]! : null
})
const svgText = (text: string) => text.replace(/[  ]/g, ' ')

const series = computed(() => [
  { key: 'income', color: 'var(--chart-income)', shape: 'bar' },
  ...(withExpenses.value
    ? [
        { key: 'expenses', color: 'var(--chart-expense)', shape: 'bar' },
        { key: 'profit', color: 'var(--chart-profit)', shape: 'line' },
      ]
    : []),
])
</script>

<template>
  <WCard
    :title="t('dashboard.money.title')"
    :subtitle="withExpenses ? t('dashboard.money.subtitle') : t('dashboard.money.incomeOnly')"
    class="h-full"
  >
    <template #actions>
      <div
        class="flex rounded-[10px] border border-line p-0.5"
        role="radiogroup"
        :aria-label="t('dashboard.money.range')"
      >
        <button
          v-for="count in [6, 12] as const"
          :key="count"
          type="button"
          role="radio"
          :aria-checked="span === count"
          class="h-7 rounded-[8px] px-2.5 text-[12.5px] font-bold"
          :class="span === count ? 'bg-surface-2 text-ink' : 'text-muted hover:text-ink'"
          @click="span = count"
        >
          {{ t('dashboard.money.months', { count }) }}
        </button>
      </div>
    </template>

    <ul class="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] font-semibold text-ink-2">
      <li v-for="item in series" :key="item.key" class="flex items-center gap-1.5">
        <span
          v-if="item.shape === 'bar'"
          class="size-2.5 rounded-[3px]"
          :style="{ background: item.color }"
        />
        <span v-else class="h-0.5 w-3.5 rounded-full" :style="{ background: item.color }" />
        {{ t(`dashboard.money.${item.key}`) }}
      </li>
    </ul>

    <div v-if="!asTable" class="relative -mx-1 overflow-x-auto">
      <div class="relative min-w-[460px]">
        <svg
          :viewBox="`0 0 ${BARS_WIDTH} ${BARS_HEIGHT}`"
          class="block h-auto w-full overflow-visible"
          role="img"
          :aria-label="t('dashboard.money.aria', { count: span })"
          @mouseleave="hovered = null"
        >
          <g class="text-[11px]">
            <g v-for="tick in geometry.ticks" :key="tick.value">
              <line
                :x1="BARS_LEFT"
                :x2="BARS_WIDTH"
                :y1="tick.y"
                :y2="tick.y"
                :stroke="tick.value === 0 ? 'var(--line-2)' : 'var(--chart-grid)'"
                stroke-width="1"
              />
              <text
                :x="BARS_LEFT - 8"
                :y="tick.y + 4"
                text-anchor="end"
                fill="var(--muted)"
                font-weight="600"
              >
                {{ svgText(formatMoneyShort(tick.value)) }}
              </text>
            </g>
          </g>
          <rect
            v-if="tipColumn"
            :x="tipColumn.bandX + 2"
            :y="8"
            :width="tipColumn.bandWidth - 4"
            :height="BARS_BOTTOM - 8"
            rx="8"
            fill="var(--surface-2)"
          />
          <g v-for="column in geometry.columns" :key="column.index">
            <rect
              :x="column.income.x"
              :y="column.income.y"
              :width="column.income.width"
              :height="column.income.height"
              rx="4"
              fill="var(--chart-income)"
            />
            <rect
              v-if="column.expense"
              :x="column.expense.x"
              :y="column.expense.y"
              :width="column.expense.width"
              :height="column.expense.height"
              rx="4"
              fill="var(--chart-expense)"
            />
            <text
              :x="column.x"
              :y="BARS_BOTTOM + 22"
              text-anchor="middle"
              fill="var(--muted)"
              font-size="11.5"
              font-weight="700"
            >
              {{ rows[column.index]?.label }}
            </text>
          </g>
          <path
            v-if="geometry.profitLine"
            :d="geometry.profitLine"
            fill="none"
            stroke="var(--chart-profit)"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
          <template v-for="column in geometry.columns" :key="`p${column.index}`">
            <circle
              v-if="column.profit"
              :cx="column.profit.x"
              :cy="column.profit.y"
              :r="hovered === column.index ? 5.5 : 4"
              fill="var(--chart-profit)"
              stroke="var(--surface)"
              stroke-width="2"
            />
          </template>
          <text
            v-if="lastProfit?.profit && rows[lastProfit.index]?.profit !== null"
            :x="Math.min(lastProfit.profit.x, BARS_WIDTH - 4)"
            :y="lastProfit.profit.y - 10"
            text-anchor="end"
            fill="var(--ink-2)"
            font-size="11.5"
            font-weight="700"
          >
            {{ svgText(formatMoneyShort(rows[lastProfit.index]!.profit!)) }}
          </text>
          <!-- Hit areas: the whole month band, bigger than the marks, keyboard reachable. -->
          <rect
            v-for="column in geometry.columns"
            :key="`h${column.index}`"
            :x="column.bandX"
            y="0"
            :width="column.bandWidth"
            :height="BARS_BOTTOM + 28"
            fill="transparent"
            tabindex="0"
            class="outline-none focus-visible:stroke-violet"
            :aria-label="`${rows[column.index]?.label}`"
            @mouseenter="hovered = column.index"
            @focus="hovered = column.index"
            @blur="hovered = null"
          />
        </svg>
        <div
          v-if="tip && tipColumn"
          class="pointer-events-none absolute top-1 z-10 min-w-[170px] -translate-x-1/2 rounded-[12px] bg-tooltip px-3 py-2.5 text-[12.5px] text-tooltip-ink shadow-wd-lg"
          :style="{
            left: `${Math.min(Math.max((tipColumn.x / BARS_WIDTH) * 100, 16), 84)}%`,
          }"
          role="status"
        >
          <p class="mb-1 font-bold capitalize">{{ tip.label }} {{ tip.month.slice(0, 4) }}</p>
          <p class="flex items-center justify-between gap-4">
            <span class="flex items-center gap-1.5"
              ><span class="size-2 rounded-[2px] bg-chart-income" />{{
                t('dashboard.money.income')
              }}</span
            ><span class="num font-bold">{{ formatAmount(tip.income) }}</span>
          </p>
          <template v-if="tip.expenses !== null">
            <p class="flex items-center justify-between gap-4">
              <span class="flex items-center gap-1.5"
                ><span class="size-2 rounded-[2px] bg-chart-expense" />{{
                  t('dashboard.money.expenses')
                }}</span
              ><span class="num font-bold">{{ formatAmount(tip.expenses) }}</span>
            </p>
            <p class="flex items-center justify-between gap-4">
              <span class="flex items-center gap-1.5"
                ><span class="h-0.5 w-2.5 rounded-full bg-chart-profit" />{{
                  t('dashboard.money.profit')
                }}</span
              ><span class="num font-bold">{{ formatAmount(tip.profit ?? 0) }}</span>
            </p>
          </template>
        </div>
      </div>
    </div>

    <div v-else class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="text-left text-muted">
            <th class="py-1.5 pr-3 font-semibold">{{ t('dashboard.money.month') }}</th>
            <th class="py-1.5 pr-3 text-right font-semibold">{{ t('dashboard.money.income') }}</th>
            <template v-if="withExpenses">
              <th class="py-1.5 pr-3 text-right font-semibold">
                {{ t('dashboard.money.expenses') }}
              </th>
              <th class="py-1.5 text-right font-semibold">{{ t('dashboard.money.profit') }}</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.month" class="border-t border-line">
            <td class="py-1.5 pr-3 font-semibold capitalize">
              {{ row.label }} {{ row.month.slice(0, 4) }}
            </td>
            <td class="num py-1.5 pr-3 text-right">{{ formatAmount(row.income) }}</td>
            <template v-if="withExpenses">
              <td class="num py-1.5 pr-3 text-right">{{ formatAmount(row.expenses ?? 0) }}</td>
              <td class="num py-1.5 text-right font-bold">{{ formatAmount(row.profit ?? 0) }}</td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <button
      type="button"
      class="mt-2 text-[12.5px] font-bold text-violet hover:underline"
      @click="asTable = !asTable"
    >
      {{ asTable ? t('dashboard.money.showChart') : t('dashboard.money.showTable') }}
    </button>
  </WCard>
</template>
