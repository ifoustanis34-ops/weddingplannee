import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'

import type { Role, Session } from '@/api/auth'
import { api } from '@/api/client'
import { useSessionStore } from '@/stores/session'

/** Presentation mode (feedback 16/11/2026): open only on the demo agencies (server decides). */
export const demoApi = {
  config: () => api.get<{ enabled: boolean; roles: Role[] }>('/demo/config').then((r) => r.data),
  switchRole: (role: Role) => api.post<Session>('/demo/switch', { role }).then((r) => r.data),
}

export function useDemoConfig() {
  const session = useSessionStore()
  return useQuery({
    queryKey: computed(() => ['demo-config', session.currentOrganization?.slug]),
    queryFn: demoApi.config,
    enabled: computed(() => Boolean(session.currentOrganization)),
    staleTime: 5 * 60_000,
  })
}
