<script setup lang="ts">
import { toTypedSchema } from '@/app/zodSchema'
import { CircleCheck, LoaderCircle } from '@lucide/vue'
import { type TypedSchema, useForm } from 'vee-validate'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { type Plan, type SignupPayload, authApi } from '@/api/auth'
import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WSelect } from '@/design'
import { useSessionStore } from '@/stores/session'

import PasswordInput from '../components/PasswordInput.vue'
import {
  COUNTRIES,
  SLUG_PATTERN,
  WEDDING_VOLUMES,
  type SignupForm,
  accountStepSchema,
  companyStepSchema,
  signupSchema,
  spaceStepSchema,
} from '../schemas'

const { t } = useI18n()
const router = useRouter()
const session = useSessionStore()
const toast = useToast()
const applyServerErrors = useServerErrors()

const STEPS = [
  {
    key: 'company',
    schema: companyStepSchema,
    fields: ['companyName', 'city', 'country', 'weddingsPerYear'],
  },
  { key: 'account', schema: accountStepSchema, fields: ['fullName', 'email', 'phone', 'password'] },
  { key: 'space', schema: spaceStepSchema, fields: ['slug'] },
] as const
const step = ref(0)
// One form across steps: values survive going back and forth; the current step's fields are
// required, the others stay optional (but still validated when filled).
const currentSchema = computed(
  () =>
    toTypedSchema(
      signupSchema.partial().extend(STEPS[step.value]!.schema.shape),
    ) as unknown as TypedSchema<SignupForm>,
)
const { defineField, errors, handleSubmit, isSubmitting, values } = useForm<SignupForm>({
  validationSchema: currentSchema,
  keepValuesOnUnmount: true,
  initialValues: { country: 'CM', plan: 'pro' as Plan, phone: '' },
})
const [companyName, companyNameAttrs] = defineField('companyName')
const [city, cityAttrs] = defineField('city')
const [country, countryAttrs] = defineField('country')
const [weddingsPerYear, weddingsPerYearAttrs] = defineField('weddingsPerYear')
const [fullName, fullNameAttrs] = defineField('fullName')
const [email, emailAttrs] = defineField('email')
const [phone, phoneAttrs] = defineField('phone')
const [password, passwordAttrs] = defineField('password')
const [slug, slugAttrs] = defineField('slug')

const countryOptions = COUNTRIES.map(([value, label]) => ({ value, label }))
const volumeOptions = computed(() =>
  WEDDING_VOLUMES.map((volume) => ({
    value: volume.value,
    label: t(`auth.signup.volumes.${volume.key}`),
  })),
)

// --- Server errors ---------------------------------------------------------------------
// Kept apart from vee-validate: changing step swaps the schema and resets its errors. A server
// message stays under its field until the planner edits that field.
type FieldName = keyof SignupForm
const serverErrors = ref<Partial<Record<FieldName, string>>>({})
const fieldError = (field: FieldName): string | undefined =>
  errors.value[field] ?? serverErrors.value[field]

watch(
  () => ({ ...values }),
  (current, previous) => {
    for (const field of Object.keys(serverErrors.value) as FieldName[]) {
      if (current[field] !== previous[field]) delete serverErrors.value[field]
    }
  },
)

// --- Live subdomain check ---------------------------------------------------------------
const slugEdited = ref(false)
const slugState = ref<{ checking: boolean; available: boolean | null; reason: string | null }>({
  checking: false,
  available: null,
  reason: null,
})
let slugTimer: ReturnType<typeof setTimeout> | undefined
let slugRequest = 0

async function suggestSlug(): Promise<void> {
  if (slugEdited.value || !values.companyName) return
  try {
    const result = await authApi.slugAvailable({ name: String(values.companyName) })
    if (!slugEdited.value) slug.value = result.slug
  } catch {
    // The planner can still type an address; the check below reports problems.
  }
}

watch(slug, (value) => {
  clearTimeout(slugTimer)
  slugState.value = { checking: false, available: null, reason: null }
  const candidate = String(value ?? '')
    .trim()
    .toLowerCase()
  if (!SLUG_PATTERN.test(candidate)) return
  slugState.value.checking = true
  const request = ++slugRequest
  slugTimer = setTimeout(async () => {
    try {
      const result = await authApi.slugAvailable({ slug: candidate })
      if (request !== slugRequest) return
      slugState.value = { checking: false, available: result.available, reason: result.reason }
    } catch {
      if (request === slugRequest) slugState.value.checking = false
    }
  }, 400)
})

function onSlugInput(): void {
  slugEdited.value = true
}

// --- Navigation and submit ----------------------------------------------------------------
const next = handleSubmit(async () => {
  if (step.value < STEPS.length - 1) {
    step.value += 1
    if (step.value === 2) await suggestSlug()
    return
  }
  if (slugState.value.available === false) {
    serverErrors.value.slug = slugState.value.reason ?? t('validation.slugUnavailable')
    return
  }
  await submit()
})

