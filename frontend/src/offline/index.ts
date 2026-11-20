import type { QueryClient } from '@tanstack/vue-query'
import { watch } from 'vue'
import type { Router } from 'vue-router'

import { configureApi } from '@/api/client'
import { useToast } from '@/composables/useToast'
import { i18n } from '@/i18n'
import type { useSessionStore } from '@/stores/session'

import { forgetCaches, startCache, stopCache } from './cache'
import { canQueue, enqueue, flush, onQueueSynced, online, setUser, watchNetwork } from './queue'

/**
 * Offline mode (feedback 20/11/2026):
 * - what was already seen stays readable (`cache.ts`), the screens open without network once
 *   visited or preloaded (`public/sw.js` keeps the app and its pages);
 * - changes made without connection wait on the device (`queue.ts`) and leave by themselves when
 *   the network is back, then every screen refreshes.
 */
export function setupOffline(
  queryClient: QueryClient,
  router: Router,
  session: ReturnType<typeof useSessionStore>,
): void {
  watchNetwork()
  configureApi({
    onNetworkError: (config, slug) => {
      if (!canQueue(config)) return false
      enqueue(config, slug)
      return true
    },
  })
  onQueueSynced((count) => {
    void queryClient.invalidateQueries()
    useToast().success(i18n.global.t('offline.synced', { count }, count))
  })

  let signedIn = false
  watch(
    () => [session.user?.id ?? null, session.currentSlug] as const,
    ([userId, slug]) => {
      setUser(userId)
      if (userId) {
        signedIn = true
        void startCache(queryClient, userId, slug)
      } else if (signedIn && session.status === 'anonymous') {
        signedIn = false
        void forgetCaches()
      } else {
        stopCache()
      }
    },
    { immediate: true },
  )

  // Opened without network from the saved session: confirm it with the server once back.
  watch(online, (isOnline) => {
    if (!isOnline) return
    if (session.offline) void session.refresh().catch(() => undefined)
    void flush()
  })

  if (!import.meta.env.DEV) preloadPages(router)
}

/** Loads every screen of the app in the background so that they open offline too. */
function preloadPages(router: Router): void {
  const later = (callback: () => void) =>
    'requestIdleCallback' in window
      ? window.requestIdleCallback(callback)
      : setTimeout(callback, 3000)
  later(() => {
    if (!navigator.onLine) return
    for (const route of router.getRoutes()) {
      const component = route.components?.default
      if (typeof component === 'function') {
        void (component as () => Promise<unknown>)().catch(() => undefined)
      }
    }
  })
}
