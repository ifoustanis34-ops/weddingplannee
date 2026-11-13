<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WInput, WModal } from '@/design'

import { useWeddingAction, weddingsApi } from '../api'
import type { Wedding } from '../types'

/** « Nouveau mariage » (complement §11), with the 12 standard tasks as an option. */
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [wedding: Wedding] }>()
const { t } = useI18n()
const toast = useToast()

const title = ref('')
const date = ref('')
const guestCount = ref<number | null>(null)
const venue = ref('')
const standardTasks = ref(true)
const errors = ref<Record<string, string | undefined>>({})

watch(open, (isOpen) => {
  if (!isOpen) return
  title.value = ''
  date.value = ''
  guestCount.value = null
  venue.value = ''
  standardTasks.value = true
  errors.value = {}
})

const create = useWeddingAction(() =>
  weddingsApi.create({
    title: title.value.trim(),
    date: date.value || null,
    guestCount: typeof guestCount.value === 'number' ? guestCount.value : null,
    venue: venue.value.trim(),
    standardTasks: standardTasks.value,
  }),
)
async function submit(): Promise<void> {
  errors.value = {}
  if (!title.value.trim()) {
    errors.value.title = t('weddings.form.titleRequired')
    return
  }
  try {
    const wedding = await create.mutateAsync(undefined)
    toast.success(t('weddings.form.created', { title: wedding.title }))
    emit('created', wedding)
    open.value = false
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    if (!Object.keys(apiError.fields).length) toast.error(apiError.message)
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="t('weddings.new')">
    <form id="wedding-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="submit">
      <WInput
        v-model="title"
        class="sm:col-span-2"
        :label="t('weddings.form.couple')"
        :placeholder="t('weddings.form.couplePlaceholder')"
        :error="errors.title"
        required
        autofocus
      />
      <WInput
        v-model="date"
        type="date"
        :label="t('common.fields.weddingDate')"
        :error="errors.date"
      />
      <WInput
        v-model.number="guestCount"
        type="number"
        min="0"
        inputmode="numeric"
        :label="t('weddings.guests')"
        :error="errors.guestCount"
      />
      <WInput v-model="venue" class="sm:col-span-2" :label="t('weddings.form.venue')" />
      <label class="flex cursor-pointer items-center gap-2.5 font-semibold sm:col-span-2">
        <input v-model="standardTasks" type="checkbox" class="size-[18px] accent-[var(--violet)]" />
        {{ t('weddings.form.standardTasks') }}
      </label>
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="wedding-form" :loading="create.isPending.value">{{
        t('weddings.form.create')
      }}</WButton>
    </template>
  </WModal>
</template>
