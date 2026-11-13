<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { formatDate } from '@/composables/useDate'
import { formatAmount } from '@/composables/useMoney'
import { WCard, WEmptyState, WTabs } from '@/design'

import { staffApi, staffKeys } from '../api'
import DayPayPanel from '../components/DayPayPanel.vue'
import PayPeriodsPanel from '../components/PayPeriodsPanel.vue'

/**
 * « Paie » (feedback 13/11/2026): pay the day workers of an event on the spot, pay the employees'
 * salaries for the month, and see every payment made.
 */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const TABS = ['jour', 'salaires', 'historique'] as const
const tab = computed({
  get: () =>
    (TABS as readonly string[]).includes(String(route.query.onglet))
      ? String(route.query.onglet)
      : 'jour',
  set: (value: string) => void router.replace({ query: { ...route.query, onglet: value } }),
})
const tabs = computed(() => TABS.map((key) => ({ key, label: t(`staff.payPage.tabs.${key}`) })))
const history = useQuery({
  queryKey: [...staffKeys.all, 'payments'],
  queryFn: staffApi.payments,
  enabled: computed(() => tab.value === 'historique'),
})
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header>
      <h1>{{ t('staff.payPage.title') }}</h1>
      <p class="mt-1 max-w-[70ch] text-muted">{{ t('staff.payPage.subtitle') }}</p>
    </header>
    <WTabs v-model="tab" :tabs="tabs" :label="t('staff.payPage.title')" />
    <DayPayPanel v-if="tab === 'jour'" />
    <PayPeriodsPanel v-else-if="tab === 'salaires'" />
    <WCard
      v-else
      :title="t('staff.payPage.historyTitle')"
      :subtitle="t('staff.payPage.historyHint')"
    >
      <div v-if="history.isPending.value" class="skeleton h-40" />
      <WEmptyState
        v-else-if="!history.data.value?.length"
        :title="t('staff.payPage.historyEmpty')"
      />
      <ul v-else class="-my-1 divide-y divide-line">
        <li
          v-for="payment in history.data.value"
          :key="payment.id"
          class="flex flex-wrap items-center gap-3 py-2.5"
        >
          <span class="w-[100px] text-[13px] text-ink-2">{{ formatDate(payment.date) }}</span>
          <span class="min-w-0 flex-1">
            <span class="block font-semibold">{{ payment.staffName }}</span>
            <span class="block text-[12.5px] text-muted">{{
              [payment.reservationNumber, t(`finance.methods.${payment.method}`), payment.note]
                .filter(Boolean)
                .join(' · ')
            }}</span>
          </span>
          <span class="num font-bold">{{ formatAmount(payment.amount) }}</span>
        </li>
      </ul>
    </WCard>
  </div>
</template>
