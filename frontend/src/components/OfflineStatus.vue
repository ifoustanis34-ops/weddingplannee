<script setup lang="ts">
import { CloudOff, RefreshCw, TriangleAlert } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatDateTime } from '@/composables/useDate'
import { WButton, WModal } from '@/design'
import {
  discard,
  failed,
  flush,
  online,
  pending,
  type PendingChange,
  retry,
  syncing,
} from '@/offline/queue'

/**
 * Top bar state of the offline mode (feedback 20/11/2026): « Hors ligne », changes waiting to
 * leave, sending, or refused on their return. Hidden while online with nothing waiting.
 */
const { t } = useI18n()
const open = ref(false)
const visible = computed(
  () => !online.value || syncing.value || pending.value.length > 0 || failed.value.length > 0,
)
const label = computed(() => {
  if (syncing.value) return t('offline.syncing')
  if (failed.value.length) return t('offline.failedShort', { count: failed.value.length })
  if (!online.value)
    return pending.value.length
      ? t('offline.offlinePending', { count: pending.value.length })
      : t('offline.offline')
  return t('offline.pendingShort', { count: pending.value.length })
})
const tone = computed(() =>
  failed.value.length
    ? 'border-red bg-red-soft text-red'
    : !online.value
      ? 'border-line-2 bg-grey-soft text-ink-2'
      : 'border-violet bg-violet-soft text-violet',
)

const SECTIONS = [
  'quotes',
  'clients',
  'prospects',
  'reservations',
  'floor-plans',
  'staff',
  'stock',
  'items',
  'payments',
  'expenses',
  'weddings',
  'vendors',
  'tasks',
]
function describe(change: PendingChange): string {
  const segment = change.url.split('/').filter(Boolean)[0] ?? ''
  const section = SECTIONS.includes(segment) ? t(`offline.sections.${segment}`) : 'Wedivo'
  const action =
    change.method === 'delete'
      ? t('offline.actions.delete')
      : change.method === 'post'
        ? t('offline.actions.create')
        : t('offline.actions.update')
  return `${section} · ${action}`
}
</script>

<template>
  <button
    v-if="visible"
    type="button"
    class="inline-flex h-10 shrink-0 items-center gap-2 rounded-[10px] border px-3 text-[13px] font-bold"
    :class="tone"
    :aria-label="label"
    @click="open = true"
  >
    <RefreshCw v-if="syncing" class="size-[16px] animate-spin" aria-hidden="true" />
    <TriangleAlert v-else-if="failed.length" class="size-[16px]" aria-hidden="true" />
    <CloudOff v-else class="size-[16px]" aria-hidden="true" />
    <span class="hidden sm:inline">{{ label }}</span>
    <span v-if="pending.length + failed.length" class="num sm:hidden">{{
      pending.length + failed.length
    }}</span>
  </button>

  <WModal v-model:open="open" :title="t('offline.title')" size="md">
    <p class="text-[14px] text-ink-2">
      {{ online ? t('offline.onlineText') : t('offline.offlineText') }}
    </p>

    <template v-if="failed.length">
      <h3 class="mt-4 text-[14px] font-semibold text-red">
        {{ t('offline.failedTitle', { count: failed.length }, failed.length) }}
      </h3>
      <ul class="mt-2 divide-y divide-line rounded-wd border border-line">
        <li v-for="change in failed" :key="change.id" class="flex flex-col gap-2 px-3 py-2.5">
          <div>
            <p class="font-semibold">{{ describe(change) }}</p>
            <p class="text-[12.5px] text-muted">{{ formatDateTime(change.createdAt) }}</p>
            <p class="mt-1 text-[13px] text-red">{{ change.error }}</p>
          </div>
          <div class="flex gap-2">
            <WButton size="sm" variant="secondary" :disabled="!online" @click="retry(change.id)">
              {{ t('offline.retry') }}
            </WButton>
            <WButton size="sm" variant="ghost" @click="discard(change.id)">
              {{ t('offline.discard') }}
            </WButton>
          </div>
        </li>
      </ul>
    </template>

    <template v-if="pending.length">
      <h3 class="mt-4 text-[14px] font-semibold">
        {{ t('offline.pendingTitle', { count: pending.length }, pending.length) }}
      </h3>
      <ul class="mt-2 divide-y divide-line rounded-wd border border-line">
        <li
          v-for="change in pending"
          :key="change.id"
          class="flex items-center justify-between gap-3 px-3 py-2.5"
        >
          <span class="font-semibold">{{ describe(change) }}</span>
          <span class="text-[12.5px] text-muted">{{ formatDateTime(change.createdAt) }}</span>
        </li>
      </ul>
    </template>

    <template #footer>
      <WButton variant="secondary" @click="open = false">{{ t('common.close') }}</WButton>
      <WButton v-if="pending.length" :disabled="!online" :loading="syncing" @click="flush">
        <RefreshCw class="size-4" aria-hidden="true" />{{ t('offline.sendNow') }}
      </WButton>
    </template>
  </WModal>
</template>
