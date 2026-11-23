<script setup lang="ts">
import HoneypotField from '@/components/HoneypotField.vue'
import { toTypedSchema } from '@/app/zodSchema'
import { useForm } from 'vee-validate'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { safeRedirect } from '@/app/router'
import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput } from '@/design'
import { useSessionStore } from '@/stores/session'

import PasswordInput from '../components/PasswordInput.vue'
import { loginSchema } from '../schemas'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const toast = useToast()
const applyServerErrors = useServerErrors()

const { defineField, errors, handleSubmit, isSubmitting, setFieldError } = useForm({
  validationSchema: toTypedSchema(loginSchema),
})
const [email, emailAttrs] = defineField('email')
const [password, passwordAttrs] = defineField('password')

const onSubmit = handleSubmit(async (values) => {
  try {
    await session.login(values.email, values.password)
    toast.success(t('auth.login.welcome', { name: session.firstName }))
    await router.push(safeRedirect(route.query.redirect))
  } catch (error) {
    applyServerErrors(error, (field, message) => setFieldError(field as 'email', message), [
      'email',
      'password',
    ])
  }
})
</script>

<template>
  <div>
    <h1>{{ t('auth.login.title') }}</h1>
    <p class="mt-1 text-muted">{{ t('auth.login.subtitle') }}</p>

    <form class="relative mt-7 flex flex-col gap-4" novalidate @submit="onSubmit">
      <HoneypotField />
      <WInput
        v-model="email"
        v-bind="emailAttrs"
        :label="t('auth.workEmail')"
        :error="errors.email"
        type="email"
        autocomplete="email"
        inputmode="email"
        required
      />
      <PasswordInput
        v-model="password"
        v-bind="passwordAttrs"
        :label="t('auth.password')"
        :error="errors.password"
        autocomplete="current-password"
        required
      >
        <template #label-aside>
          <RouterLink
            :to="{ name: 'forgot-password' }"
            class="text-[13px] font-bold text-violet hover:underline"
          >
            {{ t('auth.login.forgot') }}
          </RouterLink>
        </template>
      </PasswordInput>
      <WButton type="submit" size="lg" block class="mt-2" :loading="isSubmitting">{{
        t('auth.login.submit')
      }}</WButton>
    </form>
  </div>
</template>
