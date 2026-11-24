<script setup lang="ts">
import { Banknote, CalendarDays, FileDown, Files } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { formatAmount, formatMoney } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WCard, WEmptyState, WInput, WSelect } from '@/design'
import { iso } from '@/modules/calendar/month'

import { type DaySheet, staffApi, staffKeys, useStaffMutation } from '../api'

/**
 * « Payer la journée » (feedback 13/11/2026): pick the day (and the event), the people who
 * worked come with what we owe them; tick, adjust, pay everyone at once. Each payment creates
 * its expense and is deducted from the month's pay.
 */
const { t } = useI18n()
const toast = useToast()
const day = ref(iso(new Date()))
const reservation = ref('')
const sheet = useQuery({
  queryKey: computed(() => [...staffKeys.all, 'day-sheet', day.value, reservation.value]),
  queryFn: () => staffApi.daySheet(day.value, reservation.value),
})
watch(day, () => (reservation.value = ''))

// One editable line per person: ticked when something is due. The day's amount, a bonus and a
// deduction (feedback 24/11/2026) make the « Fiche de paie journalière ».
interface Line {
  pay: boolean
  amount: number
  bonus: number
  deduction: number
  note: string
}
type Row = DaySheet['rows'][number]
const lines = ref<Record<string, Line>>({})
const blankLine = (amount: number): Line => ({
  pay: amount > 0,
  amount,
  bonus: 0,
  deduction: 0,
  note: '',
})

// Anyone of the team can be added, with or without a mission recorded that day.
const team = useQuery({
  queryKey: [...staffKeys.all, 'list', 'pay-day'],
  queryFn: () => staffApi.list({}),
})
const added = ref<string[]>([])
const addChoice = ref('')
const listed = computed(() => new Set((sheet.data.value?.rows ?? []).map((r) => r.staff)))
const addOptions = computed(() => [
  { value: '', label: t('staff.dayPay.addChoose') },
  ...(team.data.value ?? [])
    .filter((m) => m.isActive && !listed.value.has(m.id) && !added.value.includes(m.id))
    .map((m) => ({ value: m.id, label: `${m.fullName} · ${m.position}` })),
])
function addPerson(id: string): void {
  if (!id) return
  added.value.push(id)
  const member = team.data.value?.find((m) => m.id === id)
  const due = member && member.payMode === 'daily' ? (member.payRate ?? 0) : 0
  lines.value[id] = { ...blankLine(due), pay: true }
  addChoice.value = ''
}
watch(addChoice, addPerson)

const rows = computed<Row[]>(() => [
  ...(sheet.data.value?.rows ?? []),
  ...added.value.flatMap((id) => {
    const member = team.data.value?.find((m) => m.id === id)
    if (!member) return []
    return [
      {
        staff: member.id,
        name: member.fullName,
        position: member.position,
        payMode: member.payMode,
        payRate: member.payRate ?? 0,
        mobileMoney: member.mobileMoney,
        status: 'planned' as const,
        hours: 0,
        reservations: [],
        salaried: false, // added by hand: paid for this day whatever the contract
        suggested: 0,
        alreadyPaid: 0,
      },
    ]
  }),
])
watch(
  () => sheet.data.value,
  (data) => {
    added.value = []
    lines.value = Object.fromEntries(
      (data?.rows ?? []).map((row) => [row.staff, blankLine(row.suggested)]),
    )
  },
  { immediate: true },
)
const netOf = (line: Line | undefined) =>
  line
    ? Math.max(
        0,
        (Number(line.amount) || 0) + (Number(line.bonus) || 0) - (Number(line.deduction) || 0),
      )
    : 0
const selectedTotal = computed(() =>
  rows.value.reduce((sum, row) => {
    const line = lines.value[row.staff]
    return sum + (line?.pay ? netOf(line) : 0)
  }, 0),
)
const selectedCount = computed(
  () =>
    rows.value.filter((row) => lines.value[row.staff]?.pay && netOf(lines.value[row.staff]) > 0)
      .length,
)
const eventOptions = computed(() => [
  { value: '', label: t('staff.dayPay.allEvents') },
  ...(sheet.data.value?.reservations ?? []).map((r) => ({
    value: r.id,
    label: `${r.number} · ${r.title}`,
  })),
])
const method = ref('mtn_momo')
const methods = computed(() =>
  ['mtn_momo', 'orange_money', 'cash', 'transfer'].map((value) => ({
    value,
    label: t(`finance.methods.${value}`),
  })),
)
const STATUS_TONES = { present: 'green', late: 'gold', absent: 'red', planned: 'grey' } as const

