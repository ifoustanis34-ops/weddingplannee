import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { type MaybeRefOrGetter, computed, toValue } from 'vue'

import { api } from '@/api/client'

import type {
  Reservation,
  ReservationInput,
  ReservationRow,
  ReservationStats,
  Shortage,
} from './types'

export interface ReservationFilters {
  tab?: string
  kind?: string
  owner?: string
  client?: string
  from?: string
  to?: string
  search?: string
}

export const reservationKeys = {
  all: ['reservations'] as const,
  list: (filters: ReservationFilters) => [...reservationKeys.all, 'list', filters] as const,
  detail: (id: string) => [...reservationKeys.all, 'detail', id] as const,
  shortages: (id: string) => [...reservationKeys.all, 'shortages', id] as const,
  stats: () => [...reservationKeys.all, 'stats'] as const,
}

const clean = (filters: ReservationFilters) =>
  Object.fromEntries(Object.entries(filters).filter(([, v]) => v && v !== 'all'))

export const reservationsApi = {
  list: (filters: ReservationFilters) =>
    api.get<ReservationRow[]>('/reservations', { params: clean(filters) }).then((r) => r.data),
  get: (id: string) => api.get<Reservation>(`/reservations/${id}`).then((r) => r.data),
  create: (input: ReservationInput) =>
    api.post<Reservation>('/reservations', input).then((r) => r.data),
  update: (id: string, input: Partial<ReservationInput>) =>
    api.patch<Reservation>(`/reservations/${id}`, input).then((r) => r.data),
  move: (id: string, days: number) =>
    api.post<Reservation>(`/reservations/${id}/move`, { days }).then((r) => r.data),
  confirm: (id: string) => api.post<Reservation>(`/reservations/${id}/confirm`).then((r) => r.data),
  status: (id: string, status: string) =>
    api.post<Reservation>(`/reservations/${id}/status`, { status }).then((r) => r.data),
  checkout: (id: string, quantities: Record<string, number>) =>
    api.post<Reservation>(`/reservations/${id}/checkout`, { quantities }).then((r) => r.data),
  return: (
    id: string,
    lines: Record<string, { returned: number; damaged: number; missing: number }>,
  ) => api.post<Reservation>(`/reservations/${id}/return`, { lines }).then((r) => r.data),
  cancel: (id: string, reason: string) =>
    api.post<Reservation>(`/reservations/${id}/cancel`, { reason }).then((r) => r.data),
  pay: (
    id: string,
    input: { amount: number; method: string; paidAt: string; reference: string; kind: string },
  ) => api.post<Reservation>(`/reservations/${id}/payments`, input).then((r) => r.data),
  settleSecurity: (id: string, input: { retained: number; method: string; reason: string }) =>
    api.post<Reservation>(`/reservations/${id}/security`, input).then((r) => r.data),
  cancelPayment: (id: string, reason: string) =>
    api.post(`/reservation-payments/${id}/cancel`, { reason }).then((r) => r.data),
  shortages: (id: string) =>
    api.get<Shortage[]>(`/reservations/${id}/shortages`).then((r) => r.data),
  stats: () => api.get<ReservationStats>('/reservations/stats').then((r) => r.data),
}

export function useReservations(filters: MaybeRefOrGetter<ReservationFilters>) {
  return useQuery({
    queryKey: computed(() => reservationKeys.list({ ...toValue(filters) })),
    queryFn: () => reservationsApi.list(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

export function useReservation(id: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => reservationKeys.detail(toValue(id) ?? '')),
    queryFn: () => reservationsApi.get(toValue(id)!),
    enabled: computed(() => Boolean(toValue(id))),
  })
}

export const useReservationStats = () =>
  useQuery({ queryKey: reservationKeys.stats(), queryFn: reservationsApi.stats })

/** Any reservation change: lists, stock, dashboard and alerts follow. */
export function useReservationMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      if (result && typeof result === 'object' && 'id' in result)
        queryClient.setQueryData(reservationKeys.detail(String(result.id)), result)
      for (const key of [
        reservationKeys.all,
        ['stock'],
        ['dashboard'],
        ['alerts'],
        ['clients'],
        ['calendar'],
      ])
        void queryClient.invalidateQueries({ queryKey: key })
    },
  })
}

/** Live availability of items over a period (« 180 disponibles sur 250 »), own lines aside. */
export function useAvailability(
  params: MaybeRefOrGetter<{ from: string; to: string; exclude?: string | null } | null>,
) {
  return useQuery({
    queryKey: computed(() => ['stock', 'availability', toValue(params)]),
    queryFn: () =>
      api
        .get<{
          items: {
            item: string
            total: number
            available: number
            reserved: number
            out: number
            maintenance: number
          }[]
        }>('/availability', {
          params: { ...toValue(params), exclude: toValue(params)?.exclude || undefined },
        })
        .then((r) => r.data),
    enabled: computed(() => Boolean(toValue(params)?.from && toValue(params)?.to)),
    placeholderData: keepPreviousData,
  })
}
