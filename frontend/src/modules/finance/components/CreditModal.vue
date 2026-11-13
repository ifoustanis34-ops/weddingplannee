<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatMoney } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal } from '@/design'

import { billingApi, type Invoice, useBillingMutation } from '../billing'

/** « Émettre un avoir » on an invoice: all or part of what it still claims (§6.3). */
const props = defineProps<{ invoice: Invoice | null }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const toast = useToast()
const amount = ref(0)
const reason = ref('')
const left = computed(() => (props.invoice ? props.invoice.total - props.invoice.credited : 0))
watch(
  () => props.invoice,
  () => {
    amount.value = left.value
    reason.value = ''
  },
)
const open = computed({
  get: () => props.invoice !== null,
  set: (value) => {
    if (!value) emit('close')
  },
})
const credit = useBillingMutation((input: { id: string; amount: number; reason: string }) =>
  billingApi.credit(input.id, { amount: input.amount, reason: input.reason }),
)
async function submit(): Promise<void> {
  if (!props.invoice) return
  try {
    const note = await credit.mutateAsync({
      id: props.invoice.id,
      amount: amount.value,
      reason: reason.value,
    })
    toast.success(t('finance.invoices.credited', { number: note.number }))
    emit('close')
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="t('finance.invoices.creditTitle')" size="sm">
    <form v-if="invoice" id="credit-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <p class="text-[13.5px] text-ink-2">
        {{
          t('finance.invoices.creditText', { number: invoice.number, amount: formatMoney(left) })
        }}
      </p>
      <WInput
        v-model.number="amount"
        type="number"
        min="1"
        :max="left"
        inputmode="numeric"
        :label="t('finance.invoices.creditAmount')"
        required
      />
      <WInput
        v-model="reason"
        :label="t('finance.invoices.creditReason')"
        required
        maxlength="255"
      />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="emit('close')">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="credit-form" :loading="credit.isPending.value">{{
        t('finance.invoices.creditSave')
      }}</WButton>
    </template>
  </WModal>
</template>
