<script setup lang="ts">
import { FileDown, Plus, Trash2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatMoney } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect } from '@/design'

import { type PayItem, type PayLine, type PayMode, staffApi, useStaffMutation } from '../api'

/**
 * One person's pay for the period (feedback 24/11/2026): the salary itself (set it here, no need
 * to open the staff record), the named lines (bonuses, allowances, overtime, advances, loans,
 * absences), what is withheld and the net; then the « Bulletin de paie ».
 */
const props = defineProps<{ line: PayLine | null; draft: boolean }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const toast = useToast()

const open = computed({
  get: () => props.line !== null,
  set: (value) => {
    if (!value) emit('close')
  },
})

const payMode = ref<PayMode>('monthly')
const payRate = ref(0)
const declared = ref(false)
const items = ref<PayItem[]>([])
watch(
  () => props.line,
  (line) => {
    if (!line) return
    payMode.value = line.payMode
    payRate.value = line.payRate
    declared.value = line.declared
    items.value = line.items.map((item) => ({ ...item }))
  },
  { immediate: true },
)
const salaryChanged = computed(
  () =>
    props.line !== null &&
    (payMode.value !== props.line.payMode ||
      Number(payRate.value) !== props.line.payRate ||
      declared.value !== props.line.declared),
)
const itemsChanged = computed(
  () => props.line !== null && JSON.stringify(items.value) !== JSON.stringify(props.line.items),
)

const PRESETS = [
  { label: 'Heures supplémentaires', kind: 'gain', taxable: true },
  { label: 'Prime de rendement', kind: 'gain', taxable: true },
  { label: 'Prime d’ancienneté', kind: 'gain', taxable: true },
  { label: 'Indemnité de transport', kind: 'gain', taxable: false },
  { label: 'Indemnité de logement', kind: 'gain', taxable: true },
  { label: 'Avance sur salaire', kind: 'deduction', taxable: false },
  { label: 'Remboursement de prêt', kind: 'deduction', taxable: false },
  { label: 'Absence non payée', kind: 'deduction', taxable: false },
] as const
function add(preset?: (typeof PRESETS)[number]): void {
  items.value.push({
    label: preset?.label ?? '',
    amount: 0,
    kind: preset?.kind ?? 'gain',
    taxable: preset?.taxable ?? true,
  })
}
const kindOptions = computed(() => [
  { value: 'gain', label: t('staff.payLine.gain') },
  { value: 'deduction', label: t('staff.payLine.deduction') },
])
const modeOptions = computed(() =>
  (['monthly', 'daily', 'mission', 'hourly'] as const).map((value) => ({
    value,
    label: t(`staff.payModes.${value}`),
  })),
)

