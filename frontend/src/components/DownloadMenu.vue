<script setup lang="ts">
import { ChevronDown, Download, FileSpreadsheet, FileText, Table } from '@lucide/vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { api } from '@/api/client'
import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton } from '@/design'

/**
 * « Télécharger » (product request, Nov. 2026): the same button, top right of every screen,
 * gives what the screen lists in PDF (agency colors), CSV or Excel. `url` is the export
 * endpoint (`/exports/{kind}`, `/reports/{type}`…), `params` the screen's filters.
 */
type Format = 'pdf' | 'csv' | 'xlsx'
const props = withDefaults(
  defineProps<{
    url: string
    filename: string
    params?: Record<string, string | undefined>
    formats?: Format[]
    /** Name of the format parameter: `output` everywhere, `type` for the contracts export. */
    param?: string
  }>(),
  { params: () => ({}), formats: () => ['pdf', 'csv', 'xlsx'], param: 'output' },
)
const { t } = useI18n()
const toast = useToast()
const open = ref(false)
const busy = ref<Format | null>(null)
const root = ref<HTMLElement>()
const ICONS = { pdf: FileText, csv: Table, xlsx: FileSpreadsheet } as const

async function download(format: Format): Promise<void> {
  open.value = false
  busy.value = format
  try {
    const response = await api.get<Blob>(props.url, {
      params: { ...props.params, [props.param]: format },
      responseType: 'blob',
    })
    const href = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = href
    link.download = `${props.filename}.${format}`
    link.click()
    setTimeout(() => URL.revokeObjectURL(href), 60_000)
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busy.value = null
  }
}
function outside(event: MouseEvent): void {
  if (root.value && !root.value.contains(event.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('click', outside))
onBeforeUnmount(() => document.removeEventListener('click', outside))
</script>

<template>
  <div ref="root" class="relative" @keydown.escape="open = false">
    <WButton
      variant="secondary"
      :loading="busy !== null"
      :aria-expanded="open"
      aria-haspopup="menu"
      @click="open = !open"
    >
      <Download class="size-[18px]" aria-hidden="true" />{{ t('download.label') }}
      <ChevronDown class="size-4" aria-hidden="true" />
    </WButton>
    <div
      v-if="open"
      role="menu"
      class="absolute right-0 z-30 mt-1 flex w-52 flex-col rounded-wd border border-line bg-surface p-1 shadow-wd-lg"
    >
      <button
        v-for="format in formats"
        :key="format"
        type="button"
        role="menuitem"
        class="flex items-center gap-2.5 rounded-wd-sm px-3 py-2 text-left font-semibold hover:bg-violet-soft"
        @click="download(format)"
      >
        <component :is="ICONS[format]" class="size-4 text-violet" aria-hidden="true" />
        {{ t(`download.formats.${format}`) }}
      </button>
    </div>
  </div>
</template>
