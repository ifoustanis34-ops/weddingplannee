import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { api } from '@/api/client'
import { reservationsApi, useReservationMutation } from '@/modules/reservations/api'
import type { ReservationStatus } from '@/modules/reservations/types'

/** Kinds of the centralized calendar (reservations-stock.md §4.3), in the order of a day. */
export const KINDS = [
  'event',
  'delivery',
  'setup',
  'teardown',
  'pickup',
  'return',
  'maintenance',
  'payment',
  'task',
] as const
export type CalendarKind = (typeof KINDS)[number]

export interface CalendarItem {
  kind: CalendarKind
  id: string
  date: string
  /** Last day of a multi-day item (event over several days, maintenance). */
  endDate: string | null
  time: string | null
  title: string
  subtitle: string
  status: ReservationStatus | null
  team: string[]
  owner: string | null
  vehicle: string
  wedding: string | null
  reservation: string | null
  contract: string | null
  item: string | null
  amount: number | null
  /** The signed-in member may drag it (reservation not out yet, owner or planner). */
  movable: boolean
}

export interface CalendarFilters {
  from: string
  to: string
  member: string
  kinds: CalendarKind[]
  status: string
}

export const calendarApi = {
  items: (filters: CalendarFilters) =>
    api
      .get<CalendarItem[]>('/calendar', {
        params: {
          from: filters.from,
          to: filters.to,
          member: filters.member || undefined,
          // Every kind = no filter (shorter address, same answer).
          kinds: filters.kinds.length < KINDS.length ? filters.kinds.join(',') : undefined,
          statuses: filters.status || undefined,
        },
      })
      .then((r) => r.data),
}

export function useCalendar(filters: MaybeRefOrGetter<CalendarFilters>) {
  return useQuery({
    queryKey: computed(() => ['calendar', { ...toValue(filters) }]),
    queryFn: () => calendarApi.items(toValue(filters)),
    placeholderData: keepPreviousData,
    enabled: computed(() => toValue(filters).kinds.length > 0),
  })
}

/** Drag in the calendar: every date of the reservation shifts, the stock is checked again. */
export const useMoveReservation = () =>
  useReservationMutation(({ id, days }: { id: string; days: number }) =>
    reservationsApi.move(id, days),
  )
