<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { RefreshCw } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Role } from '@/api/auth'
import { platformApi } from '@/api/platform'
import { generatePassword } from '@/app/passwords'
import AccountCredentials from '@/components/AccountCredentials.vue'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect, WSwitch } from '@/design'

import { fieldErrors } from '../errors'

/**
 * A new Wedivo account with a temporary password, placed in an agency with a role (or not), or
 * a new member of the Wedivo team. With `agency`, the agency is fixed (from its page).
 */
const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ agency?: { id: string; name: string } }>()
const emit = defineEmits<{ created: [id: string] }>()
const { t } = useI18n()
const toast = useToast()
const queryClient = useQueryClient()

const ROLES: Role[] = [
  'owner',
  'planner',
  'assistant',
  'accountant',
  'storekeeper',
  'team_lead',
  'staff',
]
const roleOptions = computed(() => ROLES.map((r) => ({ value: r, label: t(`roles.${r}`) })))

const agencies = useQuery({
  queryKey: ['platform', 'agencies', 'choices'],
  queryFn: () => platformApi.agencies({ pageSize: 100 }),
  enabled: computed(() => open.value && !props.agency),
  staleTime: 60_000,
})
const agencyOptions = computed(() => [
  { value: '', label: t('platform.accounts.form.noAgency') },
  ...(agencies.data.value?.results ?? []).map((a) => ({ value: a.id, label: a.name })),
])

const empty = () => ({
  fullName: '',
  email: '',
  phone: '',
  password: generatePassword(),
  organizationId: props.agency?.id ?? '',
  role: 'planner' as Role,
  isPlatformAdmin: false,
})
const form = ref(empty())
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)
const result = ref<{
  id: string
  name: string
  email: string
  password: string
  phone: string
  agency: string
} | null>(null)

watch(open, (isOpen) => {
  if (!isOpen) return
  form.value = empty()
  errors.value = {}
  result.value = null
})

async function submit(): Promise<void> {
  errors.value = {}
  const f = form.value
  if (!f.fullName.trim()) errors.value.fullName = t('validation.required')
  if (!/^\S+@\S+\.\S+$/.test(f.email.trim())) errors.value.email = t('validation.email')
  if (f.password.length < 8) errors.value.password = t('credentials.tooShort')
  if (Object.keys(errors.value).length) return
  saving.value = true
  try {
    const account = await platformApi.createAccount({
      fullName: f.fullName.trim(),
      email: f.email.trim(),
      phone: f.phone.trim(),
      password: f.password,
      organizationId: f.organizationId || null,
      role: f.organizationId ? f.role : '',
      isPlatformAdmin: f.isPlatformAdmin,
    })
    void queryClient.invalidateQueries({ queryKey: ['platform'] })
    result.value = {
      id: account.id,
      name: account.fullName,
      email: account.email,
      password: f.password,
      phone: account.phone,
      agency: account.memberships[0]?.organizationName ?? t('platform.name'),
    }
    toast.success(t('platform.accounts.form.created', { name: account.fullName }))
  } catch (error) {
    const { fields, message } = fieldErrors(error)
    errors.value = fields
    if (!Object.keys(fields).length) toast.error(message)
  } finally {
    saving.value = false
  }
}

function finish(): void {
  const id = result.value?.id
  open.value = false
  if (id) emit('created', id)
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="
      result
        ? t('credentials.title')
        : agency
          ? `${t('platform.accounts.form.title')} · ${agency.name}`
          : t('platform.accounts.form.title')
    "
  >
    <AccountCredentials
      v-if="result"
      :name="result.name"
      :email="result.email"
      :password="result.password"
      :phone="result.phone"
      :organization-name="result.agency"
    />
    <form
      v-else
      id="account-create-form"
      class="flex flex-col gap-4"
      novalidate
      @submit.prevent="submit"
    >
      <WInput
        v-model="form.fullName"
        :label="t('platform.accounts.detail.fullName')"
        :error="errors.fullName"
        autocomplete="off"
        required
        autofocus
      />
      <div class="grid gap-4 sm:grid-cols-2">
        <WInput
          v-model="form.email"
          type="email"
          :label="t('platform.accounts.detail.email')"
          :error="errors.email"
          autocomplete="off"
          required
        />
        <WInput
          v-model="form.phone"
          type="tel"
          :label="t('platform.accounts.detail.phone')"
          :error="errors.phone"
          autocomplete="off"
        />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <WSelect
          v-if="!agency"
          v-model="form.organizationId"
          :label="t('platform.accounts.form.agency')"
          :options="agencyOptions"
          :error="errors.organizationId"
        />
        <WSelect
          v-if="form.organizationId"
          v-model="form.role"
          :label="t('platform.accounts.form.role')"
          :options="roleOptions"
          :error="errors.role"
        />
      </div>
      <WSwitch
        v-if="!agency"
        v-model="form.isPlatformAdmin"
        :label="t('platform.accounts.form.admin')"
        :description="t('platform.accounts.detail.adminHint')"
      />
      <div class="flex items-end gap-2">
        <WInput
          v-model="form.password"
          class="flex-1"
          :label="t('credentials.temporary')"
          :error="errors.password"
          autocomplete="off"
          spellcheck="false"
          required
        />
        <WButton
          variant="secondary"
          icon
          :aria-label="t('credentials.generate')"
          :title="t('credentials.generate')"
          :class="errors.password && 'mb-[22px]'"
          @click="form.password = generatePassword()"
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
        <WButton type="submit" form="account-create-form" :loading="saving">{{
          t('platform.accounts.form.submit')
        }}</WButton>
      </template>
    </template>
  </WModal>
</template>
