<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatAmount, formatMoney } from '@/composables/useMoney'
import { WCard, WChips, WEmptyState } from '@/design'
import type { PeriodRequest } from '@/modules/dashboard/api'

import { useRevenues } from '../billing'

/** « Recettes » (§6.1): each payment split by category, created automatically. */
const props = defineProps<{ period: PeriodRequest }>()
const { t } = useI18n()
const category = ref('')
const revenues = useRevenues(() => props.period, category)
const categories = computed(() =>
  ['', 'rental', 'sale', 'service', 'transport', 'damage'].map((value) => ({
    value,
    label: value ? t(`finance.revenues.categories.${value}`) : t('finance.revenues.all'),
  })),
)
const total = computed(() =>
  (revenues.data.value ?? []).filter((r) => !r.isCancelled).reduce((sum, r) => sum + r.amount, 0),
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <WChips v-model="category" :options="categories" :label="t('finance.revenues.filter')" />
      <p class="text-[13.5px] text-ink-2">
        {{ t('finance.revenues.total') }} <b class="num">{{ formatMoney(total) }}</b>
      </p>
    </div>
    <WCard>
      <WEmptyState
        v-if="revenues.isError.value"
        :title="t('finance.revenues.loadError')"
        :description="toApiError(revenues.error.value).message"
      />
      <div v-else-if="revenues.isPending.value" class="skeleton h-40" />
      <WEmptyState v-else-if="!revenues.data.value?.length" :title="t('finance.revenues.empty')" />
      <ul v-else class="-my-1 divide-y divide-line">
        <li
          v-for="revenue in revenues.data.value"
          :key="revenue.id"
          class="flex items-center gap-4 py-2.5"
          :class="revenue.isCancelled && 'text-muted line-through'"
        >
          <span class="w-[92px] shrink-0 text-[13px] text-ink-2">{{
            formatDate(revenue.date)
          }}</span>
          <span class="min-w-0 flex-1">
            <span class="block truncate font-semibold">{{
              revenue.clientName ?? revenue.label
            }}</span>
            <span class="block truncate text-[12.5px] text-muted"
              >{{ revenue.categoryLabel }} · {{ revenue.label }}</span
            >
          </span>
          <span class="num shrink-0 font-semibold">{{ formatAmount(revenue.amount) }}</span>
        </li>
      </ul>
    </WCard>
  </div>
</template>
