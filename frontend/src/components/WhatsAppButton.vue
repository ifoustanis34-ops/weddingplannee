<script setup lang="ts">
import { MessageCircle } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { useWhatsApp } from '@/composables/useWhatsApp'
import { WButton } from '@/design'

/**
 * « WhatsApp » next to a document (invoice, slip, order; feedback 20/11/2026): the PDF alone goes
 * to the recipient, from the planner's own WhatsApp (see `useWhatsApp`).
 */
const props = withDefaults(
  defineProps<{
    phone?: string | null
    file: () => Promise<Blob>
    filename: string
    /** Accessible name, e.g. « Envoyer FA-2026-0004 sur WhatsApp ». */
    label?: string
    /** Square icon-only button. */
    icon?: boolean
    size?: 'sm' | 'md'
  }>(),
  { phone: null, label: undefined, icon: false, size: 'sm' },
)
const { t } = useI18n()
const toast = useToast()
const whatsapp = useWhatsApp()

async function send(): Promise<void> {
  try {
    await whatsapp.share({
      phone: props.phone,
      file: props.file,
      filename: props.filename,
    })
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <WButton
    :size="size"
    variant="secondary"
    :icon="icon"
    :loading="whatsapp.pending.value"
    :aria-label="label ?? t('whatsapp.send')"
    :title="label ?? t('whatsapp.send')"
    class="text-green"
    @click="send"
  >
    <MessageCircle :class="size === 'sm' ? 'size-[15px]' : 'size-[18px]'" aria-hidden="true" />
    <template v-if="!icon">{{ t('whatsapp.short') }}</template>
  </WButton>
</template>
