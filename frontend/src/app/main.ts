import '@/design/main.css'

import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import { configureApi } from '@/api/client'
import { useToast } from '@/composables/useToast'
import { i18n } from '@/i18n'
import { setupOffline } from '@/offline'
import { useSessionStore } from '@/stores/session'

import App from './App.vue'
import { setupPwa } from './pwa'
import { router } from './router'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
    // Offline mode: a change is tried even without network, so that it waits on the device
    // (`offline/queue.ts`) instead of staying paused and lost at the next reload.
    mutations: { networkMode: 'always' },
  },
})

const pinia = createPinia()
const app = createApp(App).use(pinia).use(i18n).use(VueQueryPlugin, { queryClient })

const session = useSessionStore(pinia)
configureApi({
  organizationSlug: () => session.currentOrganization?.slug ?? null,
  onSessionExpired: () => {
    if (!session.isAuthenticated) return
    session.clear()
    queryClient.clear()
    useToast().info(i18n.global.t('shell.sessionExpired'))
    const current = router.currentRoute.value
    void router.push({ name: 'login', query: { redirect: current.fullPath } })
  },
})

app.use(router).mount('#app')
// Installable app and Web Push (feedback 13/11/2026).
setupPwa(queryClient)
// Offline mode (feedback 20/11/2026): data already seen, changes sent when the network is back.
setupOffline(queryClient, router, session)
