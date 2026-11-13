<script setup lang="ts">
import { ArrowLeftRight } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import DownloadMenu from '@/components/DownloadMenu.vue'
import { toApiError } from '@/api/errors'
import { formatDateTime } from '@/composables/useDate'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import {
  type TableColumn,
  WButton,
  WCard,
  WEmptyState,
  WInput,
  WModal,
  WSelect,
  WTable,
} from '@/design'

import { stockApi, useMovements, useStockMutation } from '../api'
import MovementModal from '../components/MovementModal.vue'
import type { Movement, MovementKind } from '../types'

/** « Mouvements » (reservations-stock.md §5.3): immutable journal, cancelled with a reason. */
const { t } = useI18n()
const toast = useToast()
const { can } = usePermissions()

const KINDS: MovementKind[] = [
  'purchase',
  'checkout',
  'return',
  'sale',
  'breakage',
  'loss',
  'maintenance_out',
  'maintenance_in',
  'adjustment',
]
const kind = ref('')
const from = ref('')
const to = ref('')
const movements = useMovements(() => ({ kind: kind.value, from: from.value, to: to.value }))
const rows = computed(() => movements.data.value?.results ?? [])
const kindOptions = computed(() => [
  { value: '', label: t('stock.movements.allKinds') },
  ...KINDS.map((value) => ({ value, label: t(`stock.movement.kinds.${value}`) })),
])
const columns = computed<TableColumn[]>(() => [
  { key: 'occurredAt', label: t('stock.movements.columns.date') },
  { key: 'itemName', label: t('stock.movements.columns.item') },
  { key: 'kind', label: t('stock.movements.columns.kind') },
  { key: 'quantity', label: t('stock.movements.columns.quantity'), align: 'right' },
  { key: 'reason', label: t('stock.movements.columns.reason') },
  { key: 'authorName', label: t('stock.movements.columns.author') },
  ...(can('editStock') ? [{ key: 'actions', label: '' }] : []),
])
const row = (value: unknown) => value as Movement
const MANUAL = ['purchase', 'sale', 'breakage', 'loss', 'adjustment']

const createOpen = ref(false)
const cancelling = ref<Movement | null>(null)
const reason = ref('')
const reasonError = ref<string>()
const cancel = useStockMutation(({ id, reason }: { id: string; reason: string }) =>
  stockApi.cancelMovement(id, reason),
)
function askCancel(movement: Movement): void {
  cancelling.value = movement
  reason.value = ''
  reasonError.value = undefined
}
async function confirmCancel(): Promise<void> {
  if (!cancelling.value) return
  if (!reason.value.trim()) {
    reasonError.value = t('stock.movements.reasonRequired')
    return
  }
  try {
    await cancel.mutateAsync({ id: cancelling.value.id, reason: reason.value })
    cancelling.value = null
    toast.success(t('stock.movements.cancelDone'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const cancelOpen = computed({
  get: () => cancelling.value !== null,
  set: (value) => {
    if (!value) cancelling.value = null
  },
})
</script>

<template>
  <div class="flex flex-col gap-[22px]">
    <header class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0 flex-1">
        <h1>{{ t('stock.movements.title') }}</h1>
        <p class="mt-1 max-w-[70ch] text-muted">{{ t('stock.movements.subtitle') }}</p>
      </div>
      <DownloadMenu url="/exports/movements" filename="mouvements" />
      <WButton v-if="can('editStock')" @click="createOpen = true">
        <ArrowLeftRight class="size-[18px]" aria-hidden="true" />{{ t('stock.addMovement') }}
      </WButton>
    </header>

    <div class="flex flex-wrap items-end gap-3">
      <WSelect
        v-model="kind"
        class="w-[230px]"
        :label="t('stock.movement.kind')"
        :options="kindOptions"
      />
      <WInput v-model="from" type="date" :label="t('stock.movements.from')" class="w-[170px]" />
      <WInput v-model="to" type="date" :label="t('stock.movements.to')" class="w-[170px]" />
    </div>

    <WCard>
      <WEmptyState
        v-if="movements.isError.value"
        :title="t('stock.loadError')"
        :description="toApiError(movements.error.value).message"
      />
      <WTable
        v-else
        :columns="columns"
        :rows="rows as unknown as Record<string, unknown>[]"
        row-key="id"
        :caption="t('stock.movements.title')"
        :loading="movements.isPending.value"
      >
        <template #empty>
          <WEmptyState :icon="ArrowLeftRight" :title="t('stock.movements.empty')" />
        </template>
        <template #cell-occurredAt="{ row: r }">
          <span :class="row(r).cancelledAt && 'text-muted line-through'">{{
            formatDateTime(row(r).occurredAt)
          }}</span>
        </template>
        <template #cell-itemName="{ row: r }">
          <span class="block font-bold" :class="row(r).cancelledAt && 'text-muted line-through'">{{
            row(r).itemName
          }}</span>
          <span class="text-[12px] text-muted"
            >{{ row(r).itemReference
            }}<template v-if="row(r).serialNumber"> · {{ row(r).serialNumber }}</template></span
          >
        </template>
        <template #cell-kind="{ row: r }">{{ t(`stock.movement.kinds.${row(r).kind}`) }}</template>
        <template #cell-quantity="{ row: r }">
          <span
            class="num font-bold"
            :class="[
              row(r).cancelledAt ? 'text-muted line-through' : '',
              row(r).delta > 0 ? 'text-green' : row(r).delta < 0 ? 'text-coral' : '',
            ]"
            >{{ row(r).delta > 0 ? '+' : row(r).delta < 0 ? '−' : '' }}{{ row(r).quantity }}</span
          >
        </template>
        <template #cell-reason="{ row: r }">
          <span v-if="row(r).cancelledAt" class="text-[12.5px] font-semibold text-coral">{{
            t('stock.movements.cancelled', { reason: row(r).cancelReason })
          }}</span>
          <span v-else>{{ row(r).reason || '—' }}</span>
        </template>
        <template #cell-authorName="{ row: r }">{{ row(r).authorName ?? '—' }}</template>
        <template #cell-actions="{ row: r }">
          <WButton
            v-if="!row(r).cancelledAt && MANUAL.includes(row(r).kind)"
            size="sm"
            variant="ghost"
            @click="askCancel(row(r))"
            >{{ t('stock.movements.cancel') }}</WButton
          >
        </template>
      </WTable>
    </WCard>

    <MovementModal v-model:open="createOpen" />
    <WModal v-model:open="cancelOpen" :title="t('stock.movements.cancelTitle')" size="sm">
      <p class="mb-3 text-ink-2">{{ t('stock.movements.cancelText') }}</p>
      <WInput
        v-model="reason"
        :label="t('stock.movements.cancelReason')"
        :error="reasonError"
        required
      />
      <template #footer>
        <WButton variant="secondary" @click="cancelling = null">{{ t('common.cancel') }}</WButton>
        <WButton variant="danger" :loading="cancel.isPending.value" @click="confirmCancel">{{
          t('stock.movements.cancelSave')
        }}</WButton>
      </template>
    </WModal>
  </div>
</template>
