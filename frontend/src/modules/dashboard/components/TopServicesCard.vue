<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatMoneyShort } from '@/composables/useMoney'
import { WCard } from '@/design'

import type { DashboardSummary } from '../api'

/**
 * « Prestations les plus demandées »: ranked horizontal bars, one color for every bar (a single
 * series: the length carries the value, never a ramp). Revenue is hidden for the assistant.
 */
const props = defineProps<{ services: DashboardSummary['topServices'] }>()
const { t } = useI18n()
const max = computed(() => Math.max(1, ...props.services.map((s) => s.count)))
</script>

<template>
  <WCard
    :title="t('dashboard.services.title')"
    :subtitle="t('dashboard.services.subtitle')"
    class="h-full"
  >
    <p v-if="!services.length" class="text-muted">{{ t('dashboard.services.empty') }}</p>
    <ol v-else class="flex flex-col gap-3">
      <li v-for="(service, index) in services" :key="service.name">
        <div class="flex items-baseline gap-2 text-[13.5px]">
          <span class="num w-4 shrink-0 font-bold text-muted">{{ index + 1 }}</span>
          <span class="min-w-0 flex-1 truncate font-semibold">{{ service.name }}</span>
          <span v-if="service.revenue !== null" class="num shrink-0 font-bold">{{
            formatMoneyShort(service.revenue)
          }}</span>
        </div>
        <div class="mt-1 flex items-center gap-2 pl-6">
          <div class="h-2 flex-1 rounded-full bg-surface-2">
            <div
              class="h-full rounded-full bg-chart-income"
              :style="{ width: `${Math.max(4, (service.count / max) * 100)}%` }"
            />
          </div>
          <span class="num w-14 shrink-0 text-right text-[12px] font-semibold text-muted">{{
            t('dashboard.services.times', { count: service.count }, service.count)
          }}</span>
        </div>
      </li>
    </ol>
  </WCard>
</template>
