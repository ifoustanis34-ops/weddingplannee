<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal, WSelect } from '@/design'

import { ticketsApi, useTicketAction } from '../api'
import type { Guest, GuestInput } from '../types'

const props = defineProps<{ weddingId: string; guest: Guest | null; categories: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()

const empty = (): GuestInput => ({
  name: '',
  email: '',
  phone: '',
  seats: 1,
  category: props.categories[0] ?? '',
  table: '',
  notes: '',
})
const form = ref<GuestInput>(empty())
const errors = ref<Record<string, string | undefined>>({})

watch(open, (isOpen) => {
  if (!isOpen) return
  errors.value = {}
  const guest = props.guest
  form.value = guest
    ? {
        name: guest.name,
        email: guest.email,
        phone: guest.phone,
        seats: guest.seats,
        category: guest.category,
        table: guest.table,
        notes: guest.notes,
      }
    : empty()
})

const categoryOptions = computed(() => {
  const values = new Set([...props.categories, form.value.category].filter(Boolean))
  return [
    { value: '', label: t('tickets.guests.noCategory') },
    ...[...values].map((v) => ({ value: v, label: v })),
  ]
})

const save = useTicketAction((input: GuestInput) =>
  props.guest
    ? ticketsApi.updateGuest(props.guest.id, input)
    : ticketsApi.addGuest(props.weddingId, input),
)

async function submit(): Promise<void> {
  errors.value = {}
  if (!form.value.name.trim()) errors.value.name = t('validation.required')
  if (!(form.value.seats >= 1 && form.value.seats <= 50))
    errors.value.seats = t('tickets.guests.seatsRange')
  if (Object.values(errors.value).some(Boolean)) return
  try {
    await save.mutateAsync({ ...form.value, name: form.value.name.trim() })
    toast.success(
      props.guest
        ? t('tickets.guests.saved')
        : t('tickets.guests.added', { name: form.value.name }),
    )
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="guest ? t('tickets.guests.edit') : t('tickets.guests.add')">
    <form id="guest-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
      <WInput
        v-model="form.name"
        class="sm:col-span-2"
        :label="t('tickets.guests.name')"
        :hint="t('tickets.guests.nameHint')"
        :error="errors.name"
        maxlength="120"
        required
        autofocus
      />
      <WInput
        v-model.number="form.seats"
        :label="t('tickets.guests.seats')"
        type="number"
        min="1"
        max="50"
        :error="errors.seats"
      />
      <WSelect
        v-model="form.category"
        :label="t('tickets.guests.category')"
        :options="categoryOptions"
      />
      <WInput v-model="form.table" :label="t('tickets.guests.table')" maxlength="30" />
      <WInput v-model="form.phone" :label="t('tickets.guests.phone')" type="tel" maxlength="32" />
      <WInput
        v-model="form.email"
        class="sm:col-span-2"
        :label="t('tickets.guests.email')"
        type="email"
        :error="errors.email"
      />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="guest-form" :loading="save.isPending.value">{{
        guest ? t('tickets.guests.save') : t('tickets.guests.add')
      }}</WButton>
    </template>
  </WModal>
</template>
