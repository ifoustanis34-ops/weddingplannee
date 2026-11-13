<script setup lang="ts">
import { Plus, Trash2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatMoney } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal } from '@/design'

import { financeApi, useFinanceAction } from '../api'
import type { ContractDetail } from '../types'

const props = defineProps<{ contract: ContractDetail | null }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const rows = ref<{ label: string; amount: number; dueDate: string }[]>([])
const error = ref<string | null>(null)

watch(open, (isOpen) => {
  if (isOpen && props.contract) {
    rows.value = props.contract.schedule.map((s) => ({
      label: s.label,
      amount: s.amount,
      dueDate: s.dueDate,
    }))
    error.value = null
  }
})

const sum = computed(() => rows.value.reduce((total, row) => total + (Number(row.amount) || 0), 0))
const difference = computed(() => (props.contract?.total ?? 0) - sum.value)
const save = useFinanceAction((input: { id: string; rows: typeof rows.value }) =>
  financeApi.updateSchedule(input.id, input.rows),
)

function add(): void {
  rows.value.push({
    label: t('finance.schedule.installment'),
    amount: Math.max(difference.value, 0),
    dueDate: new Date().toISOString().slice(0, 10),
  })
}

async function submit(): Promise<void> {
  if (!props.contract) return
  if (difference.value !== 0) {
    error.value = t('finance.schedule.mismatch', {
      amount: formatMoney(Math.abs(difference.value)),
      direction: difference.value > 0 ? t('finance.schedule.missing') : t('finance.schedule.extra'),
    })
    return
  }
  try {
    await save.mutateAsync({
      id: props.contract.id,
      rows: rows.value.map((r) => ({ ...r, amount: Number(r.amount) })),
    })
    toast.success(t('finance.schedule.saved'))
    open.value = false
  } catch (failure) {
    error.value = toApiError(failure).message
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="t('finance.schedule.edit')"
    :description="t('finance.schedule.editHint')"
    size="lg"
  >
    <form id="schedule-form" class="flex flex-col gap-3" @submit.prevent="submit">
      <div
        v-for="(row, index) in rows"
        :key="index"
        class="grid grid-cols-[1.4fr_1fr_1fr_auto] items-end gap-2"
      >
        <WInput v-model="row.label" :label="t('finance.schedule.label')" :hide-label="index > 0" />
        <WInput
          v-model.number="row.amount"
          :label="t('finance.schedule.amount')"
          :hide-label="index > 0"
          type="number"
          min="1"
        />
        <WInput
          v-model="row.dueDate"
          :label="t('finance.schedule.dueDate')"
          :hide-label="index > 0"
          type="date"
        />
        <WButton
          variant="ghost"
          size="sm"
          class="mb-1"
          :disabled="rows.length === 1"
          :aria-label="t('common.delete')"
          @click="rows.splice(index, 1)"
        >
          <Trash2 class="size-4" aria-hidden="true" />
        </WButton>
      </div>
      <WButton variant="ghost" size="sm" class="self-start" @click="add"
        ><Plus class="size-4" aria-hidden="true" />{{ t('finance.schedule.add') }}</WButton
      >
      <p class="tabular text-[13.5px]" :class="difference === 0 ? 'text-green' : 'text-coral'">
        {{
          t('finance.schedule.total', {
            sum: formatMoney(sum),
            total: formatMoney(contract?.total ?? 0),
          })
        }}
      </p>
      <p v-if="error" class="text-[13px] font-semibold text-red" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="schedule-form" :loading="save.isPending.value">{{
        t('finance.schedule.save')
      }}</WButton>
    </template>
  </WModal>
</template>
