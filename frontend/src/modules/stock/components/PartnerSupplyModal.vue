<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import { WButton, WChips, WInput, WModal, WSelect, WSwitch, WTextarea } from '@/design'
import { useVendors } from '@/modules/vendors/api'

import { stockApi, stockKeys, useItemCategories, useItems } from '../api'
import type { PartnerSupply, PartnerSupplyInput } from '../types'

/**
 * What a partner can lend (feedback 14/11/2026): an item of our stock, or a new one we do not
 * own. With `supply`, edits it (quantity, price, notes, on / off).
 */
const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ supply?: PartnerSupply | null; vendorId?: string | null }>()
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()
const queryClient = useQueryClient()
const seesCosts = computed(() => can('viewMargins'))

const vendors = useVendors()
const partnerOptions = computed(() =>
  [...(vendors.data.value ?? [])]
    .sort((a, b) => Number(b.kind === 'partner') - Number(a.kind === 'partner'))
    .map((v) => ({ value: v.id, label: v.name })),
)
const items = useItems(() => ({}))
const itemOptions = computed(() =>
  (items.data.value ?? []).map((i) => ({ value: i.id, label: `${i.name} (${i.reference})` })),
)
const categories = useItemCategories()
const categoryOptions = computed(() =>
  (categories.data.value ?? []).map((c) => ({ value: c.id, label: c.name })),
)

const mode = ref<'existing' | 'new'>('existing')
const form = ref({
  vendor: '',
  item: '',
  newItemName: '',
  newItemCategory: '',
  newItemRentPrice: 0,
  quantity: 0,
  unitCost: 0,
  notes: '',
  isActive: true,
})
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)

watch(open, (isOpen) => {
  if (!isOpen) return
  const s = props.supply
  mode.value = 'existing'
  errors.value = {}
  form.value = {
    vendor: s?.vendor ?? props.vendorId ?? '',
    item: s?.item ?? '',
    newItemName: '',
    newItemCategory: categories.data.value?.[0]?.id ?? '',
    newItemRentPrice: 0,
    quantity: s?.quantity ?? 0,
    unitCost: s?.unitCost ?? 0,
    notes: s?.notes ?? '',
    isActive: s?.isActive ?? true,
  }
})

async function submit(): Promise<void> {
  errors.value = {}
  const f = form.value
  if (!props.supply) {
    if (!f.vendor) errors.value.vendor = t('validation.required')
    if (mode.value === 'existing' && !f.item) errors.value.item = t('validation.required')
    if (mode.value === 'new' && !f.newItemName.trim())
      errors.value.newItemName = t('validation.required')
  }
  if (!(f.quantity >= 0)) errors.value.quantity = t('validation.required')
  if (Object.keys(errors.value).length) return
  saving.value = true
  try {
    const common: Partial<PartnerSupplyInput> = {
      quantity: f.quantity,
      notes: f.notes.trim(),
      isActive: f.isActive,
      ...(seesCosts.value ? { unitCost: f.unitCost || 0 } : {}),
    }
    if (props.supply) {
      await stockApi.updatePartnerSupply(props.supply.id, common)
    } else {
      await stockApi.createPartnerSupply({
        ...common,
        vendor: f.vendor,
        quantity: f.quantity,
        ...(mode.value === 'existing'
          ? { item: f.item }
          : {
              newItemName: f.newItemName.trim(),
              newItemCategory: f.newItemCategory,
              newItemRentPrice: f.newItemRentPrice || 0,
            }),
      })
    }
    void queryClient.invalidateQueries({ queryKey: stockKeys.all })
    toast.success(t('stock.partners.saved'))
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(
      Object.entries(apiError.fields).map(([key, messages]) => [key, messages[0]]),
    )
    toast.error(apiError.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="supply ? `${supply.itemName} · ${supply.vendorName}` : t('stock.partners.form.title')"
  >
    <form id="partner-supply-form" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <template v-if="!supply">
        <WSelect
          v-model="form.vendor"
          :label="t('stock.partners.form.partner')"
          :options="partnerOptions"
          :placeholder="t('stock.partners.form.partner')"
          :hint="
            partnerOptions.length
              ? t('stock.partners.form.partnerHint')
              : t('stock.partners.form.noPartner')
          "
          :error="errors.vendor"
          required
        />
        <WChips
          v-model="mode"
          :label="t('stock.partners.form.item')"
          :options="[
            { value: 'existing', label: t('stock.partners.form.existing') },
            { value: 'new', label: t('stock.partners.form.newItem') },
          ]"
        />
        <WSelect
          v-if="mode === 'existing'"
          v-model="form.item"
          :label="t('stock.partners.form.item')"
          :options="itemOptions"
          :placeholder="t('stock.partners.form.item')"
          :error="errors.item"
          required
        />
        <template v-else>
          <WInput
            v-model="form.newItemName"
            :label="t('stock.partners.form.newName')"
            :error="errors.newItemName"
            required
          />
          <div class="grid gap-4 sm:grid-cols-2">
            <WSelect
              v-model="form.newItemCategory"
              :label="t('stock.partners.form.category')"
              :options="categoryOptions"
              :error="errors.newItemCategory"
            />
            <WInput
              v-model.number="form.newItemRentPrice"
              type="number"
              min="0"
              inputmode="numeric"
              :label="t('stock.partners.form.rentPrice')"
            />
          </div>
        </template>
      </template>
      <div class="grid gap-4 sm:grid-cols-2">
        <WInput
          v-model.number="form.quantity"
          type="number"
          min="0"
          inputmode="numeric"
          :label="t('stock.partners.form.quantity')"
          :error="errors.quantity"
          required
        />
        <WInput
          v-if="seesCosts"
          v-model.number="form.unitCost"
          type="number"
          min="0"
          inputmode="numeric"
          :label="t('stock.partners.form.unitCost')"
          :error="errors.unitCost"
        />
      </div>
      <WTextarea v-model="form.notes" :rows="2" :label="t('stock.partners.form.notes')" />
      <WSwitch v-if="supply" v-model="form.isActive" :label="t('stock.partners.form.active')" />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="partner-supply-form" :loading="saving">{{
        t('platform.common.save')
      }}</WButton>
    </template>
  </WModal>
</template>
