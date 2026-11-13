<script setup lang="ts">
import { TrendingDown, TrendingUp } from '@lucide/vue'
import { computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import { useCountUp } from '@/composables/useCountUp'
import { formatAmount, formatMoneyShort } from '@/composables/useMoney'
import { WRibbons } from '@/design'

import type { DashboardSummary, MonthRow } from '../api'
import { signedPct, sparkline } from '../charts'

/**
 * « Zone signature » (reservations-stock.md §8): the one strong block of the page. Ink background
 * with the logo ribbons, revenue of the period in 46px, its variation, the 12-month trend and
 * the three figures. Without access to money it shows the day's workload instead.
 */
const props = defineProps<{
  signature: NonNullable<DashboardSummary['signature']> | null
  monthly: MonthRow[] | null
  today: DashboardSummary['today']
  alerts: number
  periodLabel: string
}>()
const { t } = useI18n()
const id = useId()

const revenue = useCountUp(() => props.signature?.revenue ?? props.today.tasksToday)
const variation = computed(() => signedPct(props.signature?.revenueVariation ?? null))
const up = computed(() => (props.signature?.revenueVariation ?? 0) >= 0)

const SPARK_W = 260
const SPARK_H = 64
const trendValues = computed(() => (props.monthly ?? []).map((row) => row.revenue))
const trend = computed(() => sparkline(trendValues.value, SPARK_W, SPARK_H, 5))
const trendLabel = computed(() =>
  t('dashboard.signature.trend', {
    values: (props.monthly ?? [])
      .map((row) => `${row.label} ${formatMoneyShort(row.revenue)}`)
      .join(', '),
  }),
)

const figures = computed(() => {
  const s = props.signature
  if (!s) return []
  return [
    { key: 'collected', value: s.collected },
    { key: 'toCollect', value: s.toCollect },
    ...(s.profit !== null ? [{ key: 'profit', value: s.profit }] : []),
  ]
})
</script>

<template>
  <section
    class="relative isolate flex h-full flex-col overflow-hidden rounded-wd-lg bg-hero p-6 text-hero-ink sm:p-7"
    :aria-label="signature ? t('dashboard.signature.label') : t('dashboard.signature.opsTitle')"
  >
    <WRibbons
      class="pointer-events-none absolute -top-16 -right-24 -z-10 w-[420px] opacity-90 sm:-right-16"
    />

    <template v-if="signature">
      <p class="text-[13px] font-semibold text-hero-muted">
        {{ t('dashboard.signature.revenue') }} · {{ periodLabel }}
      </p>
      <p class="mt-1.5 flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
        <span
          class="font-display text-[clamp(34px,4.6vw,46px)] leading-none font-semibold tracking-[-0.02em]"
          data-testid="signature-revenue"
          >{{ formatAmount(revenue) }}</span
        >
        <span class="font-display text-[17px] font-semibold text-hero-muted">FCFA</span>
      </p>
      <p class="mt-3">
        <span
          v-if="variation"
          class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12.5px] font-bold"
          :class="
            up ? 'bg-green/20 text-[var(--toast-success)]' : 'bg-red/25 text-[var(--toast-alert)]'
          "
        >
          <component :is="up ? TrendingUp : TrendingDown" class="size-[15px]" aria-hidden="true" />
          {{ t('dashboard.signature.variation', { pct: variation }) }}
        </span>
        <span v-else class="text-[12.5px] font-semibold text-hero-muted">{{
          t('dashboard.signature.noComparison')
        }}</span>
      </p>

      <svg
        v-if="trend.line"
        :viewBox="`0 0 ${SPARK_W} ${SPARK_H}`"
        class="mt-4 h-16 w-full max-w-[320px] overflow-visible"
        role="img"
        :aria-label="trendLabel"
      >
        <defs>
          <linearGradient :id="`${id}-stroke`" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stop-color="#7B4DFF" />
            <stop offset="0.42" stop-color="#B23BC0" />
            <stop offset="0.7" stop-color="#F0508D" />
            <stop offset="1" stop-color="#FF9A55" />
          </linearGradient>
          <linearGradient :id="`${id}-area`" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#F0508D" stop-opacity="0.32" />
            <stop offset="1" stop-color="#F0508D" stop-opacity="0" />
          </linearGradient>
        </defs>
        <path :d="trend.area" :fill="`url(#${id}-area)`" />
        <path
          :d="trend.line"
          fill="none"
          :stroke="`url(#${id}-stroke)`"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <circle
          v-if="trend.last"
          :cx="trend.last.x"
          :cy="trend.last.y"
          r="4.5"
          fill="#FF9A55"
          stroke="var(--hero)"
          stroke-width="2"
        />
      </svg>

      <dl class="mt-auto grid grid-cols-3 gap-3 border-t border-white/12 pt-4">
        <div v-for="figure in figures" :key="figure.key" class="min-w-0">
          <dt class="truncate text-[12.5px] font-semibold text-hero-muted">
            {{ t(`dashboard.signature.${figure.key}`) }}
          </dt>
          <dd
            :data-testid="`signature-${figure.key}`"
            class="mt-0.5 font-display text-[17px] font-semibold sm:text-[20px]"
            :class="figure.key === 'profit' && figure.value < 0 && 'text-[var(--toast-alert)]'"
          >
            {{ formatMoneyShort(figure.value) }}
          </dd>
        </div>
      </dl>
    </template>

    <template v-else>
      <p class="text-[13px] font-semibold text-hero-muted">
        {{ t('dashboard.signature.opsTitle') }}
      </p>
      <p class="mt-1.5 font-display text-[46px] leading-none font-semibold">{{ revenue }}</p>
      <p class="mt-2 text-[14px] font-semibold text-hero-muted">
        {{ t('dashboard.signature.tasks') }}
      </p>
      <dl class="mt-auto grid grid-cols-2 gap-3 border-t border-white/12 pt-4">
        <div>
          <dt class="text-[12.5px] font-semibold text-hero-muted">
            {{ t('dashboard.signature.weddingsWeek') }}
          </dt>
          <dd class="mt-0.5 font-display text-[20px] font-semibold">{{ today.weddingsWeek }}</dd>
        </div>
        <div>
          <dt class="text-[12.5px] font-semibold text-hero-muted">
            {{ t('dashboard.signature.alerts') }}
          </dt>
          <dd class="mt-0.5 font-display text-[20px] font-semibold">{{ alerts }}</dd>
        </div>
      </dl>
    </template>
  </section>
</template>
