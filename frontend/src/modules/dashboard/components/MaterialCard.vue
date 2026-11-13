<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatAmount } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { WButton, WCard } from '@/design'
import StockBar from '@/modules/stock/components/StockBar.vue'
import StockLegend from '@/modules/stock/components/StockLegend.vue'

import type { DashboardSummary } from '../api'

/** « Matériel aujourd'hui » (reservations-stock.md §8): stacked bar per category. */
const props = defineProps<{ material: DashboardSummary['materialToday'] }>()
const { t } = useI18n()
const { can } = usePermissions()
const rows = computed(() => props.material.categories)
</script>

<template>
  <WCard
    :title="t('dashboard.material.title')"
    :subtitle="t('dashboard.material.subtitle')"
    class="h-full"
  >
    <template v-if="can('viewStock')" #actions>
      <WButton :to="{ name: 'stock' }" variant="secondary" size="sm">{{
        t('dashboard.seeAll')
      }}</WButton>
    </template>
    <p v-if="!rows.length" class="text-muted">{{ t('dashboard.material.empty') }}</p>
    <template v-else>
      <p class="flex items-baseline gap-2">
        <span class="font-display text-[28px] leading-none font-semibold">{{
          formatAmount(material.available)
        }}</span>
        <span class="text-[13px] font-semibold text-muted">{{
          t('dashboard.material.available')
        }}</span>
      </p>
      <ul class="mt-4 flex flex-col gap-2.5">
        <li v-for="row in rows" :key="row.name">
          <div class="mb-1 flex items-baseline justify-between gap-2 text-[12.5px]">
            <span class="truncate font-semibold text-ink-2">{{ row.name }}</span>
            <span class="num shrink-0 font-bold">{{ formatAmount(row.available) }}</span>
          </div>
          <StockBar
            :available="row.available"
            :reserved="row.reserved"
            :out="row.out"
            :maintenance="row.maintenance"
            :height="7"
          />
        </li>
      </ul>
      <StockLegend class="mt-3" />
    </template>
  </WCard>
</template>
