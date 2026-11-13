<script setup lang="ts">
import { CircleCheck, LoaderCircle } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { authApi } from '@/api/auth'
import { toApiError } from '@/api/errors'
import { WButton } from '@/design'
import { useSessionStore } from '@/stores/session'

const { t } = useI18n()
const route = useRoute()
const session = useSessionStore()
const state = ref<'pending' | 'done' | 'error'>('pending')
const message = ref('')

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) {
    state.value = 'error'
    message.value = t('auth.verify.invalidLink')
    return
  }
  try {
    await authApi.verifyEmail(token)
    state.value = 'done'
    if (session.isAuthenticated) await session.refresh()
  } catch (error) {
    state.value = 'error'
    message.value = toApiError(error).message
  }
})
</script>

<template>
  <div aria-live="polite">
    <h1 class="text-[26px] font-semibold">{{ t('auth.verify.title') }}</h1>
    <p v-if="state === 'pending'" class="mt-6 flex items-center gap-2 text-muted">
      <LoaderCircle class="size-4 animate-spin" aria-hidden="true" />
      {{ t('auth.verify.pending') }}
    </p>
    <div v-else-if="state === 'done'" class="mt-6 flex flex-col gap-5">
      <p class="flex gap-3 rounded-wd border border-line bg-surface p-4">
        <CircleCheck class="mt-0.5 size-5 shrink-0 text-green" aria-hidden="true" />
        {{ t('auth.verify.done') }}
      </p>
      <WButton :to="{ name: session.isAuthenticated ? 'dashboard' : 'login' }">
        {{ session.isAuthenticated ? t('auth.verify.continue') : t('auth.verify.toLogin') }}
      </WButton>
    </div>
    <div v-else class="mt-6 flex flex-col gap-5">
      <p class="rounded-r-wd border-l-[3px] border-red bg-red-soft px-4 py-3" role="alert">
        {{ message }}
      </p>
      <WButton :to="{ name: session.isAuthenticated ? 'dashboard' : 'login' }" variant="secondary">
        {{ session.isAuthenticated ? t('auth.verify.continue') : t('auth.verify.toLogin') }}
      </WButton>
    </div>
  </div>
</template>
