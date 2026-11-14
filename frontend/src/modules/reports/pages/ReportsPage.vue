<script setup lang="ts">
import { TrendingDown, TrendingUp } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import DownloadMenu from '@/components/DownloadMenu.vue'
import { formatMoney } from '@/composables/useMoney'
import { WButton, WCard, WEmptyState } from '@/design'
import type { PeriodRequest } from '@/modules/dashboard/api'
import PeriodPicker from '@/modules/dashboard/components/PeriodPicker.vue'
import { REPORT_TYPES, type ReportType, useReport } from '@/modules/finance/billing'
import ReportTable from '@/modules/finance/components/ReportTable.vue'

/** « Rapports » (reservations-stock.md §6.5): pick a report and a period, read, export. */
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const type = computed<ReportType>({
  get: () =>
    (REPORT_TYPES as readonly string[]).includes(String(route.query.rapport))
      ? (route.query.rapport as ReportType)
      : 'revenue',
  set: (value) => void router.replace({ query: { ...route.query, rapport: value } }),
})
const period = ref<PeriodRequest>({ period: 'month' })
const report = useReport(type, period)
const data = computed(() => report.data.value)
const COUNTS = ['revenue', 'expenses', 'clients', 'profitable', 'margins', 'unpaid']
const isMoney = computed(() => COUNTS.includes(type.value))
const headlineValue = (value: number) =>
  isMoney.value ? formatMoney(value) : value.toLocaleString(locale.value)
const variation = computed(() => data.value?.headline.variationPct ?? null)
// Expenses going up is not good news: the arrow keeps its direction, the color its meaning.
const goodNews = computed(() =>
  variation.value === null
    ? null
    : type.value === 'expenses'
      ? variation.value < 0
      : variation.value > 0,
)
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('reports.title') }}</h1>
        <p class="mt-1 max-w-[64ch] text-muted">{{ t('reports.subtitle') }}</p>
      </div>
      <DownloadMenu
        :url="`/reports/${type}`"
        :filename="`rapport-${type}`"
        :params="{
          period: period.period,
          from: period.period === 'custom' ? period.from : undefined,
          to: period.period === 'custom' ? period.to : undefined,
        }"
      />
    </header>

    <!-- One bounded column on mobile: the report list scrolls sideways instead of widening the page. -->
    <div
      class="grid grid-cols-[minmax(0,1fr)] gap-[18px] min-[1101px]:grid-cols-[260px_minmax(0,1fr)]"
    >
      <nav class="min-w-0" :aria-label="t('reports.choose')">
        <ul class="flex gap-1.5 overflow-x-auto min-[1101px]:flex-col">
          <li v-for="key in REPORT_TYPES" :key="key" class="shrink-0">
            <button
              type="button"
              class="w-full rounded-wd px-3 py-2.5 text-left text-[13.5px] font-semibold whitespace-nowrap transition-colors min-[1101px]:whitespace-normal"
              :class="type === key ? 'bg-violet-soft text-violet' : 'text-ink-2 hover:bg-surface-2'"
              :aria-current="type === key ? 'page' : undefined"
              @click="type = key"
            >
              {{ t(`reports.types.${key}`) }}
            </button>
          </li>
        </ul>
      </nav>

      <div class="flex min-w-0 flex-col gap-4">
        <PeriodPicker v-if="type !== 'unpaid'" v-model="period" />
        <WEmptyState
          v-if="report.isError.value"
          :title="t('reports.loadError')"
          :description="toApiError(report.error.value).message"
        >
          <WButton variant="secondary" @click="report.refetch()">{{ t('common.retry') }}</WButton>
        </WEmptyState>
        <div v-else-if="!data" class="skeleton h-[360px] rounded-wd-lg" />
        <template v-else>
          <div class="grid gap-3.5 sm:grid-cols-3" aria-live="polite">
            <div class="rounded-wd-lg border border-line bg-surface p-4">
              <p class="text-[12.5px] font-bold text-muted">{{ data.headline.label }}</p>
              <p class="num mt-1 font-display text-[22px] font-semibold">
                {{ headlineValue(data.headline.current) }}
              </p>
            </div>
            <div
              v-if="data.headline.previous !== null"
              class="rounded-wd-lg border border-line bg-surface p-4"
            >
              <p class="text-[12.5px] font-bold text-muted">{{ t('reports.previous') }}</p>
              <p class="num mt-1 font-display text-[22px] font-semibold">
                {{ headlineValue(data.headline.previous) }}
              </p>
            </div>
            <div
              v-if="data.headline.previous !== null"
              class="rounded-wd-lg border border-line bg-surface p-4"
            >
              <p class="text-[12.5px] font-bold text-muted">{{ t('reports.variation') }}</p>
              <p
                class="num mt-1 flex items-center gap-1.5 font-display text-[22px] font-semibold"
                :class="goodNews === null ? 'text-muted' : goodNews ? 'text-green' : 'text-red'"
              >
                <template v-if="variation !== null">
                  <component
                    :is="variation >= 0 ? TrendingUp : TrendingDown"
                    class="size-5"
                    aria-hidden="true"
                  />
                  {{ variation > 0 ? '+' : '' }}{{ variation.toLocaleString(locale) }} %
                </template>
                <template v-else>—</template>
              </p>
            </div>
          </div>
          <WCard :title="data.title">
            <ReportTable
              :columns="data.columns"
              :rows="data.rows"
              :totals="data.totals"
              :caption="data.title"
            />
          </WCard>
        </template>
      </div>
    </div>
  </div>
</template>
