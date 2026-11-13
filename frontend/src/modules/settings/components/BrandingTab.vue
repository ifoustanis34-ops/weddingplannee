<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { Plus, X } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  type Branding,
  type BrandingFileKind,
  type BrandingIcon,
  type BrandingInput,
  brandingApi,
} from '@/api/branding'
import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WCard, WInput, WNote, WSelect, WSwitch, WTextarea } from '@/design'
import { useSessionStore } from '@/stores/session'

import BrandingFileSlot from './BrandingFileSlot.vue'
import BrandingPreview from './BrandingPreview.vue'

/** « Identité des documents » (docs/specs/devis-billets.md §4): what quotes and tickets show. */
const { t } = useI18n()
const toast = useToast()
const session = useSessionStore()
const queryClient = useQueryClient()

const KEY = computed(() => ['organization-branding', session.currentOrganization?.slug])
const branding = useQuery({ queryKey: KEY, queryFn: brandingApi.get })

type Form = Required<BrandingInput>
const form = ref<Form | null>(null)
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)
const busyFile = ref<BrandingFileKind | null>(null)

const FILES: BrandingFileKind[] = ['logo', 'logoOnDark', 'signatureImage', 'stampImage']
const SOCIALS = ['facebook', 'instagram', 'tiktok', 'linkedin', 'youtube'] as const
const TAX_IDS = ['rccm', 'nif', 'ncc', 'niu', 'ninea', 'ifu'] as const
const SCRIPTS = ['satisfaction', 'detail', 'detailSub', 'priority', 'thanks', 'footer'] as const
const ICONS: BrandingIcon[] = [
  'rings',
  'cake',
  'glass',
  'briefcase',
  'star',
  'team',
  'clock',
  'heart',
  'flower',
  'camera',
  'music',
  'gift',
  'car',
  'calendar',
  'shield',
  'sparkles',
]
const iconOptions = computed(() =>
  ICONS.map((value) => ({ value, label: t(`settings.branding.icons.${value}`) })),
)
const COLORS = ['primaryColor', 'secondaryColor', 'monogramColor'] as const

function fill(value: Branding): void {
  form.value = {
    primaryColor: value.primaryColor,
    secondaryColor: value.secondaryColor,
    monogramColor: value.monogramColor,
    useBrandColors: value.useBrandColors,
    tradeName: value.tradeName,
    legalName: value.legalName,
    activity: value.activity,
    slogan: value.slogan,
    address: value.address,
    // Three phone fields are always shown; empty ones are dropped by the server.
    phones: [...value.phones, '', '', ''].slice(0, 3),
    whatsapp: value.whatsapp,
    email: value.email,
    website: value.website,
    socials: { ...value.socials },
    taxIds: { ...value.taxIds },
    vatRate: value.vatRate,
    bankDetails: value.bankDetails,
    mobileMoneyNumbers: value.mobileMoneyNumbers.map((item) => ({ ...item })),
    activities: value.activities.map((item) => ({ ...item })),
    engagements: value.engagements.map((item) => ({ ...item })),
    quoteTagline: value.quoteTagline,
    scripts: { ...value.scripts },
    signatory: value.signatory,
    signatoryRole: value.signatoryRole,
    footerKeywords: [...value.footerKeywords],
    quoteTerms: value.quoteTerms,
    paymentTerms: value.paymentTerms,
    footerText: value.footerText,
    showWedivoMention: value.showWedivoMention,
  }
}
watch(
  () => branding.data.value,
  (value) => value && !form.value && fill(value),
  { immediate: true },
)

const keywords = computed({
  get: () => form.value?.footerKeywords.join(', ') ?? '',
  set: (text: string) => {
    if (form.value) form.value.footerKeywords = text.split(',').map((word) => word.trim())
  },
})

const preview = computed(() =>
  form.value && branding.data.value
    ? { ...form.value, monogram: branding.data.value.monogram }
    : null,
)
const warnings = computed(() => branding.data.value?.warnings ?? [])
const missing = computed(() => branding.data.value?.missing ?? [])