async function submit(): Promise<void> {
  const payload = {
    companyName: String(values.companyName ?? '').trim(),
    city: String(values.city ?? '').trim(),
    country: String(values.country ?? 'CM'),
    weddingsPerYear:
      typeof values.weddingsPerYear === 'number' && !Number.isNaN(values.weddingsPerYear)
        ? values.weddingsPerYear
        : null,
    fullName: String(values.fullName ?? '').trim(),
    email: String(values.email ?? '').trim(),
    phone: String(values.phone ?? '').trim(),
    password: String(values.password ?? ''),
    slug: String(values.slug ?? '')
      .trim()
      .toLowerCase(),
    plan: values.plan ?? 'pro',
  } satisfies SignupPayload
  try {
    await session.signup(payload)
    toast.success(t('auth.signup.created', { slug: payload.slug }))
    await router.push({ name: 'dashboard' })
  } catch (error) {
    const allFields: string[] = STEPS.flatMap((s) => [...s.fields])
    const failed = applyServerErrors(
      error,
      (field, message) => (serverErrors.value[field as FieldName] = message),
      allFields,
    )
    // Bring the planner back to the first step holding an error.
    const target = STEPS.findIndex((s) => s.fields.some((field) => failed.includes(field)))
    if (target >= 0 && target !== step.value) {
      step.value = target
      toast.error(t('auth.signup.fixErrors'))
    }
  }
}
</script>

<template>
  <div>
    <h1>{{ t('auth.signup.title') }}</h1>
    <p class="mt-1 text-muted">{{ t('auth.signup.subtitle') }}</p>

    <ol
      class="mt-6 grid grid-cols-3 gap-2"
      :aria-label="t('auth.signup.stepOf', { step: step + 1 })"
    >
      <li v-for="(item, index) in STEPS" :key="item.key">
        <div
          class="h-1 rounded-full"
          :class="index <= step ? 'bg-violet' : 'bg-line-2'"
          aria-hidden="true"
        />
        <p
          class="mt-2 text-[12.5px] font-bold"
          :class="index <= step ? 'text-ink' : 'text-muted'"
          :aria-current="index === step ? 'step' : undefined"
        >
          {{ index + 1 }}. {{ t(`auth.signup.steps.${item.key}`) }}
        </p>
      </li>
    </ol>

    <form class="mt-6 flex flex-col gap-4" novalidate @submit="next">
      <template v-if="step === 0">
        <WInput
          v-model="companyName"
          v-bind="companyNameAttrs"
          :label="t('auth.signup.companyName')"
          :placeholder="t('auth.signup.companyNamePlaceholder')"
          :error="fieldError('companyName')"
          autocomplete="organization"
          required
        />
        <div class="grid gap-4 sm:grid-cols-2">
          <WInput
            v-model="city"
            v-bind="cityAttrs"
            :label="t('auth.signup.city')"
            :error="fieldError('city')"
            autocomplete="address-level2"
            required
          />
          <WSelect
            v-model="country"
            v-bind="countryAttrs"
            :label="t('auth.signup.country')"
            :options="countryOptions"
            :error="fieldError('country')"
            required
          />
        </div>
        <WSelect
          v-model="weddingsPerYear"
          v-bind="weddingsPerYearAttrs"
          :label="t('auth.signup.weddingsPerYear')"
          :placeholder="t('auth.signup.weddingsPerYearPlaceholder')"
          :options="volumeOptions"
          :error="errors.weddingsPerYear ? t('validation.number') : serverErrors.weddingsPerYear"
        />
      </template>

      <template v-else-if="step === 1">
        <WInput
          v-model="fullName"
          v-bind="fullNameAttrs"
          :label="t('auth.signup.fullName')"
          :error="fieldError('fullName')"
          autocomplete="name"
          required
        />
        <WInput
          v-model="email"
          v-bind="emailAttrs"
          :label="t('auth.workEmail')"
          :error="fieldError('email')"
          type="email"
          autocomplete="email"
          inputmode="email"
          required
        />
        <WInput
          v-model="phone"
          v-bind="phoneAttrs"
          :label="t('auth.signup.phone')"
          :hint="t('auth.signup.phoneHint')"
          :error="fieldError('phone')"
          type="tel"
          autocomplete="tel"
        />
        <PasswordInput
          v-model="password"
          v-bind="passwordAttrs"
          :label="t('auth.password')"
          :hint="t('auth.signup.passwordHint')"
          :error="fieldError('password')"
          autocomplete="new-password"
          required
        />
      </template>

      <template v-else>
        <WInput
          v-model="slug"
          v-bind="slugAttrs"
          :label="t('auth.signup.slug')"
          addon=".wedivo.pro"
          :error="
            fieldError('slug') ??
            (slugState.available === false ? (slugState.reason ?? undefined) : undefined)
          "
          autocapitalize="none"
          autocomplete="off"
          spellcheck="false"
          required
          @input="onSlugInput"
        />
        <p
          v-if="!fieldError('slug') && (slugState.checking || slugState.available)"
          class="-mt-2 flex items-center gap-1.5 text-[13px] font-semibold"
          :class="slugState.available ? 'text-green' : 'text-muted'"
          aria-live="polite"
        >
          <LoaderCircle
            v-if="slugState.checking"
            class="size-3.5 animate-spin"
            aria-hidden="true"
          />
          <CircleCheck v-else class="size-3.5" aria-hidden="true" />
          {{ slugState.checking ? t('auth.signup.slugChecking') : t('auth.signup.slugAvailable') }}
        </p>

        <!-- No offer nor price for now (feedback 15/11/2026): all features included. -->
        <p class="rounded-wd bg-violet-soft px-3.5 py-3 text-[13.5px] text-ink-2">
          {{ t('auth.signup.allIncluded') }}
        </p>
      </template>

      <div class="mt-2 flex gap-2">
        <WButton
          v-if="step > 0"
          size="lg"
          variant="secondary"
          :disabled="isSubmitting"
          @click="step -= 1"
        >
          {{ t('common.back') }}
        </WButton>
        <WButton type="submit" size="lg" class="flex-1" :loading="isSubmitting">
          {{ step < STEPS.length - 1 ? t('auth.signup.continue') : t('auth.signup.submit') }}
        </WButton>
      </div>
    </form>
  </div>
</template>