const pay = useStaffMutation(() =>
  staffApi.payNow({
    date: day.value,
    reservation: reservation.value || null,
    method: method.value,
    lines: rows.value
      .filter((row) => lines.value[row.staff]?.pay)
      .map((row) => {
        const line = lines.value[row.staff]!
        return {
          staff: row.staff,
          base: Number(line.amount) || 0,
          hours: row.hours,
          items: [
            {
              label: t('staff.dayPay.bonusLabel'),
              amount: Number(line.bonus) || 0,
              kind: 'gain' as const,
            },
            {
              label: t('staff.dayPay.deductionLabel'),
              amount: Number(line.deduction) || 0,
              kind: 'deduction' as const,
            },
          ].filter((item) => item.amount > 0),
          note: line.note,
        }
      }),
  }),
)
// « Feuille de paie du jour » (15/11/2026): one PDF with everyone already paid, to sign.
const anyPaid = computed(() => rows.value.some((row) => row.alreadyPaid > 0))
const downloading = ref(false)
const downloadingSlips = ref(false)
async function downloadSlips(): Promise<void> {
  downloadingSlips.value = true
  try {
    await staffApi.daySlips(day.value, reservation.value)
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    downloadingSlips.value = false
  }
}
async function downloadSheet(): Promise<void> {
  downloading.value = true
  try {
    await staffApi.daySheetPdf(day.value, reservation.value)
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    downloading.value = false
  }
}