function addItem(list: 'activities' | 'engagements'): void {
  form.value?.[list].push({ label: '', icon: 'star' })
}

function apply(saved: Branding, resetForm: boolean): void {
  queryClient.setQueryData(KEY.value, saved)
  // The logo also shows on quotes, the organization profile and the starter card.
  void queryClient.invalidateQueries({ queryKey: ['organization'] })
  void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  if (resetForm) fill(saved)
  else if (form.value) {
    // Colours may have been proposed from a new logo: take them, keep the other edits.
    for (const key of COLORS) if (!form.value[key]) form.value[key] = saved[key]
  }
}

async function upload(kind: BrandingFileKind, file: File): Promise<void> {
  busyFile.value = kind
  try {
    apply(await brandingApi.upload(kind, file), false)
    toast.success(t('settings.branding.files.saved'))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busyFile.value = null
  }
}

async function remove(kind: BrandingFileKind): Promise<void> {
  busyFile.value = kind
  try {
    apply(await brandingApi.remove(kind), false)
    toast.success(t('settings.branding.files.removed'))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busyFile.value = null
  }
}

async function save(): Promise<void> {
  if (!form.value) return
  saving.value = true
  errors.value = {}
  try {
    const value = form.value
    apply(
      await brandingApi.update({
        ...value,
        vatRate: value.vatRate === '' ? null : value.vatRate,
        activities: value.activities.filter((item) => item.label.trim()),
        engagements: value.engagements.filter((item) => item.label.trim()),
      }),
      true,
    )
    toast.success(t('settings.branding.saved'))
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
  <WCard v-if="branding.isError.value" :title="t('settings.branding.title')">
    <p class="text-muted">{{ t('settings.branding.loadError') }}</p>
    <WButton class="mt-3" variant="secondary" @click="branding.refetch()">{{
      t('common.retry')
    }}</WButton>
  </WCard>
  <div v-else-if="!form" class="skeleton h-96" />
  <form v-else class="flex flex-col gap-5" novalidate @submit.prevent="save">
    <WCard :title="t('settings.branding.title')" :subtitle="t('settings.branding.subtitle')">
      <BrandingPreview
        v-if="preview"
        :branding="preview"
        :logo="branding.data.value?.files.logo ?? null"
      />
      <WNote v-if="missing.length" class="mt-4">
        {{
          t('settings.branding.missing', {
            list: missing.map((key) => t(`settings.branding.missingFields.${key}`)).join(', '),
          })
        }}
      </WNote>
    </WCard>

    <WCard
      :title="t('settings.branding.files.title')"
      :subtitle="t('settings.branding.files.subtitle')"
    >
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <BrandingFileSlot
          v-for="kind in FILES"
          :key="kind"
          :label="t(`settings.branding.files.${kind}`)"
          :hint="t(`settings.branding.files.${kind}Hint`)"
          :url="branding.data.value?.files[kind] ?? null"
          :busy="busyFile === kind"
          :dark="kind === 'logoOnDark'"
          @upload="upload(kind, $event)"
          @remove="remove(kind)"
        />
      </div>
      <div v-if="warnings.length" class="mt-4 flex flex-col gap-2" role="status">
        <WNote v-for="warning in warnings" :key="warning">{{
          t(`settings.branding.warnings.${warning}`)
        }}</WNote>
      </div>
    </WCard>

    <WCard
      :title="t('settings.branding.colors.title')"
      :subtitle="t('settings.branding.colors.subtitle')"
    >
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div v-for="key in COLORS" :key="key" class="flex min-w-0 items-end gap-2">
          <input
            v-model="form[key]"
            type="color"
            class="h-10 w-12 shrink-0 cursor-pointer rounded-[10px] border border-line-2 bg-surface p-1"
            :aria-label="t(`settings.branding.colors.${key}`)"
          />
          <WInput
            v-model="form[key]"
            class="min-w-0 flex-1"
            :label="t(`settings.branding.colors.${key}`)"
            :error="errors[key]"
            placeholder="#5126C2"
            maxlength="7"
            spellcheck="false"
          />
        </div>
      </div>
      <WSwitch
        v-model="form.useBrandColors"
        class="mt-4"
        :label="t('settings.branding.colors.useBrandColors')"
        :description="t('settings.branding.colors.useBrandColorsHint')"
      />
    </WCard>

    <WCard :title="t('settings.branding.identity.title')">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <WInput
          v-model="form.tradeName"
          :label="t('settings.branding.identity.tradeName')"
          :error="errors.tradeName"
          maxlength="120"
        />
        <WInput
          v-model="form.legalName"
          :label="t('settings.branding.identity.legalName')"
          :error="errors.legalName"
          maxlength="160"
        />
        <WInput
          v-model="form.activity"
          :label="t('settings.branding.identity.activity')"
          :error="errors.activity"
          maxlength="80"
        />
        <WInput
          v-model="form.slogan"
          :label="t('settings.branding.identity.slogan')"
          :error="errors.slogan"
          maxlength="60"
        />
        <WInput
          v-model="form.address"
          class="sm:col-span-2"
          :label="t('settings.branding.identity.address')"
          :error="errors.address"
          maxlength="200"
        />
        <WInput
          v-for="(_, index) in form.phones"
          :key="`phone-${index}`"
          v-model="form.phones[index]"
          :label="t('settings.branding.identity.phone', { n: index + 1 })"
          :error="index === 0 ? errors.phones : undefined"
          type="tel"
          maxlength="32"
        />
        <WInput
          v-model="form.whatsapp"
          :label="t('settings.branding.identity.whatsapp')"
          :error="errors.whatsapp"
          type="tel"
          maxlength="32"
        />
        <WInput
          v-model="form.email"
          :label="t('settings.branding.identity.email')"
          :error="errors.email"
          type="email"
        />
        <WInput
          v-model="form.website"
          :label="t('settings.branding.identity.website')"
          :error="errors.website"
          maxlength="120"
        />
        <WInput
          v-for="network in SOCIALS"
          :key="network"
          v-model="form.socials[network]"
          :label="t(`settings.branding.socials.${network}`)"
          maxlength="60"
        />
      </div>
    </WCard>

    <WCard
      :title="t('settings.branding.legal.title')"
      :subtitle="t('settings.branding.legal.subtitle')"
    >
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <WInput
          v-for="id in TAX_IDS"
          :key="id"
          v-model="form.taxIds[id]"
          :label="t(`settings.branding.taxIds.${id}`)"
          maxlength="40"
        />
        <WInput
          v-model="form.vatRate"
          :label="t('settings.branding.legal.vatRate')"
          :error="errors.vatRate"
          type="number"
          min="0"
          max="100"
          step="0.01"
          addon="%"
        />
        <WTextarea
          v-model="form.bankDetails"
          class="sm:col-span-2"
          :label="t('settings.branding.legal.bankDetails')"
          :error="errors.bankDetails"
          :rows="2"
        />
      </div>
      <fieldset class="mt-4">
        <legend class="mb-2 font-bold">{{ t('settings.branding.legal.mobileMoney') }}</legend>
        <div class="flex flex-col gap-2">
          <div
            v-for="(item, index) in form.mobileMoneyNumbers"
            :key="index"
            class="flex items-end gap-2"
          >
            <WInput
              v-model="item.provider"
              class="w-[120px] shrink-0 sm:w-40"
              :label="t('settings.branding.legal.provider')"
              maxlength="20"
              placeholder="Orange Money"
            />
            <WInput
              v-model="item.number"
              class="min-w-0 flex-1"
              :label="t('settings.branding.legal.number')"
              type="tel"
              maxlength="32"
            />
            <WButton
              icon
              variant="ghost"
              :aria-label="t('settings.branding.remove')"
              @click="form.mobileMoneyNumbers.splice(index, 1)"
            >
              <X class="size-[18px]" aria-hidden="true" />
            </WButton>
          </div>
        </div>
        <WButton
          v-if="form.mobileMoneyNumbers.length < 4"
          class="mt-2"
          variant="secondary"
          size="sm"
          @click="form.mobileMoneyNumbers.push({ provider: '', number: '' })"
        >
          <Plus class="size-[15px]" aria-hidden="true" />{{
            t('settings.branding.legal.addNumber')
          }}
        </WButton>
        <p class="mt-2 text-[12.5px] text-muted">
          {{ t('settings.branding.legal.mobileMoneyHint') }}
        </p>
      </fieldset>
    </WCard>

    <WCard
      :title="t('settings.branding.texts.title')"
      :subtitle="t('settings.branding.texts.subtitle')"
    >
      <div class="flex flex-col gap-5">
        <fieldset v-for="list in ['activities', 'engagements'] as const" :key="list">
          <legend class="mb-2 font-bold">{{ t(`settings.branding.texts.${list}`) }}</legend>
          <p v-if="errors[list]" class="mb-2 text-[12.5px] text-red" role="alert">
            {{ errors[list] }}
          </p>
          <div class="flex flex-col gap-2">
            <div v-for="(item, index) in form[list]" :key="index" class="flex items-end gap-2">
              <WSelect
                v-model="item.icon"
                class="w-[120px] shrink-0 sm:w-40"
                :label="t('settings.branding.texts.icon')"
                :options="iconOptions"
                :hide-label="index > 0"
              />
              <WInput
                v-model="item.label"
                class="min-w-0 flex-1"
                :label="t('settings.branding.texts.label', { n: index + 1 })"
                :hide-label="index > 0"
                :maxlength="list === 'activities' ? 40 : 70"
              />
              <WButton
                icon
                variant="ghost"
                :aria-label="t('settings.branding.remove')"
                @click="form[list].splice(index, 1)"
              >
                <X class="size-[18px]" aria-hidden="true" />
              </WButton>
            </div>
          </div>
          <WButton
            v-if="form[list].length < 4"
            class="mt-2"
            variant="secondary"
            size="sm"
            @click="addItem(list)"
          >
            <Plus class="size-[15px]" aria-hidden="true" />{{ t('settings.branding.texts.add') }}
          </WButton>
        </fieldset>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <WInput
            v-model="form.quoteTagline"
            class="sm:col-span-2"
            :label="t('settings.branding.texts.quoteTagline')"
            :error="errors.quoteTagline"
          />
          <WInput
            v-for="key in SCRIPTS"
            :key="key"
            v-model="form.scripts[key]"
            :label="t(`settings.branding.scripts.${key}`)"
            :error="errors[key]"
            maxlength="70"
          />
          <WInput
            v-model="form.signatory"
            :label="t('settings.branding.texts.signatory')"
            :error="errors.signatory"
            maxlength="80"
          />
          <WInput
            v-model="form.signatoryRole"
            :label="t('settings.branding.texts.signatoryRole')"
            :error="errors.signatoryRole"
            maxlength="60"
          />
          <WInput
            v-model="keywords"
            class="sm:col-span-2"
            :label="t('settings.branding.texts.footerKeywords')"
            :hint="t('settings.branding.texts.footerKeywordsHint')"
            :error="errors.footerKeywords"
          />
          <WTextarea
            v-model="form.quoteTerms"
            class="sm:col-span-2"
            :label="t('settings.branding.texts.quoteTerms')"
            :error="errors.quoteTerms"
            :rows="3"
          />
          <WTextarea
            v-model="form.paymentTerms"
            class="sm:col-span-2"
            :label="t('settings.branding.texts.paymentTerms')"
            :error="errors.paymentTerms"
            :rows="2"
          />
          <WTextarea
            v-model="form.footerText"
            class="sm:col-span-2"
            :label="t('settings.branding.texts.footerText')"
            :error="errors.footerText"
            :rows="2"
          />
        </div>
        <WSwitch
          v-model="form.showWedivoMention"
          :label="t('settings.branding.texts.showWedivoMention')"
        />
      </div>
    </WCard>

    <div class="sticky bottom-[calc(76px+env(safe-area-inset-bottom))] nav:bottom-4">
      <WButton type="submit" :loading="saving">{{ t('settings.branding.save') }}</WButton>
    </div>
  </form>
</template>
