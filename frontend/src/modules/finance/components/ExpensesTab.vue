<script setup lang="ts">
import { Paperclip, Plus, Upload } from '@lucide/vue'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatAmount, formatMoney } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import { WButton, WCard, WEmptyState } from '@/design'

import { billingApi, billingKeys, type ExpenseRow, useExpenses } from '../billing'
import ExpenseModal from './ExpenseModal.vue'

/** « Dépenses » (§6.2): quick entry with the receipt, attached to a reservation or not. */
const { t } = useI18n()
const toast = useToast()
const queryClient = useQueryClient()
const expenses = useExpenses()
const rows = computed(() =>
  (expenses.data.value ?? []).slice().sort((a, b) => (b.date ?? '').localeCompare(a.date ?? '')),
)
const total = computed(() => rows.value.reduce((sum, e) => sum + e.amount, 0))
const modalOpen = ref(false)
const uploading = ref<string | null>(null)
async function upload(expense: ExpenseRow, event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = expense.id
  try {
    await billingApi.uploadReceipt(expense.id, file)
    toast.success(t('finance.expenseList.receiptSaved'))
    void queryClient.invalidateQueries({ queryKey: billingKeys.all })
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    uploading.value = null
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-[13.5px] text-ink-2">
        {{ t('finance.expenseList.total') }} <b class="num">{{ formatMoney(total) }}</b>
      </p>
      <WButton @click="modalOpen = true">
        <Plus class="size-[18px]" aria-hidden="true" />{{ t('dashboard.actions.newExpense') }}
      </WButton>
    </div>
    <WCard>
      <WEmptyState
        v-if="expenses.isError.value"
        :title="t('finance.expenseList.loadError')"
        :description="toApiError(expenses.error.value).message"
      />
      <div v-else-if="expenses.isPending.value" class="skeleton h-40" />
      <WEmptyState v-else-if="!rows.length" :title="t('finance.expenseList.empty')" />
      <ul v-else class="-my-1 divide-y divide-line">
        <li
          v-for="expense in rows"
          :key="expense.id"
          class="flex flex-wrap items-center gap-x-4 gap-y-1 py-2.5"
        >
          <span class="w-[92px] shrink-0 text-[13px] text-ink-2">{{
            expense.date ? formatDate(expense.date) : '—'
          }}</span>
          <span class="min-w-[180px] flex-1">
            <span class="block font-semibold">{{ expense.label }}</span>
            <span class="block text-[12.5px] text-muted">{{
              [
                expense.categoryName,
                expense.reservationNumber ?? expense.weddingTitle,
                expense.supplier,
              ]
                .filter(Boolean)
                .join(' · ')
            }}</span>
          </span>
          <span class="num font-semibold">{{ formatAmount(expense.amount) }}</span>
          <a
            v-if="expense.receiptUrl"
            :href="expense.receiptUrl"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-1 text-[13px] font-bold text-violet hover:underline"
            ><Paperclip class="size-[15px]" aria-hidden="true" />{{
              t('finance.expenseList.seeReceipt')
            }}</a
          >
          <label
            v-else
            class="inline-flex cursor-pointer items-center gap-1 text-[13px] font-bold text-ink-2 hover:text-violet"
            :class="uploading === expense.id && 'opacity-60'"
          >
            <Upload class="size-[15px]" aria-hidden="true" />{{
              t('finance.expenseList.addReceipt')
            }}
            <input
              type="file"
              class="sr-only"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              @change="upload(expense, $event)"
            />
          </label>
        </li>
      </ul>
    </WCard>
    <ExpenseModal v-model:open="modalOpen" />
  </div>
</template>
