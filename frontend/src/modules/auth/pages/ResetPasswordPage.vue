<script setup lang="ts">
import { toTypedSchema } from '@/app/zodSchema'
import { useForm } from 'vee-validate'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { authApi } from '@/api/auth'
import { ApiError } from '@/api/errors'
import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton } from '@/design'

import PasswordInput from '../components/PasswordInput.vue'
import { resetSchema } from '../schemas'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const applyServerErrors = useServerErrors()

const uid = computed(() => (typeof route.query.uid === 'string' ? route.query.uid : ''))
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''))

const { defineField, errors, handleSubmit, isSubmitting, setFieldError } = useForm({
  validationSchema: toTypedSchema(resetSchema),
})
const [password, passwordAttrs] = defineField('password')
const [confirm, confirmAttrs] = defineField('confirm')

const onSubmit = handleSubmit(async (values) => {
  try {
    await authApi.confirmPasswordReset(uid.value, token.value, values.password)
    toast.success(t('auth.reset.done'))
    await router.push({ name: 'login' })
  } catch (error) {
    if (error instanceof ApiError && error.code === 'invalid_token') {
      toast.error(error.message)
      await router.push({ name: 'forgot-password' })
      return
    }
    applyServerErrors(error, (field, message) => setFieldError(field as 'password', message), [
      'password',
    ])
  }
})
</script>

<template>
  <div>
    <h1 class="text-[26px] font-semibold">{{ t('auth.reset.title') }}</h1>
    <template v-if="uid && token">
      <p class="mt-1 text-muted">{{ t('auth.reset.subtitle') }}</p>
      <form class="mt-8 flex flex-col gap-4" novalidate @submit="onSubmit">
        <PasswordInput
          v-model="password"
          v-bind="passwordAttrs"
          :label="t('auth.reset.password')"
          :error="errors.password"
          autocomplete="new-password"
          required
        />
        <PasswordInput
          v-model="confirm"
          v-bind="confirmAttrs"
          :label="t('auth.reset.confirm')"
          :error="errors.confirm"
          autocomplete="new-password"
          required
        />
        <WButton type="submit" block :loading="isSubmitting">{{ t('auth.reset.submit') }}</WButton>
      </form>
    </template>
    <div v-else class="mt-6 flex flex-col gap-4">
      <p class="rounded-r-wd border-l-[3px] border-red bg-red-soft px-4 py-3" role="alert">
        {{ t('auth.reset.invalidLink') }}
      </p>
      <WButton :to="{ name: 'forgot-password' }" variant="secondary">
        {{ t('auth.forgot.submit') }}
      </WButton>
    </div>
  </div>
</template>
