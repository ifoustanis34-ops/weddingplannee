import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { type MaybeRefOrGetter, computed, toValue } from 'vue'

import { api } from '@/api/client'
import type { Alert } from '@/modules/alerts/api'

/** reservations-stock.md §8. Every amount is null for a role that must not see it (§12). */
export type PeriodKey = 'today' | 'week' | 'month' | 'quarter' | 'year' | 'custom'

export interface PeriodRequest {
  period: PeriodKey
  from?: string
  to?: string
}

export interface PlanningItem {
  kind: 'event' | 'task' | 'payment' | 'delivery' | 'setup' | 'pickup' | 'return'
  time?: string
  reservation?: string
  id: string
  title: string
  subtitle: string
  team: string[]
  amount?: number
  wedding?: string
  contract?: string
}

/** Same alerts as the bell (`/alerts`), already filtered by role. */
export type DashboardAlert = Alert

export interface MonthRow {
  month: string
  label: string
  revenue: number
  income: number
  expenses: number | null
  profit: number | null
}

export interface DashboardSummary {
  period: {
    key: PeriodKey
    start: string
    end: string
    previousStart: string
    previousEnd: string
  }
  isNew: boolean
  today: {
    date: string
    weddingsToday: number
    weddingsWeek: number
    tasksToday: number
    paymentsToday: number | null
    deliveriesToday: number
    returnsToday: number
    eventsToday: number
  }
  signature: {
    revenue: number
    revenueVariation: number | null
    collected: number
    toCollect: number
    profit: number | null
    profitVariation: number | null
  } | null
  performance: {
    utilisation: number | null
    utilisationDelta: number | null
    marginAvg: number | null
    marginAvgDelta: number | null
    basketAvg: number | null
    basketAvgVariation: number | null
    quoteConfirmation: number | null
    quoteConfirmationDelta: number | null
    collectionRate: number | null
    collectionRateDelta: number | null
  } | null
  orders: { confirmed: number; pending: number; cancelled: number }
  topServices: { name: string; count: number; revenue: number | null }[]
  /** « Matériel aujourd'hui »: quantities per category (no amounts, every role). */
  materialToday: {
    available: number
    categories: {
      name: string
      available: number
      reserved: number
      out: number
      maintenance: number
    }[]
  }
  upcomingWeddings: {
    id: string
    title: string
    date: string | null
    days: number | null
    venue: string
    progress: number
    tasksTotal: number
  }[]
  monthly: MonthRow[] | null
  expensesByCategory:
    { id: string | null; name: string | null; slot: number; amount: number }[] | null
  balances:
    | {
        contract: string | null
        reservation: string | null
        number: string
        clientName: string
        balance: number
        dueDate: string | null
        isOverdue: boolean
      }[]
    | null
  planning: { date: string; items: PlanningItem[] }[]
  alerts: DashboardAlert[]
  teamToday: {
    name: string
    total: number
    done: number
    status: 'done' | 'in_progress' | 'todo' | 'absent'
    late?: boolean
  }[]
  starter: { catalogItems: number; clients: number; hasLogo: boolean; teamMembers: number }
}

export function useDashboard(request: MaybeRefOrGetter<PeriodRequest>) {
  return useQuery({
    queryKey: computed(() => ['dashboard', { ...toValue(request) }]),
    queryFn: () =>
      api
        .get<DashboardSummary>('/dashboard/summary', { params: toValue(request) })
        .then((r) => r.data),
    // Changing the period keeps the previous figures (dimmed) instead of flashing skeletons.
    placeholderData: keepPreviousData,
    refetchInterval: 120_000,
  })
}
