<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { z } from 'zod'

import { useServerErrors } from '@/composables/useServerErrors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WTextarea } from '@/design'
import { i18n } from '@/i18n'

import { useCreateClient, useUpdateClient } from '../api'
import type { Client, ClientInput } from '../types'

const props = defineProps<{ client?: Client | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [client: Client] }>()

const { t } = useI18n()
const toast = useToast()
const applyServerErrors = useServerErrors()
const create = useCreateClient()
const update = useUpdateClient()
const isEdit = computed(() => Boolean(props.client))

const gt = (key: string) => i18n.global.t(key)
const text = (max: number) => z.string().trim().max(max).optional().default('')

// Same rules as crm.serializers.ClientSerializer.
const schema = z.object({
  name: z
    .string({ required_error: gt('validation.required') })
    .trim()
    .min(1, gt('clients.form.nameRequired'))
    .max(160),
  company: text(160),
  phone: text(32),
  phoneAlt: text(32),
  email: z
    .union([z.literal(''), z.string().trim().email(gt('validation.email'))])
    .optional()
    .default(''),
  address: z.string().optional().default(''),
  notes: z.string().optional().default(''),
  preferences: z.string().optional().default(''),
})
type FormValues = z.input<typeof schema>
type FormOutput = z.output<typeof schema>

const FIELDS = [
  'name',
  'company',
  'phone',
  'phoneAlt',
  'email',
  'address',
  'notes',
  'preferences',
] as const

const { defineField, errors, handleSubmit, isSubmitting, resetForm, setFieldError } = useForm<
  FormValues,
  FormOutput
>({ validationSchema: toTypedSchema(schema) })
const [name, nameAttrs] = defineField('name')
const [company] = defineField('company')
const [phone, phoneAttrs] = defineField('phone')
const [phoneAlt] = defineField('phoneAlt')
const [email, emailAttrs] = defineField('email')
const [address] = defineField('address')
const [notes] = defineField('notes')
const [preferences] = defineField('preferences')

watch(open, (isOpen) => {
  if (!isOpen) return
  const c = props.client
  resetForm({
    values: {
      name: c?.name ?? '',
      company: c?.company ?? '',
      phone: c?.phone ?? '',
      phoneAlt: c?.phoneAlt ?? '',
      email: c?.email ?? '',
      address: c?.address ?? '',
      notes: c?.notes ?? '',
      preferences: c?.preferences ?? '',
    },
  })
})

const onSubmit = handleSubmit(async (values) => {
  const input: ClientInput = { ...values }
  try {
    const saved = props.client
      ? await update.mutateAsync({ id: props.client.id, input })
      : await create.mutateAsync(input)
    toast.success(
      isEdit.value ? t('clients.form.saved') : t('clients.form.created', { name: saved.name }),
    )
    emit('saved', saved)
    open.value = false
  } catch (error) {
    applyServerErrors(error, (field, message) => setFieldError(field as 'name', message), FIELDS)
  }
})
</script>

<template>
  <WModal
    v-model:open="open"
    :title="isEdit ? t('clients.form.editTitle') : t('clients.form.createTitle')"
    size="md"
  >
    <form id="client-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit="onSubmit">
      <WInput
        v-model="name"
        v-bind="nameAttrs"
        class="sm:col-span-2"
        :label="t('clients.fields.name')"
        :placeholder="t('clients.placeholders.name')"
        :error="errors.name"
        required
        autofocus
      />
      <WInput
        v-model="company"
        class="sm:col-span-2"
        :label="t('clients.fields.company')"
        :error="errors.company"
        autocomplete="organization"
      />
      <WInput
        v-model="phone"
        v-bind="phoneAttrs"
        :label="t('clients.fields.phone')"
        :error="errors.phone"
        type="tel"
        autocomplete="off"
      />
      <WInput
        v-model="phoneAlt"
        :label="t('clients.fields.phoneAlt')"
        :error="errors.phoneAlt"
        type="tel"
        autocomplete="off"
      />
      <WInput
        v-model="email"
        v-bind="emailAttrs"
        class="sm:col-span-2"
        :label="t('clients.fields.email')"
        :error="errors.email"
        type="email"
        autocomplete="off"
      />
      <WTextarea
        v-model="address"
        class="sm:col-span-2"
        :label="t('clients.fields.address')"
        :error="errors.address"
        :rows="2"
      />
      <WTextarea
        v-model="preferences"
        class="sm:col-span-2"
        :label="t('clients.fields.preferences')"
        :placeholder="t('clients.placeholders.preferences')"
        :error="errors.preferences"
        :rows="2"
      />
      <WTextarea
        v-model="notes"
        class="sm:col-span-2"
        :label="t('clients.fields.notes')"
        :placeholder="t('clients.placeholders.notes')"
        :error="errors.notes"
        :rows="2"
      />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="client-form" :loading="isSubmitting">
        {{ isEdit ? t('clients.form.save') : t('clients.form.create') }}
      </WButton>
    </template>
  </WModal>
</template>
