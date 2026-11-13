<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { invitationApi } from '@/api/auth'
import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WEmptyState, WInput } from '@/design'
import { useSessionStore } from '@/stores/session'

import PasswordInput from '../components/PasswordInput.vue'

/** Team invitation link: join the space (new account, or existing account with its password). */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const session = useSessionStore()

const token = computed(() => String(route.params.token))
const preview = useQuery({
  queryKey: computed(() => ['invitation', token.value]),
  queryFn: () => invitationApi.preview(token.value),
  retry: false,
})

const fullName = ref('')
const password = ref('')
const errors = ref<Record<string, string | undefined>>({})
const joining = ref(false)

async function join(): Promise<void> {
  const invitation = preview.data.value
  if (!invitation) return
  errors.value = {}
  if (!invitation.hasAccount && !fullName.value.trim()) {
    errors.value.fullName = t('validation.fullName')
    return
  }
  if (!invitation.hasAccount && password.value.length < 8) {
    errors.value.password = t('validation.passwordLength')
    return
  }
  joining.value = true
  try {
    await session.acceptInvitation(
      token.value,
      { fullName: fullName.value.trim(), password: password.value },
      invitation.organizationSlug,
    )
    toast.success(t('auth.invitation.joined', { name: invitation.organizationName }))
    await router.push({ name: 'dashboard' })
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    if (apiError.code === 'invalid_credentials') errors.value.password = apiError.message
    else if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  } finally {
    joining.value = false
  }
}
</script>

<template>
  <div>
    <div v-if="preview.isPending.value" class="skeleton h-64" />
    <WEmptyState
      v-else-if="preview.isError.value || !preview.data.value"
      :title="t('auth.invitation.invalidTitle')"
      :description="toApiError(preview.error.value).message"
    >
      <WButton :to="{ name: 'login' }" variant="secondary">{{ t('auth.login.submit') }}</WButton>
    </WEmptyState>
    <template v-else>
      <h1>{{ t('auth.invitation.title', { name: preview.data.value.organizationName }) }}</h1>
      <p class="mt-1 text-muted">
        {{
          t('auth.invitation.subtitle', {
            inviter: preview.data.value.invitedByName ?? t('auth.invitation.team'),
            role: preview.data.value.roleLabel,
          })
        }}
      </p>
      <form class="mt-7 flex flex-col gap-4" novalidate @submit.prevent="join">
        <WInput
          :model-value="preview.data.value.email"
          :label="t('auth.workEmail')"
          type="email"
          disabled
        />
        <WInput
          v-if="!preview.data.value.hasAccount"
          v-model="fullName"
          :label="t('auth.signup.fullName')"
          :error="errors.fullName ?? errors.full_name"
          autocomplete="name"
          required
        />
        <PasswordInput
          v-model="password"
          :label="
            preview.data.value.hasAccount ? t('auth.password') : t('auth.invitation.newPassword')
          "
          :hint="
            preview.data.value.hasAccount
              ? t('auth.invitation.existing')
              : t('auth.signup.passwordHint')
          "
          :error="errors.password"
          :autocomplete="preview.data.value.hasAccount ? 'current-password' : 'new-password'"
          required
        />
        <WButton type="submit" size="lg" block class="mt-2" :loading="joining">{{
          t('auth.invitation.join')
        }}</WButton>
      </form>
    </template>
  </div>
</template>
