<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatMoneyShort } from '@/composables/useMoney'

import type { DashboardSummary } from '../api'
import { signedPct } from '../charts'

/**
 * « Performance » 2 × 2 (reservations-stock.md §8), each figure with its change vs the previous
 * period. Material utilisation takes the first tile once the stock module exists; until then the
 * collection rate of the installments completes the grid. Hidden figures (role) are skipped.
 */
const props = defineProps<{ performance: NonNullable<DashboardSummary['performance']> }>()
const { t } = useI18n()

interface Tile {
  key: string
  value: string
  change: string | null
  /** Positive change is good news for every tile. */
  trend: number | null
}

const pct = (value: number) => `${String(Math.round(value * 10) / 10).replace('.', ',')} %`
const points = (delta: number | null) =>
  delta === null ? null : t('dashboard.performance.points', { delta: signedPct(delta, '') })

const tiles = computed<Tile[]>(() => {
  const p = props.performance
  const list: Tile[] = []
  if (p.utilisation !== null)
    list.push({
      key: 'utilisation',
      value: pct(p.utilisation),
      change: points(p.utilisationDelta),
      trend: p.utilisationDelta,
    })
  if (p.marginAvg !== null)
    list.push({
      key: 'margin',
      value: pct(p.marginAvg),
      change: points(p.marginAvgDelta),
      trend: p.marginAvgDelta,
    })
  list.push({
    key: 'basket',
    value: p.basketAvg === null ? '—' : formatMoneyShort(p.basketAvg),
    change: signedPct(p.basketAvgVariation),
    trend: p.basketAvgVariation,
  })
  list.push({
    key: 'confirmation',
    value: p.quoteConfirmation === null ? '—' : pct(p.quoteConfirmation),
    change: points(p.quoteConfirmationDelta),
    trend: p.quoteConfirmationDelta,
  })
  if (p.utilisation === null || p.marginAvg === null)
    list.push({
      key: 'collection',
      value: p.collectionRate === null ? '—' : pct(p.collectionRate),
      change: points(p.collectionRateDelta),
      trend: p.collectionRateDelta,
    })
  return list.slice(0, 4)
})
</script>

<template>
  <section
    class="flex h-full flex-col rounded-wd-lg border border-line bg-surface"
    :aria-labelledby="'performance-title'"
  >
    <h2 id="performance-title" class="px-5 pt-5 text-[17px] font-semibold">
      {{ t('dashboard.performance.title') }}
    </h2>
    <dl
      class="grid flex-1 grid-cols-2 [&>div]:border-line [&>div:nth-child(-n+2)]:border-b [&>div:nth-child(odd)]:border-r"
    >
      <div
        v-for="(tile, index) in tiles"
        :key="tile.key"
        class="flex flex-col p-5"
        :class="tiles.length === 3 && index === 2 && 'col-span-2'"
      >
        <dt class="text-[13px] font-semibold text-muted">
          {{ t(`dashboard.performance.${tile.key}`) }}
        </dt>
        <dd class="mt-1 font-display text-[24px] font-semibold">{{ tile.value }}</dd>
        <dd
          class="mt-auto pt-1 text-[12.5px] font-bold"
          :class="
            tile.trend === null || tile.trend === 0
              ? 'text-muted'
              : tile.trend > 0
                ? 'text-green'
                : 'text-red'
          "
        >
          {{
            tile.change === null
              ? t('dashboard.performance.noComparison')
              : tile.trend === 0
                ? t('dashboard.performance.stable')
                : tile.change
          }}
        </dd>
      </div>
    </dl>
  </section>
</template>
