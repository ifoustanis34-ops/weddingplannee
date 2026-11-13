<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePermissions } from '@/composables/usePermissions'
import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect, WSwitch, WTextarea } from '@/design'

import { stockApi, useItemCategories, useStockMutation } from '../api'
import type { Item, ItemInput } from '../types'

/** New or edited article (reservations-stock.md §5.1). Costs only for owner and accountant. */
const props = defineProps<{ item?: Item | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [item: Item] }>()
const { t } = useI18n()
const toast = useToast()
const applyServerErrors = useServerErrors()
const { can } = usePermissions()
const categories = useItemCategories()
const isEdit = computed(() => Boolean(props.item))

interface Form {
  reference: string
  name: string
  category: string
  description: string
  location: string
  tracking: 'quantity' | 'unit'
  initialQuantity: number | null
  serials: string
  rentPrice: number | null
  rentUnit: 'day' | 'event'
  salePrice: number | null
  purchaseCost: number | null
  deposit: number | null
  alertThreshold: number | null
  cleaningDays: number | null
  isActive: boolean
}
const form = ref<Form>(blank())
const errors = ref<Record<string, string>>({})
const FIELDS = [
  'reference',
  'name',
  'category',
  'description',
  'location',
  'tracking',
  'initialQuantity',
  'serials',
  'rentPrice',
  'rentUnit',
  'salePrice',
  'purchaseCost',
  'deposit',
  'alertThreshold',
  'cleaningDays',
] as const

function blank(): Form {
  return {
    reference: '',
    name: '',
    category: '',
    description: '',
    location: '',
    tracking: 'quantity',
    initialQuantity: 0,
    serials: '',
    rentPrice: 0,
    rentUnit: 'event',
    salePrice: null,
    purchaseCost: 0,
    deposit: 0,
    alertThreshold: 0,
    cleaningDays: null,
    isActive: true,
  }
}

watch(open, (isOpen) => {
  if (!isOpen) return
  errors.value = {}
  const i = props.item
  form.value = i
    ? {
        reference: i.reference,
        name: i.name,
        category: i.category,
        description: i.description,
        location: i.location,
        tracking: i.tracking,
        initialQuantity: null,
        serials: '',
        rentPrice: i.rentPrice,
        rentUnit: i.rentUnit,
        salePrice: i.salePrice,
        purchaseCost: i.purchaseCost,
        deposit: i.deposit,
        alertThreshold: i.alertThreshold,
        cleaningDays: i.cleaningDays,
        isActive: i.isActive,
      }
    : blank()
})

const categoryOptions = computed(() =>
  (categories.data.value ?? []).map((c) => ({ value: c.id, label: c.name })),
)
const categoryDelay = computed(
  () => categories.data.value?.find((c) => c.id === form.value.category)?.cleaningDays ?? 0,
)
const trackingOptions = computed(() =>
  (['quantity', 'unit'] as const).map((value) => ({
    value,
    label: t(`stock.tracking.${value}`),
  })),
)
const rentUnitOptions = computed(() =>
  (['event', 'day'] as const).map((value) => ({ value, label: t(`stock.rentUnits.${value}`) })),
)
const save = useStockMutation((input: ItemInput) =>
  props.item ? stockApi.updateItem(props.item.id, input) : stockApi.createItem(input),
)

const number = (value: number | null) => (typeof value === 'number' && !isNaN(value) ? value : 0)