const save = useStaffMutation(async () => {
  const line = props.line!
  if (salaryChanged.value) {
    await staffApi.setSalary(line.staff, {
      payMode: payMode.value,
      payRate: Number(payRate.value) || 0,
      declared: declared.value,
    }) // recomputes the periods still in progress
  }
  if (itemsChanged.value) {
    await staffApi.updateLine(line.id, {
      items: items.value.filter((item) => item.label.trim() && Number(item.amount) > 0),
    })
  }
})
async function submit(): Promise<void> {
  try {
    await save.mutateAsync(undefined)
    toast.success(t('staff.payLine.saved', { name: props.line!.staffName }))
    emit('close')
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const downloading = ref(false)
async function slip(): Promise<void> {
  if (!props.line) return
  downloading.value = true
  try {
    await staffApi.statement(props.line.id, props.line.staffName)
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="line ? t('staff.payLine.title', { name: line.staffName }) : ''"
    size="lg"
  >
    <div v-if="line" class="flex flex-col gap-5">
      <!-- Salary -->
      <section>
        <h3 class="text-[14px] font-semibold">{{ t('staff.payLine.salary') }}</h3>
        <p v-if="!line.payRate" class="mt-1 text-[13px] font-semibold text-coral">
          {{ t('staff.payLine.noSalary') }}
        </p>
        <div class="mt-2 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <WSelect
            v-model="payMode"
            :options="modeOptions"
            :label="t('staff.form.payMode')"
            :disabled="!draft"
          />
          <WInput
            v-model.number="payRate"
            type="number"
            min="0"
            inputmode="numeric"
            addon="FCFA"
            :label="t(`staff.form.rate.${payMode}`)"
            :disabled="!draft"
          />
          <label
            class="flex items-center gap-2 self-end pb-2.5 text-[13.5px] font-semibold text-ink-2"
          >
            <input
              v-model="declared"
              type="checkbox"
              class="size-5 accent-violet"
              :disabled="!draft"
            />
            {{ t('staff.form.declared') }}
          </label>
        </div>
      </section>

      <!-- Named lines -->
      <section>
        <h3 class="text-[14px] font-semibold">{{ t('staff.payLine.lines') }}</h3>
        <p class="mt-0.5 text-[12.5px] text-muted">{{ t('staff.payLine.linesHint') }}</p>
        <ul class="mt-2 flex flex-col gap-2">
          <li
            v-for="(item, index) in items"
            :key="index"
            class="grid grid-cols-[minmax(0,1fr)_120px] items-end gap-2 sm:grid-cols-[minmax(0,1fr)_140px_130px_auto_auto]"
          >
            <WInput
              v-model="item.label"
              :label="t('staff.payLine.label')"
              :hide-label="index > 0"
              maxlength="80"
              :disabled="!draft"
            />
            <WSelect
              v-model="item.kind"
              :options="kindOptions"
              :label="t('staff.payLine.kind')"
              :hide-label="index > 0"
              :disabled="!draft"
            />
            <WInput
              v-model.number="item.amount"
              type="number"
              min="0"
              inputmode="numeric"
              :label="t('staff.payLine.amount')"
              :hide-label="index > 0"
              :disabled="!draft"
            />
            <label
              class="flex h-10 items-center gap-1.5 text-[12.5px] text-ink-2"
              :class="item.kind === 'deduction' && 'invisible'"
            >
              <input
                v-model="item.taxable"
                type="checkbox"
                class="accent-violet"
                :disabled="!draft"
              />
              {{ t('staff.payLine.taxable') }}
            </label>
            <WButton
              v-if="draft"
              variant="ghost"
              icon
              :aria-label="t('staff.payLine.remove')"
              @click="items.splice(index, 1)"
            >
              <Trash2 class="size-[16px]" aria-hidden="true" />
            </WButton>
          </li>
        </ul>
        <div v-if="draft" class="mt-2 flex flex-wrap gap-1.5">
          <button
            v-for="preset in PRESETS"
            :key="preset.label"
            type="button"
            class="rounded-full border border-line-2 px-2.5 py-1 text-[12.5px] font-semibold hover:border-violet hover:text-violet"
            :class="preset.kind === 'deduction' ? 'text-coral' : 'text-ink-2'"
            @click="add(preset)"
          >
            + {{ preset.label }}
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-full border border-dashed border-line-2 px-2.5 py-1 text-[12.5px] font-semibold text-violet"
            @click="add()"
          >
            <Plus class="size-3.5" aria-hidden="true" />{{ t('staff.payLine.other') }}
          </button>
        </div>
      </section>

      <!-- Result (as last saved) -->
      <section class="rounded-wd bg-surface-2 p-3 text-[13.5px]">
        <h3 class="mb-2 text-[14px] font-semibold">
          {{ t('staff.payLine.result') }}
          <span
            v-if="salaryChanged || itemsChanged"
            class="ml-1 text-[12px] font-normal text-coral"
            >{{ t('staff.payLine.saveToUpdate') }}</span
          >
        </h3>
        <dl class="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
          <dt>{{ t('staff.pay.base') }}</dt>
          <dd class="num text-right">{{ formatMoney(line.base) }}</dd>
          <dt>{{ t('staff.payLine.gross') }}</dt>
          <dd class="num text-right font-semibold">{{ formatMoney(line.gross) }}</dd>
          <template v-for="c in line.slip.employee ?? []" :key="c.code">
            <dt class="text-ink-2">
              {{ c.label }} <span class="text-muted">({{ c.rate }})</span>
            </dt>
            <dd class="num text-right text-ink-2">− {{ formatMoney(c.amount) }}</dd>
          </template>
          <template v-if="line.advances">
            <dt class="text-ink-2">{{ t('staff.payLine.otherDeductions') }}</dt>
            <dd class="num text-right text-ink-2">− {{ formatMoney(line.advances) }}</dd>
          </template>
          <dt class="font-semibold">{{ t('staff.payLine.net') }}</dt>
          <dd class="num text-right font-semibold">{{ formatMoney(line.net) }}</dd>
          <template v-if="line.alreadyPaid">
            <dt class="text-ink-2">{{ t('staff.pay.alreadyPaid') }}</dt>
            <dd class="num text-right text-ink-2">− {{ formatMoney(line.alreadyPaid) }}</dd>
          </template>
          <dt class="text-[15px] font-bold">{{ t('staff.payLine.toPay') }}</dt>
          <dd class="num text-right text-[15px] font-bold">{{ formatMoney(line.total) }}</dd>
        </dl>
        <p v-if="line.slip.employerTotal" class="mt-2 text-[12.5px] text-muted">
          {{ t('staff.payLine.employer', { amount: formatMoney(line.slip.employerTotal) }) }}
        </p>
      </section>
    </div>
    <template #footer>
      <WButton variant="secondary" :loading="downloading" @click="slip">
        <FileDown class="size-4" aria-hidden="true" />{{ t('staff.payLine.slip') }}
      </WButton>
      <WButton
        v-if="draft"
        :loading="save.isPending.value"
        :disabled="!salaryChanged && !itemsChanged"
        @click="submit"
        >{{ t('staff.payLine.save') }}</WButton
      >
    </template>
  </WModal>
</template>
