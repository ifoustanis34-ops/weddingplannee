<script setup lang="ts">
import { Ban, CalendarClock, FileDown, Paperclip, Plus, Trash2, Wallet } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatDate } from '@/composables/useDate'
import { formatMoney } from '@/composables/useMoney'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import {
  WBadge,
  WButton,
  WDrawer,
  WEmptyState,
  WInput,
  WModal,
  WMoney,
  WProgress,
  WTextarea,
} from '@/design'

import { financeApi, useContract, useFinanceAction } from '../api'
import type { Payment, ScheduleItem } from '../types'
import PaymentModal from './PaymentModal.vue'
import ScheduleModal from './ScheduleModal.vue'

const props = defineProps<{ contractId: string | null }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const canManage = computed(() => can('manageFinance'))

const open = computed({
  get: () => props.contractId !== null,
  set: (value) => !value && emit('close'),
})
const contract = useContract(computed(() => props.contractId))
const data = computed(() => contract.data.value)
const showMargins = computed(() => data.value?.margin !== undefined)

const paymentOpen = ref(false)
const suggested = ref<number | null>(null)
function markPaid(item: ScheduleItem): void {
  suggested.value = item.remaining
  paymentOpen.value = true
}
function newPayment(): void {
  suggested.value = null
  paymentOpen.value = true
}

const scheduleOpen = ref(false)

const cancelTarget = ref<Payment | null>(null)
const cancelReason = ref('')
const cancelError = ref<string>()
const cancel = useFinanceAction(({ id, reason }: { id: string; reason: string }) =>
  financeApi.cancelPayment(id, reason),
)
function askCancel(payment: Payment): void {
  cancelTarget.value = payment
  cancelReason.value = ''
  cancelError.value = undefined
}
async function confirmCancel(): Promise<void> {
  if (!cancelTarget.value) return
  try {
    await cancel.mutateAsync({ id: cancelTarget.value.id, reason: cancelReason.value })
    toast.success(t('finance.payment.cancelled'))
    cancelTarget.value = null
  } catch (error) {
    cancelError.value = toApiError(error).fieldError('reason') ?? toApiError(error).message
  }
}

const expenseLabel = ref('')
const expenseAmount = ref<number | ''>('')
const expenseError = ref<string>()
const addExpense = useFinanceAction(financeApi.addExpense)
const removeExpense = useFinanceAction(financeApi.deleteExpense)
async function saveExpense(): Promise<void> {
  if (!data.value?.wedding) return
  if (
    !expenseLabel.value.trim() ||
    !(Number(expenseAmount.value) >= 0) ||
    expenseAmount.value === ''
  ) {
    expenseError.value = t('finance.expenses.invalid')
    return
  }
  try {
    await addExpense.mutateAsync({
      wedding: data.value.wedding,
      label: expenseLabel.value.trim(),
      amount: Number(expenseAmount.value),
      date: null,
    })
    expenseLabel.value = ''
    expenseAmount.value = ''
    expenseError.value = undefined
    toast.success(t('finance.expenses.added'))
  } catch (error) {
    expenseError.value = toApiError(error).message
  }
}

