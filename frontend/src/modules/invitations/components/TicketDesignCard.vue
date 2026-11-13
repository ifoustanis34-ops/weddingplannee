<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { RefreshCw } from '@lucide/vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WCard, WInput, WSwitch, WTextarea } from '@/design'
import { documentsApi } from '@/modules/quotes/api'

import { ticketKeys, ticketsApi, useTicketDesign } from '../api'
import type { TicketDesign, TicketDesignInput } from '../types'

/**
 * « Informations communes » of the tickets (§6, §2f) with the server rendering on the right:
 * an example guest, the same image as the future tickets.
 */
const props = defineProps<{ weddingId: string; readOnly?: boolean }>()
const { t } = useI18n()
const toast = useToast()
const queryClient = useQueryClient()

const design = useTicketDesign(() => props.weddingId)
const palettes = useQuery({ queryKey: ['document-designs'], queryFn: documentsApi.designs })

type Form = Required<TicketDesignInput>
const form = ref<Form | null>(null)
const errors = ref<Record<string, string | undefined>>({})
const saving = ref(false)

function fill(value: TicketDesign): void {
  const copy: Partial<TicketDesign> = { ...value }
  delete copy.id
  delete copy.updatedAt
  delete copy.startsAt
  const rest = copy as Required<TicketDesignInput>
  form.value = {
    ...rest,
    categories: [...value.categories],
    startsAtLocal: value.startsAtLocal ?? '',
  }
}
watch(
  () => design.data.value,
  (value) => value && !form.value && fill(value),
  { immediate: true },
)

const payload = computed<TicketDesignInput>(() =>
  form.value ? { ...form.value, startsAtLocal: form.value.startsAtLocal || null } : {},
)
const categoriesText = computed({
  get: () => form.value?.categories.join(', ') ?? '',
  set: (text: string) => {
    if (form.value) form.value.categories = text.split(',').map((item) => item.trim())
  },
})

// --- Server preview, 400 ms after the last change ------------------------------------------
const previewUrl = ref<string | null>(null)
const previewLoading = ref(false)
const previewFailed = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | null = null

