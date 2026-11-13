<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { formatDate } from '@/composables/useDate'
import { formatMoneyShort } from '@/composables/useMoney'
import { WButton, WCard } from '@/design'

import type { DashboardSummary } from '../api'

/** « Soldes à encaisser »: the largest balances, their next due date and « Encaisser ». */
defineProps<{ balances: NonNullable<DashboardSummary['balances']>; canRecord: boolean }>()
const emit = defineEmits<{ record: [contractId: string] }>()
const { t } = useI18n()
type Row = NonNullable<DashboardSummary['balances']>[number]
/** Reservation balances open the reservation sheet (its own payment form); contracts, finance. */
const target = (row: Row) =>
  row.reservation
    ? { name: 'reservations', query: { reservation: row.reservation } }
    : { name: 'finance', query: { contract: row.contract } }
</script>

<template>
  <WCard
    :title="t('dashboard.balances.title')"
    :subtitle="t('dashboard.balances.subtitle')"
    class="h-full"
  >
    <p v-if="!balances.length" class="text-muted">{{ t('dashboard.balances.empty') }}</p>
    <ul v-else class="-my-1 divide-y divide-line">
      <li
        v-for="row in balances"
        :key="row.reservation ?? row.contract ?? row.number"
        class="flex items-center gap-3 py-2.5"
      >
        <div class="min-w-0 flex-1">
          <RouterLink :to="target(row)" class="block truncate font-bold hover:text-violet">{{
            row.clientName
          }}</RouterLink>
          <p
            class="truncate text-[12.5px]"
            :class="row.isOverdue ? 'font-semibold text-coral' : 'text-muted'"
          >
            {{
              !row.dueDate
                ? t('dashboard.balances.noDue')
                : row.isOverdue
                  ? t('dashboard.balances.overdue', { date: formatDate(row.dueDate) })
                  : t('dashboard.balances.due', { date: formatDate(row.dueDate) })
            }}
          </p>
        </div>
        <span class="num shrink-0 font-display text-[15px] font-semibold">{{
          formatMoneyShort(row.balance)
        }}</span>
        <WButton
          v-if="canRecord"
          size="sm"
          variant="secondary"
          :aria-label="t('dashboard.balances.recordFor', { name: row.clientName })"
          :to="row.reservation ? target(row) : undefined"
          @click="row.contract && emit('record', row.contract)"
          >{{ t('dashboard.balances.record') }}</WButton
        >
      </li>
    </ul>
  </WCard>
</template>
