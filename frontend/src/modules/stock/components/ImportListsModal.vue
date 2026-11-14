<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { Download, FileCheck2, Upload } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { WButton, WModal, WNote } from '@/design'

import { stockApi, stockKeys } from '../api'
import type { ImportReport } from '../types'

/**
 * The agency's two equipment lists in one sheet (feedback 14/11/2026): ours with exact
 * quantities, and what each partner can lend. Checked first (nothing saved), then imported.
 */
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const queryClient = useQueryClient()

const file = ref<File | null>(null)
const report = ref<ImportReport | null>(null)
const busy = ref(false)
watch(open, (isOpen) => {
  if (isOpen) {
    file.value = null
    report.value = null
  }
})

const SUMMARY = [
  'itemsCreated',
  'itemsUpdated',
  'stockAdjusted',
  'partnersCreated',
  'suppliesCreated',
  'suppliesUpdated',
] as const
const lines = computed(() =>
  report.value
    ? SUMMARY.filter((key) => report.value![key] > 0).map((key) => ({
        key,
        count: report.value![key],
      }))
    : [],
)
const checked = computed(() => !!report.value?.dryRun && !report.value.errors.length)

function pick(event: Event): void {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
  report.value = null
}

async function downloadTemplate(): Promise<void> {
  try {
    const blob = await stockApi.importTemplate()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'modele-materiel-wedivo.xlsx'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}

async function run(dryRun: boolean): Promise<void> {
  if (!file.value) return
  busy.value = true
  try {
    report.value = await stockApi.importLists(file.value, dryRun)
    if (!dryRun && !report.value.errors.length) {
      void queryClient.invalidateQueries({ queryKey: stockKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['vendors'] })
      toast.success(t('stock.import.done'))
    }
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <WModal v-model:open="open" size="lg" :title="t('stock.import.title')">
    <div class="flex flex-col gap-4">
      <p class="text-ink-2">{{ t('stock.import.intro') }}</p>
      <WNote>{{ t('stock.import.columns') }}</WNote>
      <WButton variant="secondary" class="self-start" @click="downloadTemplate">
        <Download class="size-[16px]" aria-hidden="true" />{{ t('stock.import.template') }}
      </WButton>
      <label
        class="flex cursor-pointer flex-col items-center gap-2 rounded-wd border border-dashed border-line-2 px-4 py-6 text-center hover:bg-surface-2"
      >
        <Upload class="size-6 text-violet" aria-hidden="true" />
        <span class="font-bold">{{ file ? file.name : t('stock.import.file') }}</span>
        <input type="file" accept=".xlsx,.csv" class="sr-only" @change="pick" />
      </label>

      <div v-if="report" class="flex flex-col gap-3" role="status">
        <div
          v-if="report.errors.length"
          class="rounded-wd border border-red bg-red-soft px-3.5 py-3 text-[13.5px]"
        >
          <p class="font-bold text-red">{{ t('stock.import.errorsTitle') }}</p>
          <ul class="mt-1 list-disc pl-5">
            <li v-for="error in report.errors" :key="error">{{ error }}</li>
          </ul>
        </div>
        <div v-else class="rounded-wd border border-line px-3.5 py-3 text-[13.5px]">
          <p class="flex items-center gap-2 font-bold">
            <FileCheck2 class="size-4 text-green" aria-hidden="true" />{{
              report.dryRun ? t('stock.import.checking') : t('stock.import.done')
            }}
          </p>
          <ul class="mt-1.5 grid gap-1 sm:grid-cols-2">
            <li v-for="line in lines" :key="line.key">
              <span class="num font-bold">{{ line.count }}</span>
              {{ t(`stock.import.summary.${line.key}`) }}
            </li>
          </ul>
        </div>
        <div
          v-if="report.warnings.length"
          class="rounded-wd bg-gold-soft px-3.5 py-3 text-[13.5px]"
        >
          <p class="font-bold">{{ t('stock.import.warningsTitle') }}</p>
          <ul class="mt-1 list-disc pl-5">
            <li v-for="warning in report.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>
      </div>
    </div>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.close') }}</WButton>
      <WButton v-if="!checked" :disabled="!file" :loading="busy" @click="run(true)">{{
        t('stock.import.preview')
      }}</WButton>
      <WButton v-else :loading="busy" @click="run(false)">{{ t('stock.import.apply') }}</WButton>
    </template>
  </WModal>
</template>
