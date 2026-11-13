<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePermissions } from '@/composables/usePermissions'
import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect, WTextarea } from '@/design'

import { stockApi, useItemActivity, useItems, useStockMutation } from '../api'
import type { ManualKind, MovementInput } from '../types'

/**
 * Manual movement (reservations-stock.md §5.3): purchase, sale, breakage, loss, adjustment.
 * Checkouts and returns come from the reservations (S4), maintenance from its own form.
 */
const props = defineProps<{ itemId?: string | null }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const applyServerErrors = useServerErrors()
const { can } = usePermissions()
const items = useItems({})

const KINDS: ManualKind[] = ['purchase', 'sale', 'breakage', 'loss', 'adjustment']
const item = ref('')
const kind = ref<ManualKind>('purchase')
const quantity = ref<number | null>(1)
const unit = ref('')
const direction = ref<'1' | '-1'>('1')
const unitCost = ref<number | null>(null)
const serials = ref('')
const reason = ref('')
const reference = ref('')
const errors = ref<Record<string, string>>({})
const FIELDS = ['item', 'kind', 'quantity', 'unit', 'unitCost', 'serials', 'reason', 'reference']

watch(open, (isOpen) => {
  if (!isOpen) return
  item.value = props.itemId ?? ''
  kind.value = 'purchase'
  quantity.value = 1
  unit.value = ''
  direction.value = '1'
  unitCost.value = null
  serials.value = ''
  reason.value = ''
  reference.value = ''
  errors.value = {}
})

const selected = computed(() => items.data.value?.find((i) => i.id === item.value))
const tracked = computed(() => selected.value?.tracking === 'unit')
const activity = useItemActivity(() => (open.value && tracked.value ? item.value : null))
const needsUnit = computed(() => tracked.value && kind.value !== 'purchase')
const kindOptions = computed(() =>
  KINDS.filter((k) => !(tracked.value && k === 'adjustment')).map((value) => ({
    value,
    label: t(`stock.movement.kinds.${value}`),
  })),
)
const itemOptions = computed(() =>
  (items.data.value ?? []).map((i) => ({ value: i.id, label: `${i.name} (${i.reference})` })),
)
const unitOptions = computed(() =>
  (activity.data.value?.units ?? [])
    .filter((u) => u.status === 'available' || u.status === 'out_of_service')
    .map((u) => ({
      value: u.id,
      label: `${u.serialNumber} · ${t(`stock.unitStatus.${u.status}`)}`,
    })),
)
watch(needsUnit, (value) => {
  if (value) quantity.value = 1
})

const save = useStockMutation(stockApi.recordMovement)

async function submit(): Promise<void> {
  errors.value = {}
  if (!item.value) errors.value.item = t('stock.movement.chooseItem')
  if (!quantity.value || quantity.value < 1)
    errors.value.quantity = t('stock.movement.quantityRequired')
  if (needsUnit.value && !unit.value) errors.value.unit = t('stock.movement.chooseUnit')
  if (Object.keys(errors.value).length) return
  const input: MovementInput = {
    item: item.value,
    kind: kind.value,
    quantity: quantity.value!,
    direction: direction.value === '1' ? 1 : -1,
    unit: needsUnit.value ? unit.value : null,
    reason: reason.value,
    reference: reference.value,
  }
  if (kind.value === 'purchase' && can('viewStockCosts') && unitCost.value)
    input.unitCost = unitCost.value
  const list = serials.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  if (kind.value === 'purchase' && tracked.value && list.length) input.serials = list
  try {
    const movement = await save.mutateAsync(input)
    toast.success(
      t('stock.movement.saved', {
        kind: t(`stock.movement.kinds.${movement.kind}`),
        name: movement.itemName,
        quantity: movement.quantity,
      }),
    )
    open.value = false
  } catch (error) {
    applyServerErrors(error, (field, message) => (errors.value[field] = message), FIELDS)
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="t('stock.movement.title')" size="md">
    <form id="movement-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
      <WSelect
        v-model="item"
        class="sm:col-span-2"
        :label="t('stock.movement.item')"
        :options="itemOptions"
        :placeholder="t('stock.movement.chooseItem')"
        :error="errors.item"
        required
      />
      <WSelect
        v-model="kind"
        :label="t('stock.movement.kind')"
        :options="kindOptions"
        :error="errors.kind"
      />
      <WSelect
        v-if="kind === 'adjustment'"
        v-model="direction"
        :label="t('stock.movement.direction')"
        :options="[
          { value: '1', label: t('stock.movement.add') },
          { value: '-1', label: t('stock.movement.remove') },
        ]"
      />
      <WSelect
        v-if="needsUnit"
        v-model="unit"
        :label="t('stock.movement.unit')"
        :options="unitOptions"
        :placeholder="t('stock.movement.chooseUnit')"
        :error="errors.unit"
        required
      />
      <WInput
        v-else
        v-model.number="quantity"
        :label="t('stock.movement.quantity')"
        :error="errors.quantity"
        type="number"
        min="1"
        inputmode="numeric"
        required
      />
      <WInput
        v-if="kind === 'purchase' && can('viewStockCosts')"
        v-model.number="unitCost"
        :label="t('stock.movement.unitCost')"
        :hint="t('stock.movement.unitCostHint')"
        :error="errors.unitCost"
        type="number"
        min="0"
        step="500"
        inputmode="numeric"
      />
      <WTextarea
        v-if="kind === 'purchase' && tracked"
        v-model="serials"
        class="sm:col-span-2"
        :label="t('stock.movement.serials')"
        :error="errors.serials"
        :rows="3"
      />
      <WInput
        v-model="reason"
        class="sm:col-span-2"
        :label="t('stock.movement.reason')"
        :error="errors.reason"
      />
      <WInput
        v-model="reference"
        class="sm:col-span-2"
        :label="t('stock.movement.reference')"
        :error="errors.reference"
      />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="movement-form" :loading="save.isPending.value">{{
        t('stock.movement.save')
      }}</WButton>
    </template>
  </WModal>
</template>
