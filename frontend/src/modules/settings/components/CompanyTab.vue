<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { ImageUp } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { type Organization, type OrganizationInput, organizationApi } from '@/api/organization'
import { useToast } from '@/composables/useToast'
import { WAvatar, WButton, WCard, WInput, WSelect, WSwitch, WTextarea } from '@/design'
import { COUNTRIES } from '@/modules/auth/schemas'
import { useSessionStore } from '@/stores/session'

import { CURRENCIES, TIMEZONES } from '../constants'

/** « Profil de l’entreprise » (complement §15): shown on quotes, contracts and invitations. */
const { t } = useI18n()
const toast = useToast()
const session = useSessionStore()
const queryClient = useQueryClient()

const organization = useQuery({
  queryKey: computed(() => ['organization', session.currentOrganization?.slug]),
  queryFn: organizationApi.get,
})

type Form = Required<OrganizationInput>
const form = ref<Form | null>(null)
const logoPreview = ref<string | null>(null)
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)

function fill(value: Organization): void {
  form.value = {
    name: value.name,
    slug: value.slug,
    city: value.city,
    country: value.country,
    currency: value.currency,
    timezone: value.timezone,
    legalMentions: value.legalMentions,
    quotePrefix: value.quotePrefix,
    quoteValidityDays: value.quoteValidityDays,
    alertDigest: value.alertDigest,
    depositKeptOnCancel: value.depositKeptOnCancel,
    weddingsEnabled: value.weddingsEnabled,
  }
  logoPreview.value = value.logo
}
watch(
  () => organization.data.value,
  (value) => value && fill(value),
  { immediate: true },
)

const countryOptions = computed(() => {
  const options = COUNTRIES.map(([value, label]) => ({ value, label }))
  const current = form.value?.country
  return current && !options.some((o) => o.value === current)
    ? [...options, { value: current, label: current }]
    : options
})
const currencyOptions = computed(() =>
  CURRENCIES.map((value) => ({ value, label: t(`settings.company.currencies.${value}`) })),
)
const timezoneOptions = computed(() => {
  const options = TIMEZONES.map((value) => ({ value, label: value.replace('_', ' ') }))
  const current = form.value?.timezone
  return current && !options.some((o) => o.value === current)
    ? [...options, { value: current, label: current }]
    : options
})

async function save(): Promise<void> {
  if (!form.value) return
  saving.value = true
  errors.value = {}
  const previousSlug = session.currentOrganization?.slug
  try {
    const saved = await organizationApi.update(form.value)
    fill(saved)
    // A new space address: follow it (the session lists the spaces by address).
    if (saved.slug !== previousSlug) session.selectOrganization(saved.slug)
    // The menu shows the new name and the modules turned on or off at once.
    await session.refresh()
    void queryClient.invalidateQueries({ queryKey: ['organization'] })
    void queryClient.invalidateQueries({ queryKey: ['organization-settings'] })
    toast.success(t('settings.company.saved'))
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    toast.error(apiError.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <WCard :title="t('settings.company.title')" :subtitle="t('settings.company.subtitle')">
    <div v-if="organization.isPending.value || !form" class="skeleton h-80" />
    <form v-else class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="save">
      <div class="flex items-center gap-4 sm:col-span-2">
        <img
          v-if="logoPreview"
          :src="logoPreview"
          alt=""
          class="size-14 rounded-wd border border-line object-contain"
        />
        <WAvatar v-else :name="form.name" kind="organization" :size="56" />
        <RouterLink
          :to="{ name: 'settings', params: { tab: 'identite' } }"
          class="inline-flex h-8 shrink-0 items-center gap-2 rounded-[8px] border border-line-2 bg-surface px-[11px] text-[13px] font-bold hover:bg-surface-2"
        >
          <ImageUp class="size-[15px]" aria-hidden="true" />{{ t('settings.company.logo') }}
        </RouterLink>
        <span class="text-[12.5px] text-muted">{{ t('settings.company.logoHint') }}</span>
      </div>
      <WInput
        v-model="form.name"
        class="sm:col-span-2"
        :label="t('settings.company.name')"
        :error="errors.name"
        required
      />
      <WInput
        v-model="form.slug"
        class="sm:col-span-2"
        :label="t('auth.signup.slug')"
        addon=".wedivo.app"
        :hint="t('settings.company.slugHint')"
        :error="errors.slug"
        autocapitalize="none"
        spellcheck="false"
      />
      <WInput v-model="form.city" :label="t('auth.signup.city')" :error="errors.city" />
      <WSelect
        v-model="form.country"
        :label="t('auth.signup.country')"
        :options="countryOptions"
        :error="errors.country"
      />
      <WSelect
        v-model="form.currency"
        :label="t('settings.company.currency')"
        :options="currencyOptions"
        :error="errors.currency"
      />
      <WSelect
        v-model="form.timezone"
        :label="t('settings.company.timezone')"
        :options="timezoneOptions"
        :error="errors.timezone"
      />
      <WInput
        v-model="form.quotePrefix"
        :label="t('settings.company.quotePrefix')"
        :hint="t('settings.company.quotePrefixHint', { prefix: form.quotePrefix || 'DV' })"
        :error="errors.quotePrefix"
        maxlength="8"
      />
      <WInput
        v-model.number="form.quoteValidityDays"
        :label="t('settings.company.validity')"
        type="number"
        min="1"
        max="365"
        :addon="t('settings.company.days')"
        :error="errors.quoteValidityDays"
      />
      <WTextarea
        v-model="form.legalMentions"
        class="sm:col-span-2"
        :label="t('settings.company.legalMentions')"
        :error="errors.legalMentions"
        :rows="3"
      />
      <WSwitch
        v-model="form.depositKeptOnCancel"
        class="sm:col-span-2"
        :label="t('settings.company.depositKept')"
        :description="t('settings.company.depositKeptHint')"
      />
      <WSwitch
        v-model="form.weddingsEnabled"
        class="sm:col-span-2"
        :label="t('settings.company.weddingsModule')"
        :description="t('settings.company.weddingsModuleHint')"
      />
      <WSwitch
        v-model="form.alertDigest"
        class="sm:col-span-2"
        :label="t('settings.company.alertDigest')"
        :description="t('settings.company.alertDigestHint')"
      />
      <div class="sm:col-span-2">
        <WButton type="submit" :loading="saving">{{ t('settings.company.save') }}</WButton>
      </div>
    </form>
  </WCard>
</template>