async function submit(): Promise<void> {
  errors.value = {}
  const f = form.value
  if (!f.name.trim()) errors.value.name = t('stock.form.nameRequired')
  if (!f.category) errors.value.category = t('stock.form.categoryRequired')
  if (Object.keys(errors.value).length) return
  const input: ItemInput = {
    reference: f.reference.trim(),
    name: f.name.trim(),
    category: f.category,
    description: f.description,
    location: f.location,
    tracking: f.tracking,
    rentUnit: f.rentUnit,
    alertThreshold: number(f.alertThreshold),
    cleaningDays:
      typeof f.cleaningDays === 'number' && !isNaN(f.cleaningDays) ? f.cleaningDays : null,
    isActive: f.isActive,
  }
  if (can('viewStockPrices')) {
    input.rentPrice = number(f.rentPrice)
    input.salePrice = typeof f.salePrice === 'number' && !isNaN(f.salePrice) ? f.salePrice : null
    input.deposit = number(f.deposit)
  }
  if (can('viewStockCosts')) input.purchaseCost = number(f.purchaseCost)
  if (!props.item) {
    input.initialQuantity = number(f.initialQuantity)
    const serials = f.serials
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    if (serials.length) input.serials = serials
  }
  try {
    const saved = await save.mutateAsync(input)
    toast.success(
      isEdit.value ? t('stock.form.saved') : t('stock.form.created', { name: saved.name }),
    )
    emit('saved', saved)
    open.value = false
  } catch (error) {
    applyServerErrors(error, (field, message) => (errors.value[field] = message), FIELDS)
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="isEdit ? t('stock.form.editTitle') : t('stock.form.createTitle')"
    size="lg"
  >
    <form id="item-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
      <WInput
        v-model="form.name"
        class="sm:col-span-2"
        :label="t('stock.fields.name')"
        :error="errors.name"
        required
        autofocus
      />
      <WSelect
        v-model="form.category"
        :label="t('stock.fields.category')"
        :options="categoryOptions"
        :placeholder="t('stock.fields.category')"
        :error="errors.category"
        required
      />
      <WInput
        v-model="form.reference"
        :label="t('stock.fields.reference')"
        :hint="t('stock.fields.referenceHint')"
        :error="errors.reference"
        maxlength="32"
      />
      <WSelect
        v-model="form.tracking"
        :label="t('stock.fields.tracking')"
        :options="trackingOptions"
        :error="errors.tracking"
        :disabled="isEdit && (item?.totalQuantity ?? 0) > 0"
      />
      <WInput
        v-if="!isEdit"
        v-model.number="form.initialQuantity"
        :label="t('stock.fields.initialQuantity')"
        :error="errors.initialQuantity"
        type="number"
        min="0"
        inputmode="numeric"
      />
      <WTextarea
        v-if="!isEdit && form.tracking === 'unit'"
        v-model="form.serials"
        class="sm:col-span-2"
        :label="t('stock.fields.serials')"
        :error="errors.serials"
        :rows="3"
      />
      <template v-if="can('viewStockPrices')">
        <WInput
          v-model.number="form.rentPrice"
          :label="t('stock.fields.rentPrice')"
          :error="errors.rentPrice"
          type="number"
          min="0"
          step="500"
          inputmode="numeric"
        />
        <WSelect
          v-model="form.rentUnit"
          :label="t('stock.fields.rentUnit')"
          :options="rentUnitOptions"
        />
        <WInput
          v-model.number="form.salePrice"
          :label="t('stock.fields.salePrice')"
          :error="errors.salePrice"
          type="number"
          min="0"
          step="500"
          inputmode="numeric"
        />
        <WInput
          v-model.number="form.deposit"
          :label="t('stock.fields.deposit')"
          :error="errors.deposit"
          type="number"
          min="0"
          step="500"
          inputmode="numeric"
        />
      </template>
      <WInput
        v-if="can('viewStockCosts')"
        v-model.number="form.purchaseCost"
        :label="t('stock.fields.purchaseCost')"
        :error="errors.purchaseCost"
        type="number"
        min="0"
        step="500"
        inputmode="numeric"
      />
      <WInput
        v-model.number="form.alertThreshold"
        :label="t('stock.fields.alertThreshold')"
        :hint="t('stock.fields.alertThresholdHint')"
        :error="errors.alertThreshold"
        type="number"
        min="0"
        inputmode="numeric"
      />
      <WInput
        v-model.number="form.cleaningDays"
        :label="t('stock.fields.cleaningDays')"
        :hint="t('stock.fields.cleaningDaysHint', { days: categoryDelay })"
        :error="errors.cleaningDays"
        type="number"
        min="0"
        inputmode="numeric"
      />
      <WInput
        v-model="form.location"
        :label="t('stock.fields.location')"
        :error="errors.location"
      />
      <WTextarea
        v-model="form.description"
        class="sm:col-span-2"
        :label="t('stock.fields.description')"
        :rows="2"
      />
      <WSwitch v-if="isEdit" v-model="form.isActive" :label="t('stock.fields.isActive')" />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="item-form" :loading="save.isPending.value">
        {{ isEdit ? t('stock.form.save') : t('stock.form.create') }}
      </WButton>
    </template>
  </WModal>
</template>
