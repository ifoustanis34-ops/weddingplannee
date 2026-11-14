<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { RefreshCw } from '@lucide/vue'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Plan } from '@/api/auth'
import { authApi } from '@/api/auth'
import { platformApi } from '@/api/platform'
import { generatePassword } from '@/app/passwords'
import AccountCredentials from '@/components/AccountCredentials.vue'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect, WSwitch } from '@/design'

import { fieldErrors } from '../errors'

/** Open an agency for a customer, with its owner (temporary password), lifetime if wanted. */
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [id: string] }>()
const { t } = useI18n()
const toast = useToast()
const queryClient = useQueryClient()

const PLANS: Plan[] = ['essentiel', 'pro', 'agence']
const planOptions = PLANS.map((value) => ({
  value,
  label: value.charAt(0).toUpperCase() + value.slice(1),
}))
const empty = () => ({
  name: '',
  slug: '',
  city: '',
  country: 'CM',
  plan: 'pro' as Plan,
  ownerFullName: '',
  ownerEmail: '',
  ownerPhone: '',
  ownerPassword: generatePassword(),
  lifetimeAccess: false,
  weddingsEnabled: false,
})
const form = ref(empty())
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)
const result = ref<{
  agencyId: string
  agencyName: string
  name: string
  email: string
  password: string | null
  phone: string
} | null>(null)
let slugTouched = false

watch(open, (isOpen) => {
  if (!isOpen) return
  form.value = empty()
  errors.value = {}
  result.value = null
  slugTouched = false
})

// Address proposed from the name (same rules as the sign-up), until edited by hand.
let slugTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => form.value.name,
  (name) => {
    if (slugTouched) return
    clearTimeout(slugTimer)
    slugTimer = setTimeout(async () => {
      if (!name.trim() || slugTouched) return
      try {
        const proposal = await authApi.slugAvailable({ name })
        if (!slugTouched) form.value.slug = proposal.slug
      } catch {
        // No proposal: the field stays editable.
      }
    }, 350)
  },
)

async function submit(): Promise<void> {
  errors.value = {}
  const f = form.value
  if (!f.name.trim()) errors.value.name = t('validation.required')
  if (!f.slug.trim()) errors.value.slug = t('validation.required')
  if (!f.city.trim()) errors.value.city = t('validation.required')
  if (f.country.trim().length !== 2) errors.value.country = t('platform.agencies.form.countryHint')
  if (!f.ownerFullName.trim()) errors.value.ownerFullName = t('validation.required')
  if (!/^\S+@\S+\.\S+$/.test(f.ownerEmail.trim())) errors.value.ownerEmail = t('validation.email')
  if (f.ownerPassword.length < 8) errors.value.ownerPassword = t('credentials.tooShort')
  if (Object.keys(errors.value).length) return
  saving.value = true
  try {
    const created = await platformApi.createAgency({
      ...f,
      name: f.name.trim(),
      slug: f.slug.trim().toLowerCase(),
      city: f.city.trim(),
      country: f.country.trim().toUpperCase(),
      ownerFullName: f.ownerFullName.trim(),
      ownerEmail: f.ownerEmail.trim(),
      ownerPhone: f.ownerPhone.trim(),
    })
    void queryClient.invalidateQueries({ queryKey: ['platform'] })
    result.value = {
      agencyId: created.agency.id,
      agencyName: created.agency.name,
      name: f.ownerFullName.trim(),
      email: created.ownerEmail,
      password: created.createdAccount ? f.ownerPassword : null,
      phone: f.ownerPhone.trim(),
    }
    toast.success(t('platform.agencies.form.created', { name: created.agency.name }))
  } catch (error) {
    const { fields, message } = fieldErrors(error)
    errors.value = fields
    if (!Object.keys(fields).length) toast.error(message)
  } finally {
    saving.value = false
  }
}

function finish(): void {
  const id = result.value?.agencyId
  open.value = false
  if (id) emit('created', id)
}
</script>

<template>
  <WModal
    v-model:open="open"
    size="lg"
    :title="result ? t('credentials.title') : t('platform.agencies.form.title')"
  >
    <AccountCredentials
      v-if="result"
      :name="result.name"
      :email="result.email"
      :password="result.password"
      :phone="result.phone"
      :organization-name="result.agencyName"
    />
    <form
      v-else
      id="agency-create-form"
      class="flex flex-col gap-4"
      novalidate
      @submit.prevent="submit"
    >
      <h3 class="font-semibold">{{ t('platform.agencies.form.agency') }}</h3>
      <WInput
        v-model="form.name"
        :label="t('platform.agencies.form.name')"
        :error="errors.name"
        required
        autofocus
      />
      <WInput
        v-model="form.slug"
        addon=".wedivo.pro"
        :label="t('platform.agencies.form.slug')"
        :error="errors.slug"
        required
        @input="slugTouched = true"
      />
      <div class="grid gap-4 sm:grid-cols-3">
        <WInput
          v-model="form.city"
          :label="t('platform.agencies.form.city')"
          :error="errors.city"
          required
        />
        <WInput
          v-model="form.country"
          maxlength="2"
          :label="t('platform.agencies.form.country')"
          :hint="t('platform.agencies.form.countryHint')"
          :error="errors.country"
          required
        />
        <WSelect
          v-model="form.plan"
          :label="t('platform.agencies.form.plan')"
          :options="planOptions"
          :error="errors.plan"
        />
      </div>
      <WSwitch v-model="form.lifetimeAccess" :label="t('platform.agencies.form.lifetime')" />
      <WSwitch v-model="form.weddingsEnabled" :label="t('platform.agencies.form.weddings')" />

      <h3 class="mt-2 font-semibold">{{ t('platform.agencies.form.owner') }}</h3>
      <WInput
        v-model="form.ownerFullName"
        :label="t('platform.agencies.form.ownerName')"
        :error="errors.ownerFullName"
        autocomplete="off"
        required
      />
      <div class="grid gap-4 sm:grid-cols-2">
        <WInput
          v-model="form.ownerEmail"
          type="email"
          :label="t('platform.agencies.form.ownerEmail')"
          :hint="t('platform.agencies.form.ownerEmailHint')"
          :error="errors.ownerEmail"
          autocomplete="off"
          required
        />
        <WInput
          v-model="form.ownerPhone"
          type="tel"
          :label="t('platform.agencies.form.ownerPhone')"
          :error="errors.ownerPhone"
          autocomplete="off"
        />
      </div>
      <div class="flex items-end gap-2">
        <WInput
          v-model="form.ownerPassword"
          class="flex-1"
          :label="t('credentials.temporary')"
          :error="errors.ownerPassword"
          autocomplete="off"
          spellcheck="false"
          required
        />
        <WButton
          variant="secondary"
          icon
          :aria-label="t('credentials.generate')"
          :title="t('credentials.generate')"
          :class="errors.ownerPassword && 'mb-[22px]'"
          @click="form.ownerPassword = generatePassword()"
        >
          <RefreshCw class="size-[16px]" aria-hidden="true" />
        </WButton>
      </div>
      <p class="-mt-2 text-[12.5px] text-muted">{{ t('credentials.temporaryHint') }}</p>
    </form>
    <template #footer>
      <WButton v-if="result" @click="finish">{{ t('credentials.done') }}</WButton>
      <template v-else>
        <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
        <WButton type="submit" form="agency-create-form" :loading="saving">{{
          t('platform.agencies.form.submit')
        }}</WButton>
      </template>
    </template>
  </WModal>
</template>
