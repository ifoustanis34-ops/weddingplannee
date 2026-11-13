<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatMoney } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect } from '@/design'

import { financeApi, useContracts, useFinanceAction } from '../api'
import { PAYMENT_METHODS, type PaymentMethod } from '../types'

/** « Enregistrer un paiement » (CLAUDE.md §7.5), from a contract or from the dashboard. */
const props = defineProps<{ contractId?: string | null; suggestedAmount?: number | null }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const contracts = useContracts()

const today = () => new Date().toISOString().slice(0, 10)
const contract = ref<string>('')
const amount = ref<number | ''>('')
const method = ref<PaymentMethod>('orange_money')
const paidAt = ref(today())
const reference = ref('')
const proof = ref<File | null>(null)
const errors = ref<Record<string, string | undefined>>({})

const openContracts = computed(() =>
  (contracts.data.value ?? []).filter((c) => c.status === 'active' && c.balance > 0),
)
const selected = computed(() => (contracts.data.value ?? []).find((c) => c.id === contract.value))
const maximum = computed(() => selected.value?.balance ?? 0)

watch(
  open,
  (isOpen) => {
    if (!isOpen) return
    contract.value = props.contractId ?? openContracts.value[0]?.id ?? ''
    amount.value = props.suggestedAmount ?? ''
    method.value = 'orange_money'
    paidAt.value = today()
    reference.value = ''
    proof.value = null
    errors.value = {}
  },
  { immediate: true },
)
// The contract list may arrive after the modal opened: preselect the first open contract then.
watch(openContracts, (list) => {
  if (open.value && !contract.value) contract.value = props.contractId ?? list[0]?.id ?? ''
})

const contractOptions = computed(() =>
  openContracts.value.map((c) => ({
    value: c.id,
    label: t('finance.payment.option', { client: c.clientName, amount: formatMoney(c.balance) }),
  })),
)
const methodOptions = computed(() =>
  PAYMENT_METHODS.map((m) => ({ value: m, label: t(`finance.methods.${m}`) })),
)
const record = useFinanceAction(
  ({ id, input }: { id: string; input: Parameters<typeof financeApi.recordPayment>[1] }) =>
    financeApi.recordPayment(id, input),
)

function onFile(event: Event): void {
  proof.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function submit(): Promise<void> {
  errors.value = {}
  const value = Number(amount.value)
  if (!contract.value) errors.value.contract = t('finance.payment.chooseContract')
  if (!Number.isInteger(value) || value <= 0)
    errors.value.amount = t('finance.payment.amountInvalid')
  else if (selected.value && value > maximum.value)
    errors.value.amount = t('finance.payment.exceeds', { amount: formatMoney(maximum.value) })
  if (Object.values(errors.value).some(Boolean)) return
  try {
    await record.mutateAsync({
      id: contract.value,
      input: {
        amount: value,
        method: method.value,
        paidAt: paidAt.value,
        reference: reference.value,
        proof: proof.value,
      },
    })
    toast.success(
      t('finance.payment.recorded', {
        amount: formatMoney(value),
        client: selected.value?.clientName ?? '',
      }),
    )
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    if (apiError.code === 'payment_exceeds_balance' || !Object.keys(apiError.fields).length)
      toast.error(apiError.message)
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="t('finance.payment.title')" size="md">
    <form id="payment-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
      <WSelect
        v-model="contract"
        class="sm:col-span-2"
        :label="t('finance.payment.contract')"
        :options="contractOptions"
        :placeholder="
          openContracts.length
            ? t('finance.payment.chooseContract')
            : t('finance.payment.noOpenContract')
        "
        :error="errors.contract"
        :disabled="Boolean(contractId)"
        required
      />
      <WInput
        v-model.number="amount"
        :label="t('finance.payment.amount')"
        :hint="selected ? t('finance.payment.max', { amount: formatMoney(maximum) }) : undefined"
        :error="errors.amount"
        type="number"
        min="1"
        :max="maximum || undefined"
        inputmode="numeric"
        required
        autofocus
      />
      <WSelect
        v-model="method"
        :label="t('finance.payment.method')"
        :hint="t('finance.payment.methodHint')"
        :options="methodOptions"
        required
      />
      <WInput
        v-model="paidAt"
        :label="t('finance.payment.date')"
        type="date"
        :max="today()"
        :error="errors.paidAt"
        required
      />
      <WInput
        v-model="reference"
        :label="t('finance.payment.reference')"
        :placeholder="t('finance.payment.referencePlaceholder')"
        :error="errors.reference"
      />
      <label class="flex flex-col gap-1.5 sm:col-span-2">
        <span class="text-[13px] font-bold text-ink-2">{{ t('finance.payment.proof') }}</span>
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp,.heic"
          class="text-[13px] file:mr-3 file:rounded-[10px] file:border file:border-line file:bg-surface file:px-3 file:py-2 file:font-bold"
          @change="onFile"
        />
        <span v-if="errors.proof" class="text-[13px] font-semibold text-red">{{
          errors.proof
        }}</span>
        <span v-else class="text-[13px] text-muted">{{ t('finance.payment.proofHint') }}</span>
      </label>
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="payment-form" :loading="record.isPending.value">{{
        t('finance.payment.submit')
      }}</WButton>
    </template>
  </WModal>
</template>
