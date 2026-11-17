<script setup lang="ts">
import { Bell, Check, CheckCheck, ChevronRight } from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { toApiError } from '@/api/errors'
import { useToast } from '@/composables/useToast'
import { type AppNotification, useInbox, useMarkRead } from '@/modules/notifications/api'
import { showUnread } from '@/modules/notifications/badge'
import { ago, kindIcon } from '@/modules/notifications/format'

import { useAlerts, useDismissAlert } from '../api'
import { alertDetail, alertTarget, SEVERITY } from '../format'

/**
 * The bell of the top bar (feedback 17/11/2026, like WhatsApp): « Notifications » — every event
 * of the flow, unread in bold, the red count on the bell, the app icon and the tab title — and
 * « Alertes », the situations to handle (reservations-stock.md §2). Real time: a push refreshes
 * it at once; otherwise it is read again every 10 s and when the tab comes back.
 */
const { t } = useI18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const alerts = useAlerts()
const dismiss = useDismissAlert()
const inbox = useInbox()
const markRead = useMarkRead()
const panelId = useId()

const open = ref(false)
const tab = ref<'notifications' | 'alerts'>('notifications')
const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const rows = computed(() => alerts.data.value?.results ?? [])
const alertCount = computed(() => alerts.data.value?.count ?? 0)
const urgent = computed(() => rows.value.some((a) => a.severity === 'critical'))
const notifications = computed(() => inbox.data.value?.results ?? [])
const unread = computed(() => inbox.data.value?.unread ?? 0)

// The count outside the page: app icon (installed app) and « (3) Wedivo » in the tab.
watch(
  () => inbox.data.value?.unreadAll ?? 0,
  (count) => showUnread(count),
  { immediate: true },
)
onBeforeUnmount(() => showUnread(0))

/** The bell shows the unread notifications; with none, the open alerts as before. */
const badge = computed(() =>
  unread.value
    ? { count: unread.value, tone: 'bg-red' }
    : alertCount.value
      ? { count: alertCount.value, tone: urgent.value ? 'bg-red' : 'bg-coral' }
      : null,
)
const bellLabel = computed(() =>
  t('notifications.bellLabel', { unread: unread.value, alerts: alertCount.value }),
)

function toggle(): void {
  open.value = !open.value
  // What is new first: unread notifications, otherwise the alerts if there are some.
  if (open.value) tab.value = unread.value || !alertCount.value ? 'notifications' : 'alerts'
}

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
async function openNotification(item: AppNotification): Promise<void> {
  if (!item.read) void markRead.mutateAsync(item.id).catch(() => undefined)
  open.value = false
  if (item.url) await router.push(item.url).catch(() => undefined)
}
async function readAll(): Promise<void> {
  try {
    await markRead.mutateAsync('all')
  } catch (error) {
    toast.error(toApiError(error).message)
  }
}
const when = (iso: string) => {
  const value = ago(iso)
  return t(`notifications.ago.${value.key}`, { n: value.n, date: value.date })
}
</script>