async function download(url: string, filename?: string): Promise<void> {
  try {
    await financeApi.download(url, filename)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <WDrawer
    v-model:open="open"
    :title="data ? `${data.clientName}` : t('common.loading')"
    :subtitle="
      data
        ? t('finance.contractSubtitle', {
            number: data.number,
            date: data.weddingDate ? formatDate(data.weddingDate) : '—',
          })
        : undefined
    "
  >
    <div v-if="contract.isPending.value" class="flex flex-col gap-3">
      <div v-for="n in 4" :key="n" class="skeleton h-16" />
    </div>
    <WEmptyState
      v-else-if="contract.isError.value || !data"
      :title="t('finance.notFound')"
      :description="toApiError(contract.error.value).message"
    />

    <div v-else class="flex flex-col gap-6">
      <!-- Amounts -->
      <section class="grid grid-cols-2 gap-3">
        <div class="rounded-wd border border-line p-3">
          <p class="text-[12px] font-bold text-muted">{{ t('finance.fields.total') }}</p>
          <WMoney :amount="data.total" class="text-[17px] font-bold" />
        </div>
        <div class="rounded-wd border border-line p-3">
          <p class="text-[12px] font-bold text-muted">{{ t('finance.fields.balance') }}</p>
          <WMoney
            :amount="data.balance"
            class="text-[17px] font-bold"
            :class="data.balance > 0 ? 'text-coral' : 'text-green'"
          />
        </div>
        <div class="rounded-wd border border-line p-3">
          <p class="text-[12px] font-bold text-muted">{{ t('finance.fields.collected') }}</p>
          <WMoney :amount="data.collected" class="text-[17px] font-bold text-green" />
        </div>
        <div v-if="showMargins" class="rounded-wd border border-line p-3">
          <p class="text-[12px] font-bold text-muted">{{ t('finance.fields.margin') }}</p>
          <p class="text-[17px] font-bold">
            <WMoney :amount="data.margin ?? 0" />
            <span v-if="data.marginPct !== null" class="tabular text-[13px] text-muted">
              · {{ String(data.marginPct).replace('.', ',') }} %</span
            >
          </p>
          <p class="text-[12px] text-muted">
            {{ t('finance.fields.expensesShort', { amount: formatMoney(data.expenses ?? 0) }) }}
          </p>
        </div>
        <WProgress
          class="col-span-2"
          :value="data.progress"
          :label="t('finance.fields.progress')"
          show-value
        />
      </section>
      <p v-if="showMargins" class="rounded-wd bg-gold-soft px-3 py-2 text-[12.5px] text-ink-2">
        {{ t('finance.marginNotice') }}
      </p>

      <div
        v-if="canManage && data.balance > 0 && data.status === 'active'"
        class="flex flex-wrap gap-2"
      >
        <WButton @click="newPayment"
          ><Wallet class="size-4" aria-hidden="true" />{{ t('finance.payment.title') }}</WButton
        >
      </div>

      <!-- Schedule -->
      <section>
        <div class="mb-2 flex items-center gap-2">
          <h3 class="flex-1 font-semibold">{{ t('finance.schedule.title') }}</h3>
          <WButton v-if="canManage" size="sm" variant="ghost" @click="scheduleOpen = true"
            ><CalendarClock class="size-4" aria-hidden="true" />{{ t('common.edit') }}</WButton
          >
        </div>
        <ul class="divide-y divide-line rounded-wd border border-line">
          <li
            v-for="item in data.schedule"
            :key="item.id"
            class="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2.5"
          >
            <div class="min-w-0 flex-1">
              <p class="font-semibold">{{ item.label }}</p>
              <p class="text-[12.5px] text-muted">
                {{ formatDate(item.dueDate)
                }}<template v-if="item.paid && !item.isPaid">
                  · {{ t('finance.schedule.partly', { amount: formatMoney(item.paid) }) }}</template
                >
              </p>
            </div>
            <WMoney :amount="item.amount" class="font-semibold" />
            <WBadge v-if="item.isPaid" tone="green">{{ t('finance.schedule.paid') }}</WBadge>
            <WBadge v-else-if="item.isOverdue" tone="red">{{
              t('finance.schedule.overdue')
            }}</WBadge>
            <WButton
              v-if="!item.isPaid && canManage && data.status === 'active'"
              size="sm"
              variant="secondary"
              @click="markPaid(item)"
              >{{ t('finance.schedule.markPaid') }}</WButton
            >
          </li>
        </ul>
      </section>

      <!-- Payments -->
      <section>
        <h3 class="mb-2 font-semibold">{{ t('finance.payments.title') }}</h3>
        <p v-if="!data.payments.length" class="text-muted">{{ t('finance.payments.empty') }}</p>
        <ul v-else class="divide-y divide-line rounded-wd border border-line">
          <li
            v-for="payment in data.payments"
            :key="payment.id"
            class="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2.5"
            :class="payment.isCancelled && 'opacity-60'"
          >
            <div class="min-w-0 flex-1">
              <p class="font-semibold" :class="payment.isCancelled && 'line-through'">
                <WMoney :amount="payment.amount" /> · {{ t(`finance.methods.${payment.method}`) }}
              </p>
              <p class="text-[12.5px] text-muted">
                {{ formatDate(payment.paidAt) }} · {{ payment.receiptNumber
                }}<template v-if="payment.reference"> · {{ payment.reference }}</template>
                <template v-if="payment.isCancelled">
                  ·
                  {{
                    t('finance.payments.cancelledBecause', { reason: payment.cancelReason })
                  }}</template
                >
              </p>
            </div>
            <WButton
              v-if="payment.hasReceipt"
              size="sm"
              variant="ghost"
              :aria-label="t('finance.payments.receipt')"
              @click="download(`/payments/${payment.id}/receipt`)"
              ><FileDown class="size-4" aria-hidden="true" />{{
                t('finance.payments.receipt')
              }}</WButton
            >
            <WButton
              v-if="payment.hasProof"
              size="sm"
              variant="ghost"
              :aria-label="t('finance.payments.proof')"
              @click="
                download(`/payments/${payment.id}/proof`, `justificatif-${payment.receiptNumber}`)
              "
              ><Paperclip class="size-4" aria-hidden="true"
            /></WButton>
            <WButton
              v-if="!payment.isCancelled && canManage"
              size="sm"
              variant="ghost"
              class="text-red"
              @click="askCancel(payment)"
              ><Ban class="size-4" aria-hidden="true" />{{ t('finance.payments.cancel') }}</WButton
            >
          </li>
        </ul>
      </section>

      <!-- Expenses (owner, accountant) -->
      <section v-if="data.expenseItems">
        <h3 class="mb-2 font-semibold">{{ t('finance.expenses.title') }}</h3>
        <ul
          v-if="data.expenseItems.length"
          class="mb-3 divide-y divide-line rounded-wd border border-line"
        >
          <li
            v-for="expense in data.expenseItems"
            :key="expense.id"
            class="flex items-center gap-3 px-3 py-2"
          >
            <span class="flex-1">{{ expense.label }}</span>
            <WMoney :amount="expense.amount" class="font-semibold" />
            <WButton
              v-if="canManage"
              size="sm"
              variant="ghost"
              :aria-label="t('common.delete')"
              @click="removeExpense.mutate(expense.id)"
              ><Trash2 class="size-4" aria-hidden="true"
            /></WButton>
          </li>
        </ul>
        <form
          v-if="canManage && data.wedding"
          class="grid grid-cols-[1.5fr_1fr_auto] items-end gap-2"
          @submit.prevent="saveExpense"
        >
          <WInput
            v-model="expenseLabel"
            :label="t('finance.expenses.label')"
            :placeholder="t('finance.expenses.placeholder')"
          />
          <WInput
            v-model.number="expenseAmount"
            :label="t('finance.expenses.amount')"
            type="number"
            min="0"
          />
          <WButton
            type="submit"
            size="md"
            variant="secondary"
            :loading="addExpense.isPending.value"
            :aria-label="t('finance.expenses.add')"
            ><Plus class="size-4" aria-hidden="true"
          /></WButton>
          <p v-if="expenseError" class="col-span-3 text-[13px] font-semibold text-red">
            {{ expenseError }}
          </p>
        </form>
      </section>

      <RouterLink
        :to="{ name: 'quote-edit', params: { id: data.quote.id } }"
        class="text-[13px] font-bold text-violet hover:underline"
        >{{ t('finance.fromQuote', { number: data.quote.number }) }}</RouterLink
      >
    </div>
  </WDrawer>

  <PaymentModal
    v-model:open="paymentOpen"
    :contract-id="contractId"
    :suggested-amount="suggested"
  />
  <ScheduleModal v-model:open="scheduleOpen" :contract="data ?? null" />
  <WModal
    :open="cancelTarget !== null"
    :title="t('finance.payments.cancelTitle')"
    size="sm"
    @update:open="(v: boolean) => !v && (cancelTarget = null)"
  >
    <p class="mb-3 text-[13.5px]">
      {{ t('finance.payments.cancelHint', { amount: formatMoney(cancelTarget?.amount ?? 0) }) }}
    </p>
    <form id="cancel-payment" @submit.prevent="confirmCancel">
      <WTextarea
        v-model="cancelReason"
        :label="t('finance.payments.cancelReason')"
        :error="cancelError"
        :rows="2"
        required
        autofocus
      />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="cancelTarget = null">{{ t('common.close') }}</WButton>
      <WButton
        type="submit"
        form="cancel-payment"
        variant="danger"
        :loading="cancel.isPending.value"
        >{{ t('finance.payments.cancel') }}</WButton
      >
    </template>
  </WModal>
</template>
