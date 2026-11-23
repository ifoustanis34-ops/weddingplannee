<script setup lang="ts">
import { FileText, Share2 } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToast } from '@/composables/useToast'
import { openShareSheet, readyShare } from '@/composables/useWhatsApp'
import { WButton, WModal } from '@/design'

/**
 * The document is ready but the phone wants a fresh tap before opening the share sheet (the
 * PDF took a few seconds to prepare): one button, the sheet opens at once.
 */
const { t } = useI18n()
const toast = useToast()
const open = computed({
  get: () => readyShare.value !== null,
  set: (value) => {
    if (!value) readyShare.value = null
  },
})

async function share(): Promise<void> {
  const ready = readyShare.value
  if (!ready) return
  readyShare.value = null
  try {
    await openShareSheet(ready.data, ready.filename)
  } catch {
    toast.error(t('share.failed'))
  }
}
</script>

<template>
  <WModal v-model:open="open" :title="t('share.readyTitle')" size="sm">
    <p class="flex items-center gap-2 font-semibold">
      <FileText class="size-5 text-violet" aria-hidden="true" />{{ readyShare?.filename }}
    </p>
    <p class="mt-2 text-[14px] text-ink-2">{{ t('share.readyText') }}</p>
    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.cancel') }}</WButton>
      <WButton @click="share"
        ><Share2 class="size-4" aria-hidden="true" />{{ t('share.send') }}</WButton
      >
    </template>
  </WModal>
</template>
