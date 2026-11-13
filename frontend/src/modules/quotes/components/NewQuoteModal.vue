<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WModal, WSelect } from '@/design'
import { useClients } from '@/modules/crm/api'

import { quotesApi, useQuotes } from '../api'

const props = defineProps<{ clientId?: string }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const router = useRouter()
const toast = useToast()

const clients = useClients({})
const templates = useQuotes({ status: 'templates' })
const client = ref<string>('')
const template = ref<string>('')
const error = ref<string>()
const busy = ref(false)

watch(open, (isOpen) => {
  if (isOpen) {
    client.value = props.clientId ?? ''
    template.value = ''
    error.value = undefined
  }
})

const clientOptions = computed(() =>
  (clients.data.value?.results ?? []).map((c) => ({ value: c.id, label: c.name })),
)
const templateOptions = computed(() => [
  { value: '', label: t('quotes.blank') },
  ...(templates.data.value?.results ?? []).map((q) => ({ value: q.id, label: q.templateName })),
])

async function start(): Promise<void> {
  if (!client.value) {
    error.value = t('quotes.chooseClient')
    return
  }
  if (!template.value) {
    open.value = false
    await router.push({ name: 'quote-new', query: { client: client.value } })
    return
  }
  busy.value = true
  try {
    const quote = await quotesApi.duplicate(template.value, { client: client.value })
    open.value = false
    await router.push({ name: 'quote-edit', params: { id: quote.id } })
  } catch (failure) {
    toast.error(toApiError(failure).message)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="t('quotes.new')" size="sm">
    <form id="new-quote-form" class="flex flex-col gap-4" @submit.prevent="start">
      <WSelect
        v-model="client"
        :label="t('quotes.client')"
        :options="clientOptions"
        :placeholder="t('quotes.chooseClient')"
        :error="error"
        required
      />
      <WSelect v-model="template" :label="t('quotes.startFrom')" :options="templateOptions" />
    </form>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton type="submit" form="new-quote-form" :loading="busy">{{
        t('quotes.create')
      }}</WButton>
    </template>
  </WModal>
</template>
