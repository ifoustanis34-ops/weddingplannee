<script setup lang="ts">
import { Bell, BellOff, Download, Share, Smartphone } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { toApiError } from '@/api/errors'
import {
  currentSubscription,
  disablePush,
  enablePush,
  installable,
  installed,
  isIos,
  promptInstall,
  pushApi,
  pushSupported,
} from '@/app/pwa'
import { useToast } from '@/composables/useToast'
import { WBadge, WButton, WCard, WNote } from '@/design'

/**
 * « Application et notifications » (feedback 13/11/2026): install Wedivo on this device and turn
 * the push notifications on or off for it, with a test message.
 */
const { t } = useI18n()
const toast = useToast()

type State = 'loading' | 'unsupported' | 'off-server' | 'denied' | 'off' | 'on' | 'ios-install'
const state = ref<State>('loading')
const busy = ref(false)

async function refresh(): Promise<void> {
  if (!pushSupported()) {
    state.value = isIos() && !installed.value ? 'ios-install' : 'unsupported'
    return
  }
  try {
    const config = await pushApi.config()
    if (!config.enabled) state.value = 'off-server'
    else if (Notification.permission === 'denied') state.value = 'denied'
    else state.value = (await currentSubscription()) ? 'on' : 'off'
  } catch {
    state.value = 'unsupported'
  }
}
onMounted(refresh)

async function turnOn(): Promise<void> {
  busy.value = true
  try {
    const result = await enablePush()
    if (result === 'granted') toast.success(t('push.enabled'))
    else if (result === 'denied') toast.error(t('push.deniedToast'))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busy.value = false
    await refresh()
  }
}
async function turnOff(): Promise<void> {
  busy.value = true
  await disablePush()
  busy.value = false
  toast.success(t('push.disabled'))
  await refresh()
}
async function test(): Promise<void> {
  busy.value = true
  try {
    await pushApi.test()
    toast.success(t('push.testSent'))
  } catch (error) {
    toast.error(toApiError(error).message)
  } finally {
    busy.value = false
  }
}
async function install(): Promise<void> {
  if (await promptInstall()) toast.success(t('push.installed'))
}
</script>

<template>
  <WCard :title="t('push.title')" :subtitle="t('push.subtitle')">
    <div class="flex flex-col divide-y divide-line">
      <!-- Install -->
      <div class="flex flex-wrap items-center gap-3 pb-4">
        <span
          class="flex size-10 shrink-0 items-center justify-center rounded-[11px] bg-violet-soft text-violet"
        >
          <Smartphone class="size-5" aria-hidden="true" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block font-bold">{{ t('push.install') }}</span>
          <span class="block text-[13px] text-muted">{{
            installed
              ? t('push.installedText')
              : isIos()
                ? t('push.iosInstall')
                : t('push.installText')
          }}</span>
        </span>
        <WBadge v-if="installed" tone="green">{{ t('push.installedBadge') }}</WBadge>
        <WButton v-else-if="installable" @click="install">
          <Download class="size-[18px]" aria-hidden="true" />{{ t('push.installAction') }}
        </WButton>
        <Share v-else-if="isIos()" class="size-5 text-muted" aria-hidden="true" />
      </div>

      <!-- Notifications -->
      <div class="flex flex-wrap items-center gap-3 pt-4">
        <span
          class="flex size-10 shrink-0 items-center justify-center rounded-[11px]"
          :class="state === 'on' ? 'bg-green-soft text-green' : 'bg-surface-2 text-muted'"
        >
          <component :is="state === 'on' ? Bell : BellOff" class="size-5" aria-hidden="true" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block font-bold">{{ t('push.notifications') }}</span>
          <span class="block text-[13px] text-muted">{{ t(`push.states.${state}`) }}</span>
        </span>
        <template v-if="state === 'off'">
          <WButton :loading="busy" @click="turnOn">
            <Bell class="size-[18px]" aria-hidden="true" />{{ t('push.enable') }}
          </WButton>
        </template>
        <template v-else-if="state === 'on'">
          <WButton variant="secondary" :loading="busy" @click="test">{{ t('push.test') }}</WButton>
          <WButton variant="ghost" @click="turnOff">{{ t('push.disable') }}</WButton>
        </template>
      </div>
      <WNote v-if="state === 'on' || state === 'off'" class="mt-4">{{ t('push.what') }}</WNote>
    </div>
  </WCard>
</template>