<template>
  <div ref="root" class="relative" @keydown="onKeydown">
    <button
      ref="button"
      type="button"
      class="relative inline-flex size-10 items-center justify-center rounded-[10px] border border-line-2 bg-surface text-ink-2 hover:bg-surface-2"
      :aria-label="bellLabel"
      :aria-expanded="open"
      :aria-controls="panelId"
      data-testid="alert-bell"
      @click="toggle"
    >
      <Bell class="size-[18px]" aria-hidden="true" />
      <span
        v-if="badge"
        class="num absolute -top-1.5 -right-1.5 min-w-[19px] rounded-full px-1 text-center text-[11px] leading-[19px] font-bold text-white ring-2 ring-surface"
        :class="badge.tone"
        aria-hidden="true"
        >{{ badge.count > 9 ? '9+' : badge.count }}</span
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
        class="absolute right-0 z-40 mt-2 w-[min(400px,calc(100vw-32px))] overflow-hidden rounded-wd-lg border border-line bg-surface shadow-wd-lg"
        :aria-label="t('notifications.panel')"
      >
        <div class="flex border-b border-line px-2 pt-2" role="tablist">
          <button
            v-for="key in ['notifications', 'alerts'] as const"
            :key="key"
            type="button"
            role="tab"
            class="relative flex flex-1 items-center justify-center gap-2 rounded-t-[10px] px-3 py-2.5 text-[14px] font-bold"
            :class="tab === key ? 'text-ink' : 'text-muted hover:text-ink'"
            :aria-selected="tab === key"
            @click="tab = key"
          >
            {{ key === 'notifications' ? t('notifications.title') : t('alerts.title') }}
            <span
              v-if="key === 'notifications' ? unread : alertCount"
              class="num min-w-[20px] rounded-full px-1.5 text-[11.5px] leading-[20px] text-white"
              :class="key === 'notifications' ? 'bg-red' : urgent ? 'bg-red' : 'bg-coral'"
              >{{ key === 'notifications' ? unread : alertCount }}</span
            >
            <span
              v-if="tab === key"
              class="absolute inset-x-3 bottom-0 h-[3px] rounded-t-full bg-violet"
              aria-hidden="true"
            />
          </button>
        </div>

        <!-- Notifications -->
        <template v-if="tab === 'notifications'">
          <header class="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
            <span class="text-[12.5px] font-semibold text-muted">{{
              t('notifications.subtitle')
            }}</span>
            <button
              v-if="unread"
              type="button"
              class="inline-flex items-center gap-1 rounded-[8px] px-2 py-1 text-[12.5px] font-bold text-violet hover:bg-violet-soft"
              @click="readAll"
            >
              <CheckCheck class="size-[15px]" aria-hidden="true" />{{ t('notifications.readAll') }}
            </button>
          </header>
          <div v-if="inbox.isPending.value" class="p-4"><div class="skeleton h-16" /></div>
          <p v-else-if="!notifications.length" class="flex items-center gap-2 px-4 py-6 text-muted">
            <Check class="size-[18px] text-green" aria-hidden="true" />{{
              t('notifications.empty')
            }}
          </p>
          <ul
            v-else
            class="max-h-[min(440px,70vh)] divide-y divide-line overflow-y-auto"
            aria-live="polite"
          >
            <li v-for="item in notifications" :key="item.id">
              <button
                type="button"
                class="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-surface-2"
                :class="!item.read && 'bg-violet-soft/40'"
                @click="openNotification(item)"
              >
                <span
                  class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-[9px]"
                  :class="item.read ? 'bg-surface-2 text-muted' : 'bg-violet-soft text-violet'"
                >
                  <component :is="kindIcon(item.kind)" class="size-[16px]" aria-hidden="true" />
                </span>
                <span class="min-w-0 flex-1">
                  <span
                    class="block text-[14px] leading-snug"
                    :class="item.read ? 'font-semibold text-ink-2' : 'font-bold text-ink'"
                    >{{ item.title }}</span
                  >
                  <span v-if="item.body" class="block text-[12.5px] leading-snug text-ink-2">{{
                    item.body
                  }}</span>
                  <span class="mt-0.5 block text-[11.5px] text-muted">{{
                    when(item.createdAt)
                  }}</span>
                </span>
                <span
                  v-if="!item.read"
                  class="mt-2 size-2.5 shrink-0 rounded-full bg-violet"
                  :aria-label="t('notifications.unreadMark')"
                />
              </button>
            </li>
          </ul>
        </template>

        <!-- Alerts -->
        <template v-else>
          <header
            class="flex items-baseline justify-between gap-3 border-b border-line px-4 py-2.5"
          >
            <span class="text-[12.5px] font-semibold text-muted">{{ t('alerts.subtitle') }}</span>
          </header>
          <div v-if="alerts.isPending.value" class="p-4"><div class="skeleton h-16" /></div>
          <p v-else-if="!rows.length" class="flex items-center gap-2 px-4 py-6 text-muted">
            <Check class="size-[18px] text-green" aria-hidden="true" />{{ t('alerts.empty') }}
          </p>
          <ul
            v-else
            class="max-h-[min(440px,70vh)] divide-y divide-line overflow-y-auto"
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
        </template>
      </section>
    </Transition>
  </div>
</template>