async function submit(): Promise<void> {
  try {
    const done = await pay.mutateAsync(undefined)
    toast.success(
      t('staff.dayPay.paid', {
        count: done.length,
        amount: formatMoney(done.reduce((sum, p) => sum + p.amount, 0)),
      }),
    )
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-end gap-3">
      <WInput v-model="day" type="date" class="w-[180px]" :label="t('staff.dayPay.day')" />
      <WSelect
        v-model="reservation"
        class="min-w-[280px]"
        :label="t('staff.dayPay.event')"
        :options="eventOptions"
      />
      <WSelect
        v-model="addChoice"
        class="min-w-[260px]"
        :label="t('staff.dayPay.add')"
        :options="addOptions"
      />
    </div>

    <WEmptyState
      v-if="sheet.isError.value"
      :title="t('staff.dayPay.loadError')"
      :description="toApiError(sheet.error.value).message"
    />
    <div v-else-if="sheet.isPending.value" class="skeleton h-64 rounded-wd-lg" />
    <WEmptyState
      v-else-if="!rows.length"
      :icon="CalendarDays"
      :title="t('staff.dayPay.nobody')"
      :description="t('staff.dayPay.nobodyAdd')"
    />
    <WCard v-else :title="t('staff.dayPay.title')" :subtitle="t('staff.dayPay.subtitle')">
      <template #actions>
        <WButton
          size="sm"
          variant="secondary"
          :disabled="!anyPaid"
          :title="anyPaid ? undefined : t('staff.dayPay.sheetHint')"
          :loading="downloadingSlips"
          @click="downloadSlips"
          ><Files class="size-[15px]" aria-hidden="true" />{{ t('staff.dayPay.slips') }}</WButton
        >
        <WButton
          size="sm"
          variant="secondary"
          :disabled="!anyPaid"
          :title="anyPaid ? undefined : t('staff.dayPay.sheetHint')"
          :loading="downloading"
          @click="downloadSheet"
          ><FileDown class="size-[15px]" aria-hidden="true" />{{ t('staff.dayPay.sheet') }}</WButton
        >
      </template>
      <ul class="-my-1 divide-y divide-line">
        <li
          v-for="row in rows"
          :key="row.staff"
          class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-2 py-3 md:grid-cols-[auto_minmax(0,1.4fr)_minmax(0,1fr)_150px_minmax(0,1fr)]"
          :class="row.salaried && 'opacity-70'"
        >
          <input
            v-model="lines[row.staff]!.pay"
            type="checkbox"
            class="size-5 accent-violet"
            :disabled="row.salaried"
            :aria-label="t('staff.dayPay.payFor', { name: row.name })"
          />
          <span class="min-w-0">
            <span class="block font-bold">{{ row.name }}</span>
            <span class="block text-[12.5px] text-muted"
              >{{ row.position }} · {{ t(`staff.payModes.${row.payMode}`) }} ·
              {{ formatAmount(row.payRate) }}</span
            >
          </span>
          <span
            class="col-span-2 flex flex-wrap items-center gap-1.5 text-[12.5px] text-ink-2 md:col-span-1"
          >
            <WBadge :tone="STATUS_TONES[row.status]">{{
              t(`staff.dayPay.status.${row.status}`)
            }}</WBadge>
            <span>{{ row.reservations.join(', ') }}</span>
            <span v-if="row.alreadyPaid" class="font-semibold text-green">{{
              t('staff.dayPay.alreadyPaid', { amount: formatAmount(row.alreadyPaid) })
            }}</span>
          </span>
          <span v-if="row.salaried" class="col-span-2 text-[12.5px] text-muted md:col-span-2">
            {{ t('staff.dayPay.salaried') }}
          </span>
          <template v-else>
            <label class="col-span-2 flex items-center gap-2 md:col-span-1">
              <input
                v-model.number="lines[row.staff]!.amount"
                type="number"
                min="0"
                step="500"
                class="num h-10 w-full rounded-[10px] border border-line-2 bg-surface px-3 text-right font-bold"
                :aria-label="t('staff.dayPay.amountFor', { name: row.name })"
              />
              <span class="text-[12.5px] text-muted">FCFA</span>
            </label>
            <span class="col-span-2 flex flex-wrap items-center gap-2 md:col-span-5 md:col-start-2">
              <label class="flex items-center gap-1.5 text-[12.5px] text-ink-2">
                {{ t('staff.dayPay.bonus') }}
                <input
                  v-model.number="lines[row.staff]!.bonus"
                  type="number"
                  min="0"
                  step="500"
                  class="num h-9 w-28 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
                  :aria-label="t('staff.dayPay.bonusFor', { name: row.name })"
                />
              </label>
              <label class="flex items-center gap-1.5 text-[12.5px] text-ink-2">
                {{ t('staff.dayPay.deduction') }}
                <input
                  v-model.number="lines[row.staff]!.deduction"
                  type="number"
                  min="0"
                  step="500"
                  class="num h-9 w-28 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
                  :aria-label="t('staff.dayPay.deductionFor', { name: row.name })"
                />
              </label>
              <span class="ml-auto text-[13px] font-semibold"
                >{{ t('staff.dayPay.net') }}
                <b class="num">{{ formatAmount(netOf(lines[row.staff])) }}</b></span
              >
            </span>
            <input
              v-model="lines[row.staff]!.note"
              class="col-span-2 h-10 rounded-[10px] border border-line-2 bg-surface px-3 text-[13.5px] md:col-span-1"
              :placeholder="
                row.mobileMoney
                  ? t('staff.dayPay.notePlaceholderMm', { number: row.mobileMoney })
                  : t('staff.dayPay.notePlaceholder')
              "
              :aria-label="t('staff.dayPay.noteFor', { name: row.name })"
              maxlength="160"
            />
          </template>
        </li>
      </ul>
      <div class="mt-4 flex flex-wrap items-center gap-3 rounded-wd bg-surface-2 p-3">
        <p class="mr-auto text-[14px]">
          {{ t('staff.dayPay.summary', { count: selectedCount }, selectedCount) }}
          <b class="num text-[16px]">{{ formatMoney(selectedTotal) }}</b>
        </p>
        <WSelect
          v-model="method"
          class="w-[190px]"
          :label="t('staff.pay.method')"
          :options="methods"
          hide-label
        />
        <WButton :loading="pay.isPending.value" :disabled="!selectedCount" @click="submit">
          <Banknote class="size-[18px]" aria-hidden="true" />{{
            t('staff.dayPay.payAll', { amount: formatMoney(selectedTotal) })
          }}
        </WButton>
      </div>
    </WCard>
  </div>
</template>
