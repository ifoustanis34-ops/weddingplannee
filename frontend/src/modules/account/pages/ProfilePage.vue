<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import PushSettings from '@/components/PushSettings.vue'
import { useToast } from '@/composables/useToast'
import { WAlert, WAvatar, WBadge, WButton, WCard, WInput } from '@/design'
import PasswordInput from '@/modules/auth/components/PasswordInput.vue'
import { useSessionStore } from '@/stores/session'

/**
 * « Mon profil » (feedback 13/11/2026): each person changes their own name, phone and password.
 * An account opened by the owner lands here first, to replace its temporary password.
 */
const { t } = useI18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const user = computed(() => session.user)
const mustChange = computed(() => !!user.value?.mustChangePassword)

// Identity
const identity = ref({ fullName: '', phone: '' })
const identityErrors = ref<Record<string, string | undefined>>({})
const savingIdentity = ref(false)
watch(
  user,
  (value) => {
    if (value) identity.value = { fullName: value.fullName, phone: value.phone }
  },
  { immediate: true },
)
const identityChanged = computed(
  () =>
    !!user.value &&
    (identity.value.fullName.trim() !== user.value.fullName ||
      identity.value.phone.trim() !== user.value.phone),
)
async function saveIdentity(): Promise<void> {
  identityErrors.value = {}
  if (!identity.value.fullName.trim()) {
    identityErrors.value.fullName = t('validation.required')
    return
  }
  savingIdentity.value = true
  try {
    await session.updateProfile({
      fullName: identity.value.fullName.trim(),
      phone: identity.value.phone.trim(),
    })
    toast.success(t('profile.saved'))
  } catch (error) {
    const apiError = toApiError(error)
    identityErrors.value = {
      fullName: apiError.fields.full_name?.[0],
      phone: apiError.fields.phone?.[0],
    }
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  } finally {
    savingIdentity.value = false
  }
}

// Password
const passwords = ref({ current: '', next: '', confirm: '' })
const passwordErrors = ref<Record<string, string | undefined>>({})
const savingPassword = ref(false)
async function savePassword(): Promise<void> {
  const p = passwords.value
  passwordErrors.value = {}
  if (!p.current) passwordErrors.value.current = t('validation.required')
  if (p.next.length < 8) passwordErrors.value.next = t('credentials.tooShort')
  else if (p.next !== p.confirm) passwordErrors.value.confirm = t('profile.mismatch')
  if (Object.keys(passwordErrors.value).length) return
  savingPassword.value = true
  const wasForced = mustChange.value
  try {
    await session.changePassword(p.current, p.next)
    passwords.value = { current: '', next: '', confirm: '' }
    toast.success(t('profile.passwordChanged'))
    if (wasForced)
      await router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
  } catch (error) {
    const apiError = toApiError(error)
    passwordErrors.value = {
      current: apiError.fields.current_password?.[0],
      next: apiError.fields.new_password?.[0],
    }
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  } finally {
    savingPassword.value = false
  }
}
</script>

<template>
  <div v-if="user" class="mx-auto flex w-full max-w-[860px] flex-col gap-5">
    <header class="flex items-center gap-4">
      <WAvatar :name="user.fullName" :size="56" />
      <div class="min-w-0">
        <h1>{{ t('profile.title') }}</h1>
        <p class="text-muted">{{ user.email }}</p>
      </div>
    </header>

    <WAlert
      v-if="mustChange"
      :title="t('profile.mustChangeTitle')"
      :text="t('profile.mustChangeText')"
    />

    <WCard :title="t('profile.password')" :subtitle="t('profile.passwordHint')">
      <form class="grid gap-4 sm:grid-cols-3" novalidate @submit.prevent="savePassword">
        <PasswordInput
          v-model="passwords.current"
          :label="mustChange ? t('profile.temporary') : t('profile.current')"
          :error="passwordErrors.current"
          autocomplete="current-password"
          required
        />
        <PasswordInput
          v-model="passwords.next"
          :label="t('profile.next')"
          :error="passwordErrors.next"
          autocomplete="new-password"
          required
        />
        <PasswordInput
          v-model="passwords.confirm"
          :label="t('profile.confirm')"
          :error="passwordErrors.confirm"
          autocomplete="new-password"
          required
        />
        <div class="sm:col-span-3">
          <WButton type="submit" :loading="savingPassword">{{ t('profile.savePassword') }}</WButton>
        </div>
      </form>
    </WCard>

    <WCard :title="t('profile.identity')" :subtitle="t('profile.identityHint')">
      <form class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="saveIdentity">
        <WInput
          v-model="identity.fullName"
          :label="t('profile.fullName')"
          :error="identityErrors.fullName"
          autocomplete="name"
          maxlength="120"
          required
        />
        <WInput
          v-model="identity.phone"
          type="tel"
          :label="t('profile.phone')"
          :error="identityErrors.phone"
          autocomplete="tel"
          maxlength="32"
        />
        <WInput
          :model-value="user.email"
          class="sm:col-span-2"
          :label="t('auth.email')"
          :hint="t('profile.emailHint')"
          readonly
          disabled
        />
        <div class="sm:col-span-2">
          <WButton type="submit" :loading="savingIdentity" :disabled="!identityChanged">{{
            t('profile.save')
          }}</WButton>
        </div>
      </form>
    </WCard>

    <PushSettings />

    <WCard :title="t('profile.spaces')" :subtitle="t('profile.spacesHint')">
      <ul class="flex flex-col divide-y divide-line">
        <li
          v-for="space in session.organizations"
          :key="space.organizationId"
          class="flex items-center justify-between gap-3 py-2.5"
        >
          <span class="font-semibold">{{ space.name }}</span>
          <WBadge :tone="space.role === 'owner' ? 'violet' : 'grey'">{{ space.roleLabel }}</WBadge>
        </li>
      </ul>
    </WCard>
  </div>
</template>