async function refreshPreview(): Promise<void> {
  if (!form.value) return
  controller?.abort()
  controller = new AbortController()
  previewLoading.value = true
  previewFailed.value = false
  try {
    const image = await ticketsApi.preview(props.weddingId, payload.value, controller.signal)
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = URL.createObjectURL(image)
  } catch (error) {
    if ((error as { name?: string }).name !== 'CanceledError') previewFailed.value = true
  } finally {
    previewLoading.value = false
  }
}
watch(
  () => JSON.stringify(payload.value),
  () => {
    clearTimeout(timer)
    timer = setTimeout(refreshPreview, 400)
  },
)
onBeforeUnmount(() => {
  clearTimeout(timer)
  controller?.abort()
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

async function save(): Promise<void> {
  if (!form.value) return
  saving.value = true
  errors.value = {}
  try {
    const saved = await ticketsApi.updateDesign(props.weddingId, payload.value)
    queryClient.setQueryData(ticketKeys.design(props.weddingId), saved)
    fill(saved)
    toast.success(t('tickets.design.saved'))
  } catch (error) {
    const apiError = toApiError(error)
    errors.value = Object.fromEntries(Object.entries(apiError.fields).map(([k, v]) => [k, v[0]]))
    toast.error(apiError.message)
  } finally {
    saving.value = false
  }
}

const TEXTS = [
  ['title', 40],
  ['subtitle', 40],
  ['panelText', 60],
  ['bottomSlogan', 60],
  ['scriptLine', 70],
  ['stubTitle', 30],
  ['stubSubtitle', 30],
  ['stubScript', 50],
  ['stubFooter', 30],
] as const
</script>

<template>
  <WCard :title="t('tickets.design.title')" :subtitle="t('tickets.design.subtitle')">
    <div v-if="design.isError.value" class="text-muted" role="alert">
      {{ t('tickets.design.loadError') }}
    </div>
    <div v-else-if="!form" class="skeleton h-80" />
    <div v-else class="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <form class="grid grid-cols-1 gap-3 sm:grid-cols-2" novalidate @submit.prevent="save">
        <WInput
          v-model="form.partner1"
          :label="t('tickets.design.partner1')"
          maxlength="40"
          :disabled="readOnly"
        />
        <WInput
          v-model="form.partner2"
          :label="t('tickets.design.partner2')"
          maxlength="40"
          :disabled="readOnly"
        />
        <WInput
          v-model="form.startsAtLocal"
          :label="t('tickets.design.startsAt')"
          type="datetime-local"
          :error="errors.startsAtLocal"
          :disabled="readOnly"
        />
        <WInput
          v-model="form.dressCode"
          :label="t('tickets.design.dressCode')"
          maxlength="60"
          :disabled="readOnly"
        />
        <WInput
          v-model="form.venue"
          :label="t('tickets.design.venue')"
          maxlength="80"
          :disabled="readOnly"
        />
        <WInput
          v-model="form.address"
          :label="t('tickets.design.address')"
          maxlength="80"
          :disabled="readOnly"
        />
        <WTextarea
          v-model="form.intro"
          class="sm:col-span-2"
          :label="t('tickets.design.intro')"
          :rows="2"
          maxlength="200"
          :disabled="readOnly"
        />
        <WInput
          v-model="categoriesText"
          class="sm:col-span-2"
          :label="t('tickets.design.categories')"
          :hint="t('tickets.design.categoriesHint')"
          :error="errors.categories"
          :disabled="readOnly"
        />
        <div class="sm:col-span-2">
          <p class="mb-2 font-bold">{{ t('tickets.design.palette') }}</p>
          <div
            role="radiogroup"
            :aria-label="t('tickets.design.palette')"
            class="flex flex-wrap gap-1.5"
          >
            <button
              v-for="palette in palettes.data.value?.palettes ?? []"
              :key="palette.code"
              type="button"
              role="radio"
              :aria-checked="form.palette === palette.code"
              :aria-label="palette.name"
              :title="palette.name"
              :disabled="readOnly"
              class="size-7 rounded-full border-2 disabled:opacity-50"
              :class="
                form.palette === palette.code
                  ? 'border-violet shadow-[0_0_0_3px_var(--violet-soft)]'
                  : 'border-line-2'
              "
              :style="{
                background: `linear-gradient(135deg, ${palette.dark} 0 55%, ${palette.accent} 55% 100%)`,
              }"
              @click="form.palette = palette.code"
            />
          </div>
        </div>
        <details class="sm:col-span-2">
          <summary class="cursor-pointer font-bold">{{ t('tickets.design.texts') }}</summary>
          <div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <WInput
              v-for="[key, max] in TEXTS"
              :key="key"
              v-model="form[key]"
              :label="t(`tickets.design.fields.${key}`)"
              :maxlength="max"
              :disabled="readOnly"
            />
            <WSwitch
              v-model="form.showMonogram"
              class="sm:col-span-2"
              :label="t('tickets.design.showMonogram')"
              :disabled="readOnly"
            />
          </div>
        </details>
        <div v-if="!readOnly" class="sm:col-span-2">
          <WButton type="submit" :loading="saving">{{ t('tickets.design.save') }}</WButton>
        </div>
      </form>

      <div class="min-w-0">
        <div
          v-if="!previewUrl && !previewFailed"
          class="skeleton aspect-[200/118] w-full rounded-wd"
        />
        <div
          v-else-if="previewFailed && !previewUrl"
          class="flex aspect-[200/118] w-full flex-col items-center justify-center gap-3 rounded-wd border border-dashed border-line-2 text-muted"
          role="alert"
        >
          <p>{{ t('tickets.design.previewFailed') }}</p>
          <WButton variant="secondary" size="sm" @click="refreshPreview">
            <RefreshCw class="size-[15px]" aria-hidden="true" />{{ t('common.retry') }}
          </WButton>
        </div>
        <img
          v-else
          :src="previewUrl ?? undefined"
          :alt="t('tickets.design.previewAlt')"
          class="w-full rounded-wd border border-line bg-white transition-opacity"
          :class="previewLoading && 'opacity-60'"
          data-testid="ticket-preview"
        />
        <p class="mt-2 text-[12.5px] text-muted">{{ t('tickets.design.previewHint') }}</p>
      </div>
    </div>
  </WCard>
</template>
