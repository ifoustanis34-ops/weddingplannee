<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { WButton, WCard } from '@/design'
import { alertDetail as detail, alertTarget, SEVERITY } from '@/modules/alerts/format'

import type { DashboardAlert } from '../api'

/**
 * « Alertes » (reservations-stock.md §8): internal notices for the team, most urgent first, each
 * with its action. Status colors always come with an icon and a label, never color alone.
 * Stock alerts (insufficient stock, late returns, maintenance) join with step S3.
 */
const props = defineProps<{ alerts: DashboardAlert[]; canRecord: boolean }>()
const emit = defineEmits<{ record: [contractId: string] }>()
const { t } = useI18n()
const LIMIT = 6
const shown = computed(() => props.alerts.slice(0, LIMIT))
</script>

<template>
  <WCard
    :title="t('dashboard.alerts.title')"
    :subtitle="t('dashboard.alerts.subtitle')"
    class="h-full"
  >
    <p v-if="!alerts.length" class="text-muted">{{ t('dashboard.alerts.empty') }}</p>
    <ul v-else class="-my-1 divide-y divide-line" aria-live="polite">
      <li v-for="alert in shown" :key="alert.id" class="flex items-center gap-3 py-2.5">
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-[10px]"
          :class="SEVERITY[alert.severity].classes"
        >
          <component :is="SEVERITY[alert.severity].icon" class="size-[18px]" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate font-bold">
            <span class="sr-only">{{ t(`dashboard.alerts.severity.${alert.severity}`) }} : </span
            >{{ alert.title }}
          </p>
          <p class="truncate text-[12.5px] text-ink-2">
            <span class="font-semibold" :class="SEVERITY[alert.severity].text">{{
              t(`dashboard.alerts.severity.${alert.severity}`)
            }}</span>
            · {{ detail(alert) }}
          </p>
        </div>
        <WButton
          v-if="alert.kind === 'overdue_payment' && canRecord && alert.contract"
          size="sm"
          variant="secondary"
          @click="emit('record', alert.contract)"
          >{{ t('dashboard.alerts.record') }}</WButton
        >
        <WButton
          v-else-if="alertTarget(alert)"
          size="sm"
          variant="secondary"
          :to="alertTarget(alert)!"
          >{{ t('dashboard.alerts.open') }}</WButton
        >
      </li>
    </ul>
    <p v-if="alerts.length > LIMIT" class="mt-2 text-[12.5px] font-semibold text-muted">
      {{ t('dashboard.alerts.more', { count: alerts.length - LIMIT }) }}
    </p>
  </WCard>
</template>
