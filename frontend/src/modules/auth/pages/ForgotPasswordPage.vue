<script setup lang="ts">
import HoneypotField from '@/components/HoneypotField.vue'
import { toTypedSchema } from '@/app/zodSchema'
import { MailCheck } from '@lucide/vue'
import { useForm } from 'vee-validate'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { z } from 'zod'

import { authApi } from '@/api/auth'
import { useServerErrors } from '@/composables/useServerErrors'
import { WButton, WInput } from '@/design'

import { emailSchema } from '../schemas'

const { t } = useI18n()
const applyServerErrors = useServerErrors()
const sent = ref(false)

const { defineField, errors, handleSubmit, isSubmitting, setFieldError } = useForm({
  validationSchema: toTypedSchema(z.object({ email: emailSchema })),
})
const [email, emailAttrs] = defineField('email')

const onSubmit = handleSubmit(async (values) => {
  try {
    await authApi.requestPasswordReset(values.email)
    sent.value = true
  } catch (error) {
    applyServerErrors(error, (field, message) => setFieldError(field as 'email', message), [
      'email',
    ])
  }
})
</script>

<template>
  <div>
    <h1 class="text-[26px] font-semibold">{{ t('auth.forgot.title') }}</h1>
    <div
      v-if="sent"
      class="mt-6 flex gap-3 rounded-wd border border-line bg-surface p-4"
      role="status"
    >
      <MailCheck class="mt-0.5 size-5 shrink-0 text-green" aria-hidden="true" />
      <p>{{ t('auth.forgot.sent') }}</p>
    </div>
    <template v-else>
      <p class="mt-1 text-muted">{{ t('auth.forgot.subtitle') }}</p>
      <form class="relative mt-8 flex flex-col gap-4" novalidate @submit="onSubmit">
        <HoneypotField />
        <WInput
          v-model="email"
          v-bind="emailAttrs"
          :label="t('auth.email')"
          :error="errors.email"
          type="email"
          autocomplete="email"
          required
        />
        <WButton type="submit" block :loading="isSubmitting">{{ t('auth.forgot.submit') }}</WButton>
      </form>
    </template>
    <RouterLink
      :to="{ name: 'login' }"
      class="mt-8 block text-center font-bold text-violet hover:underline"
    >
      {{ t('auth.forgot.backToLogin') }}
    </RouterLink>
  </div>
</template>
