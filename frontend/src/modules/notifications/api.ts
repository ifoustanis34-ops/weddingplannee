import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import { api } from '@/api/client'
import { useSessionStore } from '@/stores/session'

/**
 * The person's notifications (feedback 17/11/2026: like WhatsApp — every event of the flow, an
 * unread count on the bell, the app icon and the tab title). Fresh in real time: a push refreshes
 * it at once (`app/pwa.ts`), and it is read again every 10 s and when the tab comes back.
 */
export interface AppNotification {
  id: string
  kind: string
  title: string
  body: string
  url: string
  read: boolean
  createdAt: string
}
export interface Inbox {
  results: AppNotification[]
  /** Unread in this space (the bell). */
  unread: number
  /** Unread over every space (the app icon: one per device). */
  unreadAll: number
}

export const notificationKeys = { all: ['notifications'] as const }

export const notificationsApi = {
  list: () => api.get<Inbox>('/notifications').then((r) => r.data),
  read: (id: string) => api.post(`/notifications/${id}/read`).then(() => undefined),
  readAll: () => api.post('/notifications/read-all').then(() => undefined),
}

export function useInbox() {
  const session = useSessionStore()
  return useQuery({
    queryKey: computed(() => [...notificationKeys.all, session.currentOrganization?.slug]),
    queryFn: notificationsApi.list,
    enabled: computed(() => Boolean(session.currentOrganization && session.isAuthenticated)),
    refetchInterval: 10_000,
    refetchOnWindowFocus: true,
  })
}

export function useMarkRead() {
  const queryClient = useQueryClient()
  return useMutation({
    // An id, or « all » to read everything.
    mutationFn: (id: string) =>
      id === 'all' ? notificationsApi.readAll() : notificationsApi.read(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
  })
}
