<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePermissions } from '@/composables/usePermissions'
import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect } from '@/design'

import { stockApi, useStockMutation } from '../api'
import type { Item, ItemUnit, Maintenance } from '../types'

/**
 * Two forms in one: send equipment away for repair, or bring it back (with its cost, which
 * becomes a « Maintenance et réparation » expense for owner and accountant).
 */
const props = defineProps<{ item: Item; units: ItemUnit[]; closing?: Maintenance | null }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const applyServerErrors = useServerErrors()
const { can } = usePermissions()

const reason = ref('')
const expectedEnd = ref('')
const quantity = ref<number | null>(1)
const unit = ref('')
const cost = ref<number | null>(null)
const notes = ref('')
const errors = ref<Record<string, string>>({})
const FIELDS = ['reason', 'expectedEnd', 'quantity', 'unit', 'cost', 'notes']

watch(open, (isOpen) => {
  if (!isOpen) return
  reason.value = ''
  expectedEnd.value = ''
  quantity.value = 1
  unit.value = ''
  cost.value = null
  notes.value = ''
  errors.value = {}
})

const tracked = computed(() => props.item.tracking === 'unit')
const unitOptions = computed(() =>
  props.units
    .filter((u) => u.status === 'available' || u.status === 'out_of_service')
    .map((u) => ({
      value: u.id,
      label: `${u.serialNumber} · ${t(`stock.unitStatus.${u.status}`)}`,
    })),
)

const start = useStockMutation(stockApi.startMaintenance)
const close = useStockMutation(
  ({ id, cost, notes }: { id: string; cost: number | null; notes: string }) =>
    stockApi.closeMaintenance(id, { cost, notes }),
)

async function submit(): Promise<void> {
  errors.value = {}
  try {
    if (props.closing) {
      await close.mutateAsync({
        id: props.closing.id,
        cost: can('viewStockCosts') && cost.value ? cost.value : null,
        notes: notes.value,
      })
      toast.success(t('stock.maintenance.closed', { name: props.item.name }))
    } else {
      if (!reason.value.trim()) {
        errors.value.reason = t('stock.maintenance.reasonRequired')
        return
      }
      await start.mutateAsync({
        item: props.item.id,
        unit: tracked.value ? unit.value || null : null,
        quantity: tracked.value ? 1 : (quantity.value ?? 1),
        reason: reason.value,
        expectedEnd: expectedEnd.value || null,
      })
      toast.success(t('stock.maintenance.saved', { name: props.item.name }))
    }
    open.value = false
  } catch (error) {
    applyServerErrors(error, (field, message) => (errors.value[field] = message), FIELDS)
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="closing ? t('stock.maintenance.closeTitle') : t('stock.maintenance.title')"
    :description="item.name"
    size="sm"
  >
    <form id="maintenance-form" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <template v-if="closing">
        <WInput
          v-if="can('viewStockCosts')"
          v-model.number="cost"
          :label="t('stock.maintenance.cost')"
          :hint="t('stock.maintenance.costHint')"
          :error="errors.cost"
          type="number"
          min="0"
          step="500"
          inputmode="numeric"
        />
        <WInput v-model="notes" :label="t('stock.maintenance.notes')" :error="errors.notes" />
      </template>
      <template v-else>
        <WSelect
          v-if="tracked"
          v-model="unit"
          :label="t('stock.maintenance.unit')"
          :options="unitOptions"
          :placeholder="t('stock.movement.chooseUnit')"
          :error="errors.unit"
          required
        />
        <WInput
          v-else
          v-model.number="quantity"
          :label="t('stock.maintenance.quantity')"
          :error="errors.quantity"
          type="number"
          min="1"
          inputmode="numeric"
        />
        <WInput
          v-model="reason"
          :label="t('stock.maintenance.reason')"
          :placeholder="t('stock.maintenance.reasonPlaceholder')"
          :error="errors.reason"
          required
        />
        <WInput
          v-model="expectedEnd"
          :label="t('stock.maintenance.expectedEnd')"
          :error="errors.expectedEnd"
          type="date"
        />
      </template>
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton
        type="submit"
        form="maintenance-form"
        :loading="start.isPending.value || close.isPending.value"
        >{{ closing ? t('stock.maintenance.closeSave') : t('stock.maintenance.save') }}</WButton
      >
    </template>
  </WModal>
</template>
