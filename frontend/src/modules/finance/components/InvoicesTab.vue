<script setup lang="ts">
import { Download, FileMinus } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatAmount } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WCard, WChips, WEmptyState } from '@/design'

import { billingApi, INVOICE_TONES, type Invoice, useInvoices } from '../billing'
import CreditModal from './CreditModal.vue'

/** « Factures » (§6.3): every invoice, what it received, what it still claims, its credit notes. */
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const status = ref('')
const invoices = useInvoices(() => ({ status: status.value || undefined }))
const statusOptions = computed(() =>
  ['', 'overdue', 'issued', 'partial', 'paid', 'cancelled'].map((value) => ({
    value,
    label: value ? t(`finance.invoices.statuses.${value}`) : t('finance.invoices.all'),
  })),
)
const crediting = ref<Invoice | null>(null)
async function pdf(url: string, number: string): Promise<void> {
  try {
    await billingApi.file(url, {}, `${number}.pdf`)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <WChips v-model="status" :options="statusOptions" :label="t('finance.invoices.filter')" />
    <WCard>
      <WEmptyState
        v-if="invoices.isError.value"
        :title="t('finance.invoices.loadError')"
        :description="toApiError(invoices.error.value).message"
      />
      <div v-else-if="invoices.isPending.value" class="skeleton h-40" />
      <WEmptyState
        v-else-if="!invoices.data.value?.length"
        :title="t('finance.invoices.emptyTitle')"
        :description="t('finance.invoices.emptyText')"
      />
      <ul v-else class="-my-1 divide-y divide-line">
        <li
          v-for="invoice in invoices.data.value"
          :key="invoice.id"
          class="flex flex-wrap items-center gap-x-4 gap-y-2 py-3"
        >
          <div class="min-w-[180px] flex-1">
            <p class="font-bold">
              <span class="num">{{ invoice.number }}</span>
              <span class="ml-2 text-[12.5px] font-semibold text-muted">{{
                invoice.kindLabel
              }}</span>
            </p>
            <p class="text-[13px] text-ink-2">
              {{ invoice.clientDetail.name }} ·
              <RouterLink
                :to="{ name: 'reservations', query: { reservation: invoice.reservation } }"
                class="font-semibold text-violet hover:underline"
                >{{ invoice.reservationDetail.number }}</RouterLink
              >
            </p>
            <p class="text-[12.5px] text-muted">
              {{
                t('finance.invoices.dates', {
                  issued: formatDate(invoice.issuedAt),
                  due: formatDate(invoice.dueAt),
                })
              }}
            </p>
            <p v-for="note in invoice.creditNotes" :key="note.id" class="text-[12.5px] text-muted">
              <button
                type="button"
                class="font-semibold text-ink-2 hover:underline"
                @click="pdf(`/credit-notes/${note.id}/pdf`, note.number)"
              >
                {{ note.number }}
              </button>
              · −{{ formatAmount(note.amount) }} · {{ note.reason }}
            </p>
          </div>
          <div class="text-right">
            <p class="num font-bold">{{ formatAmount(invoice.total - invoice.credited) }} FCFA</p>
            <p
              v-if="invoice.balance && invoice.status !== 'cancelled'"
              class="num text-[12.5px] font-semibold text-coral"
            >
              {{ t('finance.invoices.left', { amount: formatAmount(invoice.balance) }) }}
            </p>
          </div>
          <WBadge :tone="INVOICE_TONES[invoice.status]">{{
            t(`finance.invoices.statuses.${invoice.status}`)
          }}</WBadge>
          <div class="flex gap-1.5">
            <WButton
              size="sm"
              variant="secondary"
              icon
              :aria-label="t('finance.invoices.pdf', { number: invoice.number })"
              @click="pdf(`/invoices/${invoice.id}/pdf`, invoice.number)"
            >
              <Download class="size-[15px]" aria-hidden="true" />
            </WButton>
            <WButton
              v-if="can('manageFinance') && invoice.total > invoice.credited"
              size="sm"
              variant="secondary"
              icon
              :aria-label="t('finance.invoices.credit', { number: invoice.number })"
              @click="crediting = invoice"
            >
              <FileMinus class="size-[15px]" aria-hidden="true" />
            </WButton>
          </div>
        </li>
      </ul>
    </WCard>
    <CreditModal :invoice="crediting" @close="crediting = null" />
  </div>
</template>
