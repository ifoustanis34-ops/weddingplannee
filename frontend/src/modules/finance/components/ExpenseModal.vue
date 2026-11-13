<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { z } from 'zod'

import { toApiError } from '@/api/errors'
import { formatMoney } from '@/composables/useMoney'
import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect } from '@/design'
import { i18n } from '@/i18n'
import { useWeddings } from '@/modules/events/api'
import { useReservations } from '@/modules/reservations/api'

import { useCreateExpense, useExpenseCategories } from '../api'
import { billingApi } from '../billing'
import { PAYMENT_METHODS } from '../types'

/**
 * « Enregistrer une dépense » (reservations-stock.md §6.2, §8): quick entry, optionally attached
 * to a wedding (it then counts in that wedding's margin). Same rules as the server: a general
 * expense needs its category.
 */
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const applyServerErrors = useServerErrors()
const categories = useExpenseCategories(() => open.value)
const weddings = useWeddings()
const create = useCreateExpense()

const gt = (key: string) => i18n.global.t(key)
const today = () => new Date().toISOString().slice(0, 10)
const schema = z
  .object({
    label: z.string().trim().min(1, gt('dashboard.expense.labelRequired')).max(160),
    amount: z
      .number({ invalid_type_error: gt('dashboard.expense.amountRequired') })
      .int()
      .min(1, gt('dashboard.expense.amountRequired')),
    category: z.string().optional().default(''),
    wedding: z.string().optional().default(''),
    reservation: z.string().optional().default(''),
    date: z.string().min(1, gt('validation.required')),
    supplier: z.string().trim().max(160).optional().default(''),
    method: z.string().optional().default(''),
  })
  .refine((v) => Boolean(v.category) || Boolean(v.wedding) || Boolean(v.reservation), {
    path: ['category'],
    message: gt('dashboard.expense.categoryRequired'),
  })
type FormValues = z.input<typeof schema>
type FormOutput = z.output<typeof schema>
const FIELDS = [
  'label',
  'amount',
  'category',
  'wedding',
  'reservation',
  'date',
  'supplier',
  'method',
] as const

const { defineField, errors, handleSubmit, isSubmitting, resetForm, setFieldError } = useForm<
  FormValues,
  FormOutput
>({ validationSchema: toTypedSchema(schema) })
const [label, labelAttrs] = defineField('label')
const [amount] = defineField('amount')
const [category] = defineField('category')
const [wedding] = defineField('wedding')
const [reservation] = defineField('reservation')
const receipt = ref<File | null>(null)
const [date] = defineField('date')
const [supplier] = defineField('supplier')
const [method] = defineField('method')

watch(open, (isOpen) => {
  if (isOpen)
    resetForm({
      values: {
        label: '',
        amount: undefined,
        category: '',
        wedding: '',
        reservation: '',
        date: today(),
        supplier: '',
        method: '',
      },
    })
})

const categoryOptions = computed(() =>
  (categories.data.value ?? [])
    .filter((c) => c.isActive)
    .map((c) => ({ value: c.id, label: c.name })),
)
const weddingOptions = computed(() => [
  { value: '', label: t('dashboard.expense.noWedding') },
  ...(weddings.data.value ?? []).map((w) => ({ value: w.id, label: w.title })),
])
// §6.2: attach the expense to a reservation for its profitability.
const reservations = useReservations(() => ({ tab: 'all' }))
const reservationOptions = computed(() => [
  { value: '', label: t('finance.expenseList.noReservation') },
  ...(reservations.data.value ?? [])
    .filter((r) => r.status !== 'cancelled')
    .map((r) => ({ value: r.id, label: `${r.number} · ${r.title}` })),
])
const methodOptions = computed(() => [
  { value: '', label: t('dashboard.expense.noMethod') },
  ...PAYMENT_METHODS.map((m) => ({ value: m, label: t(`finance.methods.${m}`) })),
])

const onSubmit = handleSubmit(async (values) => {
  try {
    const created = await create.mutateAsync({
      label: values.label,
      amount: values.amount,
      category: values.category || null,
      wedding: values.wedding || null,
      reservation: values.reservation || null,
      date: values.date,
      supplier: values.supplier,
      method: values.method as (typeof PAYMENT_METHODS)[number] | '',
    })
    if (receipt.value) {
      try {
        await billingApi.uploadReceipt(created.id, receipt.value)
      } catch (error) {
        toast.error(toApiError(error).message) // the expense stays; the receipt can be added later
      }
    }
    receipt.value = null
    toast.success(t('dashboard.expense.saved', { amount: formatMoney(values.amount) }))
    open.value = false
  } catch (error) {
    applyServerErrors(error, (field, message) => setFieldError(field as 'label', message), FIELDS)
  }
})
</script>

<template>
  <WModal v-model:open="open" :title="t('dashboard.expense.title')" size="md">
    <form id="expense-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit="onSubmit">
      <WInput
        v-model="label"
        v-bind="labelAttrs"
        class="sm:col-span-2"
        :label="t('dashboard.expense.label')"
        :placeholder="t('dashboard.expense.labelPlaceholder')"
        :error="errors.label"
        required
        autofocus
      />
      <WInput
        v-model.number="amount"
        :label="t('dashboard.expense.amount')"
        :error="errors.amount"
        type="number"
        inputmode="numeric"
        min="1"
        step="500"
        required
      />
      <WInput
        v-model="date"
        :label="t('dashboard.expense.date')"
        :error="errors.date"
        type="date"
      />
      <WSelect
        v-model="category"
        :label="t('dashboard.expense.category')"
        :options="categoryOptions"
        :placeholder="t('dashboard.expense.chooseCategory')"
        :error="errors.category"
      />
      <WSelect
        v-model="wedding"
        :label="t('dashboard.expense.wedding')"
        :options="weddingOptions"
        :error="errors.wedding"
      />
      <WSelect
        v-model="reservation"
        :label="t('finance.expenseList.reservation')"
        :options="reservationOptions"
        :error="errors.reservation"
      />
      <WInput
        v-model="supplier"
        :label="t('dashboard.expense.supplier')"
        :error="errors.supplier"
      />
      <WSelect
        v-model="method"
        :label="t('dashboard.expense.method')"
        :options="methodOptions"
        :error="errors.method"
      />
      <label class="flex flex-col gap-1.5 sm:col-span-2">
        <span class="text-[13px] font-bold">{{ t('finance.expenseList.receipt') }}</span>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          capture="environment"
          class="text-[13px] file:mr-3 file:rounded-[8px] file:border file:border-line-2 file:bg-surface file:px-3 file:py-1.5 file:font-bold"
          @change="receipt = ($event.target as HTMLInputElement).files?.[0] ?? null"
        />
        <span class="text-[12px] text-muted">{{ t('finance.expenseList.receiptHint') }}</span>
      </label>
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="expense-form" :loading="isSubmitting">
        {{ t('dashboard.expense.save') }}
      </WButton>
    </template>
  </WModal>
</template>
