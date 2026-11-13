<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Role } from '@/api/auth'
import { toApiError } from '@/api/errors'
import { organizationApi } from '@/api/organization'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WNote, WSelect } from '@/design'

/** « Inviter un membre »: an email with a link to join the space with this role. */
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ invited: [] }>()
const { t } = useI18n()
const toast = useToast()

const ROLES: Exclude<Role, 'owner'>[] = [
  'planner',
  'assistant',
  'accountant',
  'storekeeper',
  'team_lead',
  'staff',
]
const email = ref('')
const role = ref<Exclude<Role, 'owner'>>('planner')
const errors = ref<Record<string, string | undefined>>({})
const sending = ref(false)

watch(open, (isOpen) => {
  if (!isOpen) return
  email.value = ''
  role.value = 'planner'
  errors.value = {}
})

async function submit(): Promise<void> {
  errors.value = {}
  if (!/^\S+@\S+\.\S+$/.test(email.value.trim())) {
    errors.value.email = t('validation.email')
    return
  }
  sending.value = true
  try {
    await organizationApi.invite({ email: email.value.trim(), role: role.value })
    toast.success(t('settings.team.invitationSent', { email: email.value.trim() }))
    emit('invited')
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="t('settings.team.invite')">
    <form id="invite-form" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <WInput
        v-model="email"
        type="email"
        :label="t('auth.workEmail')"
        :error="errors.email"
        autocomplete="off"
        required
        autofocus
      />
      <WSelect
        v-model="role"
        :label="t('settings.team.role')"
        :options="ROLES.map((r) => ({ value: r, label: t(`roles.${r}`) }))"
        :hint="t(`settings.team.roleHints.${role}`)"
        :error="errors.role"
      />
      <WNote>{{ t('settings.team.inviteNote') }}</WNote>
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="invite-form" :loading="sending">{{
        t('settings.team.sendInvitation')
      }}</WButton>
    </template>
  </WModal>
</template>
