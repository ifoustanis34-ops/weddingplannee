<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { Check } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { organizationApi } from '@/api/organization'
import { plansApi } from '@/api/plans'
import { DEFAULT_TIMEZONE, daysBetween } from '@/composables/useDate'
import { formatAmount } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WEmptyState, WNote } from '@/design'
import { useSessionStore } from '@/stores/session'

/** « Abonnement » (complement §15): three offers, prices from the database. */
const { t } = useI18n()
const toast = useToast()
const session = useSessionStore()
const queryClient = useQueryClient()

const plans = useQuery({ queryKey: ['plans'], queryFn: plansApi.list, staleTime: 3_600_000 })
const organization = useQuery({
  queryKey: computed(() => ['organization', session.currentOrganization?.slug]),
  queryFn: organizationApi.get,
})
const current = computed(() => organization.data.value?.plan)
const trialDays = computed(() => {
  const ends = organization.data.value?.trialEndsAt
  if (!ends) return null
  const days = daysBetween(new Date(), ends, organization.data.value?.timezone ?? DEFAULT_TIMEZONE)
  return days >= 0 ? days : null
})

const switching = ref<string | null>(null)
async function choose(code: 'essentiel' | 'pro' | 'agence', name: string): Promise<void> {
  switching.value = code
  try {
    await organizationApi.changePlan(code)
    void queryClient.invalidateQueries({ queryKey: ['organization'] })
    toast.success(t('settings.plan.changed', { name }))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    switching.value = null
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <WNote>{{ t('settings.plan.allIncluded') }}</WNote>
    <p
      v-if="trialDays !== null"
      class="rounded-wd bg-gold-soft px-3.5 py-3 text-[13.5px] text-ink-2"
    >
      {{ t('settings.plan.trial', { days: trialDays }) }}
    </p>
    <div v-if="plans.isPending.value" class="grid gap-4 min-[1001px]:grid-cols-3">
      <div v-for="n in 3" :key="n" class="skeleton h-72 rounded-wd-lg" />
    </div>
    <WEmptyState
      v-else-if="plans.isError.value"
      :title="t('settings.plan.loadError')"
      :description="toApiError(plans.error.value).message"
    />
    <div v-else class="grid gap-4 min-[1001px]:grid-cols-3">
      <article
        v-for="plan in plans.data.value"
        :key="plan.code"
        class="flex flex-col rounded-wd-lg border bg-surface p-5"
        :class="
          plan.code === current
            ? 'border-violet shadow-[0_0_0_3px_var(--violet-soft)]'
            : 'border-line'
        "
      >
        <div class="flex items-center gap-2">
          <h2>{{ plan.name }}</h2>
          <WBadge v-if="plan.code === current" tone="violet">{{
            t('settings.plan.current')
          }}</WBadge>
        </div>
        <p class="mt-1 text-[13px] text-muted">{{ plan.description }}</p>
        <p class="mt-4">
          <span class="num text-[24px] font-semibold">{{ formatAmount(plan.monthlyPrice) }}</span>
          <span class="text-[13px] text-muted"> {{ t('settings.plan.perMonth') }}</span>
        </p>
        <ul class="mt-4 flex flex-1 flex-col gap-2 text-[13.5px]">
          <li v-for="feature in plan.features" :key="feature" class="flex items-start gap-2">
            <Check class="mt-0.5 size-4 shrink-0 text-green" aria-hidden="true" />{{ feature }}
          </li>
        </ul>
        <WButton
          class="mt-5"
          block
          :variant="plan.code === current ? 'secondary' : 'primary'"
          :disabled="plan.code === current"
          :loading="switching === plan.code"
          @click="choose(plan.code, plan.name)"
        >
          {{
            plan.code === current
              ? t('settings.plan.current')
              : t('settings.plan.switch', { name: plan.name })
          }}
        </WButton>
      </article>
    </div>
    <p class="text-[12.5px] text-muted">{{ t('settings.plan.notice') }}</p>
  </div>
</template>
