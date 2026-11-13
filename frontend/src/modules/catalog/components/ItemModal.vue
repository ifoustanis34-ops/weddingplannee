<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect, WSwitch, WTextarea } from '@/design'

import { catalogApi, useCatalogMutation } from '../api'
import {
  SERVICE_ICONS,
  type ServiceCategory,
  type ServiceItem,
  type ServiceItemInput,
  UNITS,
} from '../types'

const props = defineProps<{
  item: ServiceItem | null
  categories: ServiceCategory[]
  categoryId?: string
}>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()

const form = ref<ServiceItemInput>({
  category: '',
  name: '',
  description: '',
  unit: 'flat',
  unitPrice: 0,
  isActive: true,
  quantityRule: 'one',
  isDefault: false,
  icon: '',
})
const errors = ref<Record<string, string | undefined>>({})

watch(open, (isOpen) => {
  if (!isOpen) return
  errors.value = {}
  const item = props.item
  form.value = item
    ? {
        category: item.category,
        name: item.name,
        description: item.description,
        unit: item.unit,
        unitPrice: item.unitPrice,
        isActive: item.isActive,
        quantityRule: item.quantityRule,
        isDefault: item.isDefault,
        icon: item.icon,
      }
    : {
        category: props.categoryId ?? props.categories[0]?.id ?? '',
        name: '',
        description: '',
        unit: 'flat',
        unitPrice: 0,
        isActive: true,
        quantityRule: 'one',
        isDefault: false,
        icon: '',
      }
})

const save = useCatalogMutation((input: ServiceItemInput) =>
  props.item ? catalogApi.updateItem(props.item.id, input) : catalogApi.createItem(input),
)
const categoryOptions = computed(() =>
  props.categories.map((c) => ({ value: c.id, label: c.name })),
)
const unitOptions = computed(() => UNITS.map((u) => ({ value: u, label: t(`catalog.units.${u}`) })))
const iconOptions = computed(() => [
  { value: '', label: t('catalog.icons.auto') },
  ...SERVICE_ICONS.map((icon) => ({ value: icon, label: t(`catalog.icons.${icon}`) })),
])
const ruleOptions = computed(() =>
  (['one', 'per_guest', 'per_ten_guests'] as const).map((rule) => ({
    value: rule,
    label: t(`catalog.rules.${rule}`),
  })),
)

async function submit(): Promise<void> {
  errors.value = {}
  if (!form.value.name.trim()) errors.value.name = t('validation.required')
  if (!Number.isInteger(form.value.unitPrice) || form.value.unitPrice < 0)
    errors.value.unitPrice = t('catalog.priceInvalid')
  if (Object.values(errors.value).some(Boolean)) return
  try {
    await save.mutateAsync({ ...form.value, name: form.value.name.trim() })
    toast.success(props.item ? t('catalog.itemSaved') : t('catalog.itemCreated'))
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="item ? t('catalog.editItem') : t('catalog.addItem')">
    <form id="item-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
      <WInput
        v-model="form.name"
        class="sm:col-span-2"
        :label="t('catalog.fields.name')"
        :error="errors.name"
        required
        autofocus
      />
      <WSelect
        v-model="form.category"
        :label="t('catalog.fields.category')"
        :options="categoryOptions"
        :error="errors.category"
        required
      />
      <WSelect
        v-model="form.unit"
        :label="t('catalog.fields.unit')"
        :options="unitOptions"
        :hint="form.unit === 'guest' ? t('catalog.guestHint') : undefined"
      />
      <WInput
        v-model.number="form.unitPrice"
        :label="t('catalog.fields.unitPrice')"
        :error="errors.unitPrice"
        type="number"
        inputmode="numeric"
        min="0"
        step="500"
        required
      />
      <div class="flex items-end pb-2">
        <WSwitch v-model="form.isActive" :label="t('catalog.fields.isActive')" />
      </div>
      <WSelect
        v-if="form.unit !== 'guest'"
        v-model="form.quantityRule"
        :label="t('catalog.fields.quantityRule')"
        :options="ruleOptions"
      />
      <div class="flex items-end pb-2">
        <WSwitch
          v-model="form.isDefault"
          :label="t('catalog.fields.isDefault')"
          :description="t('catalog.fields.isDefaultHint')"
        />
      </div>
      <WSelect
        v-model="form.icon"
        :label="t('catalog.fields.icon')"
        :hint="t('catalog.fields.iconHint')"
        :options="iconOptions"
        :error="errors.icon"
      />
      <WTextarea
        v-model="form.description"
        class="sm:col-span-2"
        :label="t('catalog.fields.description')"
        :rows="2"
      />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="item-form" :loading="save.isPending.value">{{
        t('catalog.save')
      }}</WButton>
    </template>
  </WModal>
</template>
