<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WCard, WInput, WNote, WSwitch } from '@/design'
import { useSessionStore } from '@/stores/session'

import { type PayrollSettings, staffApi, staffKeys, useStaffMutation } from '../api'

/**
 * « Réglages de la paie » (feedback 24/11/2026): the Cameroon contributions and taxes on the
 * slips of declared staff, the employer CNPS number, the work-accident rate, the signatory.
 * The owner changes them; the accountant reads them.
 */
const { t } = useI18n()
const toast = useToast()
const session = useSessionStore()
const isOwner = computed(() => session.role === 'owner')
const settings = useQuery({
  queryKey: [...staffKeys.all, 'payroll-settings'],
  queryFn: staffApi.payrollSettings,
})
const form = ref<PayrollSettings>({
  contributionsEnabled: false,
  employerCnps: '',
  accidentRate: 1.75,
  signatory: '',
})
watch(
  () => settings.data.value,
  (value) => {
    if (value) form.value = { ...value }
  },
  { immediate: true },
)
const save = useStaffMutation((input: PayrollSettings) => staffApi.savePayrollSettings(input))
async function submit(): Promise<void> {
  try {
    await save.mutateAsync(form.value)
    toast.success(t('staff.payrollSettings.saved'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <WCard :title="t('staff.payrollSettings.title')" :subtitle="t('staff.payrollSettings.subtitle')">
    <div v-if="settings.isPending.value" class="skeleton h-40" />
    <form v-else class="flex max-w-[640px] flex-col gap-4" @submit.prevent="submit">
      <WSwitch
        v-model="form.contributionsEnabled"
        :label="t('staff.payrollSettings.contributions')"
        :disabled="!isOwner"
      />
      <WNote>{{ t('staff.payrollSettings.contributionsHint') }}</WNote>
      <div class="grid gap-3 sm:grid-cols-2">
        <WInput
          v-model="form.employerCnps"
          :label="t('staff.payrollSettings.employerCnps')"
          :disabled="!isOwner"
        />
        <WInput
          v-model.number="form.accidentRate"
          type="number"
          min="0"
          max="10"
          step="0.25"
          inputmode="decimal"
          addon="%"
          :label="t('staff.payrollSettings.accidentRate')"
          :hint="t('staff.payrollSettings.accidentHint')"
          :disabled="!isOwner"
        />
        <WInput
          v-model="form.signatory"
          class="sm:col-span-2"
          :label="t('staff.payrollSettings.signatory')"
          :placeholder="t('staff.payrollSettings.signatoryPlaceholder')"
          :disabled="!isOwner"
        />
      </div>
      <p class="text-[12.5px] text-muted">{{ t('staff.payrollSettings.identity') }}</p>
      <div v-if="isOwner">
        <WButton type="submit" :loading="save.isPending.value">{{ t('staff.form.save') }}</WButton>
      </div>
    </form>
  </WCard>
</template>
