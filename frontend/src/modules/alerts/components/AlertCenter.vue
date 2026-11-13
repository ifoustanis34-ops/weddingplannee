<script setup lang="ts">
import { Bell, Check, ChevronRight } from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'

import { useAlerts, useDismissAlert } from '../api'
import { alertDetail, alertTarget, SEVERITY } from '../format'

/**
 * The bell of the top bar (reservations-stock.md §2): the internal alert center. Stock alerts,
 * late returns and maintenance join with the stock module; nothing here ever reaches a client.
 */
const { t } = useI18n()
const toast = useToast()
const route = useRoute()
const alerts = useAlerts()
const dismiss = useDismissAlert()
const panelId = useId()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const rows = computed(() => alerts.data.value?.results ?? [])
const count = computed(() => alerts.data.value?.count ?? 0)
const urgent = computed(() => rows.value.some((a) => a.severity === 'critical'))

watch(
  () => route.fullPath,
  () => (open.value = false),
)

function onDocumentClick(event: MouseEvent): void {
  if (open.value && root.value && !root.value.contains(event.target as Node)) open.value = false
}
function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && open.value) {
    open.value = false
    button.value?.focus()
  }
}
onMounted(() => document.addEventListener('mousedown', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocumentClick))

async function handled(id: string): Promise<void> {
  try {
    await dismiss.mutateAsync(id)
    toast.success(t('alerts.handled'))
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
</script>

<template>
  <div ref="root" class="relative" @keydown="onKeydown">
    <button
      ref="button"
      type="button"
      class="relative inline-flex size-10 items-center justify-center rounded-[10px] border border-line-2 bg-surface text-ink-2 hover:bg-surface-2"
      :aria-label="count ? t('alerts.bellCount', { count }, count) : t('alerts.bell')"
      :aria-expanded="open"
      :aria-controls="panelId"
      data-testid="alert-bell"
      @click="open = !open"
    >
      <Bell class="size-[18px]" aria-hidden="true" />
      <span
        v-if="count"
        class="num absolute -top-1.5 -right-1.5 min-w-[19px] rounded-full px-1 text-center text-[11px] leading-[19px] font-bold text-white ring-2 ring-surface"
        :class="urgent ? 'bg-red' : 'bg-coral'"
        aria-hidden="true"
        >{{ count > 9 ? '9+' : count }}</span
      >
    </button>

    <Transition
      enter-from-class="opacity-0 -translate-y-1"
      leave-to-class="opacity-0 -translate-y-1"
      enter-active-class="transition duration-150 motion-reduce:transition-none"
      leave-active-class="transition duration-100 motion-reduce:transition-none"
    >
      <section
        v-if="open"
        :id="panelId"
        class="absolute right-0 z-40 mt-2 w-[min(380px,calc(100vw-32px))] overflow-hidden rounded-wd-lg border border-line bg-surface shadow-wd-lg"
        :aria-label="t('alerts.title')"
      >
        <header class="flex items-baseline justify-between gap-3 border-b border-line px-4 py-3">
          <h2 class="text-[15.5px] font-semibold">{{ t('alerts.title') }}</h2>
          <span class="text-[12.5px] font-semibold text-muted">{{ t('alerts.subtitle') }}</span>
        </header>
        <div v-if="alerts.isPending.value" class="p-4"><div class="skeleton h-16" /></div>
        <p v-else-if="!rows.length" class="flex items-center gap-2 px-4 py-6 text-muted">
          <Check class="size-[18px] text-green" aria-hidden="true" />{{ t('alerts.empty') }}
        </p>
        <ul
          v-else
          class="max-h-[min(420px,70vh)] divide-y divide-line overflow-y-auto"
          aria-live="polite"
        >
          <li v-for="alert in rows" :key="alert.id" class="flex items-start gap-3 px-4 py-3">
            <span
              class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-[9px]"
              :class="SEVERITY[alert.severity].classes"
            >
              <component
                :is="SEVERITY[alert.severity].icon"
                class="size-[16px]"
                aria-hidden="true"
              />
            </span>
            <div class="min-w-0 flex-1">
              <component
                :is="alertTarget(alert) ? 'RouterLink' : 'p'"
                :to="alertTarget(alert) ?? undefined"
                class="group flex items-center gap-1 font-bold"
              >
                <span class="truncate group-hover:text-violet">{{ alert.title }}</span>
                <ChevronRight
                  v-if="alertTarget(alert)"
                  class="size-[15px] shrink-0 text-muted"
                  aria-hidden="true"
                />
              </component>
              <p class="text-[12.5px] text-ink-2">
                <span class="font-semibold" :class="SEVERITY[alert.severity].text">{{
                  t(`dashboard.alerts.severity.${alert.severity}`)
                }}</span>
                · {{ alertDetail(alert) }}
              </p>
            </div>
            <button
              type="button"
              class="shrink-0 rounded-[8px] px-2 py-1 text-[12px] font-bold text-muted hover:bg-surface-2 hover:text-ink"
              :aria-label="t('alerts.handleFor', { title: alert.title })"
              :disabled="dismiss.isPending.value"
              @click="handled(alert.id)"
            >
              {{ t('alerts.handle') }}
            </button>
          </li>
        </ul>
      </section>
    </Transition>
  </div>
</template>
