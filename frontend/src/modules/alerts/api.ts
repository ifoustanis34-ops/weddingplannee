import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import { api } from '@/api/client'
import { useSessionStore } from '@/stores/session'

/** Internal alert (reservations-stock.md §2, §5.4): for the team, never sent to clients. */
export interface Alert {
  id: string
  kind:
    | 'overdue_payment'
    | 'overdue_invoice'
    | 'late_tasks'
    | 'wedding_unready'
    | 'below_threshold'
    | 'maintenance_late'
    | 'damaged_unit'
    | 'stock_shortage'
    | 'late_return'
  severity: 'critical' | 'serious' | 'warning'
  title: string
  subtitle?: string
  /** Day of the situation (due date, oldest late task, wedding day). */
  date: string | null
  since?: string
  amount?: number
  days?: number | null
  count?: number
  contract?: string
  wedding?: string
  item?: string
  reservation?: string
  available?: number
  threshold?: number
}

export const alertKeys = { all: ['alerts'] as const }

export const alertsApi = {
  list: () => api.get<{ count: number; results: Alert[] }>('/alerts').then((r) => r.data),
  dismiss: (id: string) => api.post<Alert>(`/alerts/${id}/dismiss`).then((r) => r.data),
}

/** Open alerts the role may see; the bell polls every minute. */
export function useAlerts() {
  const session = useSessionStore()
  return useQuery({
    queryKey: computed(() => [...alertKeys.all, session.currentOrganization?.slug]),
    queryFn: alertsApi.list,
    enabled: computed(() => Boolean(session.currentOrganization)),
    refetchInterval: 60_000,
  })
}

/** « Marquer comme traitée »: the bell and the dashboard drop it at once. */
export function useDismissAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: alertsApi.dismiss,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: alertKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
