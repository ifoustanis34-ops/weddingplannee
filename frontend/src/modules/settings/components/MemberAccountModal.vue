<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Role } from '@/api/auth'
import { toApiError } from '@/api/errors'
import { type Member, organizationApi } from '@/api/organization'
import { generatePassword } from '@/app/passwords'
import AccountCredentials from '@/components/AccountCredentials.vue'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect } from '@/design'

/**
 * « Créer un compte » (feedback 13/11/2026): the owner opens an account for a team member with a
 * temporary password, without an email round trip. With `member`, gives that member a new
 * temporary password instead (forgotten, no email at hand). Then shows what to hand over.
 */
const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ member?: Member | null }>()
const emit = defineEmits<{ done: [] }>()
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
const resetting = computed(() => !!props.member)
const form = ref({
  fullName: '',
  email: '',
  phone: '',
  role: 'staff',
  password: '',
})
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)
const result = ref<{ name: string; email: string; password: string | null; phone: string } | null>(
  null,
)

watch(open, (isOpen) => {
  if (!isOpen) return
  form.value = { fullName: '', email: '', phone: '', role: 'staff', password: generatePassword() }
  errors.value = {}
  result.value = null
})

async function submit(): Promise<void> {
  errors.value = {}
  const f = form.value
  if (!resetting.value) {
    if (!f.fullName.trim()) errors.value.fullName = t('validation.required')
    if (!/^\S+@\S+\.\S+$/.test(f.email.trim())) errors.value.email = t('validation.email')
  }
  if (f.password.length < 8) errors.value.password = t('credentials.tooShort')
  if (Object.keys(errors.value).length) return
  saving.value = true
  try {
    if (props.member) {
      await organizationApi.setMemberPassword(props.member.id, f.password)
      result.value = {
        name: props.member.fullName,
        email: props.member.email,
        password: f.password,
        phone: props.member.phone,
      }
      toast.success(t('settings.team.passwordSet', { name: props.member.fullName }))
    } else {
      const created = await organizationApi.createMember({
        fullName: f.fullName.trim(),
        email: f.email.trim(),
        phone: f.phone.trim(),
        role: f.role as Exclude<Role, 'owner'>,
        password: f.password,
      })
      result.value = {
        name: created.member.fullName,
        email: created.member.email,
        password: created.createdAccount ? f.password : null,
        phone: f.phone.trim() || created.member.phone,
      }
      toast.success(t('settings.team.created', { name: created.member.fullName }))
    }
    emit('done')
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(
      Object.entries(apiError.fields).map(([k, v]) => [
        k.replace(/_(\w)/g, (_, c: string) => c.toUpperCase()),
        v[0],
      ]),
    )
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <WModal
    v-model:open="open"
    :title="
      result
        ? t('credentials.title')
        : resetting
          ? t('settings.team.newPasswordFor', { name: member?.fullName })
          : t('settings.team.create')
    "
  >
    <AccountCredentials
      v-if="result"
      :name="result.name"
      :email="result.email"
      :password="result.password"
      :phone="result.phone"
    />
    <form
      v-else
      id="member-account-form"
      class="flex flex-col gap-4"
      novalidate
      @submit.prevent="submit"
    >
      <template v-if="!resetting">
        <WInput
          v-model="form.fullName"
          :label="t('settings.team.fullName')"
          :error="errors.fullName"
          autocomplete="off"
          required
          autofocus
        />
        <div class="grid gap-4 sm:grid-cols-2">
          <WInput
            v-model="form.email"
            type="email"
            :label="t('auth.email')"
            :hint="t('settings.team.emailHint')"
            :error="errors.email"
            autocomplete="off"
            required
          />
          <WInput
            v-model="form.phone"
            type="tel"
            :label="t('settings.team.phone')"
            :hint="t('settings.team.phoneHint')"
            :error="errors.phone"
            autocomplete="off"
          />
        </div>
        <WSelect
          v-model="form.role"
          :label="t('settings.team.role')"
          :options="ROLES.map((r) => ({ value: r, label: t(`roles.${r}`) }))"
          :hint="t(`settings.team.roleHints.${form.role}`)"
          :error="errors.role"
        />
      </template>
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
      <template v-if="result">
        <WButton @click="open = false">{{ t('credentials.done') }}</WButton>
      </template>
      <template v-else>
        <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
        <WButton type="submit" form="member-account-form" :loading="saving">{{
          resetting ? t('settings.team.setPassword') : t('settings.team.createSubmit')
        }}</WButton>
      </template>
    </template>
  </WModal>
</template>
