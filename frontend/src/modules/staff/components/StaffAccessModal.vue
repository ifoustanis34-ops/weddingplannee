<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Role } from '@/api/auth'
import { toApiError } from '@/api/errors'
import { generatePassword } from '@/app/passwords'
import AccountCredentials from '@/components/AccountCredentials.vue'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect } from '@/design'

import { type StaffMember, staffApi, useStaffMutation } from '../api'

/**
 * « Créer son accès » (feedback 13/11/2026): the owner opens a Wedivo account for a person of
 * the staff. Linked to the record, it shows them « Mes missions »: their assignments and tasks.
 */
const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ member: StaffMember }>()
const emit = defineEmits<{ done: [] }>()
const { t } = useI18n()
const toast = useToast()

const ROLES: Exclude<Role, 'owner'>[] = [
  'staff',
  'team_lead',
  'storekeeper',
  'planner',
  'assistant',
  'accountant',
]
/** The role that fits the position, changed if needed. */
function guessRole(position: string): Exclude<Role, 'owner'> {
  const p = position.toLowerCase()
  if (p.includes('chef')) return 'team_lead'
  if (p.includes('magasin')) return 'storekeeper'
  if (p.includes('comptab')) return 'accountant'
  if (p.includes('planner')) return 'planner'
  return 'staff'
}
const form = ref({ email: '', role: 'staff', password: '' })
const errors = ref<Record<string, string | undefined>>({})
const result = ref<{ email: string; password: string | null } | null>(null)

watch(open, (isOpen) => {
  if (!isOpen) return
  form.value = { email: '', role: guessRole(props.member.position), password: generatePassword() }
  errors.value = {}
  result.value = null
})

const create = useStaffMutation(() =>
  staffApi.createAccess(props.member.id, {
    email: form.value.email.trim(),
    role: form.value.role as Role,
    password: form.value.password,
  }),
)
async function submit(): Promise<void> {
  errors.value = {}
  if (!/^\S+@\S+\.\S+$/.test(form.value.email.trim())) errors.value.email = t('validation.email')
  if (form.value.password.length < 8) errors.value.password = t('credentials.tooShort')
  if (Object.keys(errors.value).length) return
  try {
    const created = await create.mutateAsync(undefined)
    result.value = {
      email: created.email,
      password: created.createdAccount ? form.value.password : null,
    }
    toast.success(t('staff.access.created', { name: props.member.fullName }))
    emit('done')
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="result ? t('credentials.title') : t('staff.access.title', { name: member.fullName })"
  >
    <AccountCredentials
      v-if="result"
      :name="member.fullName"
      :email="result.email"
      :password="result.password"
      :phone="member.phone"
    />
    <form
      v-else
      id="staff-access-form"
      class="flex flex-col gap-4"
      novalidate
      @submit.prevent="submit"
    >
      <p class="text-[14px] text-ink-2">{{ t('staff.access.intro') }}</p>
      <WInput
        v-model="form.email"
        type="email"
        :label="t('auth.email')"
        :hint="t('settings.team.emailHint')"
        :error="errors.email"
        autocomplete="off"
        required
        autofocus
      />
      <WSelect
        v-model="form.role"
        :label="t('settings.team.role')"
        :options="ROLES.map((r) => ({ value: r, label: t(`roles.${r}`) }))"
        :hint="t(`settings.team.roleHints.${form.role}`)"
        :error="errors.role"
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
      <WButton v-if="result" @click="open = false">{{ t('credentials.done') }}</WButton>
      <template v-else>
        <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
        <WButton type="submit" form="staff-access-form" :loading="create.isPending.value">{{
          t('staff.access.submit')
        }}</WButton>
      </template>
    </template>
  </WModal>
</template>
