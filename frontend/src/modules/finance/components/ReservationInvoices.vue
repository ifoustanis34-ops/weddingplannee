<script setup lang="ts">
import { FileDown, ReceiptText } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatAmount, formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import WhatsAppButton from '@/components/WhatsAppButton.vue'
import { WBadge, WButton } from '@/design'

import { billingApi, INVOICE_TONES, useBillingMutation, useInvoices } from '../billing'

/** Invoices of a reservation in its sheet (§6.3): deposit, then final, then PDF and status. */
const props = defineProps<{
  reservation: { id: string; status: string; total: number | null; depositRequired: number | null }
}>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const invoices = useInvoices(() => ({ reservation: props.reservation.id }))
const rows = computed(() => invoices.data.value ?? [])
const invoiced = computed(() => rows.value.reduce((sum, i) => sum + i.total - i.credited, 0))
const billable = computed(
  () => can('manageFinance') && !['draft', 'cancelled'].includes(props.reservation.status),
)
const canDeposit = computed(
  () => billable.value && !rows.value.length && (props.reservation.depositRequired ?? 0) > 0,
)
const canFinal = computed(
  () => billable.value && (props.reservation.total ?? 0) - invoiced.value > 0,
)
const issue = useBillingMutation((kind: 'deposit' | 'final') =>
  billingApi.issue(props.reservation.id, kind),
)
async function run(kind: 'deposit' | 'final'): Promise<void> {
  try {
    const invoice = await issue.mutateAsync(kind)
    toast.success(t('finance.invoices.issued', { number: invoice.number }))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
async function pdf(id: string, number: string): Promise<void> {
  try {
    await billingApi.file(`/invoices/${id}/pdf`, {}, `${number}.pdf`)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const invoicePdf = (id: string) => billingApi.blob(`/invoices/${id}/pdf`)
</script>

<template>
  <section>
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3>{{ t('finance.invoices.title') }}</h3>
      <div class="flex flex-wrap gap-2">
        <WButton
          v-if="canDeposit"
          size="sm"
          variant="secondary"
          :loading="issue.isPending.value"
          @click="run('deposit')"
        >
          <ReceiptText class="size-[15px]" aria-hidden="true" />{{
            t('finance.invoices.issueDeposit')
          }}
        </WButton>
        <WButton
          v-if="canFinal"
          size="sm"
          variant="secondary"
          :loading="issue.isPending.value"
          @click="run('final')"
        >
          <ReceiptText class="size-[15px]" aria-hidden="true" />{{
            t('finance.invoices.issueFinal')
          }}
        </WButton>
      </div>
    </div>
    <div v-if="invoices.isPending.value" class="skeleton mt-2 h-10" />
    <p v-else-if="!rows.length" class="mt-2 text-[13px] text-muted">
      {{ t('finance.invoices.none') }}
    </p>
    <ul v-else class="mt-2 divide-y divide-line rounded-wd border border-line">
      <li
        v-for="invoice in rows"
        :key="invoice.id"
        class="flex flex-wrap items-center gap-3 px-3 py-2.5"
      >
        <span class="min-w-0 flex-1">
          <span class="block font-semibold"
            ><span class="num">{{ invoice.number }}</span> · {{ invoice.kindLabel }}</span
          >
          <span class="block text-[12.5px] text-muted">{{
            t('finance.invoices.dates', {
              issued: formatDate(invoice.issuedAt),
              due: formatDate(invoice.dueAt),
            })
          }}</span>
        </span>
        <span class="num font-semibold">{{ formatAmount(invoice.total - invoice.credited) }}</span>
        <WBadge :tone="INVOICE_TONES[invoice.status]">{{
          t(`finance.invoices.statuses.${invoice.status}`)
        }}</WBadge>
        <WButton
          size="sm"
          variant="secondary"
          icon
          :aria-label="t('finance.invoices.pdf', { number: invoice.number })"
          @click="pdf(invoice.id, invoice.number)"
        >
          <FileDown class="size-[15px]" aria-hidden="true" />
        </WButton>
        <WhatsAppButton
          icon
          :phone="invoice.clientDetail.phone"
          :message="
            t('whatsapp.invoiceMessage', {
              name: invoice.clientDetail.name,
              number: invoice.number,
              amount: formatMoney(invoice.total - invoice.credited),
              due: formatDate(invoice.dueAt),
            })
          "
          :file="() => invoicePdf(invoice.id)"
          :filename="`${invoice.number}.pdf`"
          :label="t('whatsapp.invoice', { number: invoice.number })"
        />
      </li>
    </ul>
  </section>
</template>
