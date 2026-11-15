<script setup lang="ts">
import { BellRing, X } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import { currentSubscription, enablePush, pushApi, pushSupported } from '@/app/pwa'
import { useToast } from '@/composables/useToast'
import { WButton } from '@/design'

/**
 * A quiet invitation on the home page (feedback 13/11/2026): turn on the notifications of this
 * device. Shown only while the browser can, the server is ready, the person has not decided yet;
 * « Plus tard » hides it on this device.
 */
const DISMISSED = 'wedivo-push-prompt-dismissed'
const { t } = useI18n()
const toast = useToast()
const visible = ref(false)
const busy = ref(false)

onMounted(async () => {
  try {
    if (!pushSupported() || Notification.permission !== 'default') return
    if (localStorage.getItem(DISMISSED)) return
    if (!(await pushApi.config()).enabled || (await currentSubscription())) return
    visible.value = true
  } catch {
    visible.value = false
  }
})

function later(): void {
  visible.value = false
  try {
    localStorage.setItem(DISMISSED, '1')
  } catch {
    // private mode: it will come back next time, that's fine
  }
}
async function enable(): Promise<void> {
  busy.value = true
  try {
    const result = await enablePush()
    if (result === 'granted') toast.success(t('push.enabled'))
    visible.value = false
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <!-- Phone: icon, text and close on one line, the button below at full width (it used to
       squeeze the text into a narrow column). From 640 px: everything on one line. -->
  <div
    v-if="visible"
    class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-3 rounded-wd-lg border border-violet/30 bg-violet-soft px-4 py-3 sm:flex sm:items-center"
    role="status"
  >
    <span class="flex size-10 shrink-0 items-center justify-center rounded-[11px] bg-surface">
      <BellRing class="size-5 text-violet" aria-hidden="true" />
    </span>
    <span class="min-w-0 sm:flex-1">
      <span class="block font-bold">{{ t('push.promptTitle') }}</span>
      <span class="block text-[13px] text-ink-2">{{ t('push.promptText') }}</span>
    </span>
    <WButton :loading="busy" class="col-span-3 row-start-2 sm:order-none" @click="enable">{{
      t('push.enable')
    }}</WButton>
    <button
      type="button"
      class="col-start-3 row-start-1 rounded-[8px] p-2 text-muted hover:bg-surface hover:text-ink"
      :aria-label="t('push.later')"
      :title="t('push.later')"
      @click="later"
    >
      <X class="size-4" aria-hidden="true" />
    </button>
  </div>
</template>
