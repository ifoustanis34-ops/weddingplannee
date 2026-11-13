<script setup lang="ts">
import { FileDown } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import DownloadMenu from '@/components/DownloadMenu.vue'
import { formatDate } from '@/composables/useDate'
import { formatAmount, formatMoney } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import { useSessionStore } from '@/stores/session'
import { WBadge, WButton, WCard, WEmptyState, WNote, WSelect } from '@/design'
import { iso } from '@/modules/calendar/month'

import { type PayLine, type PayPeriod, staffApi, usePayPeriods, useStaffMutation } from '../api'

/**
 * « Salaires du mois » (§7): pay periods computed from attendance, bonuses and advances; what
 * was already paid on the spot is deducted. Validation by the owner, then payment per person.
 */
const { t } = useI18n()
const toast = useToast()
const session = useSessionStore()
const isOwner = computed(() => session.role === 'owner')
const seesPay = computed(() => true)

const periods = usePayPeriods(seesPay)
const selectedId = ref<string | null>(null)
const selected = computed<PayPeriod | undefined>(
  () =>
    (periods.data.value ?? []).find((p) => p.id === selectedId.value) ?? periods.data.value?.[0],
)
const periodOptions = computed(() =>
  (periods.data.value ?? []).map((p) => ({
    value: p.id,
    label: `${formatDate(p.start)} – ${formatDate(p.end)} · ${p.statusLabel}`,
  })),
)
const createCurrent = useStaffMutation(() => {
  const now = new Date()
  const first = iso(new Date(now.getFullYear(), now.getMonth(), 1))
  const last = iso(new Date(now.getFullYear(), now.getMonth() + 1, 0))
  return staffApi.createPeriod(first, last)
})
const refresh = useStaffMutation((id: string) => staffApi.refreshPeriod(id))
const validate = useStaffMutation((id: string) => staffApi.validatePeriod(id))
const update = useStaffMutation((line: PayLine) =>
  staffApi.updateLine(line.id, { bonuses: line.bonuses, advances: line.advances }),
)
const pay = useStaffMutation(({ id, method }: { id: string; method: string }) =>
  staffApi.payLine(id, method),
)
async function attempt(promise: Promise<unknown>, message?: string): Promise<void> {
  try {
    await promise
    if (message) toast.success(message)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const methods = computed(() =>
  ['cash', 'orange_money', 'mtn_momo', 'wave', 'transfer'].map((value) => ({
    value,
    label: t(`finance.methods.${value}`),
  })),
)
const method = ref('cash')
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-end gap-3">
      <WSelect
        v-if="periodOptions.length"
        :model-value="selected?.id ?? ''"
        class="min-w-[280px]"
        :label="t('staff.pay.period')"
        :options="periodOptions"
        @update:model-value="selectedId = String($event)"
      />
      <DownloadMenu
        v-if="selected"
        class="ml-auto"
        url="/exports/pay"
        filename="paie"
        :params="{ period: selected.id }"
      />
      <WButton
        variant="secondary"
        :loading="createCurrent.isPending.value"
        @click="attempt(createCurrent.mutateAsync(undefined), t('staff.pay.created'))"
        >{{ t('staff.pay.create') }}</WButton
      >
    </div>
    <WNote>{{ t('staff.pay.legal') }}</WNote>
    <div v-if="periods.isPending.value" class="skeleton h-48" />
    <WEmptyState v-else-if="!selected" :title="t('staff.pay.none')" />
    <WCard
      v-else
      :title="`${formatDate(selected.start)} – ${formatDate(selected.end)}`"
      :subtitle="selected.statusLabel"
    >
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <p class="mr-auto text-[13.5px]">
          {{ t('staff.pay.total') }} <b class="num">{{ formatMoney(selected.total) }}</b>
        </p>
        <template v-if="selected.status === 'draft'">
          <WButton
            size="sm"
            variant="secondary"
            @click="attempt(refresh.mutateAsync(selected.id), t('staff.pay.refreshed'))"
            >{{ t('staff.pay.refresh') }}</WButton
          >
          <WButton
            v-if="isOwner"
            size="sm"
            @click="attempt(validate.mutateAsync(selected.id), t('staff.pay.validated'))"
            >{{ t('staff.pay.validate') }}</WButton
          >
        </template>
        <WSelect
          v-else-if="selected.status === 'validated'"
          v-model="method"
          class="w-[180px]"
          :label="t('staff.pay.method')"
          :options="methods"
          hide-label
        />
      </div>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[820px] border-collapse text-[13px]">
          <caption class="sr-only">
            {{
              t('staff.pay.period')
            }}
          </caption>
          <thead>
            <tr class="border-b border-line text-left text-[12px] text-muted">
              <th class="px-2 py-2">{{ t('staff.pay.person') }}</th>
              <th class="px-2 py-2 text-right">{{ t('staff.pay.worked') }}</th>
              <th class="px-2 py-2 text-right">{{ t('staff.pay.base') }}</th>
              <th class="px-2 py-2 text-right">{{ t('staff.pay.bonuses') }}</th>
              <th class="px-2 py-2 text-right">{{ t('staff.pay.advances') }}</th>
              <th class="px-2 py-2 text-right">{{ t('staff.pay.alreadyPaid') }}</th>
              <th class="px-2 py-2 text-right">{{ t('staff.pay.net') }}</th>
              <th class="px-2 py-2">
                <span class="sr-only">{{ t('staff.pay.actions') }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="line in selected.lines"
              :key="line.id"
              class="border-b border-line last:border-b-0"
            >
              <td class="px-2 py-2">
                <span class="block font-semibold">{{ line.staffName }}</span>
                <span class="block text-[12px] text-muted"
                  >{{ line.position }} · {{ t(`staff.payModes.${line.payMode}`) }}</span
                >
              </td>
              <td class="num px-2 py-2 text-right whitespace-nowrap">
                {{
                  t('staff.pay.workedValue', {
                    days: line.days,
                    missions: line.missions,
                    hours: line.hours,
                  })
                }}
              </td>
              <td class="num px-2 py-2 text-right">{{ formatAmount(line.base) }}</td>
              <td class="px-2 py-2 text-right">
                <input
                  v-if="selected.status === 'draft'"
                  v-model.number="line.bonuses"
                  type="number"
                  min="0"
                  class="num h-8 w-24 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
                  :aria-label="t('staff.pay.bonusesFor', { name: line.staffName })"
                  @change="attempt(update.mutateAsync(line))"
                />
                <span v-else class="num">{{ formatAmount(line.bonuses) }}</span>
              </td>
              <td class="px-2 py-2 text-right">
                <input
                  v-if="selected.status === 'draft'"
                  v-model.number="line.advances"
                  type="number"
                  min="0"
                  class="num h-8 w-24 rounded-[8px] border border-line-2 bg-surface px-2 text-right"
                  :aria-label="t('staff.pay.advancesFor', { name: line.staffName })"
                  @change="attempt(update.mutateAsync(line))"
                />
                <span v-else class="num">{{ formatAmount(line.advances) }}</span>
              </td>
              <td class="num px-2 py-2 text-right text-ink-2">
                {{ line.alreadyPaid ? `− ${formatAmount(line.alreadyPaid)}` : '—' }}
              </td>
              <td class="num px-2 py-2 text-right font-bold">{{ formatAmount(line.total) }}</td>
              <td class="px-2 py-2 text-right whitespace-nowrap">
                <WBadge v-if="line.paidAt" tone="green">{{
                  t('staff.pay.paidOn', { date: formatDate(line.paidAt) })
                }}</WBadge>
                <WButton
                  v-else-if="selected.status === 'validated' && line.total > 0"
                  size="sm"
                  @click="
                    attempt(
                      pay.mutateAsync({ id: line.id, method }),
                      t('staff.pay.paid', { name: line.staffName }),
                    )
                  "
                  >{{ t('staff.pay.pay') }}</WButton
                >
                <WButton
                  size="sm"
                  variant="ghost"
                  icon
                  :aria-label="t('staff.pay.statement', { name: line.staffName })"
                  @click="attempt(staffApi.statement(line.id, line.staffName))"
                >
                  <FileDown class="size-[15px]" aria-hidden="true" />
                </WButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WCard>
  </div>
</template>
