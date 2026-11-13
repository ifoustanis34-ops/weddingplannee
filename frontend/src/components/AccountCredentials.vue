<script setup lang="ts">
import { Check, Copy, MessageCircle } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { accessMessage } from '@/app/passwords'
import { whatsappHref } from '@/app/support'
import { WButton, WNote } from '@/design'
import { useSessionStore } from '@/stores/session'

/**
 * What the owner hands over after opening an account (feedback 13/11/2026): email, temporary
 * password and a ready message to copy or to open in WhatsApp. Wedivo never sends it itself.
 */
const props = defineProps<{
  name: string
  email: string
  password: string | null
  phone?: string
}>()
const { t } = useI18n()
const session = useSessionStore()
const message = computed(() =>
  accessMessage({
    name: props.name,
    organization: session.currentOrganization?.name ?? '',
    email: props.email,
    password: props.password,
    url: `${window.location.origin}/connexion`,
  }),
)
const copied = ref(false)
async function copy(): Promise<void> {
  try {
    await navigator.clipboard.writeText(message.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2500)
  } catch {
    copied.value = false
  }
}
const whatsapp = computed(() =>
  props.phone && props.phone.replace(/\D/g, '').length >= 8
    ? `${whatsappHref(props.phone)}?text=${encodeURIComponent(message.value)}`
    : null,
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <dl
      class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-wd bg-surface-2 px-4 py-3 text-[14px]"
    >
      <dt class="text-muted">{{ t('credentials.email') }}</dt>
      <dd class="font-semibold break-all">{{ email }}</dd>
      <template v-if="password">
        <dt class="text-muted">{{ t('credentials.password') }}</dt>
        <dd class="num font-bold tracking-wide select-all">{{ password }}</dd>
      </template>
    </dl>
    <WNote>{{ password ? t('credentials.firstLogin') : t('credentials.existing') }}</WNote>
    <pre
      class="rounded-wd border border-line bg-surface px-3.5 py-3 font-sans text-[13px] whitespace-pre-wrap text-ink-2"
      >{{ message }}</pre>
    <div class="flex flex-wrap gap-2">
      <WButton variant="secondary" @click="copy">
        <component :is="copied ? Check : Copy" class="size-[16px]" aria-hidden="true" />{{
          copied ? t('credentials.copied') : t('credentials.copy')
        }}
      </WButton>
      <a
        v-if="whatsapp"
        :href="whatsapp"
        target="_blank"
        rel="noopener"
        class="inline-flex h-10 items-center gap-2 rounded-[10px] border border-violet px-4 text-[14px] font-bold text-violet hover:bg-violet-soft"
      >
        <MessageCircle class="size-[16px]" aria-hidden="true" />{{ t('credentials.whatsapp') }}
      </a>
    </div>
    <p class="sr-only" aria-live="polite">{{ copied ? t('credentials.copied') : '' }}</p>
  </div>
</template>
