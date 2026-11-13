<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
import { onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { WButton } from '@/design'

import { documentsApi } from '../api'
import type { QuoteInput } from '../types'

/**
 * The quote as the server renders it (docs/specs/devis-billets.md §3): the same image as the
 * PDF and the email. Refreshed 400 ms after the last change; the previous image stays shown,
 * dimmed, while the next one is rendered.
 */
const props = defineProps<{ quoteId: string | null; draft: QuoteInput }>()
const { t } = useI18n()

const DEBOUNCE_MS = 400
const url = ref<string | null>(null)
const pages = ref(1)
const loading = ref(false)
const failed = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | null = null

async function refresh(): Promise<void> {
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  failed.value = false
  try {
    const result = await documentsApi.preview(
      { kind: 'quote', quote: props.quoteId, draft: props.draft },
      controller.signal,
    )
    if (url.value) URL.revokeObjectURL(url.value)
    url.value = URL.createObjectURL(result.image)
    pages.value = result.pages
  } catch (error) {
    if ((error as { name?: string }).name === 'CanceledError') return
    failed.value = true
  } finally {
    loading.value = false
  }
}

watch(
  () => JSON.stringify([props.quoteId, props.draft]),
  () => {
    clearTimeout(timer)
    timer = setTimeout(refresh, DEBOUNCE_MS)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  clearTimeout(timer)
  controller?.abort()
  if (url.value) URL.revokeObjectURL(url.value)
})
</script>

<template>
  <div class="relative" :aria-busy="loading">
    <div
      v-if="!url && !failed"
      class="skeleton aspect-[210/297] w-full rounded-[14px]"
      :aria-label="t('quotes.preview.loading')"
    />
    <div
      v-else-if="failed && !url"
      class="flex aspect-[210/297] w-full flex-col items-center justify-center gap-3 rounded-[14px] border border-dashed border-line-2 p-6 text-center text-muted"
      role="alert"
    >
      <p>{{ t('quotes.preview.failed') }}</p>
      <WButton variant="secondary" size="sm" @click="refresh">
        <RefreshCw class="size-[15px]" aria-hidden="true" />{{ t('common.retry') }}
      </WButton>
    </div>
    <template v-else>
      <!-- The sheet is always white: it is the document, not the interface (CLAUDE.md). -->
      <img
        :src="url ?? undefined"
        :alt="t('quotes.preview.alt', { count: pages }, pages)"
        class="w-full rounded-[14px] border border-[#E5E2F0] bg-white shadow-wd transition-opacity"
        :class="loading && 'opacity-60'"
        data-testid="server-preview"
      />
      <p v-if="pages > 1" class="mt-2 text-center text-[12.5px] text-muted">
        {{ t('quotes.preview.pages', { count: pages }, pages) }}
      </p>
      <p v-if="failed" class="mt-2 text-center text-[12.5px] text-red" role="alert">
        {{ t('quotes.preview.stale') }}
      </p>
    </template>
  </div>
</template>
